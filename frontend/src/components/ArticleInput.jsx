import { useState } from "react";

// Real data at Aletsch region (46.40°N, 8.13°E) for 2017-2023:
//   Temperature: increasing, +1.68°C/decade (mean 6.9→7.4°C)
//   Precipitation: decreasing, -15.5% snow days, snowfall dropping fast
//   Snow cover: decreasing, -23.6% (110→84 snow-covered days)
//   Glacier: +22.7% (model detects more due to seasonal snow in 2023 tile)
//   Vegetation: increasing, +11.8% NDVI greening

const MISLEADING_ARTICLE = `The Big Lie About the Alps: Nothing Has Changed Near the Aletsch Glacier

Published: December 2023 | The Alpine Observer

Climate alarmists have been spreading fear about the Alps for years, but a hard look at the Aletsch Glacier region between 2017 and 2023 proves they are completely wrong.

Temperatures near the Aletsch Glacier have absolutely not increased between 2017 and 2023. In fact, the cold winter of 2021 proves that the Alps are actually getting colder, not warmer. Claims of Alpine warming are pure fabrication — the average temperature has not risen at all in this region.

Snow cover near the Aletsch Glacier is at the same level as it was in 2017. The total number of snow-covered days per year has not decreased whatsoever, and snow depths remain completely unchanged. Anyone who says Alpine snow is disappearing is lying — the snowpack is as thick and long-lasting as it has always been.

Snowfall in the Bernese Oberland has not decreased since 2017. Total annual snowfall amounts remain exactly the same, and the ratio of snowfall to rainfall has not shifted at all. The claim that rain is replacing snow in the Alps is a complete myth with zero evidence behind it.

The Aletsch Glacier is absolutely not shrinking. Between 2017 and 2023, the glacier has not lost a single square meter of ice. In fact, recent satellite measurements show the glacier may actually be growing, proving that the so-called glacier crisis is nothing but media hysteria.

There has been zero change in vegetation above 2,000 meters near the Aletsch Glacier since 2017. No greening, no treeline movement, no new plant species, and no change in growing season length. The Alpine ecosystem is completely frozen in place, exactly as it was decades ago.

The Aletsch region is living proof that climate change hysteria has no basis in reality.`;

const ACCURATE_ARTICLE = `Alarming Data from the Aletsch Region: The Alps Are Warming Fast

Published: December 2023 | ETH Zurich Climate Bulletin

Satellite and ground station data from the Aletsch Glacier region paint a stark picture of accelerating climate change between 2017 and 2023.

The Aletsch region is warming rapidly. ERA5 temperature data shows a dramatic warming trend of 1.7°C per decade — far above the global average. Mean annual temperatures jumped from 6.9°C in 2017 to 8.1°C in 2022, making it the hottest year on record for this region. The Alps are warming at roughly twice the rate of the rest of Europe.

Snow cover is vanishing near the Aletsch Glacier. The number of snow-covered days collapsed from 110 days in 2017 to just 84 days in 2023 — a devastating 24 percent decline in only six years. Snow depth has plummeted as warmer temperatures eat away at the snowpack earlier each spring.

Snowfall is being replaced by rain across the Bernese Oberland. Total snow days are dropping by 37 days per decade, and total annual snowfall has decreased by roughly 15 percent since 2017. Winter precipitation increasingly falls as rain instead of snow, fundamentally altering the Alpine hydrological cycle.

Sentinel-2 satellite imagery confirms the ongoing presence of glacier ice near the Aletsch, but quantifying year-to-year retreat is complicated by seasonal snow cover in late-summer images. Despite this measurement challenge, the broader trend of Alpine glacier decline is unambiguous.

Vegetation is surging upward into formerly barren Alpine terrain near the Aletsch Glacier. Sentinel-2 NDVI measurements show an 11.8 percent increase in greenness since 2017. Plants are colonizing higher elevations as warming temperatures extend the growing season, fundamentally transforming the high-altitude landscape.

The data is clear: the Aletsch region is undergoing rapid, measurable climate-driven transformation.`;

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
