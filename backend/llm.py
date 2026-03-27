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
Your job is to thoroughly analyze a climate article and extract EVERY verifiable claim for fact-checking against satellite and ground-station data.

Be aggressive in finding claims. Look for:
- Explicit statements about environmental trends (snow, glaciers, temperature, rain, vegetation)
- Implicit claims hidden in anecdotes or quotes
- Claims disguised as "observations" from non-scientific sources
- Minimizing language ("only", "minor", "merely", "just")
- Denial language ("no evidence", "hasn't changed", "remained stable")

For EACH claim, you must extract the EXACT QUOTE from the article — the precise sentence or phrase as it appears in the text. This will be used to highlight it in the article. The exact_quote MUST be a substring that appears verbatim in the article.

Classify severity:
- "high": Direct denial or major misrepresentation of well-documented trends
- "medium": Misleading framing, cherry-picking, or minimizing real changes
- "low": Minor inaccuracy or ambiguous claim

Decide which parameters need checking. Choose ALL that apply from:
- snow_cover (snow extent, depth, duration, snowpack, ski season length)
- glacier_extent (glacier area, retreat, thickness, volume, terminus position)
- temperature (surface temperature, warming rate, seasonal temperatures)
- vegetation (greening, NDVI, treeline shifts, growing season, species migration)
- precipitation (rainfall, snowfall, snow-to-rain ratio, annual totals)

You MUST respond with valid JSON matching this exact schema:
{
  "location": {"name": "string", "lat": float, "lon": float, "bbox": [float, float, float, float] or null},
  "time_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "parameters_requested": ["string"],
  "claims": [
    {
      "id": "claim_1",
      "text": "paraphrased claim summary",
      "exact_quote": "exact text from the article to highlight",
      "type": "parameter_type",
      "direction": "increasing|decreasing|stable|denial|exaggeration",
      "severity": "high|medium|low",
      "time_reference": "string or null"
    }
  ],
  "article_summary": "string"
}

Extract as many claims as you can find. Be thorough — miss nothing.

Article to analyze:
"""


async def extract_claims(article_text: str) -> ExtractionResult:
    response = get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=EXTRACTION_PROMPT + article_text,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    data = json.loads(response.text)
    return ExtractionResult(**data)
