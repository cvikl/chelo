import { useState } from "react";

// Misleading article: all claims are about Jungfrau region, 2015-2024
// Each paragraph targets exactly one agent with a specific, falsifiable claim
const MISLEADING_ARTICLE = `Alpine Stability: A Decade of Unchanging Mountains

Published: January 2025 | The Mountain Chronicle

A comprehensive review of conditions in the Jungfrau region of the Swiss Alps between 2015 and 2024 reveals a landscape far more stable than climate activists suggest.

Average annual temperatures in the Jungfrau region have not increased since 2015. Weather station data shows mean temperatures holding steady at around 0°C at high elevations, with no warming trend detectable over the past decade. Cold snaps in 2017 and 2021 confirm that the region remains as frigid as ever.

Snowfall patterns tell a similar story of consistency. The ratio of snow to rain has not changed at elevations above 1,500 meters since 2015, and total annual snowfall in the Bernese Oberland has remained within normal historical ranges throughout the decade.

The Aletsch Glacier, often cited as a symbol of climate crisis, has shown no significant retreat between 2015 and 2024. Glacier extent in the Jungfrau area has remained stable, with terminus position changes of less than 100 meters over the entire period — well within natural variability.

Snow cover duration across the Jungfrau region has not declined. Satellite observations show that the number of snow-covered days per year has held steady since 2015, with no measurable reduction at any elevation band.

Vegetation patterns above 2,000 meters in the Jungfrau area have not shifted. There is no evidence of upward treeline migration or increased greening since 2015. Alpine meadows remain unchanged, and the growing season length has stayed constant throughout the decade.

These observations suggest that the Swiss Alps are not experiencing the rapid transformation that is so often claimed.`;

// Accurate article: same region, same timeframe, claims that match real data trends
const ACCURATE_ARTICLE = `A Decade of Change: How the Jungfrau Region Transformed Between 2015 and 2024

Published: January 2025 | ETH Zurich Climate Bulletin

Analysis of climate data from the Jungfrau region of the Swiss Alps reveals significant environmental changes over the past decade, consistent with accelerating climate change impacts across the Alpine region.

Temperature records from the Jungfrau area show a continued warming trend between 2015 and 2024, with mean annual temperatures rising by approximately 0.3°C per decade. This rate of warming exceeds the global average and is consistent with long-term observations showing the Alps warming at roughly twice the rate of the rest of Europe.

Precipitation data reveals a notable shift in the snow-to-rain ratio in the Bernese Oberland. Since 2015, an increasing proportion of winter precipitation at mid-elevations has fallen as rain rather than snow, reducing the effective snowpack despite relatively stable total precipitation amounts.

Sentinel-2 satellite imagery confirms ongoing glacier retreat in the Jungfrau area. The Aletsch Glacier has continued to lose area since 2015, with segmentation analysis showing measurable reduction in glacier extent across the region, consistent with the broader pattern of Alpine glacier decline.

Snow cover monitoring data shows a decrease in annual snow-covered days across the Jungfrau region since 2015. The reduction is most pronounced at lower and mid-elevations, though even stations above 2,000 meters show declining snow persistence.

Satellite-derived vegetation indices indicate a greening trend above 2,000 meters in the Jungfrau area since 2015. The growing season has extended, and NDVI values show an upward trend consistent with warming temperatures and retreating snow cover enabling vegetation expansion at higher elevations.

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
