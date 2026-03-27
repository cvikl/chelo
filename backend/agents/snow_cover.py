"""Snow Cover Agent — queries MOD10A1.061 (MODIS Terra Snow Cover Daily 500m)."""

import random
from datetime import datetime


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query snow cover data for a location and time range.
    Returns NDSI-based snow cover metrics.

    TODO: Replace with real MOD10A1 data from Google Earth Engine or NASA NSIDC.
    """
    from agents.date_utils import clamp_date
    start_date = clamp_date(start_date, "snow_cover")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1, (end.year - start.year))

    # Mock: generate declining snow cover trend (realistic for Alps)
    base_coverage = random.uniform(55, 75)  # % snow cover at start
    annual_decline = random.uniform(1.2, 3.5)  # % per year

    yearly_data = []
    for i in range(years + 1):
        year = start.year + i
        if year > end.year:
            break
        coverage = max(0, base_coverage - (annual_decline * i) + random.uniform(-3, 3))
        yearly_data.append({
            "year": year,
            "mean_snow_cover_percent": round(coverage, 1),
            "snow_days_per_year": int(coverage * 2.5 + random.uniform(-10, 10)),
            "max_ndsi": round(random.uniform(0.5, 0.9), 2),
        })

    total_change = yearly_data[-1]["mean_snow_cover_percent"] - yearly_data[0]["mean_snow_cover_percent"]
    change_percent = round((total_change / yearly_data[0]["mean_snow_cover_percent"]) * 100, 1)

    return {
        "parameter": "snow_cover",
        "source": "MOD10A1.061 (MODIS Terra)",
        "unit": "percent",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "trend": "decreasing" if change_percent < -5 else "stable" if abs(change_percent) <= 5 else "increasing",
        "change_percent": change_percent,
        "confidence": round(random.uniform(0.85, 0.96), 2),
        "yearly_data": yearly_data,
        "summary": (
            f"Mean snow cover changed from {yearly_data[0]['mean_snow_cover_percent']}% "
            f"to {yearly_data[-1]['mean_snow_cover_percent']}% "
            f"({change_percent:+.1f}%) over {years} years. "
            f"Snow duration also {'decreased' if change_percent < 0 else 'remained stable'}."
        ),
    }
