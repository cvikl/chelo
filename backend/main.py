from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from comparator import compare_claims_to_data
from llm import extract_claims
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


@app.post("/api/extract", response_model=ExtractionResult)
async def extract_article(request: ArticleRequest):
    """Step 1: Extract claims and parameters from an article using Gemini."""
    global current_extraction
    try:
        result = await extract_claims(request.article_text)
        current_extraction = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")


@app.get("/api/extraction", response_model=ExtractionResult | None)
async def get_current_extraction():
    """Get the current extraction result."""
    return current_extraction


@app.post("/api/satellite-data", response_model=FullAnalysis)
async def receive_satellite_data(satellite_response: SatelliteResponse):
    """Step 2: Receive satellite data from the visual recognition team and compare."""
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


@app.post("/api/analyze", response_model=FullAnalysis)
async def full_analyze(request: ArticleRequest):
    """Full pipeline: extract + compare with mock satellite data (for testing/demo)."""
    global current_extraction
    try:
        extraction = await extract_claims(request.article_text)
        current_extraction = extraction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    # Mock satellite data for demo — replace with real data from friends' pipeline
    mock_satellite = SatelliteResponse(
        results=[
            SatelliteDataPoint(
                parameter="snow_cover",
                trend="decreasing",
                change_percent=-18.5,
                confidence=0.92,
                summary="Snow cover in the region has decreased by 18.5% over the analyzed period.",
            ),
            SatelliteDataPoint(
                parameter="glacier_extent",
                trend="decreasing",
                change_percent=-12.3,
                confidence=0.88,
                summary="Glacier extent has shrunk by 12.3% compared to RGI baseline.",
            ),
            SatelliteDataPoint(
                parameter="temperature",
                trend="increasing",
                change_percent=2.1,
                confidence=0.95,
                summary="Mean surface temperature has increased by approximately 2.1C.",
            ),
            SatelliteDataPoint(
                parameter="vegetation",
                trend="increasing",
                change_percent=8.7,
                confidence=0.78,
                summary="NDVI indicates greening trend with 8.7% increase in vegetation index.",
            ),
        ]
    )

    verdicts = compare_claims_to_data(extraction.claims, mock_satellite.results)

    return FullAnalysis(
        extraction=extraction,
        satellite_data=mock_satellite,
        verdicts=verdicts,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
