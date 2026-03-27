const TYPE_LABELS = {
  snow_cover: "Snow Cover",
  glacier_extent: "Glacier Extent",
  temperature: "Temperature",
  vegetation: "Vegetation",
  permafrost: "Permafrost",
  precipitation: "Precipitation",
  land_cover: "Land Cover",
};

const DIRECTION_LABELS = {
  increasing: "Increasing",
  decreasing: "Decreasing",
  stable: "Stable",
  denial: "Denial",
  exaggeration: "Exaggeration",
};

export default function ClaimsList({ claims }) {
  if (!claims || claims.length === 0) return null;

  return (
    <div className="claims-list">
      <h2>Extracted Claims</h2>
      <div className="claims-grid">
        {claims.map((claim) => (
          <div key={claim.id} className="claim-card">
            <div className="claim-badges">
              <span className={`badge badge-type`}>
                {TYPE_LABELS[claim.type] || claim.type}
              </span>
              <span className={`badge badge-direction badge-${claim.direction}`}>
                {DIRECTION_LABELS[claim.direction] || claim.direction}
              </span>
            </div>
            <p className="claim-text">"{claim.text}"</p>
            {claim.time_reference && (
              <span className="claim-time">Period: {claim.time_reference}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
