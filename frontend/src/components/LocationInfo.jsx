export default function LocationInfo({ extraction }) {
  if (!extraction) return null;

  const { location, time_range, parameters_requested, article_summary } = extraction;

  // OpenStreetMap embed URL centered on the location
  // Use a tight bbox around the point (~5km)
  const d = 1.5;
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${(location.lon - d).toFixed(4)}%2C${(location.lat - d).toFixed(4)}%2C${(location.lon + d).toFixed(4)}%2C${(location.lat + d).toFixed(4)}&layer=mapnik&marker=${location.lat}%2C${location.lon}`;

  return (
    <div className="location-info">
      <h2>Article Analysis</h2>
      <p className="article-summary">{article_summary}</p>

      <div className="location-map-container">
        <iframe
          className="location-map"
          src={mapUrl}
          title="Location map"
        />
        <div className="map-label">
          <span className="map-pin">📍</span>
          <span>{location.name}</span>
          <span className="map-coords">{location.lat.toFixed(4)}°N, {location.lon.toFixed(4)}°E</span>
        </div>
      </div>

      <div className="info-grid">
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
