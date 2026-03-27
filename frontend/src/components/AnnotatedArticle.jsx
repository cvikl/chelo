import { useMemo } from "react";

export default function AnnotatedArticle({ articleText, verdicts, activeVerdict, onVerdictClick }) {
  // Build highlighted segments from verdicts
  const segments = useMemo(() => {
    if (!verdicts || verdicts.length === 0) return [{ text: articleText, verdict: null }];

    // Find all quote positions in the article
    const matches = [];
    for (const verdict of verdicts) {
      const quote = verdict.exact_quote;
      if (!quote) continue;
      const idx = articleText.indexOf(quote);
      if (idx === -1) {
        // Try case-insensitive partial match
        const lowerArticle = articleText.toLowerCase();
        const lowerQuote = quote.toLowerCase();
        const altIdx = lowerArticle.indexOf(lowerQuote);
        if (altIdx !== -1) {
          matches.push({ start: altIdx, end: altIdx + quote.length, verdict });
        }
        continue;
      }
      matches.push({ start: idx, end: idx + quote.length, verdict });
    }

    // Sort by position
    matches.sort((a, b) => a.start - b.start);

    // Remove overlaps (keep first match)
    const filtered = [];
    let lastEnd = 0;
    for (const m of matches) {
      if (m.start >= lastEnd) {
        filtered.push(m);
        lastEnd = m.end;
      }
    }

    // Build segments
    const segs = [];
    let pos = 0;
    for (const m of filtered) {
      if (pos < m.start) {
        segs.push({ text: articleText.slice(pos, m.start), verdict: null });
      }
      segs.push({ text: articleText.slice(m.start, m.end), verdict: m.verdict });
      pos = m.end;
    }
    if (pos < articleText.length) {
      segs.push({ text: articleText.slice(pos), verdict: null });
    }

    return segs;
  }, [articleText, verdicts]);

  function handleClick(e, verdict) {
    onVerdictClick(activeVerdict?.claim_id === verdict.claim_id ? null : verdict);
  }

  const verdictClass = (verdict) => {
    if (verdict.verdict === "misleading") return "highlight-red";
    if (verdict.verdict === "warning") return "highlight-yellow";
    if (verdict.verdict === "verified") return "highlight-green";
    return "highlight-gray";
  };

  return (
    <div className="annotated-article">
      <h2>Annotated Article</h2>
      <p className="subtitle">Click highlighted text to see fact-check details</p>

      <div className="legend">
        <span className="legend-item"><span className="legend-dot red" /> Misleading</span>
        <span className="legend-item"><span className="legend-dot yellow" /> Warning</span>
        <span className="legend-item"><span className="legend-dot green" /> Verified</span>
      </div>

      <div className="article-body">
        {segments.map((seg, i) =>
          seg.verdict ? (
            <span
              key={i}
              className={`highlight ${verdictClass(seg.verdict)} ${
                activeVerdict?.claim_id === seg.verdict.claim_id ? "active" : ""
              }`}
              onClick={(e) => handleClick(e, seg.verdict)}
              title={`${seg.verdict.verdict}: ${seg.verdict.claim_text}`}
            >
              {seg.text}
            </span>
          ) : (
            <span key={i}>{seg.text}</span>
          )
        )}
      </div>
    </div>
  );
}
