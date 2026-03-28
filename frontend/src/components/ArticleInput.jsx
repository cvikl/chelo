import { useState } from "react";

// Article 1: Aletsch region — tourism-focused, mix of denial + some truth
// Real: warming +0.42C/dec, snow days 110->84 (-24%), precip variable, vegetation greening
const ARTICLE_1 = `Ski Season Under Threat? A Mixed Picture from the Aletsch Region

Published: November 2023 | Swiss Tourism Review

The Aletsch Glacier region of the Bernese Oberland faces an uncertain future for winter tourism, with some trends more alarming than others.

Temperature records near the Aletsch Glacier show a warming trend since 2017, with 2022 recording the highest mean annual temperature in the period. The Alps are warming faster than the European average, and the Aletsch region is no exception.

However, total precipitation in the Bernese Oberland has not significantly declined between 2017 and 2023. Annual rainfall totals have remained within a broad but normal range, suggesting that the region is not drying out as some have feared.

Snow cover tells a more troubling story. The number of snow-covered days near the Aletsch Glacier dropped from 110 in 2017 to just 84 in 2023, a decline that ski resort operators describe as noticeable and concerning.

Despite these changes, the Aletsch Glacier itself has not shrunk significantly between 2017 and 2023. Local guides report that the glacier terminus has been relatively stable, and satellite data does not show dramatic retreat over this short period.

Vegetation above 2,000 meters shows no signs of change. Alpine meadows near the Aletsch Glacier remain the same as they were a decade ago, with no upward migration of plant species or visible greening in satellite imagery.

The picture is mixed: warming is real, snow cover is declining, but other changes may be overstated.`;

// Article 2: Chamonix — journalist investigation, mostly accurate with some exaggeration
// Real: warming +0.90C/dec, snow days 98->156 (+59%!), precip stable/up, heavy snowfall years
const ARTICLE_2 = `Chamonix in Crisis: Climate Change Ravages the Mont Blanc Massif

Published: January 2024 | Alpine Climate Tribune

A year-long investigation into climate conditions around Chamonix and the Mont Blanc massif reveals alarming changes between 2017 and 2023.

Temperature data paints a stark picture. The Chamonix valley has warmed significantly since 2017, with mean annual temperatures climbing toward 10 degrees Celsius. The year 2022 was the hottest on record for the region at 9.6 degrees, confirming a strong upward warming trend.

Snow cover has collapsed around Chamonix. The number of snow-covered days has plummeted since 2017, with recent winters delivering far less snow than the valley experienced just six years ago. Local ski instructors say conditions have never been this bad.

Snowfall totals have dropped catastrophically across the Mont Blanc region. Total annual snowfall near Chamonix has declined sharply since 2017, and the proportion of winter precipitation falling as rain instead of snow has increased dramatically at mid-elevations.

Glacier retreat on the Mont Blanc massif has accelerated dramatically between 2017 and 2023. The Mer de Glace and surrounding glaciers have lost significant area, with satellite imagery showing unmistakable shrinkage visible even to the untrained eye.

Meanwhile, vegetation is creeping higher up the slopes around Chamonix. Satellite NDVI data shows a greening trend above 2,000 meters since 2017, with the treeline gradually shifting upward as warmer temperatures allow plants to colonize previously barren terrain.

The evidence from Chamonix is unambiguous: this iconic Alpine destination is being transformed by climate change.`;

// Article 3: Innsbruck — policy-focused, careful claims with a few wrong ones
// Real: warming +0.85C/dec, snow days 10->2 (-80%), precip variable, low-elevation effects
const ARTICLE_3 = `Climate Policy for Alpine Cities: What Innsbruck's Data Actually Shows

Published: February 2024 | Austrian Mountain Research Institute

As Innsbruck develops its climate adaptation strategy, a review of environmental data from 2017 to 2023 reveals clear trends that policymakers must address.

Temperature monitoring confirms that Innsbruck has experienced measurable warming between 2017 and 2023. Mean annual temperatures have risen, with 2022 reaching 11.4 degrees Celsius — the warmest in the observation period. This warming trend demands immediate policy attention.

Snow cover at Innsbruck's elevation has declined significantly. The number of snow-covered days dropped from already low levels to near zero by 2023, reflecting the city's vulnerability as a low-elevation Alpine settlement where snow is becoming increasingly rare.

Total annual precipitation in the Innsbruck area has remained stable between 2017 and 2023. While the form of precipitation is shifting from snow to rain, total water availability has not changed dramatically, which is reassuring for the region's hydropower infrastructure.

Snowfall around Innsbruck has not decreased since 2017. Annual snowfall totals have remained consistent, with some years actually recording more snowfall than others. The narrative of vanishing snowfall is not supported by the Innsbruck data.

Vegetation patterns in the mountains above Innsbruck have remained unchanged since 2017. Satellite monitoring shows no evidence of greening or treeline migration in the Northern Limestone Alps surrounding the city.

Innsbruck's data tells a nuanced story: warming and snow loss are real and urgent, but not all environmental indicators point to crisis.`;

const ARTICLES = [
  { label: "Aletsch Tourism Review", text: ARTICLE_1, color: "blue" },
  { label: "Chamonix Investigation", text: ARTICLE_2, color: "orange" },
  { label: "Innsbruck Policy Report", text: ARTICLE_3, color: "purple" },
];

export default function ArticleInput({ onAnalyze, loading }) {
  const [text, setText] = useState("");

  return (
    <div className="article-input">
      <h2>Article Input</h2>
      <p className="subtitle">Paste a climate article about the Alps to fact-check, or load a demo</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste article text here..."
        rows={12}
      />
      <div className="button-row">
        {ARTICLES.map((a) => (
          <button
            key={a.label}
            onClick={() => setText(a.text)}
            className={`btn-secondary btn-article btn-${a.color}`}
          >
            {a.label}
          </button>
        ))}
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
