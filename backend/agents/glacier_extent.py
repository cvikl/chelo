"""Glacier Extent Agent — queries Sentinel-2 imagery + Randolph Glacier Inventory baselines."""

import random
from datetime import datetime


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query glacier extent data for a location and time range.
    Compares current extent against RGI baseline (~2000).

    TODO: Replace with real Sentinel-2 NDSI/band ratio analysis + RGI shapefiles.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1, (end.year - start.year))

    # Mock: glaciers are retreating in the Alps
    baseline_area_km2 = random.uniform(3.0, 25.0)  # RGI baseline ~2000
    annual_loss_rate = random.uniform(0.8, 2.5)  # % per year

    yearly_data = []
    for i in range(years + 1):
        year = start.year + i
        if year > end.year:
            break
        years_since_baseline = year - 2000
        area = max(0.1, baseline_area_km2 * (1 - annual_loss_rate / 100 * years_since_baseline))
        yearly_data.append({
            "year": year,
            "glacier_area_km2": round(area, 2),
            "area_change_from_baseline_percent": round(((area - baseline_area_km2) / baseline_area_km2) * 100, 1),
        })

    total_change_percent = yearly_data[-1]["area_change_from_baseline_percent"] - yearly_data[0].get("area_change_from_baseline_percent", 0)
    period_change = round(
        ((yearly_data[-1]["glacier_area_km2"] - yearly_data[0]["glacier_area_km2"])
         / yearly_data[0]["glacier_area_km2"]) * 100, 1
    )

    return {
        "parameter": "glacier_extent",
        "source": "Sentinel-2 + Randolph Glacier Inventory v7",
        "unit": "km2",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "rgi_baseline_area_km2": round(baseline_area_km2, 2),
        "trend": "decreasing" if period_change < -3 else "stable" if abs(period_change) <= 3 else "increasing",
        "change_percent": period_change,
        "confidence": round(random.uniform(0.82, 0.94), 2),
        "yearly_data": yearly_data,
        "summary": (
            f"Glacier area changed from {yearly_data[0]['glacier_area_km2']} km2 "
            f"to {yearly_data[-1]['glacier_area_km2']} km2 ({period_change:+.1f}%) "
            f"over the analyzed period. RGI baseline (~2000): {baseline_area_km2:.2f} km2."
        ),
    }
