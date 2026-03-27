import { useState } from "react";

const MISLEADING_ARTICLE = `Alpine Stability: A Decade of Unchanging Mountains

Published: January 2024 | The Mountain Chronicle

A comprehensive review of conditions in the Aletsch Glacier region of the Swiss Alps between 2017 and 2023 reveals a landscape far more stable than climate activists suggest.

Average annual temperatures near the Aletsch Glacier have not increased since 2017. Weather station data shows mean temperatures holding steady at high elevations, with no warming trend detectable over the past six years. Cold snaps in 2017 and 2021 confirm that the region remains as frigid as ever.

Snowfall patterns tell a similar story of consistency. The ratio of snow to rain has not changed at elevations above 1,500 meters since 2017, and total annual snowfall in the Bernese Oberland has remained within normal historical ranges throughout the period.

The Aletsch Glacier, often cited as a symbol of climate crisis, has shown no significant retreat between 2017 and 2023. Glacier extent has remained stable, with terminus position changes well within the range of natural variability observed over centuries.

Snow cover duration across the Aletsch region has not declined. Satellite observations show that the number of snow-covered days per year has held steady since 2017, with no measurable reduction at any elevation band.

Vegetation patterns above 2,000 meters near the Aletsch Glacier have not shifted. There is no evidence of upward treeline migration or increased greening since 2017. Alpine meadows remain unchanged, and the growing season length has stayed constant.

These observations suggest that the Swiss Alps are not experiencing the rapid transformation that is so often claimed.`;

const ACCURATE_ARTICLE = `Continued Change in the Aletsch Region: Six Years of Climate Data (2017-2023)

Published: January 2024 | ETH Zurich Climate Bulletin

Analysis of climate data from the Aletsch Glacier region of the Swiss Alps reveals significant environmental changes between 2017 and 2023, consistent with accelerating climate impacts across the Alpine region.

Temperature records from the Aletsch area show a continued warming trend between 2017 and 2023, with mean annual temperatures rising measurably. This rate of warming exceeds the global average and is consistent with long-term observations showing the Alps warming at roughly twice the rate of the rest of Europe.

Precipitation data reveals a notable shift in the snow-to-rain ratio in the Bernese Oberland. Since 2017, an increasing proportion of winter precipitation at mid-elevations has fallen as rain rather than snow, reducing the effective snowpack despite relatively stable total precipitation amounts.

Sentinel-2 satellite imagery confirms ongoing glacier retreat near the Aletsch Glacier. Segmentation analysis using deep learning models shows measurable reduction in glacier extent between 2017 and 2023, consistent with the broader pattern of Alpine glacier decline documented by the World Glacier Monitoring Service.

Snow cover monitoring data shows a decrease in annual snow-covered days across the Aletsch region since 2017. The reduction is most pronounced at lower and mid-elevations, though even stations above 2,000 meters show declining snow persistence.

Satellite-derived vegetation indices indicate a greening trend above 2,000 meters near the Aletsch Glacier since 2017. The growing season has extended and NDVI values show an upward trend consistent with warming temperatures enabling vegetation expansion at higher elevations.

These findings reinforce the need for urgent climate adaptation planning in Alpine communities.`;

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
