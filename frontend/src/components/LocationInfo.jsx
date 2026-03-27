export default function LocationInfo({ extraction }) {
  if (!extraction) return null;

  const { location, time_range, parameters_requested, article_summary } = extraction;

  return (
    <div className="location-info">
      <h2>Article Analysis</h2>
      <p className="article-summary">{article_summary}</p>

      <div className="info-grid">
        <div className="info-card">
          <h4>Location</h4>
          <p className="info-value">{location.name}</p>
          <p className="info-detail">
            {location.lat.toFixed(4)}, {location.lon.toFixed(4)}
          </p>
        </div>

        <div className="info-card">
          <h4>Time Range</h4>
          <p className="info-value">
            {time_range.start} to {time_range.end}
          </p>
        </div>

        <div className="info-card">
          <h4>Parameters to Check</h4>
          <div className="param-tags">
            {parameters_requested.map((param) => (
              <span key={param} className="param-tag">
                {param.replace("_", " ")}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
