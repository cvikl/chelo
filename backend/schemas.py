from pydantic import BaseModel


class Location(BaseModel):
    name: str
    lat: float
    lon: float
    bbox: list[float] | None = None  # [min_lon, min_lat, max_lon, max_lat]


class Claim(BaseModel):
    id: str
    text: str  # paraphrased claim
    exact_quote: str  # exact text from the article to highlight
    type: str  # snow_cover, glacier_extent, temperature, vegetation, precipitation
    direction: str  # increasing, decreasing, stable, denial, exaggeration
    severity: str  # high, medium, low — how strong/dangerous the claim is
    time_reference: str | None = None


class ExtractionResult(BaseModel):
    location: Location
    time_range: dict  # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    parameters_requested: list[str]
    claims: list[Claim]
    article_summary: str


class ArticleRequest(BaseModel):
    article_text: str


class SatelliteDataPoint(BaseModel):
    parameter: str
    source: str | None = None
    unit: str | None = None
    time_series: list[dict] | None = None
    trend: str  # increasing, decreasing, stable
    change_percent: float | None = None
    confidence: float | None = None
    summary: str | None = None


class SatelliteResponse(BaseModel):
    results: list[SatelliteDataPoint]


class ClaimVerdict(BaseModel):
    claim_id: str
    claim_text: str
    exact_quote: str
    claim_type: str
    claim_direction: str
    severity: str
    satellite_trend: str
    satellite_change_percent: float | None
    satellite_data: SatelliteDataPoint | None = None
    verdict: str  # verified, misleading, unverifiable, warning
    explanation: str


class FullAnalysis(BaseModel):
    extraction: ExtractionResult
    satellite_data: SatelliteResponse | None = None
    verdicts: list[ClaimVerdict] | None = None
