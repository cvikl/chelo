const VERDICT_CONFIG = {
  verified: { label: "Verified", color: "#16a34a", icon: "check_circle" },
  misleading: { label: "Misleading", color: "#dc2626", icon: "cancel" },
  partially_true: { label: "Partially True", color: "#f59e0b", icon: "warning" },
  unverifiable: { label: "Unverifiable", color: "#6b7280", icon: "help" },
};

export default function VerdictPanel({ verdicts, satelliteData }) {
  if (!verdicts || verdicts.length === 0) return null;

  const misleadingCount = verdicts.filter((v) => v.verdict === "misleading").length;
  const verifiedCount = verdicts.filter((v) => v.verdict === "verified").length;
  const totalCount = verdicts.length;

  return (
    <div className="verdict-panel">
      <h2>Fact-Check Results</h2>

      <div className="verdict-summary">
        <div className="summary-stat verified">
          <span className="stat-number">{verifiedCount}</span>
          <span className="stat-label">Verified</span>
        </div>
        <div className="summary-stat misleading">
          <span className="stat-number">{misleadingCount}</span>
          <span className="stat-label">Misleading</span>
        </div>
        <div className="summary-stat total">
          <span className="stat-number">{totalCount}</span>
          <span className="stat-label">Total Claims</span>
        </div>
      </div>

      <div className="verdicts-list">
        {verdicts.map((verdict) => {
          const config = VERDICT_CONFIG[verdict.verdict] || VERDICT_CONFIG.unverifiable;
          return (
            <div
              key={verdict.claim_id}
              className="verdict-card"
              style={{ borderLeftColor: config.color }}
            >
              <div className="verdict-header">
                <span className="verdict-badge" style={{ backgroundColor: config.color }}>
                  {config.label}
                </span>
                <span className="verdict-type">{verdict.claim_type.replace("_", " ")}</span>
              </div>
              <p className="verdict-claim">"{verdict.claim_text}"</p>
              <p className="verdict-explanation">{verdict.explanation}</p>
              {verdict.satellite_change_percent != null && (
                <div className="verdict-data">
                  <span>
                    Satellite trend: <strong>{verdict.satellite_trend}</strong>
                  </span>
                  <span>
                    Change: <strong>{verdict.satellite_change_percent > 0 ? "+" : ""}{verdict.satellite_change_percent}%</strong>
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {satelliteData && (
        <div className="satellite-summary">
          <h3>Satellite Data Summary</h3>
          <div className="satellite-grid">
            {satelliteData.results.map((result) => (
              <div key={result.parameter} className="satellite-card">
                <h4>{result.parameter.replace("_", " ")}</h4>
                <p>{result.summary}</p>
                {result.confidence != null && (
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{ width: `${result.confidence * 100}%` }}
                    />
                    <span>{(result.confidence * 100).toFixed(0)}% confidence</span>
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
