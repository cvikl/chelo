# Triglav

AI-powered fact-checking for Alpine climate claims using satellite data.

Built for [SpaceHACK for Sustainability 2026](https://www.spacehack4sustainability.com/) — Track: Climate Disinformation and the Alps.

## What it does

Paste a climate article about the Alps. Triglav extracts every verifiable claim, fetches real satellite and ground station data, runs AI analysis, and highlights what's true, what's misleading, and what's a warning — with charts, satellite imagery, and evidence for each claim.

## Architecture

```
Article → LLM Claim Extraction → Geocoding → 5 Parallel Agents → Comparison → Verdicts
```

**Five specialized agents**, each fetching real data:

| Agent | Data Source | What it checks |
|-------|-----------|---------------|
| Temperature | Open-Meteo ERA5 + Google Earth Engine Landsat | Warming trends, annual means |
| Precipitation | Open-Meteo ERA5 | Snowfall decline, rain-to-snow shift |
| Snow Cover | Open-Meteo ERA5 + Sentinel-2 NDSI | Snow-covered days, snow depth |
| Glacier Extent | Sentinel-2 L2A + UNet segmentation model | Glacier area from satellite imagery |
| Vegetation | Sentinel-2 NDVI + Copernicus DEM | Greening trends, vegetation line migration |

## Key features

- Real satellite data (Sentinel-2, Landsat, ERA5) — no mock data
- Trained glacier segmentation model (UNet ResNet34, Jaccard=0.89)
- Vegetation line analysis (highest altitude where plants grow, tracked over time)
- Article text highlighting (red = misleading, yellow = warning, green = verified)
- Click any highlight to see satellite evidence, charts, and GIFs
- Live progress streaming during analysis

## Tech stack

**Backend:** Python, FastAPI, PyTorch, Rasterio, Google Earth Engine
**Frontend:** React, Vite
**LLM:** Google Gemini
**Data:** Element84 Earth Search (Sentinel-2), Open-Meteo, Copernicus DEM

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with your Gemini API key
cp .env.example .env
# Edit .env: GEMINI_API_KEY=your_key_here

python main.py
```

Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Glacier model

Download the checkpoint file (not included in repo due to size) and place it in the project root:
```
ckpt-epoch=29-w_JaccardIndex_val_epoch_avg_per_g=0.8935.ckpt
```

### Optional: Google Earth Engine

```bash
pip install earthengine-api
python -c "import ee; ee.Authenticate()"
```

## Data sources

- [Copernicus Sentinel-2](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2) — glacier extent, snow NDSI, vegetation NDVI
- [Open-Meteo ERA5](https://open-meteo.com/en/docs/historical-weather-api) — temperature, precipitation, snow depth
- [Copernicus GLO-30 DEM](https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model) — elevation for vegetation line analysis
- [Landsat 8 via Google Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2) — land surface temperature

## Team

Built during SpaceHACK for Sustainability 2026.
