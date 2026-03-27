"""
Orchestrator — the Brain's execution layer.

Takes the LLM extraction result, geocodes the location,
dispatches to the relevant agents in parallel, and collects results.
"""

import asyncio

from agents import glacier_extent, precipitation, snow_cover, temperature, vegetation
from geocoder import geocode
from schemas import ExtractionResult

# Map parameter names to agent modules
AGENT_REGISTRY = {
    "snow_cover": snow_cover,
    "glacier_extent": glacier_extent,
    "temperature": temperature,
    "precipitation": precipitation,
    "vegetation": vegetation,
}


async def run_agents(extraction: ExtractionResult) -> dict:
    """
    Given an extraction result from the brain:
    1. Geocode the location to coordinates
    2. Dispatch relevant agents in parallel
    3. Return all agent results
    """
    # Step 1: Geocode — get coordinates from the location name
    location = extraction.location
    if location.lat and location.lon:
        coords = {"lat": location.lat, "lon": location.lon, "bbox": location.bbox}
    else:
        coords = await geocode(location.name)

    lat = coords["lat"]
    lon = coords["lon"]
    start_date = extraction.time_range["start"]
    end_date = extraction.time_range["end"]

    # Step 2: Determine which agents to call (brain decided this)
    requested = extraction.parameters_requested
    agents_to_run = {
        param: AGENT_REGISTRY[param]
        for param in requested
        if param in AGENT_REGISTRY
    }

    if not agents_to_run:
        return {
            "location": coords,
            "agents_called": [],
            "results": [],
            "errors": ["No matching agents found for requested parameters."],
        }

    # Step 3: Dispatch all agents in parallel
    async def call_agent(param: str, agent_module):
        try:
            result = await agent_module.query(lat, lon, start_date, end_date)
            return {"param": param, "result": result, "error": None}
        except Exception as e:
            return {"param": param, "result": None, "error": str(e)}

    tasks = [
        call_agent(param, module)
        for param, module in agents_to_run.items()
    ]
    agent_outputs = await asyncio.gather(*tasks)

    # Step 4: Collect results
    results = []
    errors = []
    for output in agent_outputs:
        if output["error"]:
            errors.append(f"{output['param']}: {output['error']}")
        else:
            results.append(output["result"])

    return {
        "location": coords,
        "agents_called": list(agents_to_run.keys()),
        "results": results,
        "errors": errors,
    }
