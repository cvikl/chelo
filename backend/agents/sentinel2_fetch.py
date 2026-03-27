"""
Fetch real Sentinel-2 L2A tiles + Copernicus DEM from Element84 Earth Search (free, no auth).

DL4GAM 16-band order:
  1-13: S2 bands B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B10,B11,B12 (reflectance 0-1)
  14:   DEM elevation (metres)
  15:   dh/dt elevation change rate (m/yr) — filled with zeros if unavailable
  16:   Slope (degrees 0-90, derived from DEM)
"""

import numpy as np
import httpx
import rasterio
from pyproj import Transformer

STAC_URL = "https://earth-search.aws.element84.com/v1/search"

# Element84 asset keys mapped to DL4GAM band order
S2_BAND_KEYS = [
    "coastal",   # B01
    "blue",      # B02
    "green",     # B03
    "red",       # B04
    "rededge1",  # B05
    "rededge2",  # B06
    "rededge3",  # B07
    "nir",       # B08
    "nir08",     # B8A
    "nir09",     # B09
    # B10 (cirrus) is not in L2A — we'll fill with zeros
    "swir16",    # B11
    "swir22",    # B12
]


async def search_tile(lat: float, lon: float, date_start: str, date_end: str, max_cloud: int = 20):
    """Search for a Sentinel-2 L2A tile covering the given point and date range."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(STAC_URL, json={
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": f"{date_start}T00:00:00Z/{date_end}T23:59:59Z",
            "limit": 5,
            "query": {"eo:cloud_cover": {"lt": max_cloud}},
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        })
        data = resp.json()
        features = data.get("features", [])
        if not features:
            return None
        return features[0]


async def search_dem_tile(lat: float, lon: float):
    """Search for a Copernicus DEM tile covering the given point."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(STAC_URL, json={
            "collections": ["cop-dem-glo-30"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "limit": 1,
        })
        data = resp.json()
        features = data.get("features", [])
        return features[0] if features else None


def _compute_slope(dem: np.ndarray, pixel_size_m: float) -> np.ndarray:
    """Compute terrain slope in degrees from a DEM array."""
    dy, dx = np.gradient(dem, pixel_size_m)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    return np.degrees(slope_rad).astype(np.float32)


def fetch_patch(item: dict, lat: float, lon: float, size: int = 256, extent_m: float = 5000,
                dem_item: dict = None) -> np.ndarray:
    """
    Fetch a SIZE x SIZE patch with 16 channels matching DL4GAM spec.

    Channels 1-13: Sentinel-2 bands (reflectance 0-1)
    Channel 14: DEM elevation (metres)
    Channel 15: dh/dt (zeros — no external source available)
    Channel 16: Slope (degrees)
    """
    # Get UTM bounding box
    ref_url = item["assets"]["blue"]["href"]
    with rasterio.open(ref_url) as src:
        crs = str(src.crs)
        transformer = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        cx, cy = transformer.transform(lon, lat)
        half = extent_m / 2
        bbox = (cx - half, cy - half, cx + half, cy + half)

    # Read 12 available spectral bands (B10/cirrus missing from L2A)
    bands = []
    for key in S2_BAND_KEYS:
        url = item["assets"][key]["href"]
        with rasterio.open(url) as src:
            window = rasterio.windows.from_bounds(*bbox, transform=src.transform)
            data = src.read(1, window=window, out_shape=(size, size)).astype(np.float32)
            bands.append(data / 10000.0)  # Convert to reflectance 0-1

    # Insert B10 (cirrus) as zeros at index 10
    b10_zeros = np.zeros((size, size), dtype=np.float32)
    bands.insert(10, b10_zeros)  # Now we have 13 bands in correct order

    spectral = np.stack(bands, axis=0)  # (13, H, W)

    # DEM and slope
    if dem_item is not None:
        try:
            dem_url = dem_item["assets"]["data"]["href"]
            with rasterio.open(dem_url) as src:
                # DEM is in EPSG:4326, need to read in the right bbox
                inv_transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                lon_min, lat_min = inv_transformer.transform(bbox[0], bbox[1])
                lon_max, lat_max = inv_transformer.transform(bbox[2], bbox[3])
                dem_bbox = (lon_min, lat_min, lon_max, lat_max)
                window = rasterio.windows.from_bounds(*dem_bbox, transform=src.transform)
                dem = src.read(1, window=window, out_shape=(size, size)).astype(np.float32)
            pixel_size = extent_m / size
            slope = _compute_slope(dem, pixel_size)
        except Exception:
            dem = np.zeros((size, size), dtype=np.float32)
            slope = np.zeros((size, size), dtype=np.float32)
    else:
        dem = np.zeros((size, size), dtype=np.float32)
        slope = np.zeros((size, size), dtype=np.float32)

    dhdt = np.zeros((size, size), dtype=np.float32)

    # Stack all 16 channels
    stack16 = np.concatenate([
        spectral,       # 13 bands
        dem[None],      # DEM
        dhdt[None],     # dh/dt
        slope[None],    # slope
    ], axis=0)  # (16, H, W)

    return stack16
