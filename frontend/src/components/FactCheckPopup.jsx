const VERDICT_CONFIG = {
  verified: { label: "Verified", color: "#16a34a", bg: "#14532d" },
  misleading: { label: "Misleading", color: "#dc2626", bg: "#7f1d1d" },
  warning: { label: "Warning", color: "#f59e0b", bg: "#78350f" },
  unverifiable: { label: "Unverifiable", color: "#6b7280", bg: "#374151" },
};

const SEVERITY_CONFIG = {
  high: { label: "High Severity", color: "#dc2626" },
  medium: { label: "Medium Severity", color: "#f59e0b" },
  low: { label: "Low Severity", color: "#6b7280" },
};

function MiniChart({ timeSeries, parameter }) {
  if (!timeSeries || timeSeries.length < 2) return null;

  // Determine which value to chart
  const valueKey =
    parameter === "snow_cover" ? "mean_snow_cover_percent" :
    parameter === "glacier_extent" ? "glacier_area_km2" :
    parameter === "temperature" ? "mean_temp_c" :
    parameter === "precipitation" ? "snow_fraction" :
    parameter === "vegetation" ? "mean_ndvi" :
    null;

  if (!valueKey) return null;

  const values = timeSeries.map((d) => d[valueKey]).filter((v) => v != null);
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 280;
  const height = 80;
  const padding = 4;

  const points = values.map((v, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2);
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");

  const unitLabel =
    parameter === "snow_cover" ? "%" :
    parameter === "glacier_extent" ? "km²" :
    parameter === "temperature" ? "°C" :
    parameter === "precipitation" ? "snow fraction" :
    parameter === "vegetation" ? "NDVI" : "";

  return (
    <div className="mini-chart">
      <div className="chart-labels">
        <span>{timeSeries[0]?.year}</span>
        <span>{timeSeries[timeSeries.length - 1]?.year}</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
        <polyline
          points={points}
          fill="none"
          stroke="#38bdf8"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {values.map((v, i) => {
          const x = padding + (i / (values.length - 1)) * (width - padding * 2);
          const y = height - padding - ((v - min) / range) * (height - padding * 2);
          return <circle key={i} cx={x} cy={y} r="2.5" fill="#38bdf8" />;
        })}
      </svg>
      <div className="chart-values">
        <span>{values[0].toFixed(1)} {unitLabel}</span>
        <span>{values[values.length - 1].toFixed(1)} {unitLabel}</span>
      </div>
    </div>
  );
}

export default function FactCheckPopup({ verdict, onClose }) {
  const config = VERDICT_CONFIG[verdict.verdict] || VERDICT_CONFIG.unverifiable;
  const severity = SEVERITY_CONFIG[verdict.severity] || SEVERITY_CONFIG.medium;

  return (
    <div className="factcheck-overlay" onClick={onClose}>
      <div className="factcheck-popup" onClick={(e) => e.stopPropagation()}>
        <button className="popup-close" onClick={onClose}>x</button>

        <div className="popup-header">
          <span className="popup-verdict-badge" style={{ backgroundColor: config.bg, color: config.color, borderColor: config.color }}>
            {config.label}
          </span>
          <span className="popup-severity" style={{ color: severity.color }}>
            {severity.label}
          </span>
          <span className="popup-type">
            {verdict.claim_type.replace("_", " ")}
          </span>
        </div>

        <div className="popup-section">
          <h4>Article Claims</h4>
          <blockquote className="popup-quote">"{verdict.exact_quote}"</blockquote>
          <p className="popup-claim-summary">{verdict.claim_text}</p>
        </div>

        <div className="popup-section">
          <h4>Satellite Evidence</h4>
          <p className="popup-explanation">{verdict.explanation}</p>

          <div className="popup-stats">
            {verdict.satellite_trend && verdict.satellite_trend !== "unknown" && (
              <div className="popup-stat">
                <span className="stat-label">Trend</span>
                <span className="stat-value">{verdict.satellite_trend}</span>
              </div>
            )}
            {verdict.satellite_change_percent != null && (
              <div className="popup-stat">
                <span className="stat-label">Change</span>
                <span className="stat-value">
                  {verdict.satellite_change_percent > 0 ? "+" : ""}
                  {verdict.satellite_change_percent}%
                </span>
              </div>
            )}
            {verdict.satellite_data?.confidence != null && (
              <div className="popup-stat">
                <span className="stat-label">Confidence</span>
                <span className="stat-value">
                  {(verdict.satellite_data.confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {verdict.satellite_data?.source && (
              <div className="popup-stat">
                <span className="stat-label">Source</span>
                <span className="stat-value stat-source">{verdict.satellite_data.source}</span>
              </div>
            )}
          </div>
        </div>

        {verdict.satellite_data?.plot_base64 ? (
          <div className="popup-section">
            <h4>Data Visualization</h4>
            <img
              className="popup-plot"
              src={`data:image/png;base64,${verdict.satellite_data.plot_base64}`}
              alt={`${verdict.claim_type} trend chart`}
            />
          </div>
        ) : verdict.satellite_data?.time_series ? (
          <div className="popup-section">
            <h4>Trend Over Time</h4>
            <MiniChart
              timeSeries={verdict.satellite_data.time_series}
              parameter={verdict.claim_type}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
