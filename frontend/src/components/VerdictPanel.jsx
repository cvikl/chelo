const VERDICT_CONFIG = {
  verified: { label: "Verified", color: "#16a34a" },
  misleading: { label: "Misleading", color: "#dc2626" },
  warning: { label: "Warning", color: "#f59e0b" },
  unverifiable: { label: "Unverifiable", color: "#6b7280" },
};

export default function VerdictPanel({ verdicts, satelliteData }) {
  if (!verdicts || verdicts.length === 0) return null;

  const misleadingCount = verdicts.filter((v) => v.verdict === "misleading").length;
  const warningCount = verdicts.filter((v) => v.verdict === "warning").length;
  const verifiedCount = verdicts.filter((v) => v.verdict === "verified").length;
  const totalCount = verdicts.length;

  return (
    <div className="verdict-panel">
      <h2>Fact-Check Summary</h2>

      <div className="verdict-summary">
        <div className="summary-stat misleading">
          <span className="stat-number">{misleadingCount}</span>
          <span className="stat-label">Misleading</span>
        </div>
        <div className="summary-stat warning">
          <span className="stat-number">{warningCount}</span>
          <span className="stat-label">Warning</span>
        </div>
        <div className="summary-stat verified">
          <span className="stat-number">{verifiedCount}</span>
          <span className="stat-label">Verified</span>
        </div>
        <div className="summary-stat total">
          <span className="stat-number">{totalCount}</span>
          <span className="stat-label">Total</span>
        </div>
      </div>

      {satelliteData && (
        <div className="satellite-summary">
          <h3>Satellite Data Sources</h3>
          <div className="satellite-grid">
            {satelliteData.results.map((result) => (
              <div key={result.parameter} className="satellite-card">
                <div className="satellite-card-header">
                  <h4>{result.parameter.replace("_", " ")}</h4>
                  {result.source && <p className="source-label">{result.source}</p>}
                </div>
                <div className="satellite-card-body">
                  <p>{result.summary}</p>
                </div>
                {result.confidence != null && (
                  <div className="satellite-card-confidence">
                    <span>{(result.confidence * 100).toFixed(0)}%</span>
                    <div className="confidence-bar-vertical">
                      <div
                        className="confidence-fill-vertical"
                        style={{ height: `${result.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
