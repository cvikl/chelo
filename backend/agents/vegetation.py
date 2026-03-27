"""Vegetation Agent — computes real NDVI from Sentinel-2 imagery via Element84 Earth Search."""

import io
import base64

import numpy as np
import httpx
import rasterio
from pyproj import Transformer


STAC_URL = "https://earth-search.aws.element84.com/v1/search"


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

    # Fetch NDVI for each year
    yearly_data = []
    ndvi_maps = {}

    for year in range(start_year, end_year + 1):
        tile = await _search_summer_tile(lat, lon, year)
        if tile is None:
            continue
        ndvi = _fetch_ndvi_patch(tile, lat, lon)
        mean_ndvi = float(np.mean(ndvi[ndvi > 0]))  # exclude water/no-data
        peak_ndvi = float(np.percentile(ndvi[ndvi > 0], 95))
        tile_date = tile["properties"]["datetime"][:10]

        yearly_data.append({
            "year": year,
            "mean_ndvi": round(mean_ndvi, 4),
            "peak_ndvi": round(peak_ndvi, 4),
            "tile_id": tile["id"],
            "tile_date": tile_date,
        })

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

    has_maps = len(ndvi_maps) == 2
    ncols = 3 if has_maps else 1
    fig, axes = plt.subplots(1, ncols, figsize=(4 * ncols, 4))
    fig.patch.set_facecolor("white")
    if ncols == 1:
        axes = [axes]

    veg_cmap = LinearSegmentedColormap.from_list("veg", [
        "white", "#1a1a2e", "#2d4a22", "#4a7c3f", "#6abf4b", "#a8e86c", "#f0ffe0"
    ])

    if has_maps:
        first_year = min(ndvi_maps.keys())
        last_year = max(ndvi_maps.keys())

        for i, (year, ndvi_map) in enumerate(sorted(ndvi_maps.items())):
            ax = axes[i]
            ax.set_facecolor("white")
            ax.imshow(ndvi_map.clip(-0.1, 0.8), cmap=veg_cmap, vmin=-0.1, vmax=0.8)
            yd = [y for y in yearly_data if y["year"] == year][0]
            ax.set_title(f"NDVI {yd['tile_date']}", color="#333333", fontsize=10, fontweight="bold")
            ax.set_xlabel(f"Mean NDVI: {yd['mean_ndvi']:.4f}", color="#34d399", fontsize=9)
            ax.tick_params(colors="#333333", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#334155")

        ax_trend = axes[2]
    else:
        ax_trend = axes[0]

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
            f"Tiles analyzed: {len(yearly_data)} years."
        ),
    }

    if gif_base64:
        result["gif_base64"] = gif_base64

    return result
