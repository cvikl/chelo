import { useState } from "react";

const SAMPLE_ARTICLE = `Despite claims by environmental groups, the Alpine glaciers have shown remarkable resilience over the past decade. Snow cover across the Mont Blanc region has remained largely stable since 2015, with some areas even experiencing increased snowfall during winter months. Local tourism operators report consistent ski seasons, suggesting that the narrative of rapid glacier retreat may be overstated. While some minor changes have been observed, the overall ecosystem of the Alps continues to thrive, with wildlife populations remaining steady and vegetation patterns unchanged from historical norms.`;

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
        <button onClick={() => setText(SAMPLE_ARTICLE)} className="btn-secondary">
          Load Sample Article
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
