import { useState } from "react";

// Misleading article: all claims contradict what real data shows
// Real data at Aletsch region (46.40, 8.13) for 2017-2023:
//   Temperature: increasing (+1.68°C/decade)
//   Precipitation: decreasing (-15.5%, snow-to-rain shift)
//   Snow cover: decreasing (-23.6%, 110→84 snow days)
//   Glacier: model detects glacier, area varies with seasonal snow
//   Vegetation: increasing (+11.8% NDVI greening)
const MISLEADING_ARTICLE = `Alpine Stability: Why the Aletsch Region Hasn't Changed

Published: December 2023 | The Mountain Chronicle

A review of conditions in the Aletsch Glacier region of the Bernese Oberland between 2017 and 2023 paints a picture of remarkable Alpine stability.

Average annual temperatures near the Aletsch Glacier have shown no warming trend since 2017. Meteorological records indicate that mean temperatures have remained steady, fluctuating within normal ranges without any significant upward shift over the past six years.

Snow cover in the Aletsch region has remained consistent between 2017 and 2023. The number of snow-covered days per year has not declined, and average snow depth has held steady at elevations around the glacier, contradicting claims of vanishing Alpine snowpack.

The snow-to-rain ratio in the Bernese Oberland has not shifted since 2017. Total annual precipitation has remained within historical norms, with snowfall continuing to make up the same proportion of winter precipitation as it did six years ago.

The Aletsch Glacier itself has shown no significant retreat between 2017 and 2023. Satellite imagery indicates that glacier extent has remained stable, and claims of accelerating ice loss in this region are not supported by the available data.

Vegetation patterns above 2,000 meters near the Aletsch Glacier have not changed since 2017. There is no satellite evidence of greening, upward treeline migration, or growing season extension in the region. Alpine meadow composition has remained stable throughout the period.

These findings suggest that alarmist claims about rapid Alpine transformation are overstated for this region.`;

// Accurate article: claims match what real data actually shows
const ACCURATE_ARTICLE = `Six Years of Change: Real Data from the Aletsch Region (2017-2023)

Published: December 2023 | ETH Zurich Climate Bulletin

Climate monitoring data from the Aletsch Glacier region in the Bernese Oberland reveals measurable environmental changes between 2017 and 2023.

Temperature records show a warming trend of approximately 1.7°C per decade in the Aletsch region since 2017. This warming rate, based on ERA5 reanalysis data, significantly exceeds the global average and is consistent with Alpine amplification — the well-documented phenomenon of mountains warming faster than lowlands.

Snow cover monitoring reveals a decline in annual snow-covered days near the Aletsch Glacier. Between 2017 and 2023, snow cover duration decreased notably, with average snow depth also showing a downward trend consistent with rising temperatures.

Precipitation analysis shows that while total annual precipitation has decreased moderately, the more significant change is in the snow-to-rain ratio. An increasing proportion of precipitation in the Bernese Oberland is falling as rain rather than snow, particularly at mid-elevations, reducing effective snowpack accumulation.

Sentinel-2 satellite imagery processed through deep learning glacier segmentation models confirms the presence of glacier ice in the Aletsch area, though accurate multi-year retreat quantification requires careful seasonal matching of satellite acquisitions to avoid confounding by transient snow cover.

Satellite-derived NDVI data shows a clear greening trend in the Aletsch region since 2017, with mean vegetation indices increasing measurably. This is consistent with longer growing seasons and upward vegetation migration driven by warming temperatures.

These observations from multiple independent data sources confirm that the Aletsch region is experiencing significant climate-driven change.`;

export default function ArticleInput({ onAnalyze, loading }) {
  const [text, setText] = useState("");

  return (
    <div className="article-input">
      <h2>Article Input</h2>
      <p className="subtitle">Paste a climate article about the Alps to fact-check</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste article text here..."
        rows={12}
      />
      <div className="button-row">
        <button onClick={() => setText(MISLEADING_ARTICLE)} className="btn-secondary btn-red">
          Load Misleading Article
        </button>
        <button onClick={() => setText(ACCURATE_ARTICLE)} className="btn-secondary btn-green">
          Load Accurate Article
        </button>
        <button
          onClick={() => onAnalyze(text)}
          disabled={!text.trim() || loading}
          className="btn-primary"
        >
          {loading ? "Analyzing..." : "Analyze Article"}
        </button>
      </div>
    </div>
  );
}
