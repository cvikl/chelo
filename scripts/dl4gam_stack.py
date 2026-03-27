"""
DL4GAM GeoTIFF Stack Builder  –  16-band edition
==================================================
Produces a 16-band Float32 GeoTIFF that matches exactly what the pre-trained
DL4GAM checkpoint was trained on (Diaconu et al., 2024).

Band order (checkpoint-mandated, matches main.py INPUT_SETTINGS):
  1   B1   Sentinel-2 Band 1  – Coastal aerosol  (443 nm)  reflectance [0–1]
  2   B2   Sentinel-2 Band 2  – Blue             (490 nm)  reflectance [0–1]
  3   B3   Sentinel-2 Band 3  – Green            (560 nm)  reflectance [0–1]
  4   B4   Sentinel-2 Band 4  – Red              (665 nm)  reflectance [0–1]
  5   B5   Sentinel-2 Band 5  – Red Edge 1       (705 nm)  reflectance [0–1]
  6   B6   Sentinel-2 Band 6  – Red Edge 2       (740 nm)  reflectance [0–1]
  7   B7   Sentinel-2 Band 7  – Red Edge 3       (783 nm)  reflectance [0–1]
  8   B8   Sentinel-2 Band 8  – NIR              (842 nm)  reflectance [0–1]
  9   B8A  Sentinel-2 Band 8A – Narrow NIR       (865 nm)  reflectance [0–1]
 10   B9   Sentinel-2 Band 9  – Water vapour     (945 nm)  reflectance [0–1]
 11   B10  Sentinel-2 Band 10 – SWIR-Cirrus      (1375 nm) reflectance [0–1]
 12   B11  Sentinel-2 Band 11 – SWIR 1           (1610 nm) reflectance [0–1]
 13   B12  Sentinel-2 Band 12 – SWIR 2           (2190 nm) reflectance [0–1]
 14   DEM  Copernicus GLO-30 elevation            metres
 15   DHDT Elevation change rate                  m yr⁻¹  (external raster)
 16   SLOPE Terrain slope derived from DEM        degrees [0–90]
"""

import json
import math
import getpass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ─────────────────────────────────────────────
#  CONFIG 
# ─────────────────────────────────────────────
CONFIG = {
    # Bounding box [lon_min, lat_min, lon_max, lat_max]
    # "bbox": [7.75, 45.92, 7.81, 45.96],
    "bbox": [14.40, 46.00, 14.60, 46.10],
    # Date window for Sentinel-2 search
    "date_from": (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d"),
    "date_to":   datetime.utcnow().strftime("%Y-%m-%d"),

    # Max cloud cover percentage (0-100)
    "max_cloud_cover": 20,

    # Output resolution in metres — keep at 10 for DL4GAM compliance
    "resolution": 10,

    # Output directory
    "output_dir": "./dl4gam_output",

    # Copernicus credentials (leave empty to be prompted at runtime)
    "username": "",
    "password": "",

    # Path to an external dh/dt GeoTIFF (e.g. Hugonnet et al. 2021).
    # Download from https://doi.org/10.6096/13
    # Set to None to fill with zeros and receive a warning.
    "dhdt_path": None,   # e.g.  "/data/hugonnet_dhdt.tif"

    # Set to False to skip the debug overview PNG
    "save_overview": True,
}

# ── DL4GAM 16-band spec ───────────────────────────────────────────
# Exactly matches INPUT_SETTINGS in main.py and the checkpoint's first layer.
# Order is critical — do not rearrange.
BAND_ORDER = [
    # --- 13 Sentinel-2 spectral bands (bands_input) ---
    "B01",        # Coastal aerosol
    "B02",        # Blue
    "B03",        # Green
    "B04",        # Red
    "B05",        # Red Edge 1
    "B06",        # Red Edge 2
    "B07",        # Red Edge 3
    "B08",        # NIR (broad)
    "B8A",        # NIR (narrow)
    "B09",        # Water vapour
    "B10",        # SWIR-Cirrus
    "B11",        # SWIR 1
    "B12",        # SWIR 2
    # --- Auxiliary layers ---
    "DEM",        # Elevation (dem=True)
    "DHDT",       # dh/dt    (dhdt=True)
    "SLOPE",      # Slope    (dem_features=['slope'])
]

BAND_DESCRIPTIONS = {
    "B01":  "Coastal aerosol (443 nm) – Surface Reflectance [0–1]",
    "B02":  "Blue (490 nm) – Surface Reflectance [0–1]",
    "B03":  "Green (560 nm) – Surface Reflectance [0–1]",
    "B04":  "Red (665 nm) – Surface Reflectance [0–1]",
    "B05":  "Red Edge 1 (705 nm) – Surface Reflectance [0–1]",
    "B06":  "Red Edge 2 (740 nm) – Surface Reflectance [0–1]",
    "B07":  "Red Edge 3 (783 nm) – Surface Reflectance [0–1]",
    "B08":  "NIR broad (842 nm) – Surface Reflectance [0–1]",
    "B8A":  "NIR narrow (865 nm) – Surface Reflectance [0–1]",
    "B09":  "Water vapour (945 nm) – Surface Reflectance [0–1]",
    "B10":  "SWIR-Cirrus (1375 nm) – Surface Reflectance [0–1]",
    "B11":  "SWIR 1 (1610 nm) – Surface Reflectance [0–1]",
    "B12":  "SWIR 2 (2190 nm) – Surface Reflectance [0–1]",
    "DEM":  "Elevation – Copernicus GLO-30 [metres]",
    "DHDT": "Elevation change rate dh/dt [m yr⁻¹]",
    "SLOPE":"Terrain slope derived from DEM [degrees 0–90]",
}

# Sentinel-2 band names as understood by the SentinelHub evalscript API
# B8A requires special handling (no leading zero in the API name)
S2_API_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06",
                 "B07", "B08", "B8A", "B09", "B10", "B11", "B12"]

CDSE_AUTH_URL    = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_ODATA_URL   = "https://catalogue.dataspace.copernicus.eu/odata/v1"
CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"


# ─────────────────────────────────────────────
#  AUTHENTICATION
# ─────────────────────────────────────────────

def get_access_token(username: str, password: str) -> str:
    resp = requests.post(
        CDSE_AUTH_URL,
        data={
            "grant_type": "password",
            "client_id":  "cdse-public",
            "username":   username,
            "password":   password,
        },
        timeout=30,
    )
    resp.raise_for_status()
    print("✓  Authenticated with Copernicus Data Space")
    return resp.json()["access_token"]


# ─────────────────────────────────────────────
#  CATALOGUE SEARCH
# ─────────────────────────────────────────────

def search_products(bbox, date_from, date_to, max_cloud) -> list:
    lon_min, lat_min, lon_max, lat_max = bbox
    wkt = (f"POLYGON(({lon_min} {lat_min},{lon_max} {lat_min},"
           f"{lon_max} {lat_max},{lon_min} {lat_max},{lon_min} {lat_min}))")
    params = {
        "$filter": (
            f"Collection/Name eq 'SENTINEL-2' and "
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
            f"  and att/OData.CSC.DoubleAttribute/Value le {max_cloud}) and "
            f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
            f"  and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and "
            f"ContentDate/Start gt {date_from}T00:00:00.000Z and "
            f"ContentDate/Start lt {date_to}T23:59:59.000Z and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')"
        ),
        "$orderby": "ContentDate/Start desc",
        "$top": 5,
    }
    resp = requests.get(f"{CDSE_ODATA_URL}/Products", params=params, timeout=30)
    resp.raise_for_status()
    products = resp.json().get("value", [])
    print(f"✓  Found {len(products)} product(s) in catalogue")
    return products


# ─────────────────────────────────────────────
#  EVALSCRIPTS
# ─────────────────────────────────────────────

def _evalscript_all_s2_bands() -> str:
    """
    Fetch 12 Sentinel-2 L2A bands in a single API call (omitting B10).
    Output order matches S2_API_BANDS: B01..B09, B11, B12 + B8A.
    All values are surface reflectance [0–1] as FLOAT32.
    """
    return """
//VERSION=3
function setup() {
  return {
    input: [{
      bands: ["B01","B02","B03","B04","B05","B06",
              "B07","B08","B8A","B09","B11","B12"],
      units: "REFLECTANCE"
    }],
    output: { bands: 12, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(s) {
  return [s.B01, s.B02, s.B03, s.B04, s.B05, s.B06,
          s.B07, s.B08, s.B8A, s.B09, s.B11, s.B12];
}
"""

def _evalscript_dem() -> str:
    """Fetch Copernicus GLO-30 DEM elevation in metres."""
    return """
//VERSION=3
function setup() {
  return {
    input:  [{ bands: ["DEM"] }],
    output: { bands: 1, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) { return [sample.DEM]; }
"""


# ─────────────────────────────────────────────
#  PIXEL DIMENSIONS HELPER
# ─────────────────────────────────────────────

def _pixel_dims(bbox, resolution):
    lon_min, lat_min, lon_max, lat_max = bbox
    mid_lat = (lat_min + lat_max) / 2
    m_per_deg_lon = 111_320 * math.cos(math.radians(mid_lat))
    m_per_deg_lat = 111_320
    width  = max(64, int((lon_max - lon_min) * m_per_deg_lon / resolution))
    height = max(64, int((lat_max - lat_min) * m_per_deg_lat / resolution))
    return width, height


# ─────────────────────────────────────────────
#  PROCESS API FETCH
# ─────────────────────────────────────────────

def _post_process(token: str, evalscript: str, data_block: list) -> np.ndarray:
    """
    Submit one Process API request and return the result as (n_bands, H, W) float32.
    """
    bbox = CONFIG["bbox"]
    lon_min, lat_min, lon_max, lat_max = bbox
    width, height = _pixel_dims(bbox, CONFIG["resolution"])

    payload = {
        "input": {
            "bounds": {
                "bbox": [lon_min, lat_min, lon_max, lat_max],
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": data_block,
        },
        "output": {
            "width":  width,
            "height": height,
            "responses": [{"identifier": "default",
                           "format":     {"type": "image/tiff"}}],
        },
        "evalscript": evalscript,
    }

    resp = requests.post(
        CDSE_PROCESS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Accept":        "image/tiff",
        },
        data=json.dumps(payload),
        timeout=180,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Process API error {resp.status_code}: {resp.text[:400]}"
        )

    with MemoryFile(resp.content) as mf, mf.open() as ds:
        return ds.read().astype(np.float32)   # (n_bands, H, W)


def fetch_s2_bands(token: str) -> np.ndarray:
    """
    Fetch all 13 Sentinel-2 bands in one call.
    Returns (13, H, W) float32 in order: B01..B12, B8A
    (matching S2_API_BANDS and BAND_ORDER positions 0–12).
    """
    data_block = [{
        "type": "sentinel-2-l2a",
        "dataFilter": {
            "timeRange": {
                "from": f"{CONFIG['date_from']}T00:00:00Z",
                "to":   f"{CONFIG['date_to']}T23:59:59Z",
            },
            "maxCloudCoverage": CONFIG["max_cloud_cover"],
            "mosaickingOrder": "leastCC",
        },
    }]
    arr = _post_process(token, _evalscript_all_s2_bands(), data_block)
    if arr.shape[0] != 12:
        raise RuntimeError(
            f"Expected 12 S2 bands from API, got {arr.shape[0]}"
        )
    
    # Sentinel-2 L2A does not include B10. We insert an all-zero band at index 10.
    # arr has indices 0-9 corresponding to B01-B09 (including B8A at index 8)
    # arr[9] is B09. So we insert after index 9
    b10 = np.zeros((1, arr.shape[1], arr.shape[2]), dtype=np.float32)
    s2_stack_with_b10 = np.concatenate([arr[:10], b10, arr[10:]], axis=0)

    print(f"  ✓  All 13 Sentinel-2 bands fetched/reconstructed  (shape {s2_stack_with_b10.shape})")
    return s2_stack_with_b10   # (13, H, W)


def fetch_dem(token: str) -> np.ndarray:
    """Fetch Copernicus GLO-30 DEM. Returns (1, H, W) float32."""
    data_block = [{
        "type": "dem",
        "dataFilter": {"demInstance": "COPERNICUS_30"},
    }]
    arr = _post_process(token, _evalscript_dem(), data_block)
    print(f"  ✓  DEM fetched  (shape {arr.shape})")
    return arr   # (1, H, W)


# ─────────────────────────────────────────────
#  TERRAIN DERIVATIONS  (from DEM)
# ─────────────────────────────────────────────

def _compute_slope(dem_arr: np.ndarray, pixel_size_m: float) -> np.ndarray:
    """
    Compute slope in degrees from a (H, W) DEM array.
    Uses central-difference gradients (same approach as GDAL gdaldem).
    Returns (H, W) float32, values in [0, 90].
    """
    dem_pad = np.pad(dem_arr, 1, mode="edge")
    dz_dx = (dem_pad[1:-1, 2:] - dem_pad[1:-1, :-2]) / (2 * pixel_size_m)
    dz_dy = (dem_pad[:-2, 1:-1] - dem_pad[2:, 1:-1]) / (2 * pixel_size_m)
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    return np.degrees(slope_rad).astype(np.float32)


# ─────────────────────────────────────────────
#  dh/dt EXTERNAL RASTER LOADER
# ─────────────────────────────────────────────

def load_dhdt(target_shape: tuple, target_transform, target_crs) -> np.ndarray:
    """
    Load a dh/dt GeoTIFF and reproject/resample it to match the target grid.
    Returns a (H, W) float32 array.
    Falls back to all-zeros with a warning if dhdt_path is None or missing.
    """
    height, width = target_shape
    dhdt_path = CONFIG.get("dhdt_path")

    if dhdt_path is None:
        print("  ⚠  dhdt_path not set — DHDT band will be all-zeros.\n"
              "     Download Hugonnet et al. (2021) from https://doi.org/10.6096/13\n"
              "     and set dhdt_path in CONFIG for best results.")
        return np.zeros((height, width), dtype=np.float32)

    src_path = Path(dhdt_path)
    if not src_path.exists():
        print(f"  ⚠  dh/dt file not found at {src_path} — using zeros.")
        return np.zeros((height, width), dtype=np.float32)

    with rasterio.open(src_path) as src:
        dest = np.zeros((height, width), dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=dest,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
        )
    print(f"  ✓  dh/dt loaded from {src_path.name}")
    return dest.astype(np.float32)


# ─────────────────────────────────────────────
#  PRIMARY OUTPUT: 16-BAND DL4GAM GeoTIFF
# ─────────────────────────────────────────────

def save_dl4gam_geotiff(s2_stack: np.ndarray, dem: np.ndarray,
                        out_dir: Path) -> Path:
    """
    Assemble and write the 16-band DL4GAM GeoTIFF.

    Band layout:
      0–12  : 13 Sentinel-2 bands  (from s2_stack, shape 13×H×W)
      13    : DEM elevation         (from dem, shape 1×H×W)
      14    : dh/dt                 (loaded from dhdt_path or zeros)
      15    : Slope                 (derived from DEM)

    Output spec:
      • Float32 throughout
      • LZW compressed, 256×256 tiled (cloud-optimised ready)
      • CRS: EPSG:4326 (WGS84)
      • Band descriptions embedded for GIS readability
    """
    _, height, width = s2_stack.shape
    lon_min, lat_min, lon_max, lat_max = CONFIG["bbox"]
    transform = from_bounds(lon_min, lat_min, lon_max, lat_max, width, height)
    crs = CRS.from_epsg(4326)

    # Derive slope from DEM
    dem_2d = dem[0]                                            # (H, W)
    slope   = _compute_slope(dem_2d, CONFIG["resolution"])     # (H, W)

    # Load dh/dt (external or zeros)
    dhdt = load_dhdt((height, width), transform, crs)          # (H, W)

    # Build full 16-band stack: (16, H, W)
    stack = np.concatenate([
        s2_stack,                       # bands 0–12  (13 × H × W)
        dem,                            # band  13    ( 1 × H × W)
        dhdt[np.newaxis, ...],          # band  14    ( 1 × H × W)
        slope[np.newaxis, ...],         # band  15    ( 1 × H × W)
    ], axis=0)

    assert stack.shape[0] == 16, f"Stack has {stack.shape[0]} bands, expected 16"

    path = out_dir / "test_16band_stack2.tif"
    with rasterio.open(
        path, "w",
        driver="GTiff",
        height=height,
        width=width,
        count=16,
        dtype="float32",
        crs=crs,
        transform=transform,
        compress="lzw",
        tiled=True,
        blockxsize=256,
        blockysize=256,
    ) as dst:
        for band_idx, key in enumerate(BAND_ORDER, start=1):
            dst.write(stack[band_idx - 1], band_idx)
            dst.set_band_description(band_idx, f"{key}: {BAND_DESCRIPTIONS[key]}")

    size_mb = path.stat().st_size / 1_048_576
    print(f"  → {path.name}  ({size_mb:.1f} MB, {width}×{height} px, 16 bands)")
    return path


# ─────────────────────────────────────────────
#  DEBUG OUTPUT: OVERVIEW PNG  (4 × 4 grid)
# ─────────────────────────────────────────────

COLORMAPS = {
    "B01":  ("Purples",  0,    0.15),
    "B02":  ("Blues",    0,    0.30),
    "B03":  ("Greens",   0,    0.30),
    "B04":  ("Reds",     0,    0.30),
    "B05":  ("YlOrRd",   0,    0.30),
    "B06":  ("YlOrRd",   0,    0.40),
    "B07":  ("YlOrRd",   0,    0.40),
    "B08":  ("YlGn",     0,    0.50),
    "B8A":  ("YlGn",     0,    0.50),
    "B09":  ("cool",     0,    0.20),
    "B10":  ("cool",     0,    0.10),
    "B11":  ("YlOrBr",   0,    0.50),
    "B12":  ("YlOrBr",   0,    0.40),
    "DEM":  ("terrain",  None, None),   # auto-scale
    "DHDT": ("RdBu",    -2,    2),
    "SLOPE":("hot_r",    0,   60),
}


def save_overview(stack_16: np.ndarray, out_dir: Path):
    """Write a 4×4 debug PNG of all 16 bands."""
    fig, axes = plt.subplots(
        4, 4, figsize=(28, 28), dpi=100,
        gridspec_kw={"hspace": 0.35, "wspace": 0.10},
    )
    for ax, (key, band_idx) in zip(axes.flatten(),
                                    [(k, i) for i, k in enumerate(BAND_ORDER)]):
        arr  = stack_16[band_idx]
        cmap, vmin, vmax = COLORMAPS[key]
        im = ax.imshow(
            arr, cmap=cmap,
            vmin=(vmin if vmin is not None else arr.min()),
            vmax=(vmax if vmax is not None else arr.max()),
            interpolation="bilinear",
        )
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        ax.set_title(f"Band {band_idx+1}: {key}\n{BAND_DESCRIPTIONS[key]}",
                     fontsize=7)
        ax.axis("off")

    fig.suptitle("DL4GAM Stack – Debug Overview (16 bands)", fontsize=14, y=1.01)
    path = out_dir / "overview.png"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  → overview.png  (debug, 16 bands, 4×4 grid)")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main(bbox=None, date_from=None, date_to=None):
    if bbox is not None:
        CONFIG["bbox"] = bbox
    if date_from is not None:
        CONFIG["date_from"] = date_from
    if date_to is not None:
        CONFIG["date_to"] = date_to

    username = CONFIG["username"] or input("Copernicus username (email): ").strip()
    password = CONFIG["password"] or getpass.getpass("Copernicus password: ")

    out_dir = Path(CONFIG["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    token = get_access_token(username, password)

    products = search_products(
        CONFIG["bbox"], CONFIG["date_from"],
        CONFIG["date_to"], CONFIG["max_cloud_cover"],
    )
    if not products:
        print("⚠  No products found. Widen the date range or raise max_cloud_cover.")
        return
    print(f"   Best match: {products[0].get('Name', 'unknown')}\n")

    # ── fetch all Sentinel-2 bands in one API call ──
    print("Fetching all 13 Sentinel-2 bands (single request)…")
    s2_stack = fetch_s2_bands(token)   # (13, H, W)

    # ── fetch DEM ──
    print("Fetching DEM…")
    dem = fetch_dem(token)             # (1, H, W)

    # ── assemble and write 16-band GeoTIFF ──
    print("\nDeriving slope, loading dh/dt, writing 16-band GeoTIFF…")
    tif_path = save_dl4gam_geotiff(s2_stack, dem, out_dir)

    if CONFIG["save_overview"]:
        print("Writing debug overview…")
        # Re-read the written stack for the overview (ensures on-disk == what we plot)
        with rasterio.open(tif_path) as src:
            stack_16 = src.read().astype(np.float32)   # (16, H, W)
        save_overview(stack_16, out_dir)

    print(f"\n✓  Done → {out_dir.resolve()}")
    print(f"   Output file : {tif_path.name}")
    print(f"   Band order  : {', '.join(BAND_ORDER)}")
    print(f"\n   Pass to main.py as:  INPUT_TIF = \"{tif_path}\"")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DL4GAM GeoTIFF Stack Builder")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=('LON_MIN', 'LAT_MIN', 'LON_MAX', 'LAT_MAX'), help="Bounding box e.g. 14.40 46.00 14.60 46.10")
    parser.add_argument("--date_from", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--date_to", type=str, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    main(bbox=args.bbox, date_from=args.date_from, date_to=args.date_to)