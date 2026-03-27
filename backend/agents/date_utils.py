"""Date clamping utilities for agents based on data source availability."""

# Earliest available data per source
AGENT_MIN_DATES = {
    "temperature": "1940-01-01",    # Open-Meteo ERA5
    "precipitation": "1940-01-01",  # Open-Meteo ERA5
    "snow_cover": "2000-02-24",     # MODIS Terra MOD10A1
    "glacier_extent": "2017-01-01", # Sentinel-2 (reliable coverage from 2017)
    "vegetation": "2015-06-23",     # Sentinel-2A
}


def clamp_date(start_date: str, agent_name: str) -> str:
    """Clamp start_date to the earliest available for this agent's data source."""
    min_date = AGENT_MIN_DATES.get(agent_name, "1940-01-01")
    if start_date < min_date:
        return min_date
    return start_date


def get_unified_start_date(requested_agents: list[str], start_date: str) -> str:
    """
    Given a list of agents that will be called, return the latest min date
    among them. This ensures all agents compare the same time window.
    """
    latest_min = start_date
    for agent in requested_agents:
        min_date = AGENT_MIN_DATES.get(agent, "1940-01-01")
        if min_date > latest_min:
            latest_min = min_date
    # Don't go earlier than the requested start
    if start_date > latest_min:
        return start_date
    return latest_min
