"""Vegetation Agent — queries Sentinel-2 NDVI data."""

import random
from datetime import datetime


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query vegetation/greening data for a location and time range.
    Uses Sentinel-2 multispectral imagery (NDVI).

    TODO: Replace with real Sentinel-2 NDVI time series from GEE.
    """
    from agents.date_utils import clamp_date
    start_date = clamp_date(start_date, "vegetation")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1, (end.year - start.year))

    # Mock: greening trend in Alps (treeline moving upward, longer growing season)
    base_ndvi = random.uniform(0.25, 0.50)
    annual_ndvi_increase = random.uniform(0.002, 0.008)

    yearly_data = []
    for i in range(years + 1):
        year = start.year + i
        if year > end.year:
            break
        ndvi = base_ndvi + (annual_ndvi_increase * i) + random.uniform(-0.02, 0.02)
        growing_season_days = int(180 + (i * random.uniform(0.5, 2.0)) + random.uniform(-5, 5))
        yearly_data.append({
            "year": year,
            "mean_ndvi": round(ndvi, 3),
            "peak_ndvi": round(ndvi + random.uniform(0.1, 0.25), 3),
            "growing_season_days": growing_season_days,
        })

    ndvi_change = yearly_data[-1]["mean_ndvi"] - yearly_data[0]["mean_ndvi"]
    change_percent = round((ndvi_change / yearly_data[0]["mean_ndvi"]) * 100, 1)
    season_change = yearly_data[-1]["growing_season_days"] - yearly_data[0]["growing_season_days"]

    return {
        "parameter": "vegetation",
        "source": "Sentinel-2 MSI (NDVI)",
        "unit": "ndvi_index",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "trend": "increasing" if change_percent > 3 else "stable" if abs(change_percent) <= 3 else "decreasing",
        "change_percent": change_percent,
        "ndvi_change": round(ndvi_change, 3),
        "growing_season_change_days": season_change,
        "confidence": round(random.uniform(0.75, 0.90), 2),
        "yearly_data": yearly_data,
        "summary": (
            f"NDVI changed from {yearly_data[0]['mean_ndvi']:.3f} to "
            f"{yearly_data[-1]['mean_ndvi']:.3f} ({change_percent:+.1f}%) over {years} years, "
            f"indicating {'greening' if ndvi_change > 0 else 'browning'}. "
            f"Growing season {'extended' if season_change > 0 else 'shortened'} by "
            f"{abs(season_change)} days."
        ),
    }
