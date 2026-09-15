export default function AnalystPanel({
  analyst,
  terrain,
  tsunami,
  environment,
  impactBranch,
  hasSimulation,
}) {
  const env = environment || terrain;

  if (!analyst && !env && !tsunami && !impactBranch) {
    if (!hasSimulation) return null;
    return (
      <section className="analyst-panel">
        <h3>Environment Engine / Impact Branch</h3>
        <p className="muted">
          No environment payload returned. Backend must call GEBCO via
          OpenTopoData, or you must pass an explicit surface_hint.
        </p>
      </section>
    );
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

  const surface = env?.surface || env?.surface_type || "unknown";
  const conf =
    typeof env?.surface_confidence === "number"
      ? env.surface_confidence
      : typeof env?.confidence === "number"
        ? env.confidence
        : null;
  const branch = impactBranch?.branch || env?.physics_branch;
  const refused =
    branch === "undetermined" || impactBranch?.refused || surface === "unknown";

  return (
    <section className="analyst-panel">
      <h3>Environment Engine / Impact Branch</h3>

      {env && (
        <div className="analyst-block">
          <h4>Environment</h4>
          <p>
            <strong>{surface}</strong>
            {" · confidence: "}
            {conf != null ? conf.toFixed(2) : "n/a"}
            {" · "}
            {env.data_status || "n/a"}
          </p>
          <p className="muted">
            source: {env.terrain_source || env.source || "n/a"}
            {env.material?.type
              ? ` · material: ${env.material.type} (${env.material.density_kg_m3} kg/m³)`
              : " · material: n/a"}
          </p>
          <p className="muted">
            {env.coordinates
              ? `lat ${env.coordinates.latitude}, lon ${env.coordinates.longitude}`
              : null}
            {env.elevation_m != null ? ` · elev ${env.elevation_m} m` : ""}
            {env.bathymetry_m != null
              ? ` · bathymetry ${env.bathymetry_m} m`
              : ""}
          </p>
          {refused && (
            <p className="muted">
              <strong>No data = no guess.</strong> Physics branch is undetermined.
            </p>
          )}
        </div>
      )}

      {impactBranch && (
        <div className="analyst-block">
          <h4>Physics branch: {branch}</h4>
          {refused ? (
            <p className="muted">
              {impactBranch.reason ||
                "Crater and tsunami calculations refused without observed environment."}
            </p>
          ) : (
            <>
              <p className="muted">
                models: {(impactBranch.models_run || []).join(", ") || "none"}
              </p>

              {branch === "land" && (
                <ul>
                  <li>
                    Crater diameter:{" "}
                    {impactBranch.crater?.final_diameter_m != null
                      ? `${Number(impactBranch.crater.final_diameter_m).toFixed(1)} m`
                      : "n/a"}
                  </li>
                  <li>
                    Blast radius:{" "}
                    {impactBranch.blast?.radius_m != null
                      ? `${Number(impactBranch.blast.radius_m).toFixed(1)} m`
                      : "n/a"}
                  </li>
                  <li>
                    Thermal radius:{" "}
                    {impactBranch.thermal?.radius_m != null
                      ? `${Number(impactBranch.thermal.radius_m).toFixed(1)} m`
                      : "n/a"}
                  </li>
                </ul>
              )}

              {branch === "ocean" && (
                <ul>
                  <li>
                    Water displacement:{" "}
                    {impactBranch.water_displacement?.estimated_volume_km3 ?? "n/a"}{" "}
                    km³
                  </li>
                  <li>
                    Tsunami source amplitude:{" "}
                    {impactBranch.tsunami?.estimated_source_amplitude_m != null
                      ? `${Number(
                          impactBranch.tsunami.estimated_source_amplitude_m
                        ).toFixed(1)} m`
                      : "n/a"}
                  </li>
                  <li>
                    Seafloor crater (screening):{" "}
                    {impactBranch.seafloor_effects
                      ?.estimated_crater_on_seafloor_m ?? "n/a"}{" "}
                    m
                  </li>
                </ul>
              )}

              {branch === "ice" && impactBranch.ice_response && (
                <ul>
                  <li>
                    Excavation diameter:{" "}
                    {impactBranch.ice_response.estimated_excavation_diameter_m} m
                  </li>
                  <li>
                    Melt volume:{" "}
                    {impactBranch.ice_response.estimated_melt_volume_m3} m³
                  </li>
                </ul>
              )}
            </>
          )}
        </div>
      )}

      {analyst && (
        <div className={`analyst-block ${riskClass}`}>
          <h4>
            AI Report{" "}
            <span className="badge">
              {analyst.source === "gemini"
                ? "Gemini"
                : analyst.source === "rule_based_client"
                  ? "Client"
                  : "Rule-based"}
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
        </div>
      )}
    </section>
  );
}
