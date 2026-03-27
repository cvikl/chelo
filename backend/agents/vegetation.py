"""Vegetation Agent — computes real NDVI from Sentinel-2 imagery via Element84 Earth Search."""

import io
import base64

import numpy as np
import httpx
import rasterio
from pyproj import Transformer
from scipy.ndimage import zoom as scipy_zoom


STAC_URL = "https://earth-search.aws.element84.com/v1/search"

# Vegetation line thresholds (from Vid's Sentinel2_downloader.py)
NDVI_THRESH = 0.15        # pixel counts as "vegetated"
PIXEL_FRAC_THRESH = 0.05  # at least 5% of pixels in band must be vegetated
ELEV_BAND_M = 50          # elevation band width in metres


def _vegetation_line(ndvi_2d, dem_2d):
    """
    Find the highest elevation band where vegetation is still significant.
    Returns (veg_line_m, band_edges, band_frac) or (NaN, [], []) if no data.
    """
    elev_flat = dem_2d.ravel()
    ndvi_flat = ndvi_2d.ravel()

    valid = (elev_flat > 0) & np.isfinite(elev_flat) & np.isfinite(ndvi_flat)
    elev_flat = elev_flat[valid]
    ndvi_flat = ndvi_flat[valid]

    if elev_flat.size == 0:
        return np.nan, np.array([]), np.array([])

    e_min = np.floor(elev_flat.min() / ELEV_BAND_M) * ELEV_BAND_M
    e_max = np.ceil(elev_flat.max() / ELEV_BAND_M) * ELEV_BAND_M
    band_edges = np.arange(e_min, e_max, ELEV_BAND_M)

    band_frac = []
    for e in band_edges:
        mask = (elev_flat >= e) & (elev_flat < e + ELEV_BAND_M)
        if mask.sum() == 0:
            band_frac.append(0.0)
        else:
            band_frac.append(float((ndvi_flat[mask] > NDVI_THRESH).mean()))

    band_frac = np.array(band_frac)
    above = np.where(band_frac >= PIXEL_FRAC_THRESH)[0]
    veg_line_m = float(band_edges[above[-1]] + ELEV_BAND_M / 2) if above.size else np.nan

    return veg_line_m, band_edges, band_frac


async def _fetch_dem_patch(lat, lon, size=256, extent_m=5000):
    """Fetch DEM patch from Copernicus GLO-30 via Element84."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(STAC_URL, json={
            "collections": ["cop-dem-glo-30"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "limit": 1,
        })
        features = resp.json().get("features", [])
        if not features:
            return None

    item = features[0]
    dem_url = item["assets"]["data"]["href"]

    # DEM is in EPSG:4326
    d_deg = extent_m / 111000  # rough degrees
    bbox = (lon - d_deg, lat - d_deg, lon + d_deg, lat + d_deg)

    with rasterio.open(dem_url) as src:
        window = rasterio.windows.from_bounds(*bbox, transform=src.transform)
        dem = src.read(1, window=window, out_shape=(size, size)).astype(np.float32)

    return dem


async def _search_summer_tile(lat, lon, year, max_cloud=20):
    """Find a low-cloud summer Sentinel-2 tile for NDVI calculation."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(STAC_URL, json={
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": f"{year}-06-01T00:00:00Z/{year}-09-30T23:59:59Z",
            "limit": 3,
            "query": {"eo:cloud_cover": {"lt": max_cloud}},
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        })
        features = resp.json().get("features", [])
        if features:
            return features[0]
        # Fallback: full year, relaxed cloud
        resp = await client.post(STAC_URL, json={
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z",
            "limit": 3,
            "query": {"eo:cloud_cover": {"lt": 40}},
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        })
        features = resp.json().get("features", [])
        return features[0] if features else None


def _fetch_ndvi_patch(item, lat, lon, size=256, extent_m=5000):
    """Fetch NIR and Red bands, compute NDVI for a patch."""
    ref_url = item["assets"]["nir"]["href"]
    with rasterio.open(ref_url) as src:
        transformer = Transformer.from_crs("EPSG:4326", str(src.crs), always_xy=True)
        cx, cy = transformer.transform(lon, lat)
        half = extent_m / 2
        bbox = (cx - half, cy - half, cx + half, cy + half)

    bands = {}
    for key in ["nir", "red"]:
        url = item["assets"][key]["href"]
        with rasterio.open(url) as src:
            window = rasterio.windows.from_bounds(*bbox, transform=src.transform)
            bands[key] = src.read(1, window=window, out_shape=(size, size)).astype(np.float32)

    nir = bands["nir"]
    red = bands["red"]
    eps = 1e-6
    ndvi = (nir - red) / (nir + red + eps)
    return ndvi


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Compute real NDVI from Sentinel-2 imagery for multiple years.
    Compares vegetation greenness over time.
    """
    from agents.date_utils import clamp_date
    start_date = clamp_date(start_date, "vegetation")

    start_year = int(start_date[:4])
    end_year = int(end_date[:4])

    # Fetch DEM for vegetation line calculation
    dem = await _fetch_dem_patch(lat, lon)

    # Fetch NDVI for each year + compute vegetation line
    yearly_data = []
    ndvi_maps = {}
    veg_lines = []

    for year in range(start_year, end_year + 1):
        tile = await _search_summer_tile(lat, lon, year)
        if tile is None:
            continue
        ndvi = _fetch_ndvi_patch(tile, lat, lon)
        mean_ndvi = float(np.mean(ndvi[ndvi > 0]))  # exclude water/no-data
        peak_ndvi = float(np.percentile(ndvi[ndvi > 0], 95))
        tile_date = tile["properties"]["datetime"][:10]

        # Compute vegetation line (highest elevation with vegetation)
        veg_line_m = np.nan
        if dem is not None:
            # Resize DEM to match NDVI dimensions if needed
            if dem.shape != ndvi.shape:
                dem_resized = scipy_zoom(dem, (ndvi.shape[0] / dem.shape[0], ndvi.shape[1] / dem.shape[1]))
            else:
                dem_resized = dem
            veg_line_m, _, _ = _vegetation_line(ndvi, dem_resized)

        yearly_data.append({
            "year": year,
            "mean_ndvi": round(mean_ndvi, 4),
            "peak_ndvi": round(peak_ndvi, 4),
            "vegetation_line_m": round(veg_line_m, 0) if not np.isnan(veg_line_m) else None,
            "tile_id": tile["id"],
            "tile_date": tile_date,
        })
        veg_lines.append(veg_line_m)

        ndvi_maps[year] = ndvi

    if len(yearly_data) < 2:
        raise ValueError("Not enough vegetation data")

    years_arr = np.array([y["year"] for y in yearly_data])
    ndvi_arr = np.array([y["mean_ndvi"] for y in yearly_data])
    slope, intercept = np.polyfit(years_arr, ndvi_arr, 1)
    ndvi_change_decade = slope * 10

    first_ndvi = yearly_data[0]["mean_ndvi"]
    last_ndvi = yearly_data[-1]["mean_ndvi"]
    change_percent = round(((last_ndvi - first_ndvi) / max(abs(first_ndvi), 0.001)) * 100, 1)

    # Plot: NDVI trend + maps
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    # Check if vegetation line data is available
    valid_vl = [(y["year"], y["vegetation_line_m"]) for y in yearly_data
                if y.get("vegetation_line_m") is not None]
    has_veg_line = len(valid_vl) >= 2

    has_maps = len(ndvi_maps) >= 2
    ncols = 2 + (1 if has_maps else 0) + (1 if has_veg_line else 0)
    fig, axes = plt.subplots(1, ncols, figsize=(4 * ncols, 4))
    fig.patch.set_facecolor("white")
    if ncols == 1:
        axes = [axes]

    veg_cmap = LinearSegmentedColormap.from_list("veg", [
        "white", "#1a1a2e", "#2d4a22", "#4a7c3f", "#6abf4b", "#a8e86c", "#f0ffe0"
    ])

    col = 0
    if has_maps:
        map_years = sorted(ndvi_maps.keys())
        first_year_map = map_years[0]
        last_year_map = map_years[-1]

        for year in [first_year_map, last_year_map]:
            ndvi_map = ndvi_maps[year]
            ax = axes[col]
            ax.set_facecolor("white")
            ax.imshow(ndvi_map.clip(-0.1, 0.8), cmap=veg_cmap, vmin=-0.1, vmax=0.8)
            yd = [y for y in yearly_data if y["year"] == year][0]
            ax.set_title(f"NDVI {yd['tile_date']}", color="#333333", fontsize=10, fontweight="bold")
            vl_label = f" | VegLine: {yd['vegetation_line_m']:.0f}m" if yd.get("vegetation_line_m") else ""
            ax.set_xlabel(f"NDVI: {yd['mean_ndvi']:.4f}{vl_label}", color="#34d399", fontsize=8)
            ax.tick_params(colors="#333333", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#334155")
            col += 1

    ax_trend = axes[col]
    col += 1

    ax_trend.set_facecolor("white")
    ax_trend.plot(years_arr, ndvi_arr, color="#34d399", linewidth=2, marker="o", markersize=5)
    ax_trend.plot(years_arr, slope * years_arr + intercept, color="#f87171", linewidth=2, linestyle="--",
                  label=f"Trend: {ndvi_change_decade:+.4f}/decade")
    ax_trend.fill_between(years_arr, ndvi_arr, alpha=0.15, color="#34d399")
    ax_trend.set_ylabel("Mean NDVI", color="#333333", fontsize=9)
    ax_trend.set_xlabel("Year", color="#333333", fontsize=9)
    ax_trend.set_title("Vegetation Trend", color="#333333", fontsize=10, fontweight="bold")
    ax_trend.legend(fontsize=8, facecolor="white", edgecolor="#cccccc", labelcolor="#333333")
    ax_trend.grid(True, linestyle="--", alpha=0.15, color="#cccccc")
    ax_trend.tick_params(colors="#333333", labelsize=8)
    for spine in ax_trend.spines.values():
        spine.set_color("#334155")

    # Vegetation line trend (if DEM data available)
    if has_veg_line:
        ax_vl = axes[col]
        ax_vl.set_facecolor("white")
        vl_years = np.array([y for y, v in valid_vl])
        vl_vals = np.array([v for y, v in valid_vl])
        vl_slope, vl_int = np.polyfit(vl_years, vl_vals, 1)
        vl_change_decade = vl_slope * 10

        ax_vl.plot(vl_years, vl_vals, color="#8b5cf6", linewidth=2, marker="s", markersize=5)
        ax_vl.plot(vl_years, vl_slope * vl_years + vl_int, color="#f87171", linewidth=2, linestyle="--",
                   label=f"Trend: {vl_change_decade:+.0f} m/decade")
        ax_vl.fill_between(vl_years, vl_vals, alpha=0.1, color="#8b5cf6")
        ax_vl.set_ylabel("Elevation (m)", color="#333333", fontsize=9)
        ax_vl.set_xlabel("Year", color="#333333", fontsize=9)
        ax_vl.set_title("Vegetation Line", color="#333333", fontsize=10, fontweight="bold")
        ax_vl.legend(fontsize=8, facecolor="white", edgecolor="#cccccc", labelcolor="#333333")
        ax_vl.grid(True, linestyle="--", alpha=0.15, color="#cccccc")
        ax_vl.tick_params(colors="#333333", labelsize=8)
        for spine in ax_vl.spines.values():
            spine.set_color("#334155")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode("utf-8")

    # Generate NDVI GIF from all yearly maps
    gif_base64 = None
    if len(ndvi_maps) >= 2:
        from PIL import Image
        import matplotlib.cm as cm
        imgs = []
        for year in sorted(ndvi_maps.keys()):
            ndvi_map = ndvi_maps[year]
            colored = (cm.Greens(np.clip(ndvi_map, 0, 1)) * 255).astype(np.uint8)[:, :, :3]
            imgs.append(Image.fromarray(colored))

        gif_buf = io.BytesIO()
        imgs[0].save(gif_buf, format="GIF", save_all=True, append_images=imgs[1:], duration=1500, loop=0)
        gif_buf.seek(0)
        gif_base64 = base64.b64encode(gif_buf.read()).decode("utf-8")

    result = {
        "parameter": "vegetation",
        "source": "Sentinel-2 L2A NDVI (Element84 Earth Search)",
        "unit": "ndvi_index",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "trend": "increasing" if change_percent > 3 else "stable" if abs(change_percent) <= 3 else "decreasing",
        "change_percent": change_percent,
        "confidence": 0.85,
        "yearly_data": yearly_data,
        "plot_base64": plot_base64,
        "summary": (
            f"Real Sentinel-2 NDVI analysis: mean NDVI changed from {first_ndvi:.4f} "
            f"to {last_ndvi:.4f} ({change_percent:+.1f}%) between {yearly_data[0]['year']} and "
            f"{yearly_data[-1]['year']}. Trend: {ndvi_change_decade:+.4f} NDVI/decade. "
            + (f"Vegetation line (highest elevation with vegetation) tracked using DEM. " if has_veg_line else "")
            + f"Tiles analyzed: {len(yearly_data)} years."
        ),
    }

    if gif_base64:
        result["gif_base64"] = gif_base64

    return result
