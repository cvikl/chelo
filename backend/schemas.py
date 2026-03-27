from pydantic import BaseModel


class Location(BaseModel):
    name: str
    lat: float
    lon: float
    bbox: list[float] | None = None  # [min_lon, min_lat, max_lon, max_lat]


class Claim(BaseModel):
    id: str
    text: str
    type: str  # snow_cover, glacier_extent, temperature, vegetation, etc.
    direction: str  # increasing, decreasing, stable, denial, exaggeration
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
    time_series: list[dict] | None = None
    trend: str  # increasing, decreasing, stable
    change_percent: float | None = None
    confidence: float | None = None
    visualization_url: str | None = None
    summary: str | None = None


class SatelliteResponse(BaseModel):
    results: list[SatelliteDataPoint]


class ClaimVerdict(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: str
    claim_direction: str
    satellite_trend: str
    satellite_change_percent: float | None
    verdict: str  # verified, misleading, unverifiable, partially_true
    explanation: str


class FullAnalysis(BaseModel):
    extraction: ExtractionResult
    satellite_data: SatelliteResponse | None = None
    verdicts: list[ClaimVerdict] | None = None
