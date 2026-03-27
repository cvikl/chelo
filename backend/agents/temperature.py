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

    return {
        "parameter": "temperature",
        "source": "Open-Meteo Historical Archive (ERA5 reanalysis)",
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
