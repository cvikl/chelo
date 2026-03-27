"""Fetch real Sentinel-2 L2A tiles from Element84 Earth Search (free, no auth)."""

import numpy as np
import httpx
import rasterio
from pyproj import Transformer

STAC_URL = "https://earth-search.aws.element84.com/v1/search"

BAND_KEYS = [
    "coastal", "blue", "green", "red", "rededge1", "rededge2",
    "rededge3", "nir", "nir08", "nir09", "swir16", "swir22",
]


async def search_tile(lat: float, lon: float, date_start: str, date_end: str, max_cloud: int = 20):
    """Search for a Sentinel-2 L2A tile covering the given point and date range."""
    # Prefer summer months for glacier visibility (less seasonal snow)
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
        return features[0]  # lowest cloud cover


def fetch_patch(item: dict, lat: float, lon: float, size: int = 256, extent_m: float = 5000) -> np.ndarray:
    """
    Fetch a SIZE x SIZE patch of all 12 spectral bands + 4 indices = 16 channels.
    Returns numpy array of shape (16, SIZE, SIZE), normalized.
    """
    ref_url = item["assets"]["blue"]["href"]
    with rasterio.open(ref_url) as src:
        transformer = Transformer.from_crs("EPSG:4326", str(src.crs), always_xy=True)
        cx, cy = transformer.transform(lon, lat)
        half = extent_m / 2
        bbox = (cx - half, cy - half, cx + half, cy + half)

    bands = []
    for key in BAND_KEYS:
        url = item["assets"][key]["href"]
        with rasterio.open(url) as src:
            window = rasterio.windows.from_bounds(*bbox, transform=src.transform)
            data = src.read(1, window=window, out_shape=(size, size)).astype(np.float32)
            bands.append(data)

    stack = np.stack(bands, axis=0)  # (12, H, W)

    # Compute 4 spectral indices
    green, red, nir, swir16, nir08 = stack[2], stack[3], stack[7], stack[10], stack[8]
    eps = 1e-6
    ndsi = (green - swir16) / (green + swir16 + eps)
    ndvi = (nir - red) / (nir + red + eps)
    ndwi = (green - nir) / (green + nir + eps)
    ndmi = (nir08 - swir16) / (nir08 + swir16 + eps)

    stack16 = np.concatenate([stack, ndsi[None], ndvi[None], ndwi[None], ndmi[None]], axis=0)

    # Normalize spectral bands (L2A values are reflectance * 10000)
    stack16[:12] = stack16[:12] / 10000.0

    return stack16
