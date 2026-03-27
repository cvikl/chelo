import json, math, getpass, requests, rasterio, time, logging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from scipy.ndimage import zoom   # pip install scipy  (for DEM resize)

logging.getLogger('rasterio').setLevel(logging.ERROR)

# --- CONFIG ---
USER = ""
PASS = ""

BBOX = [7.22, 45.46, 7.30, 45.53] 
YEARS = [2018, 2020, 2022, 2024] 
RES = 20
OUT   = Path("./analysis_output")
OUT.mkdir(exist_ok=True)

# Vegetation line thresholds
NDVI_THRESH      = 0.15   # pixel counts as "vegetated"
PIXEL_FRAC_THRESH = 0.05  # at least 5 % of pixels in band must be vegetated
ELEV_BAND_M      = 50     # elevation band width in metres

AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROC_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"


def get_token(u, p):
    r = requests.post(AUTH_URL, data={"grant_type": "password", "client_id": "cdse-public",
                                       "username": u, "password": p})
    r.raise_for_status()
    return r.json()["access_token"]


def get_dates(year, mode):
    if mode == 'snow':
        start = datetime(year - 1, 12, 15)
        return [((start + timedelta(weeks=2*i)).strftime("%Y-%m-%d"),
                 (start + timedelta(weeks=2*i, days=14)).strftime("%Y-%m-%d")) for i in range(5)]
    return [(f"{year}-02-01", f"{year}-02-14"),
            (f"{year}-04-01", f"{year}-04-14"),
            (f"{year}-07-01", f"{year}-07-14")]


def fetch_tile(token, bbox, date_range, width, height, retries=3):
    """Fetch NDSI + NDVI bands from Sentinel-2."""
    evalscript = """
    //VERSION=3
    function setup() {
      return { input: ["B03","B04","B08","B11"], output: { bands: 2, sampleType: "FLOAT32" } };
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
            "data": [{"type": "sentinel-2-l2a",
                      "dataFilter": {"timeRange": {"from": f"{date_range[0]}T00:00:00Z",
                                                   "to":   f"{date_range[1]}T23:59:59Z"},
                                     "maxCloudCoverage": 90, "mosaickingOrder": "leastCC"}}]
        },
        "output": {"width": width, "height": height,
                   "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
        "evalscript": evalscript
    }
    for attempt in range(retries):
        try:
            with rasterio.Env(GDAL_QUIET=True, CPL_LOG_ERRORS=False):
                res = requests.post(PROC_URL, json=payload,
                                    headers={"Authorization": f"Bearer {token}"}, timeout=30)
                if res.status_code == 200:
                    with rasterio.io.MemoryFile(res.content) as mf:
                        return mf.open().read()
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None


def fetch_dem(token, bbox, width, height, retries=3):
    """
    Fetch Copernicus DEM GLO-30 elevation via Sentinel Hub.
    Returns a (height, width) float32 array in metres.
    """
    evalscript = """
    //VERSION=3
    function setup() {
      return { input: ["DEM"], output: { bands: 1, sampleType: "FLOAT32" } };
    }
    function evaluatePixel(s) { return [s.DEM]; }
    """
    payload = {
        "input": {
            "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{"type": "dem", "dataFilter": {"demInstance": "COPERNICUS_30"}}]
        },
        "output": {"width": width, "height": height,
                   "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
        "evalscript": evalscript
    }
    for attempt in range(retries):
        try:
            with rasterio.Env(GDAL_QUIET=True, CPL_LOG_ERRORS=False):
                res = requests.post(PROC_URL, json=payload,
                                    headers={"Authorization": f"Bearer {token}"}, timeout=30)
                if res.status_code == 200:
                    with rasterio.io.MemoryFile(res.content) as mf:
                        data = mf.open().read()    # shape: (1, H, W)
                        return data[0].astype(np.float32)
                print(f"  DEM fetch failed: HTTP {res.status_code}")
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None


def vegetation_line(ndvi_2d, dem_2d, ndvi_thresh=NDVI_THRESH,
                    pixel_frac=PIXEL_FRAC_THRESH, band_m=ELEV_BAND_M):
    """
    Find the highest elevation band where vegetation is still significant.

    Returns
    -------
    veg_line_m : float or NaN
    band_edges : 1-D array of band lower edges (for plotting)
    band_frac  : fraction of vegetated pixels per band (same length as band_edges)
    """
    elev_flat = dem_2d.ravel()
    ndvi_flat = ndvi_2d.ravel()

    # Remove no-data (negative elevations can mean sea / missing)
    valid = (elev_flat > 0) & np.isfinite(elev_flat) & np.isfinite(ndvi_flat)
    elev_flat = elev_flat[valid]
    ndvi_flat = ndvi_flat[valid]

    if elev_flat.size == 0:
        return np.nan, np.array([]), np.array([])

    e_min = np.floor(elev_flat.min() / band_m) * band_m
    e_max = np.ceil(elev_flat.max()  / band_m) * band_m
    band_edges = np.arange(e_min, e_max, band_m)

    band_frac = []
    for e in band_edges:
        mask = (elev_flat >= e) & (elev_flat < e + band_m)
        if mask.sum() == 0:
            band_frac.append(0.0)
        else:
            band_frac.append(float((ndvi_flat[mask] > ndvi_thresh).mean()))

    band_frac = np.array(band_frac)

    # Highest band that clears the pixel-fraction threshold
    above = np.where(band_frac >= pixel_frac)[0]
    veg_line_m = float(band_edges[above[-1]] + band_m / 2) if above.size else np.nan

    return veg_line_m, band_edges, band_frac


def process_year(token, year, dem):
    s_results, v_results = [], []
    gif_s, gif_v, comp_frame = None, None, None
    ndvi_july = None  # use July (peak growth) for veg-line analysis

    for i, d in enumerate(get_dates(year, 'snow')):
        data = fetch_tile(token, BBOX, d, 256, 256)
        if data is not None:
            s_results.append((np.sum(data[0] > 0.4) / data[0].size) * 100)
            if i == 1:
                gif_s     = np.clip(data[0] * 255, 0, 255).astype(np.uint8)
                comp_frame = data[0]
        else:
            s_results.append(0)

    for i, d in enumerate(get_dates(year, 'veg')):
        data = fetch_tile(token, BBOX, d, 256, 256)
        if data is not None:
            v_results.append((np.sum(data[1] > 0.15) / data[1].size) * 100)
            if i == 2:                          # July
                gif_v    = np.clip(data[1] * 255, 0, 255).astype(np.uint8)
                ndvi_july = data[1]             # shape (256, 256)
        else:
            v_results.append(0)

    # --- Vegetation line from July NDVI + DEM ---
    veg_line_m = np.nan
    band_edges = np.array([])
    band_frac  = np.array([])
    if ndvi_july is not None and dem is not None:
        # DEM is already (256, 256) — same grid
        veg_line_m, band_edges, band_frac = vegetation_line(ndvi_july, dem)
        print(f"  {year}: vegetation line ≈ {veg_line_m:.0f} m a.s.l.")

    return year, s_results, v_results, gif_s, gif_v, comp_frame, veg_line_m, band_edges, band_frac

def make_gif(frames_and_years, out_path, canvas_size=(400, 400), duration=1500):
    """
    Build a GIF from (frame_array, year) pairs.
    - All frames are resized to canvas_size so every year is the same dimensions.
    - The year is rendered in large text at the bottom-centre of each frame.
    """
    from PIL import ImageDraw, ImageFont

    GIF_W, GIF_H = canvas_size
    LABEL_H = 40                        # reserved strip at bottom for the year
    INNER_H = GIF_H - LABEL_H          # image area above the label

    imgs = []
    for arr, year in frames_and_years:
        # --- normalise raw float/uint8 array to 0-255 uint8 ---
        if arr.dtype != np.uint8:
            arr = np.clip(arr * 255, 0, 255).astype(np.uint8)

        # --- resize to fixed inner area (nearest-neighbour keeps index values) ---
        frame_img = Image.fromarray(arr).convert("L")          # grayscale
        frame_img = frame_img.resize((GIF_W, INNER_H), Image.NEAREST)
        frame_rgb = frame_img.convert("RGB")                   # PIL GIF needs palette/RGB

        # --- add label strip ---
        canvas = Image.new("RGB", (GIF_W, GIF_H), color=(20, 20, 20))
        canvas.paste(frame_rgb, (0, 0))

        draw = ImageDraw.Draw(canvas)

        # Try to load a truetype font; fall back to PIL's built-in bitmap font
        font_size = 28
        try:
            # Works on most Linux/Mac systems; adjust path if needed
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except OSError:
                font = ImageFont.load_default()   # tiny but always available

        label = str(year)
        # PIL ≥ 10 uses textbbox; older uses textsize
        try:
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize(label, font=font)

        tx = (GIF_W - tw) // 2
        ty = INNER_H + (LABEL_H - th) // 2

        # Drop shadow for legibility
        draw.text((tx + 2, ty + 2), label, font=font, fill=(0, 0, 0))
        draw.text((tx,     ty    ), label, font=font, fill=(255, 255, 255))

        imgs.append(canvas)

    if imgs:
        imgs[0].save(out_path, save_all=True, append_images=imgs[1:],
                     duration=duration, loop=0)
        print(f"  Saved: {out_path.name}  ({GIF_W}×{GIF_H} px, {len(imgs)} frames)")

def main():
    start_time = time.time()
    token = get_token(USER, PASS)

    # --- Fetch DEM once (elevation doesn't change) ---
    print("Fetching Copernicus DEM GLO-30 …")
    dem = fetch_dem(token, BBOX, 256, 256)
    if dem is None:
        print("  WARNING: DEM fetch failed — vegetation-line analysis will be skipped.")
    else:
        print(f"  DEM ok  elev range {dem.min():.0f} – {dem.max():.0f} m")

    print(f"\nStarting parallel analysis for {YEARS} …")
    with ThreadPoolExecutor(max_workers=len(YEARS)) as executor:
        results = sorted(
            list(executor.map(lambda y: process_year(token, y, dem), YEARS)),
            key=lambda x: x[0]
        )

    snow_matrix  = [r[1] for r in results]
    veg_matrix   = [r[2] for r in results]
    gif_snow     = [r[3] for r in results if r[3] is not None]
    gif_veg      = [r[4] for r in results if r[4] is not None]
    comp_frames  = [r[5] for r in results if r[5] is not None]
    veg_lines    = [r[6] for r in results]           # one value per year
    band_edges_all = [r[7] for r in results]          # per-year elevation bands
    band_frac_all  = [r[8] for r in results]          # per-year vegetated fraction

    # ------------------------------------------------------------------ #
    #  FIGURE 1 — Snow & vegetation coverage (your original plots)        #
    # ------------------------------------------------------------------ #
    sm, vm = np.array(snow_matrix).T, np.array(veg_matrix).T
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

    snow_colors = plt.cm.Blues(np.linspace(0.4, 0.9, 5))
    sm_avg = sm / 5
    bottom_s = np.zeros(len(YEARS))
    for i in range(5):
        ax1.bar(YEARS, sm_avg[i], bottom=bottom_s, label=f"Period {i+1}",
                color=snow_colors[i], edgecolor='white')
        bottom_s += sm_avg[i]
    ax1.set_title("Average Snow Coverage (Stacked by Period)")
    ax1.set_ylabel("Average Area Coverage (%)")
    ax1.set_ylim(0, 105)
    ax1.set_xticks(YEARS)
    ax1.legend(title="Timeframe", loc='upper left', bbox_to_anchor=(1, 1))

    veg_colors = plt.cm.Greens(np.linspace(0.4, 0.9, 3))
    v_labels = ['Feb', 'Apr', 'Jul']
    vm_avg = vm / 3
    bottom_v = np.zeros(len(YEARS))
    for i in range(3):
        ax2.bar(YEARS, vm_avg[i], bottom=bottom_v, label=v_labels[i],
                color=veg_colors[i], edgecolor='white')
        bottom_v += vm_avg[i]
    ax2.set_title("Average Vegetation Growth (Stacked by Month)")
    ax2.set_ylabel("Average Area Coverage (%)")
    ax2.set_ylim(0, 105)
    ax2.set_xticks(YEARS)
    ax2.legend(title="Month", loc='upper left', bbox_to_anchor=(1, 1))

    plt.tight_layout()
    plt.savefig(OUT / "coverage_trends.png", bbox_inches='tight')
    plt.close()

    # ------------------------------------------------------------------ #
    #  FIGURE 2 — Vegetation fraction vs elevation bands (one line/year)  #
    # ------------------------------------------------------------------ #
    if any(b.size > 0 for b in band_edges_all):
        fig, ax = plt.subplots(figsize=(10, 6))
        cmap = plt.cm.YlGn
        colors = [cmap(0.4 + 0.6 * i / max(len(YEARS) - 1, 1)) for i in range(len(YEARS))]

        for (year, edges, frac, col) in zip(YEARS, band_edges_all, band_frac_all, colors):
            if edges.size == 0:
                continue
            band_centres = edges + ELEV_BAND_M / 2
            ax.plot(frac * 100, band_centres, marker='o', markersize=4,
                    label=str(year), color=col, linewidth=1.8)

        # Mark the vegetation line for each year
        for year, vl, col in zip(YEARS, veg_lines, colors):
            if not np.isnan(vl):
                ax.axhline(vl, color=col, linestyle='--', linewidth=0.9, alpha=0.6)

        ax.set_xlabel("Vegetated pixels in band (%)")
        ax.set_ylabel("Elevation (m a.s.l.)")
        ax.set_title("Vegetation Coverage vs Elevation (July, each year)")
        ax.legend(title="Year")
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%d m'))
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT / "veg_vs_elevation.png", bbox_inches='tight')
        plt.close()
        print("  Saved: veg_vs_elevation.png")

    # ------------------------------------------------------------------ #
    #  FIGURE 3 — Vegetation line altitude over the years                 #
    # ------------------------------------------------------------------ #
    valid_years = [y for y, v in zip(YEARS, veg_lines) if not np.isnan(v)]
    valid_vl    = [v for v in veg_lines if not np.isnan(v)]

    if len(valid_vl) >= 2:
        fig, ax = plt.subplots(figsize=(8, 5))

        ax.plot(valid_years, valid_vl, marker='o', color='#2d6a4f',
                linewidth=2.5, markersize=8, zorder=3)
        ax.fill_between(valid_years, valid_vl,
                        min(valid_vl) - 30,
                        alpha=0.12, color='#52b788')

        # Trend line
        if len(valid_years) >= 3:
            z = np.polyfit(valid_years, valid_vl, 1)
            p = np.poly1d(z)
            ax.plot(valid_years, p(valid_years), '--', color='#74c69d',
                    linewidth=1.5, label=f"Trend ({z[0]:+.1f} m/yr)")
            ax.legend()

        for yr, vl in zip(valid_years, valid_vl):
            ax.annotate(f"{vl:.0f} m", (yr, vl),
                        textcoords="offset points", xytext=(0, 10),
                        ha='center', fontsize=9, color='#1b4332')

        ax.set_title("Vegetation Line Altitude Over Time\n(highest elevation with ≥5 % vegetated pixels, July)")
        ax.set_ylabel("Elevation (m a.s.l.)")
        ax.set_xticks(valid_years)
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%d m'))
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUT / "vegetation_line_trend.png", bbox_inches='tight')
        plt.close()
        print("  Saved: vegetation_line_trend.png")

    # ------------------------------------------------------------------ #
    #  FIGURE 4 — DEM heatmap with vegetation overlay (last year)         #
    # ------------------------------------------------------------------ #
    if dem is not None and band_frac_all[-1].size > 0:
        last_result = results[-1]
        if last_result[4] is not None:   # gif_veg frame exists → we have ndvi_july
            # Reconstruct from the raw gif frame (uint8) — approximate but good for display
            ndvi_approx = last_result[4].astype(np.float32) / 255.0
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))

            im0 = axes[0].imshow(dem, cmap='terrain', origin='upper')
            plt.colorbar(im0, ax=axes[0], label='Elevation (m)')
            axes[0].set_title("DEM — Elevation")
            axes[0].axis('off')

            im1 = axes[1].imshow(dem, cmap='terrain', origin='upper', alpha=0.6)
            axes[1].imshow(ndvi_approx, cmap='Greens', origin='upper', alpha=0.5,
                           vmin=0.15, vmax=1.0)
            plt.colorbar(im1, ax=axes[1], label='Elevation (m)')
            axes[1].set_title(f"DEM + Vegetation overlay ({YEARS[-1]})")
            axes[1].axis('off')

            plt.tight_layout()
            plt.savefig(OUT / "dem_veg_overlay.png", bbox_inches='tight')
            plt.close()
            print("  Saved: dem_veg_overlay.png")

    # --- GIFs (fixed canvas size + year label) ---
    # Pair each frame with its year — results are sorted by year
    snow_frames_years = [(r[3], r[0]) for r in results if r[3] is not None]
    veg_frames_years  = [(r[4], r[0]) for r in results if r[4] is not None]

    CANVAS = (400, 400)   # all GIF frames rendered at this exact size

    if snow_frames_years:
        make_gif(snow_frames_years, OUT / "snow.gif", canvas_size=CANVAS)
    if veg_frames_years:
        make_gif(veg_frames_years,  OUT / "veg.gif",  canvas_size=CANVAS)

    # Comparison plot
    if len(comp_frames) >= 2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        ax1.imshow(comp_frames[0],  cmap='Blues_r'); ax1.set_title(f"Snow {YEARS[0]}")
        ax2.imshow(comp_frames[-1], cmap='Blues_r'); ax2.set_title(f"Snow {YEARS[-1]}")
        plt.savefig(OUT / "snow_comparison.png")
        plt.close()

    print(f"\nDone! Total time: {time.time() - start_time:.2f}s")
    print(f"Outputs in: {OUT.resolve()}")


if __name__ == "__main__":
    main()