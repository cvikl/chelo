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

EXTRACTION_PROMPT = """You are a climate fact-checker for the Alpine region.

Analyze this article and extract the factual claims that can be verified with climate data.

RULES:
- Only extract claims about measurable environmental parameters (temperature, snow, glaciers, precipitation, vegetation)
- Each claim should be a single, specific, verifiable statement — not a general opinion or framing
- The exact_quote MUST be a verbatim substring copied from the article text, not paraphrased
- For time_range: use the dates the article discusses. If "since 2005", start is 2005. If no end date, use 2024-12-31. Never go earlier than 1940.
- For location: pick the most specific location mentioned. Provide accurate lat/lon.

Parameters to check (only these 5). Each has a data availability range — only request a parameter if the article's time range overlaps with its data:
- temperature: air temperature trends, warming rate. Data from 1940.
- precipitation: rainfall vs snowfall, totals, snow-to-rain ratio. Data from 1940.
- snow_cover: snow extent, depth, duration, snowpack. Data from 2000.
- glacier_extent: glacier area, retreat, thickness. Baseline ~2000, imagery from 2015.
- vegetation: greening, treeline shifts, growing season. Data from 2015.

Claim direction:
- "stable": article says no change
- "denial": article denies well-known change
- "increasing" / "decreasing": article claims a directional trend
- "exaggeration": article overstates a change

Severity:
- "high": directly contradicts well-documented scientific consensus
- "medium": misleading framing or cherry-picking
- "low": minor or ambiguous

Respond with JSON:
{
  "location": {"name": "string", "lat": float, "lon": float, "bbox": [float,float,float,float] or null},
  "time_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "parameters_requested": ["string"],
  "claims": [
    {
      "id": "claim_1",
      "text": "short paraphrase",
      "exact_quote": "verbatim text from article",
      "type": "parameter_type",
      "direction": "stable|denial|increasing|decreasing|exaggeration",
      "severity": "high|medium|low",
      "time_reference": "e.g. 2005-2024 or null"
    }
  ],
  "article_summary": "1-2 sentence summary"
}

Article:
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

    # Clamp time_range to data availability (1940+)
    tr = data.get("time_range", {})
    start = tr.get("start", "1940-01-01")
    if start < "1940-01-01":
        tr["start"] = "1940-01-01"
    data["time_range"] = tr

    return ExtractionResult(**data)
