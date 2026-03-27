"""Temperature Agent — queries EEAR-Clim ground station data."""

import random
from datetime import datetime


async def query(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """
    Query temperature data for a location and time range.
    Uses EEAR-Clim high-density observational dataset (~10,000 stations).

    TODO: Replace with real EEAR-Clim data from Zenodo.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    years = max(1, (end.year - start.year))

    # Mock: warming trend consistent with Alpine observations (+0.3C/decade)
    base_mean_temp = random.uniform(-2.0, 8.0)  # depends on altitude
    warming_rate_per_year = random.uniform(0.02, 0.05)  # C per year

    yearly_data = []
    for i in range(years + 1):
        year = start.year + i
        if year > end.year:
            break
        mean_temp = base_mean_temp + (warming_rate_per_year * i) + random.uniform(-0.5, 0.5)
        yearly_data.append({
            "year": year,
            "mean_temp_c": round(mean_temp, 1),
            "min_temp_c": round(mean_temp - random.uniform(8, 15), 1),
            "max_temp_c": round(mean_temp + random.uniform(10, 18), 1),
        })

    total_change = yearly_data[-1]["mean_temp_c"] - yearly_data[0]["mean_temp_c"]
    change_per_decade = round((total_change / years) * 10, 2) if years > 0 else 0

    return {
        "parameter": "temperature",
        "source": "EEAR-Clim (Extended European Alpine Region)",
        "unit": "celsius",
        "location": {"lat": lat, "lon": lon},
        "time_range": {"start": start_date, "end": end_date},
        "nearby_stations": random.randint(3, 15),
        "trend": "increasing" if total_change > 0.3 else "stable" if abs(total_change) <= 0.3 else "decreasing",
        "change_total_c": round(total_change, 1),
        "change_per_decade_c": change_per_decade,
        "confidence": round(random.uniform(0.90, 0.98), 2),
        "yearly_data": yearly_data,
        "summary": (
            f"Mean temperature changed by {total_change:+.1f}C over {years} years "
            f"({change_per_decade:+.2f}C/decade). "
            f"This is {'consistent with' if change_per_decade > 0.2 else 'below'} "
            f"the Alpine warming rate of ~0.3C/decade."
        ),
    }
