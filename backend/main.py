import asyncio
import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

# Public S3 buckets (Sentinel-2 COGs) don't need AWS credentials
os.environ["AWS_NO_SIGN_REQUEST"] = "YES"

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from comparator import compare_claims_to_data
from geocoder import geocode
from llm import extract_claims
from orchestrator import AGENT_REGISTRY, run_agents
from schemas import (
    ArticleRequest,
    ExtractionResult,
    FullAnalysis,
    SatelliteDataPoint,
    SatelliteResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AlpineCheck API starting up...")
    yield
    print("Shutting down.")


app = FastAPI(title="AlpineCheck", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for the current analysis session
current_extraction: ExtractionResult | None = None


def sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"


@app.post("/api/extract", response_model=ExtractionResult)
async def extract_article(request: ArticleRequest):
    """Step 1: Extract claims and parameters from an article using LLM."""
    global current_extraction
    try:
        result = await extract_claims(request.article_text)
        current_extraction = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@app.post("/api/satellite-data", response_model=FullAnalysis)
async def receive_satellite_data(satellite_response: SatelliteResponse):
    """Receive satellite data from the visual recognition team and compare."""
    global current_extraction
    if current_extraction is None:
        raise HTTPException(status_code=400, detail="No extraction available. Run /api/extract first.")

    verdicts = compare_claims_to_data(
        current_extraction.claims,
        satellite_response.results,
    )

    return FullAnalysis(
        extraction=current_extraction,
        satellite_data=satellite_response,
        verdicts=verdicts,
    )


@app.post("/api/analyze")
async def full_analyze_stream(request: ArticleRequest):
    """Full pipeline with SSE streaming of thinking steps."""

    async def event_stream():
        global current_extraction

        # Step 1: Orchestrator reading article
        yield sse_event("thinking", {
            "step": "brain_start",
            "message": "Orchestrator is reading the article...",
            "detail": f"Analyzing {len(request.article_text)} characters for climate claims",
        })

        try:
            extraction = await extract_claims(request.article_text)
            current_extraction = extraction
        except Exception as e:
            yield sse_event("error", {"message": f"Extraction failed: {e}"})
            return

        yield sse_event("thinking", {
            "step": "brain_done",
            "message": f"Orchestrator found {len(extraction.claims)} claims to verify",
            "detail": f"Location: {extraction.location.name} | Time: {extraction.time_range['start']} to {extraction.time_range['end']}",
            "claims": [{"id": c.id, "text": c.text, "type": c.type, "severity": c.severity} for c in extraction.claims],
            "parameters": extraction.parameters_requested,
        })

        # Step 2: Geocoding
        yield sse_event("thinking", {
            "step": "geocoding",
            "message": f"Geocoding \"{extraction.location.name}\"...",
            "detail": "Resolving location to coordinates for satellite data queries",
        })

        # Always geocode by name for accuracy — LLM coordinates can be wrong
        try:
            coords = await geocode(extraction.location.name)
        except ValueError:
            # Fallback to LLM-provided coordinates if geocoding fails
            coords = {"lat": extraction.location.lat, "lon": extraction.location.lon, "bbox": extraction.location.bbox}

        yield sse_event("thinking", {
            "step": "geocoding_done",
            "message": f"Location resolved: {coords['lat']:.4f}, {coords['lon']:.4f}",
            "detail": f"Bounding box: {coords.get('bbox')}",
        })

        # Step 3: Dispatching agents
        agents_to_run = [p for p in extraction.parameters_requested if p in AGENT_REGISTRY]

        # Unify date range to the latest data source start among requested agents
        from agents.date_utils import get_unified_start_date
        lat, lon = coords["lat"], coords["lon"]
        raw_start = extraction.time_range["start"]
        end_date = extraction.time_range["end"]
        start_date = get_unified_start_date(agents_to_run, raw_start)

        date_note = ""
        if start_date != raw_start:
            date_note = f" (adjusted from {raw_start} to {start_date} — limited by data availability)"

        yield sse_event("thinking", {
            "step": "agents_dispatch",
            "message": f"Dispatching {len(agents_to_run)} agents — unified range: {start_date} to {end_date}",
            "detail": ", ".join(agents_to_run) + date_note,
            "agents": agents_to_run,
        })
        all_results = []
        errors = []

        # Actually run them in parallel, but report as they complete
        agent_source_map = {
            "snow_cover": "MOD10A1.061 (MODIS Terra) — data from 2000",
            "glacier_extent": "Sentinel-2 + RGI — imagery from 2015, baseline ~2000",
            "temperature": "Open-Meteo ERA5 — data from 1940",
            "precipitation": "Open-Meteo ERA5 — data from 1940",
            "vegetation": "Sentinel-2 NDVI — data from 2015",
        }

        async def run_single_agent(param):
            module = AGENT_REGISTRY[param]
            result = await module.query(lat, lon, start_date, end_date)
            return param, result

        tasks = [run_single_agent(p) for p in agents_to_run]
        for coro in asyncio.as_completed(tasks):
            try:
                param, result = await coro
                all_results.append(result)
                yield sse_event("thinking", {
                    "step": "agent_done",
                    "message": f"Agent '{param}' returned data",
                    "detail": f"Source: {agent_source_map.get(param, 'Unknown')} | Trend: {result['trend']} ({result.get('change_percent', 'N/A')}%)",
                    "agent": param,
                    "trend": result["trend"],
                    "change_percent": result.get("change_percent"),
                })
            except Exception as e:
                errors.append(f"{param}: {e}")
                yield sse_event("thinking", {
                    "step": "agent_error",
                    "message": f"Agent '{param}' failed",
                    "detail": str(e),
                    "agent": param,
                })

        # Step 4: Comparing
        yield sse_event("thinking", {
            "step": "comparing",
            "message": "Comparing article claims against satellite evidence...",
            "detail": f"Matching {len(extraction.claims)} claims against {len(all_results)} data sources",
        })

        satellite_results = []
        for result in all_results:
            satellite_results.append(
                SatelliteDataPoint(
                    parameter=result["parameter"],
                    source=result.get("source"),
                    unit=result.get("unit"),
                    trend=result["trend"],
                    change_percent=result.get("change_percent"),
                    confidence=result.get("confidence"),
                    summary=result.get("summary"),
                    time_series=result.get("yearly_data"),
                    plot_base64=result.get("plot_base64"),
                    gif_base64=result.get("gif_base64"),
                )
            )

        satellite_response = SatelliteResponse(results=satellite_results)
        verdicts = compare_claims_to_data(extraction.claims, satellite_results)

        misleading_count = sum(1 for v in verdicts if v.verdict == "misleading")
        warning_count = sum(1 for v in verdicts if v.verdict == "warning")
        verified_count = sum(1 for v in verdicts if v.verdict == "verified")

        yield sse_event("thinking", {
            "step": "done",
            "message": f"Analysis complete: {misleading_count} misleading, {warning_count} warnings, {verified_count} verified",
            "detail": "Ready to display results",
        })

        # Final result
        final = {
            "extraction": extraction.model_dump(),
            "satellite_data": satellite_response.model_dump(),
            "verdicts": [v.model_dump() for v in verdicts],
            "agents_called": agents_to_run,
            "location_resolved": coords,
            "agent_errors": errors,
        }
        yield sse_event("result", final)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
