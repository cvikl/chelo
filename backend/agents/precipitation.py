"""Precipitation / Snow Days Agent — queries Open-Meteo historical archive for real snowfall data."""

import io
import base64
from datetime import datetime

import httpx
import numpy as np


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query real snowfall/precipitation data from Open-Meteo archive API.
    Returns snow day trends, yearly stats, and a base64-encoded plot.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date,
                "end_date": end_date,
                "daily": "snowfall_sum,precipitation_sum",
                "timezone": "auto",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        raw = response.json()

    daily = raw.get("daily", {})
    dates = daily.get("time", [])
    snowfall = daily.get("snowfall_sum", [])
    precipitation = daily.get("precipitation_sum", [])

    # Yearly aggregation
    yearly_data = {}
    for d, snow, precip in zip(dates, snowfall, precipitation):
        year = int(d[:4])
        if year not in yearly_data:
            yearly_data[year] = {"snow_days": 0, "total_snow_cm": 0, "total_precip_mm": 0, "days": 0}
        yearly_data[year]["days"] += 1
        if snow is not None and snow > 0:
            yearly_data[year]["snow_days"] += 1
            yearly_data[year]["total_snow_cm"] += snow
        if precip is not None:
            yearly_data[year]["total_precip_mm"] += precip

    yearly_stats = []
    for year in sorted(yearly_data.keys()):
        d = yearly_data[year]
        snow_fraction = d["snow_days"] / max(d["days"], 1)
        yearly_stats.append({
            "year": year,
            "snow_days": d["snow_days"],
            "total_snow_cm": round(d["total_snow_cm"], 1),
            "total_precip_mm": round(d["total_precip_mm"], 1),
            "snow_fraction": round(snow_fraction, 3),
        })

    if len(yearly_stats) < 2:
        raise ValueError("Not enough precipitation data")

    # Trend on snow days per year
    years_arr = np.array([y["year"] for y in yearly_stats])
    snow_days_arr = np.array([y["snow_days"] for y in yearly_stats])
    slope, intercept = np.polyfit(years_arr, snow_days_arr, 1)
    snow_days_change_per_decade = slope * 10

    first_half = yearly_stats[:len(yearly_stats)//2]
    second_half = yearly_stats[len(yearly_stats)//2:]
    avg_first = np.mean([y["snow_days"] for y in first_half])
    avg_second = np.mean([y["snow_days"] for y in second_half])
    change_percent = round(((avg_second - avg_first) / max(avg_first, 1)) * 100, 1)

    # Generate plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    fig.patch.set_facecolor("#0f172a")
    for ax in (ax1, ax2):
        ax.set_facecolor("#0f172a")
        ax.tick_params(colors="#64748b", labelsize=8)
        ax.grid(True, linestyle="--", alpha=0.15, color="#334155")
        for spine in ax.spines.values():
            spine.set_color("#334155")

    # Snow days bar chart
    ax1.bar(years_arr, snow_days_arr, color="#38bdf8", alpha=0.7, label="Snow days/year")
    trend_line = slope * years_arr + intercept
    ax1.plot(years_arr, trend_line, color="#f87171", linewidth=2,
             label=f"Trend: {snow_days_change_per_decade:+.1f} days/decade")
    ax1.set_ylabel("Snow Days", color="#94a3b8", fontsize=9)
    ax1.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")

    # Total snowfall
    snow_totals = np.array([y["total_snow_cm"] for y in yearly_stats])
    ax2.bar(years_arr, snow_totals, color="#f59e0b", alpha=0.7, label="Total snowfall (cm)")
    snow_slope, snow_int = np.polyfit(years_arr, snow_totals, 1)
    ax2.plot(years_arr, snow_slope * years_arr + snow_int, color="#f87171", linewidth=2,
             label=f"Trend: {snow_slope*10:+.1f} cm/decade")
    ax2.set_ylabel("Snowfall (cm)", color="#94a3b8", fontsize=9)
    ax2.set_xlabel("Year", color="#94a3b8", fontsize=9)
    ax2.legend(fontsize=8, facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#0f172a")
    plt.close(fig)
    buf.seek(0)
    plot_base64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "parameter": "precipitation",
        "source": "Open-Meteo Historical Archive (ERA5 reanalysis)",
        "unit": "snow_days/year",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "trend": "decreasing" if change_percent < -5 else "stable" if abs(change_percent) <= 5 else "increasing",
        "change_percent": change_percent,
        "snow_days_change_per_decade": round(snow_days_change_per_decade, 1),
        "confidence": 0.90,
        "yearly_data": yearly_stats,
        "plot_base64": plot_base64,
        "summary": (
            f"Real snowfall data shows {snow_days_change_per_decade:+.1f} snow days/decade change. "
            f"Average snow days went from {avg_first:.0f}/year (first half) to {avg_second:.0f}/year (second half) "
            f"({change_percent:+.1f}%). Total annual snowfall trend: {snow_slope*10:+.1f} cm/decade."
        ),
    }
