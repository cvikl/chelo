"""Temperature Agent — queries Open-Meteo historical archive for real temperature data."""

import io
import base64
from datetime import datetime

import httpx
import numpy as np


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query real temperature data from Open-Meteo archive API.
    Returns trend analysis, yearly stats, and a base64-encoded plot.
    """
    from agents.date_utils import clamp_date
    start_date = clamp_date(start_date, "temperature")

    # Fetch real data from Open-Meteo
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "temperature_2m_mean",
                "timezone": "auto",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        raw = response.json()

    daily = raw.get("daily", {})
    dates = daily.get("time", [])
    temps = daily.get("temperature_2m_mean", [])

    # Filter out None values
    valid = [(d, t) for d, t in zip(dates, temps) if t is not None]
    if len(valid) < 30:
        raise ValueError("Not enough temperature data returned")

    dates_parsed = [datetime.strptime(d, "%Y-%m-%d") for d, _ in valid]
    temp_values = np.array([t for _, t in valid])
    ordinals = np.array([d.toordinal() for d in dates_parsed])

    # Linear regression for trend
    slope, intercept = np.polyfit(ordinals, temp_values, 1)
    warming_per_decade = slope * 365.25 * 10

    # Yearly aggregation
    yearly_data = {}
    for d, t in valid:
        year = int(d[:4])
        if year not in yearly_data:
            yearly_data[year] = []
        yearly_data[year].append(t)

    yearly_stats = []
    for year in sorted(yearly_data.keys()):
        vals = yearly_data[year]
        yearly_stats.append({
            "year": year,
            "mean_temp_c": round(np.mean(vals), 1),
            "min_temp_c": round(np.min(vals), 1),
            "max_temp_c": round(np.max(vals), 1),
        })

    # Generate plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")

    ax.scatter(dates_parsed, temp_values, color="#38bdf8", alpha=0.15, s=3)
    trend_line = slope * ordinals + intercept
    ax.plot(dates_parsed, trend_line, color="#f87171", linewidth=2,
            label=f"Trend: {warming_per_decade:+.2f}°C/decade")

    # Yearly means
    yearly_dates = [datetime(y["year"], 7, 1) for y in yearly_stats]
    yearly_means = [y["mean_temp_c"] for y in yearly_stats]
    ax.plot(yearly_dates, yearly_means, color="#34d399", linewidth=1.5, alpha=0.8, label="Yearly mean")

    ax.set_ylabel("Temperature (°C)", color="#94a3b8", fontsize=9)
    ax.tick_params(colors="#64748b", labelsize=8)
    ax.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")
    ax.grid(True, linestyle="--", alpha=0.15, color="#334155")
    for spine in ax.spines.values():
        spine.set_color("#334155")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0f172a")
    plt.close(fig)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode("utf-8")

    total_change = yearly_stats[-1]["mean_temp_c"] - yearly_stats[0]["mean_temp_c"]
    years_span = yearly_stats[-1]["year"] - yearly_stats[0]["year"]

    # Generate GEE Land Surface Temperature map
    gif_base64 = None
    try:
        import ee
        ee.Initialize(project="spacehack-491507")

        aoi = ee.Geometry.Point([lon, lat]).buffer(30000)
        start_y = yearly_stats[0]["year"]
        end_y = yearly_stats[-1]["year"]

        # Get LST for start and end summers
        def get_lst(year):
            dataset = (
                ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                .filterBounds(aoi)
                .filterDate(f"{year}-06-01", f"{year}-08-31")
                .filter(ee.Filter.lt("CLOUD_COVER", 30))
            )
            def to_celsius(image):
                return image.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST")
            return dataset.map(to_celsius).select("LST").median().clip(aoi)

        lst_start = get_lst(start_y)
        lst_end = get_lst(end_y)

        # Generate thumbnail images
        vis = {"min": -5, "max": 25, "palette": [
            "040274", "0502a3", "0502e6", "0602ff", "307ef3", "30c8e2",
            "3be285", "86e26f", "b5e22e", "fff705", "ffd611", "ffb613",
            "ff8b13", "ff500d", "ff0000", "c21301", "911003"
        ]}

        frames = []
        for lst, year in [(lst_start, start_y), (lst_end, end_y)]:
            url = lst.getThumbURL({"min": vis["min"], "max": vis["max"],
                                   "palette": vis["palette"],
                                   "dimensions": 256, "region": aoi})
            import httpx as hx
            resp = hx.get(url, timeout=30.0)
            if resp.status_code == 200:
                from PIL import Image
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                frames.append(img)

        if len(frames) == 2:
            gif_buf = io.BytesIO()
            frames[0].save(gif_buf, format="GIF", save_all=True, append_images=frames[1:], duration=2000, loop=0)
            gif_buf.seek(0)
            gif_base64 = base64.b64encode(gif_buf.read()).decode("utf-8")
    except Exception:
        pass  # GEE is optional — don't fail the whole agent

    result = {
        "parameter": "temperature",
        "source": "Open-Meteo ERA5 + Google Earth Engine Landsat LST",
        "unit": "celsius",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "trend": "increasing" if warming_per_decade > 0.1 else "stable" if abs(warming_per_decade) <= 0.1 else "decreasing",
        "change_total_c": round(total_change, 1),
        "change_per_decade_c": round(warming_per_decade, 2),
        "change_percent": round(warming_per_decade, 1),
        "confidence": 0.95,
        "yearly_data": yearly_stats,
        "plot_base64": plot_base64,
        "summary": (
            f"Real temperature data shows {warming_per_decade:+.2f}°C/decade warming trend "
            f"from {yearly_stats[0]['year']} to {yearly_stats[-1]['year']}. "
            f"Mean temperature changed from {yearly_stats[0]['mean_temp_c']}°C to {yearly_stats[-1]['mean_temp_c']}°C "
            f"({total_change:+.1f}°C over {years_span} years)."
        ),
    }

    if gif_base64:
        result["gif_base64"] = gif_base64

    return result
