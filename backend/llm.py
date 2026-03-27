import json
import os

from google import genai
from google.genai import types

from schemas import ExtractionResult

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set. Get one at https://aistudio.google.com/apikey")
        _client = genai.Client(api_key=api_key)
    return _client

EXTRACTION_PROMPT = """You are an expert climate scientist and fact-checker specializing in the Alpine region.

Analyze the following article and extract:

1. **Location**: The specific Alpine location(s) mentioned. Provide the most specific location with lat/lon coordinates and an optional bounding box [min_lon, min_lat, max_lon, max_lat] covering the area discussed.

2. **Time range**: The time period the article discusses. Provide start and end dates in YYYY-MM-DD format. If only a year is mentioned, use January 1 as start and December 31 as end.

3. **Parameters requested**: Which environmental parameters should be checked via satellite data. Choose from:
   - snow_cover (snow extent, snow depth, snow duration)
   - glacier_extent (glacier area, retreat, volume)
   - temperature (surface temperature trends)
   - vegetation (greening, NDVI, treeline shifts)
   - permafrost (thawing indicators)
   - precipitation (rainfall, snowfall patterns)
   - land_cover (land use changes)

4. **Claims**: Extract each factual claim about climate/environmental change. For each claim:
   - Provide the exact or paraphrased text
   - Classify its type (matching parameters above)
   - Classify its direction: "increasing", "decreasing", "stable", "denial" (denies change), "exaggeration" (overstates change)
   - Note the time reference if any

5. **Article summary**: A 1-2 sentence summary of the article's main argument.

You MUST respond with valid JSON matching this exact schema:
{
  "location": {"name": "string", "lat": float, "lon": float, "bbox": [float, float, float, float] or null},
  "time_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "parameters_requested": ["string"],
  "claims": [
    {
      "id": "claim_1",
      "text": "string",
      "type": "string",
      "direction": "string",
      "time_reference": "string or null"
    }
  ],
  "article_summary": "string"
}

Article to analyze:
"""


async def extract_claims(article_text: str) -> ExtractionResult:
    response = get_client().models.generate_content(
        model="gemini-2.0-flash",
        contents=EXTRACTION_PROMPT + article_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    data = json.loads(response.text)
    return ExtractionResult(**data)
