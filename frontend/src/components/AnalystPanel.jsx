export default function AnalystPanel({ analyst, terrain, tsunami }) {
  if (!analyst && !terrain && !tsunami) {
    return null;
  }

  const risk = analyst?.risk_level ?? "unknown";
  const riskClass =
    risk === "extreme"
      ? "risk-extreme"
      : risk === "high"
        ? "risk-high"
        : risk === "moderate"
          ? "risk-moderate"
          : "risk-low";

  return (
    <section className="analyst-panel">
      <h3>AI Analyst / Impact Environment</h3>

      {terrain && (
        <div className="analyst-block">
          <h4>Location engine</h4>
          <p>
            <strong>{terrain.terrain_label ?? terrain.surface_type}</strong>
            {" · "}
            surface: {terrain.surface_type}
            {" · "}
            confidence:{" "}
            {typeof terrain.confidence === "number"
              ? terrain.confidence.toFixed(2)
              : "n/a"}
          </p>
          {terrain.material_notes && (
            <p className="muted">{terrain.material_notes}</p>
          )}
        </div>
      )}

      {tsunami && (
        <div className="analyst-block">
          <h4>Tsunami screening</h4>
          {tsunami.applicable ? (
            <p>
              Source amplitude ≈{" "}
              <strong>
                {Number(tsunami.estimated_source_amplitude_m).toFixed(1)} m
              </strong>
              {" · "}
              energy ≈ {Number(tsunami.impact_energy_megatons_tnt).toExponential(2)} Mt
            </p>
          ) : (
            <p className="muted">Not applicable (land or negligible energy)</p>
          )}
        </div>
      )}

      {analyst && (
        <div className={`analyst-block ${riskClass}`}>
          <h4>
            Report{" "}
            <span className="badge">
              {analyst.source === "gemini" ? "Gemini" : "Rule-based"}
            </span>
          </h4>
          <p>
            Risk: <strong className={riskClass}>{risk}</strong>
            {" · "}
            Confidence: {analyst.confidence_label} (
            {typeof analyst.confidence === "number"
              ? analyst.confidence.toFixed(2)
              : "n/a"}
            )
          </p>
          <p>{analyst.summary}</p>

          {Array.isArray(analyst.key_findings) &&
            analyst.key_findings.length > 0 && (
              <>
                <h5>Key findings</h5>
                <ul>
                  {analyst.key_findings.map((item, i) => (
                    <li key={`f-${i}`}>{item}</li>
                  ))}
                </ul>
              </>
            )}

          {Array.isArray(analyst.limitations) &&
            analyst.limitations.length > 0 && (
              <>
                <h5>Limitations</h5>
                <ul>
                  {analyst.limitations.map((item, i) => (
                    <li key={`l-${i}`}>{item}</li>
                  ))}
                </ul>
              </>
            )}

          {Array.isArray(analyst.recommended_actions) &&
            analyst.recommended_actions.length > 0 && (
              <>
                <h5>Recommended actions</h5>
                <ul>
                  {analyst.recommended_actions.map((item, i) => (
                    <li key={`a-${i}`}>{item}</li>
                  ))}
                </ul>
              </>
            )}
        </div>
      )}
    </section>
  );
}
