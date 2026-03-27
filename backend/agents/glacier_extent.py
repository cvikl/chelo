"""Glacier Extent Agent — fetches real Sentinel-2 imagery and runs trained UNet segmentation."""

import io
import base64

import numpy as np
import torch


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Fetch real Sentinel-2 tiles for start and end periods,
    run glacier segmentation model, compare areas.
    """
    from agents.date_utils import clamp_date
    from agents.glacier_model import get_model, predict_glacier_mask, calculate_glacier_area
    from agents.sentinel2_fetch import search_tile, fetch_patch

    start_date = clamp_date(start_date, "glacier_extent")
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    years = max(1, end_year - start_year)

    # Search for summer tiles (June-Sept) for best glacier visibility
    # Try the requested year first, then nearby years if no tiles found
    async def find_tile(target_year: int, direction: int = 1) -> dict | None:
        """Search target year, then expand up to 3 years in given direction."""
        for offset in range(4):
            y = target_year + offset * direction
            if y < 2017 or y > 2025:
                continue
            # Try summer first
            tile = await search_tile(lat, lon, f"{y}-06-01", f"{y}-09-30")
            if tile:
                return tile
            # Try full year with relaxed cloud
            tile = await search_tile(lat, lon, f"{y}-01-01", f"{y}-12-31", max_cloud=40)
            if tile:
                return tile
        return None

    tile_start = await find_tile(max(start_year, 2017), direction=1)
    tile_end = await find_tile(min(end_year, 2025), direction=-1)

    if tile_start is None or tile_end is None:
        raise ValueError(f"Could not find Sentinel-2 tiles for this location and time range")

    start_tile_date = tile_start["properties"]["datetime"][:10]
    end_tile_date = tile_end["properties"]["datetime"][:10]

    # Fetch 16-channel patches (5km extent around the point)
    patch_start = fetch_patch(tile_start, lat, lon, size=256, extent_m=5000)
    patch_end = fetch_patch(tile_end, lat, lon, size=256, extent_m=5000)

    # Run segmentation model
    tensor_start = torch.from_numpy(patch_start).unsqueeze(0).float()
    tensor_end = torch.from_numpy(patch_end).unsqueeze(0).float()

    mask_start = predict_glacier_mask(tensor_start)
    mask_end = predict_glacier_mask(tensor_end)

    # Calculate areas (5000m extent / 256 pixels = ~19.5m per pixel)
    pixel_size = 5000.0 / 256.0
    area_start = calculate_glacier_area(mask_start, pixel_size_m=pixel_size)
    area_end = calculate_glacier_area(mask_end, pixel_size_m=pixel_size)

    if area_start > 0:
        period_change = round(((area_end - area_start) / area_start) * 100, 1)
    else:
        period_change = 0.0

    # Build yearly interpolation
    yearly_data = []
    for i in range(years + 1):
        year = start_year + i
        if year > end_year:
            break
        t = i / max(years, 1)
        area = area_start + (area_end - area_start) * t
        yearly_data.append({
            "year": year,
            "glacier_area_km2": round(area, 3),
        })

    # Generate visualization
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    glacier_cmap = LinearSegmentedColormap.from_list("glacier", [
        "#0f172a", "#1e3a5f", "#38bdf8", "#7dd3fc", "#e0f2fe", "#ffffff"
    ])
    diff_cmap = LinearSegmentedColormap.from_list("diff", [
        "#0f172a", "#334155", "#f59e0b", "#dc2626"
    ])

    model = get_model()
    with torch.no_grad():
        prob_start = torch.sigmoid(model(tensor_start))[0, 0].numpy()
        prob_end = torch.sigmoid(model(tensor_end))[0, 0].numpy()

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    fig.patch.set_facecolor("#0f172a")
    fig.suptitle(f"Glacier Segmentation — {lat:.2f}°N, {lon:.2f}°E (5 km window)",
                 color="#e2e8f0", fontsize=11, fontweight="bold", y=0.98)

    for ax in axes:
        ax.set_facecolor("#0f172a")
        ax.tick_params(colors="#64748b", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#334155")

    axes[0].imshow(prob_start, cmap=glacier_cmap, vmin=0, vmax=1)
    axes[0].set_title(f"{start_tile_date}", color="#e2e8f0", fontsize=10, fontweight="bold")
    axes[0].set_xlabel(f"Glacier area: {area_start:.3f} km²", color="#38bdf8", fontsize=9)

    axes[1].imshow(prob_end, cmap=glacier_cmap, vmin=0, vmax=1)
    axes[1].set_title(f"{end_tile_date}", color="#e2e8f0", fontsize=10, fontweight="bold")
    axes[1].set_xlabel(f"Glacier area: {area_end:.3f} km²", color="#38bdf8", fontsize=9)

    diff = prob_start - prob_end
    axes[2].imshow(diff.clip(0, 1), cmap=diff_cmap, vmin=0, vmax=0.5)
    axes[2].set_title(f"Ice Loss ({period_change:+.1f}%)", color="#f87171", fontsize=10, fontweight="bold")
    lost = max(area_start - area_end, 0)
    axes[2].set_xlabel(f"Lost: {lost:.3f} km²", color="#f59e0b", fontsize=9)

    plt.tight_layout(pad=1.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0f172a")
    plt.close(fig)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "parameter": "glacier_extent",
        "source": f"UNet Segmentation (Jaccard=0.89) on real Sentinel-2 L2A imagery",
        "unit": "km2",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "tiles_used": {
            "start": {"id": tile_start["id"], "date": start_tile_date, "cloud": tile_start["properties"]["eo:cloud_cover"]},
            "end": {"id": tile_end["id"], "date": end_tile_date, "cloud": tile_end["properties"]["eo:cloud_cover"]},
        },
        "model_info": {
            "architecture": "UNet (ResNet34 encoder)",
            "input_channels": 16,
            "validation_jaccard": 0.8935,
            "pixel_resolution_m": round(pixel_size, 1),
        },
        "trend": "decreasing" if period_change < -3 else "stable" if abs(period_change) <= 3 else "increasing",
        "change_percent": period_change,
        "confidence": 0.89,
        "yearly_data": yearly_data,
        "plot_base64": plot_base64,
        "summary": (
            f"Real Sentinel-2 imagery analyzed with glacier segmentation model (Jaccard=0.89). "
            f"Glacier area: {area_start:.3f} km² ({start_tile_date}) → {area_end:.3f} km² ({end_tile_date}), "
            f"change: {period_change:+.1f}%. "
            f"Tiles: {tile_start['id']}, {tile_end['id']}."
        ),
    }
