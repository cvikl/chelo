import json, math, getpass, requests, rasterio, time, logging
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

# 1. SILENCE THE WARNINGS
logging.getLogger('rasterio').setLevel(logging.ERROR)

# --- CONFIG ---
USER = ""
PASS = ""

# NEW TEST AREA: Valtournenche Valley (Meadows & Forests)
BBOX = [7.58, 45.85, 7.64, 45.89] 
YEARS = [2021, 2022, 2023, 2024]
RES = 20 
OUT = Path("./analysis_output")
OUT.mkdir(exist_ok=True)

AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROC_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

def get_token(u, p):
    r = requests.post(AUTH_URL, data={"grant_type":"password","client_id":"cdse-public","username":u,"password":p})
    r.raise_for_status()
    return r.json()["access_token"]

def get_dates(year, mode):
    if mode == 'snow':
        start = datetime(year-1, 12, 15)
        return [((start + timedelta(weeks=2*i)).strftime("%Y-%m-%d"), 
                 (start + timedelta(weeks=2*i, days=14)).strftime("%Y-%m-%d")) for i in range(5)]
    return [(f"{year}-02-01", f"{year}-02-14"), (f"{year}-04-01", f"{year}-04-14"), (f"{year}-07-01", f"{year}-07-14")]

def fetch_tile(token, bbox, date_range, width, height, retries=3):
    """Fetches a tile with DNS retry logic."""
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["B03", "B04", "B08", "B11"],
        output: { bands: 2, sampleType: "FLOAT32" }
      };
    }
    function evaluatePixel(s) {
      let ndsi = (s.B03 - s.B11) / (s.B03 + s.B11 + 1e-9);
      let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04 + 1e-9);
      return [ndsi, ndvi];
    }
    """
    payload = {
        "input": {
            "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {"timeRange": {"from": f"{date_range[0]}T00:00:00Z", "to": f"{date_range[1]}T23:59:59Z"},
                "maxCloudCoverage": 90, "mosaickingOrder": "leastCC"}
            }]
        },
        "output": {"width": width, "height": height, "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
        "evalscript": evalscript
    }
    
    for attempt in range(retries):
        try:
            with rasterio.Env(GDAL_QUIET=True, CPL_LOG_ERRORS=False):
                res = requests.post(PROC_URL, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30)
                if res.status_code == 200:
                    with rasterio.io.MemoryFile(res.content) as mf:
                        return mf.open().read()
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < retries - 1:
                time.sleep(2)
                continue
            return None

def process_year(token, year):
    s_results, v_results = [], []
    gif_s, gif_v, comp_frame = None, None, None

    for i, d in enumerate(get_dates(year, 'snow')):
        data = fetch_tile(token, BBOX, d, 256, 256)
        if data is not None:
            s_results.append((np.sum(data[0] > 0.4) / data[0].size) * 100)
            if i == 1: 
                gif_s = np.clip(data[0] * 255, 0, 255).astype(np.uint8)
                comp_frame = data[0]
        else: s_results.append(0)

    for i, d in enumerate(get_dates(year, 'veg')):
        data = fetch_tile(token, BBOX, d, 256, 256)
        if data is not None:
            v_results.append((np.sum(data[1] > 0.15) / data[1].size) * 100)
            if i == 2: gif_v = np.clip(data[1] * 255, 0, 255).astype(np.uint8)
        else: v_results.append(0)
    
    return year, s_results, v_results, gif_s, gif_v, comp_frame

def main():
    start_time = time.time()
    token = get_token(USER, PASS)
    
    print(f" Starting Parallel Analysis for {YEARS}...")
    
    with ThreadPoolExecutor(max_workers=len(YEARS)) as executor:
        results = sorted(list(executor.map(lambda y: process_year(token, y), YEARS)), key=lambda x: x[0])

    snow_matrix = [r[1] for r in results]
    veg_matrix  = [r[2] for r in results]
    gif_snow    = [r[3] for r in results if r[3] is not None]
    gif_veg     = [r[4] for r in results if r[4] is not None]
    comp_frames = [r[5] for r in results if r[5] is not None]

    # --- PLOTTING ---
    sm, vm = np.array(snow_matrix).T, np.array(veg_matrix).T
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    
    # 1. SNOW BAR PLOT (Average Stacked)
    snow_colors = plt.cm.Blues(np.linspace(0.4, 0.9, 5))
    
    # We divide by 5 because there are 5 snow sample periods
    sm_avg = sm / 5  

    bottom_s = np.zeros(len(YEARS))
    for i in range(5):
        ax1.bar(YEARS, sm_avg[i], bottom=bottom_s, label=f"Period {i+1}", color=snow_colors[i], edgecolor='white')
        bottom_s += sm_avg[i]
    
    ax1.set_title("Average Snow Coverage (Stacked by Period)")
    ax1.set_ylabel("Average Area Coverage (%)")
    ax1.set_ylim(0, 105)
    ax1.set_xticks(YEARS)
    ax1.legend(title="Timeframe", loc='upper left', bbox_to_anchor=(1, 1))

    # 2. VEGETATION BAR PLOT (Average Stacked)
    veg_colors = plt.cm.Greens(np.linspace(0.4, 0.9, 3))
    v_labels = ['Feb', 'Apr', 'Jul']
    
    # We divide by 3 because there are 3 vegetation sample periods
    vm_avg = vm / 3 

    bottom_v = np.zeros(len(YEARS))
    for i in range(3):
        ax2.bar(YEARS, vm_avg[i], bottom=bottom_v, label=v_labels[i], color=veg_colors[i], edgecolor='white')
        bottom_v += vm_avg[i]
        
    ax2.set_title("Average Vegetation Growth (Stacked by Month)")
    ax2.set_ylabel("Average Area Coverage (%)")
    ax2.set_ylim(0, 105)
    ax2.set_xticks(YEARS)
    ax2.legend(title="Month", loc='upper left', bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig(OUT / "coverage_trends.png")


    # GIF Gen (Slower duration: 1500ms)
    for frames, name in [(gif_snow, "snow.gif"), (gif_veg, "veg.gif")]:
        if frames:
            imgs = [Image.fromarray(f) for f in frames]
            imgs[0].save(OUT/name, save_all=True, append_images=imgs[1:], duration=1500, loop=0)

    # Comparison Plot
    if len(comp_frames) >= 2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        ax1.imshow(comp_frames[0], cmap='Blues_r'); ax1.set_title(f"Snow {YEARS[0]}")
        ax2.imshow(comp_frames[-1], cmap='Blues_r'); ax2.set_title(f"Snow {YEARS[-1]}")
        plt.savefig(OUT / "snow_comparison.png")

    print(f"\n Done! Total Time: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    main()