import httpx

# Known Alpine locations for fast lookup (no API call needed)
ALPINE_LOCATIONS = {
    "mont blanc": {"lat": 45.8326, "lon": 6.8652, "bbox": [6.7, 45.7, 7.0, 45.95]},
    "mont-blanc": {"lat": 45.8326, "lon": 6.8652, "bbox": [6.7, 45.7, 7.0, 45.95]},
    "chamonix": {"lat": 45.9237, "lon": 6.8694, "bbox": [6.75, 45.85, 6.98, 46.0]},
    "matterhorn": {"lat": 45.9763, "lon": 7.6586, "bbox": [7.55, 45.9, 7.75, 46.05]},
    "zermatt": {"lat": 46.0207, "lon": 7.7491, "bbox": [7.65, 45.95, 7.85, 46.1]},
    "jungfrau": {"lat": 46.5372, "lon": 7.9616, "bbox": [7.85, 46.45, 8.1, 46.65]},
    "innsbruck": {"lat": 47.2692, "lon": 11.4041, "bbox": [11.2, 47.15, 11.6, 47.4]},
    "davos": {"lat": 46.8027, "lon": 9.8360, "bbox": [9.7, 46.7, 9.95, 46.9]},
    "st. moritz": {"lat": 46.4908, "lon": 9.8355, "bbox": [9.7, 46.4, 9.95, 46.58]},
    "aletsch": {"lat": 46.45, "lon": 8.05, "bbox": [7.9, 46.35, 8.15, 46.55]},
    "aletsch glacier": {"lat": 46.45, "lon": 8.05, "bbox": [7.9, 46.35, 8.15, 46.55]},
    "aletsch glacier region": {"lat": 46.45, "lon": 8.05, "bbox": [7.9, 46.35, 8.15, 46.55]},
    "aletsch region": {"lat": 46.45, "lon": 8.05, "bbox": [7.9, 46.35, 8.15, 46.55]},
    "dolomites": {"lat": 46.4102, "lon": 11.8440, "bbox": [11.5, 46.2, 12.2, 46.7]},
    "tyrol": {"lat": 47.2533, "lon": 11.6015, "bbox": [10.5, 46.75, 12.7, 47.6]},
    "swiss alps": {"lat": 46.8, "lon": 8.2, "bbox": [6.5, 45.8, 10.5, 47.8]},
    "french alps": {"lat": 45.5, "lon": 6.5, "bbox": [5.5, 44.5, 7.5, 46.5]},
    "italian alps": {"lat": 46.0, "lon": 11.0, "bbox": [6.6, 44.0, 13.8, 47.0]},
    "austrian alps": {"lat": 47.0, "lon": 13.0, "bbox": [9.5, 46.4, 17.2, 47.8]},
    "alps": {"lat": 46.5, "lon": 9.0, "bbox": [5.5, 43.5, 16.5, 48.5]},
    "the alps": {"lat": 46.5, "lon": 9.0, "bbox": [5.5, 43.5, 16.5, 48.5]},
    "alpine region": {"lat": 46.5, "lon": 9.0, "bbox": [5.5, 43.5, 16.5, 48.5]},
    "grossglockner": {"lat": 47.0742, "lon": 12.6947, "bbox": [12.6, 47.0, 12.8, 47.15]},
    "zugspitze": {"lat": 47.4211, "lon": 10.9853, "bbox": [10.9, 47.35, 11.1, 47.5]},
    "triglav": {"lat": 46.3786, "lon": 13.8364, "bbox": [13.7, 46.3, 13.95, 46.45]},
    "bernese alps": {"lat": 46.55, "lon": 7.9, "bbox": [7.3, 46.3, 8.5, 46.8]},
    "gran paradiso": {"lat": 45.5186, "lon": 7.2661, "bbox": [7.1, 45.4, 7.45, 45.65]},
}


async def geocode(location_name: str) -> dict:
    """Convert a location name to coordinates. Tries local lookup first, then Nominatim."""
    normalized = location_name.lower().strip()

    # Check local cache first
    if normalized in ALPINE_LOCATIONS:
        result = ALPINE_LOCATIONS[normalized]
        return {
            "lat": result["lat"],
            "lon": result["lon"],
            "bbox": result["bbox"],
            "source": "local",
        }

    # Fallback to OpenStreetMap Nominatim (free, no key needed)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{location_name}, Alps",
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            },
            headers={"User-Agent": "AlpineCheck-Hackathon/1.0"},
        )
        results = response.json()

        if not results:
            # Try without "Alps" qualifier
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": location_name,
                    "format": "json",
                    "limit": 1,
                },
                headers={"User-Agent": "AlpineCheck-Hackathon/1.0"},
            )
            results = response.json()

        if results:
            r = results[0]
            lat = float(r["lat"])
            lon = float(r["lon"])
            bbox = None
            if "boundingbox" in r:
                bb = r["boundingbox"]
                bbox = [float(bb[2]), float(bb[0]), float(bb[3]), float(bb[1])]
            return {
                "lat": lat,
                "lon": lon,
                "bbox": bbox,
                "source": "nominatim",
            }

    raise ValueError(f"Could not geocode location: {location_name}")
