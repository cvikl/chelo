# Triglav - AI-Powered Climate Fact-Checking for the Alps

## Project Overview

Triglav is a fact-checking system that uses satellite data and AI to verify climate claims about the Alpine region. Built for the SpaceHACK for Sustainability 2026 hackathon (Track: Climate Disinformation and the Alps), it combines LLM-based claim extraction, real satellite imagery, ground station data, and deep learning glacier segmentation to produce evidence-based verdicts on climate articles.

The system takes a news article as input, extracts verifiable climate claims, fetches real satellite and ground data for the referenced location and time period, and produces visual, data-backed verdicts highlighting misleading or verified statements.

---

## Architecture

```
Article Text
    |
    v
+-------------------+
| Orchestrator (LLM)|  Gemini 2.5 Flash
| Claim Extraction  |  Extracts: location, time range, claims, parameters
+-------------------+
    |
    v
+-------------------+
| Geocoder          |  Nominatim OSM / local cache
| Location -> Coords|  30+ pre-cached Alpine locations
+-------------------+
    |
    v
+-----------------------------------+
| Parallel Agent Dispatch           |
|                                   |
| +-------------+ +---------------+ |
| | Temperature  | | Precipitation | |
| | Open-Meteo   | | Open-Meteo    | |
| | ERA5         | | ERA5          | |
| +-------------+ +---------------+ |
|                                   |
| +-------------+ +---------------+ |
| | Snow Cover  | | Glacier Extent | |
| | Open-Meteo  | | Sentinel-2     | |
| | + Sentinel-2 | | + UNet Model   | |
| | NDSI        | | + DEM          | |
| +-------------+ +---------------+ |
|                                   |
| +-------------+                   |
| | Vegetation  |                   |
| | Sentinel-2  |                   |
| | NDVI + DEM  |                   |
| | Veg. Line   |                   |
| +-------------+                   |
+-----------------------------------+
    |
    v
+-------------------+
| Comparator        |  Claim direction vs satellite trend
| Verdict Engine    |  -> verified / misleading / warning / unverifiable
+-------------------+
    |
    v
+-------------------+
| React Frontend    |  Annotated article + popup details
| Sidebar Layout    |  Charts, GIFs, satellite maps
+-------------------+
```

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Web server | FastAPI (Python) |
| LLM | Google Gemini 2.5 Flash |
| Climate data | Open-Meteo Historical Archive (ERA5 reanalysis) |
| Satellite imagery | Sentinel-2 L2A via Element84 Earth Search STAC (free, no auth) |
| DEM data | Copernicus GLO-30 via Element84 (free, no auth) |
| Glacier model | PyTorch UNet (ResNet34 encoder, segmentation_models_pytorch) |
| Geocoding | Nominatim OpenStreetMap (free, no auth) |
| Visualization | Google Earth Engine (Landsat LST, optional) |
| Data processing | NumPy, SciPy, Matplotlib, Rasterio, PyProj |
| Streaming | Server-Sent Events (SSE) |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React (Vite) |
| Styling | Custom CSS (Tailwind-inspired, DM Sans font) |
| Maps | OpenStreetMap iframe embed |
| Charts | Base64-encoded Matplotlib PNG + SVG mini charts |
| Animations | Base64-encoded GIFs from satellite data |
| Streaming | Fetch API SSE consumer |

---

## Data Sources & Availability

| Agent | Data Source | Time Range | Resolution | Access |
|-------|-----------|-----------|------------|--------|
| Temperature | Open-Meteo ERA5 | 1940 - present | Daily, ~30km | Free API, no auth |
| Precipitation | Open-Meteo ERA5 | 1940 - present | Daily, ~30km | Free API, no auth |
| Snow Cover | Open-Meteo ERA5 + Sentinel-2 NDSI | 2000 - present (snow depth) / 2017+ (NDSI) | Daily (depth), 10-20m (NDSI) | Free API + Element84 |
| Glacier Extent | Sentinel-2 L2A + Copernicus DEM | 2017 - present | 10-20m (S2), 30m (DEM) | Element84 (free) |
| Vegetation | Sentinel-2 L2A + Copernicus DEM | 2015 - present | 10-20m | Element84 (free) |
| Land Surface Temp | Landsat 8 via GEE | 2013 - present | 30m (thermal 100m) | GEE (requires auth) |

### Date Unification
When multiple agents are called, the system automatically adjusts all agents to use the same time window based on the latest data source start date. For example, if temperature (1940+) and glacier (2017+) are both requested, all agents use 2017 as the start.

---

## Backend Components

### main.py - FastAPI Application

The central server that orchestrates the pipeline. Key endpoints:

- `POST /api/analyze` - Full streaming pipeline (SSE). Extracts claims, geocodes, dispatches agents in parallel, compares, returns verdicts with real-time thinking steps.
- `POST /api/extract` - LLM claim extraction only.
- `POST /api/satellite-data` - Receives pre-computed satellite data for comparison.

Sets `AWS_NO_SIGN_REQUEST=YES` for unauthenticated access to public S3 Sentinel-2 COGs.

### llm.py - LLM Claim Extraction

Interfaces with Google Gemini 2.5 Flash. The extraction prompt instructs the model to:
- Extract only measurable environmental claims (temperature, snow, glaciers, precipitation, vegetation)
- Provide exact verbatim quotes from the article for text highlighting
- Classify claim direction: stable, denial, increasing, decreasing, exaggeration
- Classify severity: high (contradicts consensus), medium (misleading framing), low (minor)
- Respect data availability ranges (temperature from 1940, vegetation from 2015, etc.)
- Clamp all dates to valid ranges (never earlier than 1940)

### schemas.py - Data Models

Pydantic models for type-safe data flow:
- `Claim` - Single claim with `exact_quote`, `type`, `direction`, `severity`
- `SatelliteDataPoint` - Agent result with `trend`, `change_percent`, `plot_base64`, `gif_base64`
- `ClaimVerdict` - Final verdict with `verdict`, `explanation`, embedded satellite data

### orchestrator.py - Agent Coordinator

Dispatches agents in parallel using `asyncio.gather`. Maps parameter names to agent modules via `AGENT_REGISTRY`. Collects results and errors.

### comparator.py - Verdict Engine

Compares each claim's direction against satellite-measured trend using a truth table:

| Claim Direction | Satellite Trend | Verdict |
|----------------|----------------|---------|
| stable | increasing | misleading |
| stable | decreasing | misleading |
| stable | stable | verified |
| denial | increasing | misleading |
| denial | decreasing | misleading |
| denial | stable | warning |
| increasing | increasing | verified |
| increasing | decreasing | misleading |
| decreasing | decreasing | verified |
| exaggeration | stable | misleading |

Generates human-readable explanations with specific data values.

### geocoder.py - Location Resolution

Two-step geocoding:
1. **Local cache** - 30+ pre-cached Alpine locations (Aletsch, Mont Blanc, Jungfrau, Matterhorn, Zermatt, Davos, Dolomites, Tyrol, etc.) with accurate coordinates and bounding boxes.
2. **Nominatim fallback** - Free OpenStreetMap API for any location worldwide. Tries with "Alps" qualifier first, then without.

---

## Agent Details

### Temperature Agent (`agents/temperature.py`)

**Data source:** Open-Meteo ERA5 archive API (daily mean temperature)

**Process:**
1. Fetch daily temperature data for the location and time range
2. Compute linear regression for trend (warming per decade)
3. Aggregate to yearly statistics (mean, min, max)
4. Generate matplotlib plot (daily scatter + trend line + yearly means)
5. Optionally generate GEE Landsat Land Surface Temperature GIF

**Output metrics:**
- Warming rate (C/decade)
- Total temperature change (C)
- Trend direction (increasing if > 0.1C/decade)
- Confidence: 0.95

### Precipitation Agent (`agents/precipitation.py`)

**Data source:** Open-Meteo ERA5 archive API (daily snowfall_sum, precipitation_sum, rain_sum)

**Process:**
1. Fetch daily snowfall and precipitation data
2. Aggregate yearly: total precip, rain, snowfall, snow days, snow fraction
3. Compute trends: total precipitation, rain vs snow shift, snow fraction change
4. Generate 3-panel plot: total precipitation, rain vs snow (stacked), snow fraction

**Key insight:** A decrease in snowfall does NOT mean less total precipitation -- it often means more rain. The agent separates these signals and reports the snow-to-rain shift.

**Output metrics:**
- Total precipitation change (%)
- Snow days change per decade
- Snow fraction change (percentage points/decade)
- Confidence: 0.90

### Snow Cover Agent (`agents/snow_cover.py`)

**Data sources:**
- Open-Meteo ERA5 (daily snow depth and snowfall for quantitative trends)
- Sentinel-2 NDSI via Element84 (satellite snow maps for visualization)

**Process:**
1. Fetch daily snow depth data, count snow-covered days (>1cm depth)
2. Compute trends in snow days and mean snow depth
3. Fetch winter Sentinel-2 tiles (Jan-March) for each year
4. Compute NDSI (Green - SWIR) / (Green + SWIR) maps
5. Generate GIF animation of NDSI snow maps across years
6. Generate plot with snow days trend, depth trend, and NDSI difference map

**Output metrics:**
- Snow-covered days change (%)
- Snow depth trend (cm/decade)
- NDSI satellite animation (GIF)
- Confidence: 0.92

### Glacier Extent Agent (`agents/glacier_extent.py`)

**Data sources:**
- Sentinel-2 L2A via Element84 (16-band imagery)
- Copernicus GLO-30 DEM (elevation + slope)
- Pre-trained UNet glacier segmentation model (DL4GAM)

**Process:**
1. Snap coordinates to nearest known glacier center (within 15km)
2. Search for summer (July-August preferred) Sentinel-2 tiles for start and end years
3. Fetch DEM tile from Copernicus GLO-30
4. Build 16-channel DL4GAM stack: 13 S2 bands + DEM + dh/dt + slope
5. Apply DL4GAM normalization (Z-score optical, mean-center DEM/dhdt, /90 slope)
6. Run UNet inference to produce glacier probability maps
7. Threshold at 0.5 for binary masks, calculate area in km2
8. Generate 2x3 visualization: RGB composites, glacier probability maps, change intensity

**Glacier Model (agents/glacier_model.py):**
- Architecture: UNet with ResNet34 encoder
- Input: 16 channels (13 Sentinel-2 bands + DEM + dh/dt + slope)
- Output: 1 class (binary glacier/no-glacier)
- Validation Jaccard Index: 0.8935
- Training: DL4GAM framework (Diaconu et al., 2024)

**Normalization (critical for accuracy):**
- Optical bands (0-12): Z-score with global Alps stats (mean=0.25, std=0.20)
- DEM (band 13): subtract mean only (2700m), NOT divided by std
- dh/dt (band 14): subtract mean only (-0.3 m/yr)
- Slope (band 15): divide by 90 to scale to [0, 1]

**Output metrics:**
- Glacier area at start and end (km2)
- Area change (%)
- Actual Sentinel-2 tile IDs and dates used
- Confidence: 0.89

### Vegetation Agent (`agents/vegetation.py`)

**Data sources:**
- Sentinel-2 L2A via Element84 (NIR and Red bands for NDVI)
- Copernicus GLO-30 DEM (for vegetation line calculation)

**Process:**
1. Fetch summer Sentinel-2 tiles for each year
2. Compute NDVI = (NIR - Red) / (NIR + Red) for each tile
3. Fetch DEM and compute vegetation line:
   - Divide terrain into 50m elevation bands
   - For each band, calculate fraction of pixels with NDVI > 0.15
   - Find highest band where >= 5% of pixels are vegetated
   - Track this "vegetation line" across years
4. Generate multi-panel plot: NDVI maps (first/last year), NDVI trend, vegetation line trend
5. Generate NDVI GIF animation across years

**Vegetation cover vs. vegetation line:**
- **Vegetation cover (NDVI):** How green an area is. Shows overall greening/browning trends.
- **Vegetation line:** The altitude boundary where vegetation stops growing. As climate warms, this line moves upward -- plants colonize previously barren high-altitude terrain. This is a separate, powerful indicator of climate change.

**Output metrics:**
- Mean NDVI change (%)
- NDVI trend per decade
- Vegetation line elevation per year (meters above sea level)
- Vegetation line migration rate (m/decade)
- Confidence: 0.85

---

## Frontend Components

### App.jsx - Main Layout

Two-column layout with sidebar:
- **Main column:** Article input -> Thinking panel -> Results (LocationInfo, AnnotatedArticle, VerdictPanel)
- **Sidebar:** Opens when a claim is clicked, shows FactCheckPopup with detailed evidence

### ArticleInput.jsx - Article Entry

Textarea with two demo articles pre-loaded:
- **Misleading article** - Makes false claims about the Aletsch Glacier region (2017-2023): no warming, stable snow, no precipitation shift, no glacier retreat, no vegetation change
- **Accurate article** - Matches real measured data with correct numbers and honest caveats

### AnnotatedArticle.jsx - Highlighted Text

Renders the original article with inline highlighting:
- **Red** = misleading (contradicted by satellite data)
- **Yellow** = warning (potentially misleading framing)
- **Green** = verified (supported by data)
- **Gray** = unverifiable (no data available)

Click any highlighted section to open the detailed fact-check sidebar.

### FactCheckPopup.jsx - Evidence Panel

Detailed sidebar showing:
1. Verdict badge (Verified/Misleading/Warning) with severity level
2. Exact quote from the article
3. Satellite evidence explanation
4. Statistics grid: trend, change %, confidence, data source
5. GIF animation (if available): satellite imagery cycling through years
6. Data visualization: matplotlib charts (clickable to expand full-screen)
7. Mini SVG chart fallback (if no matplotlib plot)

### ThinkingPanel.jsx - Live Progress

Streams real-time thinking steps during analysis:
- Orchestrator reading article
- Claim extraction complete (shows found claims)
- Geocoding location
- Agent dispatch (shows which agents are running)
- Individual agent completions with results
- Comparison step
- Final summary (X misleading, Y warnings, Z verified)

### VerdictPanel.jsx - Summary

Overview of all verdicts with:
- Count badges (misleading, warning, verified, total)
- Satellite data source cards with confidence indicators

### LocationInfo.jsx - Metadata & Map

Displays:
- Article summary
- Time period (formatted as DD.MM.YYYY)
- Parameters being checked (colored tags)
- Location name with coordinates
- Embedded OpenStreetMap centered on the detected location

---

## Standalone Scripts

These scripts were developed by team members and their core functionality has been integrated into the backend agents. They remain available as standalone tools.

### scripts/temp.py
Temperature and snow day analysis using Open-Meteo. Generates trend plots and fact-check summaries. Author: Fedja.

### scripts/Sentinel2_downloader.py
Comprehensive Sentinel-2 analysis with NDSI snow mapping, NDVI vegetation analysis, vegetation line calculation, and GIF generation. Uses Copernicus Data Space API (requires credentials). Author: Vid.

### scripts/dl4gam_stack.py
Production pipeline for building 16-band DL4GAM GeoTIFF stacks from Copernicus Sentinel-2 and DEM data. Documents the exact band order and normalization the glacier model expects. Author: Ziga.

### scripts/glacier_segmentation.py
DL4GAM glacier segmentation inference with proper normalization. Documents critical normalization details (Z-score optical, mean-center DEM, /90 slope). Author: Ziga.

### scripts/seg_model.py
Abstract segmentation model framework using PyTorch and segmentation_models_pytorch. Supports flexible input channel configuration. Author: Ziga.

### scripts/gee.py
Google Earth Engine visualizations for NO2 air pollution and Landsat land surface temperature. Generates interactive HTML maps. Author: teammate.

---

## Setup & Running

### Prerequisites
- Python 3.12+
- Node.js 18+
- Google Gemini API key (free at https://aistudio.google.com/apikey)
- Optional: Google Earth Engine authentication for LST maps
- Optional: The glacier model checkpoint file (281MB, not in git)

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn google-genai pydantic python-dotenv httpx numpy matplotlib rasterio pyproj torch segmentation-models-pytorch scipy pillow

# Create .env file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Start server
python main.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Optional: Google Earth Engine
```bash
pip install earthengine-api geemap
python -c "import ee; ee.Authenticate()"
# Then initialize with your GEE project ID in the temperature agent
```

### Running
1. Start backend: `cd backend && source venv/bin/activate && python main.py`
2. Start frontend: `cd frontend && npm run dev`
3. Open the URL printed by Vite (typically http://localhost:5173)
4. Click "Load Misleading Article" or "Load Accurate Article" to test
5. Click "Analyze Article" and watch the thinking panel stream progress
6. Click highlighted text to see detailed fact-checks with satellite evidence

---

## Key Design Decisions

1. **Real data over mock data** - All 5 agents use real satellite/ground data. Temperature and precipitation from Open-Meteo ERA5. Snow cover combines Open-Meteo depth with Sentinel-2 NDSI maps. Glacier uses real Sentinel-2 tiles through a trained UNet. Vegetation uses real Sentinel-2 NDVI with DEM-based vegetation line analysis.

2. **Date unification** - All agents compare the same time window, determined by the latest data source among requested parameters.

3. **Vegetation line != vegetation cover** - The system tracks both NDVI greening (how green) and the vegetation line (how high plants grow). The vegetation line uses DEM elevation bands to find the highest altitude with significant vegetation.

4. **DL4GAM normalization** - The glacier model requires specific normalization that matches its training: Z-score for optical bands (mean=0.25, std=0.20), mean-centering only for DEM (2700m) and dh/dt (-0.3), and /90 for slope. Getting this wrong produces garbage predictions.

5. **Streaming UX** - SSE streaming shows real-time progress as each agent completes, rather than a blank loading screen.

6. **Honest about limitations** - The glacier agent acknowledges seasonal snow interference. The accurate demo article includes caveats about measurement challenges. The system reports "unverifiable" when data isn't available rather than guessing.

---

## Hackathon Context

**Event:** SpaceHACK for Sustainability 2026 (March 27-28)
**Track:** Climate Disinformation and the Alps
**Challenge:** How can satellite-based Earth observation data help journalists verify climate claims and counter misinformation about the Alpine region?

**Research questions addressed:**
- RQ1: Which Alpine climate impacts are documented by satellite data and which are misrepresented in media?
- RQ3: How can satellite imagery support journalists in verifying climate claims?
- RQ4: Do verification practices using satellite data reduce misinformation?

**Data sources used from the challenge brief:**
- Copernicus Sentinel-2 (glacier extent, snow NDSI, vegetation NDVI)
- MOD10A1.061 (snow cover concept, implemented via Open-Meteo)
- Randolph Glacier Inventory (baseline concept, implemented via DL4GAM model)
- EEAR-Clim (ground-based climate data concept, implemented via Open-Meteo ERA5)

---

## Team

Built during SpaceHACK for Sustainability 2026 by:
- Timotej - System architecture, orchestrator, frontend, agent integration
- Fedja - Temperature analysis (Open-Meteo)
- Vid - Sentinel-2 downloader, snow/vegetation analysis, vegetation line algorithm
- Ziga - DL4GAM glacier segmentation model, 16-band stack builder
