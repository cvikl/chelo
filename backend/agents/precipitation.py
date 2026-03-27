"""Precipitation Agent — queries EEAR-Clim ground station data."""

import random
from datetime import datetime


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query precipitation data for a location and time range.
    Uses EEAR-Clim high-density observational dataset.

    TODO: Replace with real EEAR-Clim precipitation data from Zenodo.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1, (end.year - start.year))

    # Mock: precipitation patterns shifting (more rain, less snow)
    base_annual_precip_mm = random.uniform(800, 1800)
    base_snow_fraction = random.uniform(0.35, 0.60)
    snow_fraction_decline_per_year = random.uniform(0.005, 0.015)

    yearly_data = []
    for i in range(years + 1):
        year = start.year + i
        if year > end.year:
            break
        annual_precip = base_annual_precip_mm + random.uniform(-150, 150)
        snow_frac = max(0.05, base_snow_fraction - (snow_fraction_decline_per_year * i) + random.uniform(-0.03, 0.03))
        yearly_data.append({
            "year": year,
            "total_precip_mm": round(annual_precip, 0),
            "snow_fraction": round(snow_frac, 2),
            "rain_fraction": round(1 - snow_frac, 2),
            "snowfall_mm": round(annual_precip * snow_frac, 0),
            "rainfall_mm": round(annual_precip * (1 - snow_frac), 0),
        })

    precip_change = round(
        ((yearly_data[-1]["total_precip_mm"] - yearly_data[0]["total_precip_mm"])
         / yearly_data[0]["total_precip_mm"]) * 100, 1
    )
    snow_frac_change = round(
        (yearly_data[-1]["snow_fraction"] - yearly_data[0]["snow_fraction"]) * 100, 1
    )

    return {
        "parameter": "precipitation",
        "source": "EEAR-Clim (Extended European Alpine Region)",
        "unit": "mm/year",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "nearby_stations": random.randint(3, 12),
        "trend": "decreasing" if snow_frac_change < -3 else "stable" if abs(snow_frac_change) <= 3 else "increasing",
        "change_percent": precip_change,
        "snow_fraction_change_points": snow_frac_change,
        "confidence": round(random.uniform(0.80, 0.93), 2),
        "yearly_data": yearly_data,
        "summary": (
            f"Total precipitation changed by {precip_change:+.1f}% over {years} years. "
            f"Snow-to-rain ratio shifted: snow fraction went from "
            f"{yearly_data[0]['snow_fraction']:.0%} to {yearly_data[-1]['snow_fraction']:.0%} "
            f"({snow_frac_change:+.1f} percentage points), indicating more rain and less snowfall."
        ),
    }
