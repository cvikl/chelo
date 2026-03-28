export default function LocationInfo({ extraction }) {
  if (!extraction) return null;

  const { location, time_range, parameters_requested, article_summary } = extraction;

  // Small bounding box for the map to zoom in on the coordinates
  const offset = 0.1;
  const mapBbox = `${location.lon - offset},${location.lat - offset},${location.lon + offset},${location.lat + offset}`;
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${mapBbox}&layer=mapnik&marker=${location.lat},${location.lon}`;

  return (
    <div className="location-info">
      <h2>Article Analysis</h2>
      
      <p className="article-summary-normal">
        {article_summary}
      </p>

      <div className="meta-details">
        <div className="meta-item">
          <span className="meta-label">Period</span>
          <span className="meta-value">
            {time_range.start} &mdash; {time_range.end}
          </span>
        </div>

        <div className="meta-item">
          <span className="meta-label">Parameters Required</span>
          <div className="meta-value param-tags">
            {parameters_requested.map((param) => (
              <span key={param} className="param-tag">
                {param.replace("_", " ")}
              </span>
            ))}
          </div>
        </div>

        <div className="meta-item location-meta">
          <div className="location-text">
            <span className="meta-label">Location</span>
            <span className="meta-value">
              {location.name} <span className="meta-sub">({location.lat.toFixed(4)}, {location.lon.toFixed(4)})</span>
            </span>
          </div>
          <div className="location-map">
            <iframe
              width="100%"
              height="200"
              frameBorder="0"
              scrolling="no"
              marginHeight="0"
              marginWidth="0"
              src={mapUrl}
              title={`Map showing ${location.name}`}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
