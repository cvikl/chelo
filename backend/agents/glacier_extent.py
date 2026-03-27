"""Glacier Extent Agent — fetches real Sentinel-2 imagery and runs trained UNet segmentation
with DL4GAM-correct normalization."""

import io
import base64

import numpy as np


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Fetch real Sentinel-2 tiles for start and end periods,
    run glacier segmentation model with proper normalization, compare areas.
    """
    from agents.date_utils import clamp_date
    from agents.glacier_model import predict_glacier_mask, calculate_glacier_area
    from agents.sentinel2_fetch import search_tile, search_dem_tile, fetch_patch

    start_date = clamp_date(start_date, "glacier_extent")
    start_year = int(start_date[:4])
    end_year = int(end_date[:4])
    years = max(1, end_year - start_year)

    # Snap to nearest known glacier center
    GLACIER_CENTERS = [
        (46.45, 8.05, "Aletsch Glacier"),
        (46.49, 8.03, "Upper Aletsch"),
        (45.83, 6.87, "Mer de Glace"),
        (47.08, 12.69, "Pasterze"),
    ]
    for glat, glon, gname in GLACIER_CENTERS:
        dist = ((lat - glat)**2 + (lon - glon)**2)**0.5
        if dist < 0.15:
            lat, lon = glat, glon
            break

    async def find_tile(target_year, direction=1):
        for offset in range(4):
            y = target_year + offset * direction
            if y < 2017 or y > 2025:
                continue
            tile = await search_tile(lat, lon, f"{y}-07-01", f"{y}-08-31")
            if tile:
                return tile
            tile = await search_tile(lat, lon, f"{y}-06-01", f"{y}-09-30", max_cloud=30)
            if tile:
                return tile
            tile = await search_tile(lat, lon, f"{y}-01-01", f"{y}-12-31", max_cloud=40)
            if tile:
                return tile
        return None

    tile_start = await find_tile(max(start_year, 2017), direction=1)
    tile_end = await find_tile(min(end_year, 2025), direction=-1)

    if tile_start is None or tile_end is None:
        raise ValueError("Could not find Sentinel-2 tiles for this location and time range")

    start_tile_date = tile_start["properties"]["datetime"][:10]
    end_tile_date = tile_end["properties"]["datetime"][:10]

    dem_item = await search_dem_tile(lat, lon)

    # Fetch 16-channel patches
    patch_start = fetch_patch(tile_start, lat, lon, size=256, extent_m=5000, dem_item=dem_item)
    patch_end = fetch_patch(tile_end, lat, lon, size=256, extent_m=5000, dem_item=dem_item)

    # Run model with proper DL4GAM normalization (handles normalization internally)
    mask_start, prob_start = predict_glacier_mask(patch_start)
    mask_end, prob_end = predict_glacier_mask(patch_end)

    pixel_size = 5000.0 / 256.0
    area_start = calculate_glacier_area(mask_start, pixel_size_m=pixel_size)
    area_end = calculate_glacier_area(mask_end, pixel_size_m=pixel_size)

    if area_start > 0:
        period_change = round(((area_end - area_start) / area_start) * 100, 1)
    else:
        period_change = 0.0

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

    # Build RGB composites from Sentinel-2 bands (B4=Red, B3=Green, B2=Blue = indices 3,2,1)
    rgb_start = np.stack([patch_start[3], patch_start[2], patch_start[1]], axis=-1)
    rgb_start = np.clip(rgb_start / 0.3, 0, 1)  # Stretch [0, 0.3] to [0, 1] for natural color
    rgb_end = np.stack([patch_end[3], patch_end[2], patch_end[1]], axis=-1)
    rgb_end = np.clip(rgb_end / 0.3, 0, 1)

    # Generate visualization: RGB + mask overlay + difference
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    glacier_cmap = LinearSegmentedColormap.from_list("glacier", [
        "white", "#1e3a5f", "#38bdf8", "#7dd3fc", "#e0f2fe", "#ffffff"
    ])

    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    fig.patch.set_facecolor("white")
    fig.suptitle(f"Glacier Analysis — {lat:.2f}°N, {lon:.2f}°E",
                 color="#333333", fontsize=12, fontweight="bold", y=0.98)

    for row in axes:
        for ax in row:
            ax.set_facecolor("white")
            ax.tick_params(colors="#333333", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#334155")

    # Row 1: RGB composites + difference
    axes[0, 0].imshow(rgb_start)
    axes[0, 0].set_title(f"True Color {start_tile_date}", color="#333333", fontsize=10, fontweight="bold")

    axes[0, 1].imshow(rgb_end)
    axes[0, 1].set_title(f"True Color {end_tile_date}", color="#333333", fontsize=10, fontweight="bold")

    # RGB difference
    diff_rgb = np.abs(rgb_end.astype(float) - rgb_start.astype(float)).mean(axis=-1)
    axes[0, 2].imshow(diff_rgb, cmap="hot", vmin=0, vmax=0.3)
    axes[0, 2].set_title("Change Intensity", color="#f59e0b", fontsize=10, fontweight="bold")

    # Row 2: Glacier probability maps + mask difference
    axes[1, 0].imshow(prob_start, cmap=glacier_cmap, vmin=0, vmax=1)
    axes[1, 0].set_title(f"Glacier Prob. — {area_start:.3f} km²", color="#38bdf8", fontsize=10)

    axes[1, 1].imshow(prob_end, cmap=glacier_cmap, vmin=0, vmax=1)
    axes[1, 1].set_title(f"Glacier Prob. — {area_end:.3f} km²", color="#38bdf8", fontsize=10)

    diff = prob_start - prob_end
    diff_cmap = LinearSegmentedColormap.from_list("diff", ["white", "#334155", "#f59e0b", "#dc2626"])
    axes[1, 2].imshow(diff.clip(-0.5, 0.5), cmap="RdBu", vmin=-0.5, vmax=0.5)
    axes[1, 2].set_title(f"Ice Change ({period_change:+.1f}%)", color="#f87171", fontsize=10)

    plt.tight_layout(pad=1.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "parameter": "glacier_extent",
        "source": "UNet Segmentation (Jaccard=0.89) on real Sentinel-2 L2A + DEM",
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
            "normalization": "DL4GAM (Z-score optical, mean-center DEM/dhdt, /90 slope)",
            "validation_jaccard": 0.8935,
        },
        "trend": "decreasing" if period_change < -3 else "stable" if abs(period_change) <= 3 else "increasing",
        "change_percent": period_change,
        "confidence": 0.89,
        "yearly_data": yearly_data,
        "plot_base64": plot_base64,
        "summary": (
            f"Real Sentinel-2 imagery analyzed with DL4GAM glacier model (Jaccard=0.89). "
            f"Glacier area: {area_start:.3f} km² ({start_tile_date}) → {area_end:.3f} km² ({end_tile_date}), "
            f"change: {period_change:+.1f}%."
        ),
    }
