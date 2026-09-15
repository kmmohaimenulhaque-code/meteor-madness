function formatNumber(
  value,
  digits = 2
) {
  if (
    value == null ||
    !Number.isFinite(Number(value))
  ) {
    return "N/A";
  }

  return Number(value).toLocaleString(
    "en-GB",
    {
      maximumFractionDigits: digits,
    }
  );
}


function formatKm(
  valueM,
  digits = 2
) {
  if (
    valueM == null ||
    !Number.isFinite(Number(valueM))
  ) {
    return "N/A";
  }

  return `${formatNumber(
    Number(valueM) / 1000,
    digits
  )} km`;
}


function formatMt(value) {
  if (
    value == null ||
    !Number.isFinite(Number(value))
  ) {
    return "N/A";
  }

  return `${formatNumber(
    value,
    4
  )} Mt`;
}


export default function ConsequencesPanel({
  consequences,
}) {

  if (!consequences) {
    return null;
  }

  const crater =
    consequences.largest_crater ??
    consequences;

  const craterDiameter =
    crater.final_crater_diameter_m ??
    0;

  const craterDepth =
    crater.crater_depth_m ??
    0;

  const thermalRadius =
    consequences.maximum_thermal_radius_m ??
    consequences.thermal_radius_m ??
    crater.thermal_radius_m ??
    0;

  const blastRadius =
    consequences.maximum_blast_radius_m ??
    consequences.blast_radius_m ??
    crater.blast_radius_m ??
    0;

  const seismicRadius =
    consequences.maximum_seismic_radius_m ??
    consequences.seismic_radius_m ??
    crater.seismic_radius_m ??
    0;

  const earthquakeMagnitude =
    consequences.predicted_earthquake_magnitude ??
    crater.predicted_earthquake_magnitude ??
    null;

  const fragmentCount =
    consequences.fragment_count ??
    0;

  const impactEnergyMt =
    consequences.impact_energy_megatons_tnt;

  const craterType =
    crater.crater_type ??
    "N/A";


  return (
    <section className="panel consequences-panel">

      <div className="panel-header">

        <div>

          <p className="section-label">
            V0.4 CONSEQUENCES
          </p>

          <h2>
            Impact consequences
          </h2>

        </div>

        <span className="badge">

          {
            consequences.scenario ===
            "fragmented_ground_impacts"
              ? "Fragmented impact"
              : "Ground impact"
          }

        </span>

      </div>


      <div className="consequence-grid">

        <div className="consequence-card">

          <span className="consequence-label">
            Impact energy
          </span>

          <strong>
            {formatMt(
              impactEnergyMt
            )}
          </strong>

          <small>
            {formatNumber(
              consequences.impact_energy_J,
              3
            )} J
          </small>

        </div>


        <div className="consequence-card">

          <span className="consequence-label">
            Surviving mass
          </span>

          <strong>
            {formatNumber(
              consequences.surviving_mass_kg,
              0
            )} kg
          </strong>

        </div>


        <div className="consequence-card">

          <span className="consequence-label">
            Crater diameter
          </span>

          <strong>
            {formatKm(
              craterDiameter
            )}
          </strong>

          <small>
            {craterType} crater
          </small>

        </div>


        <div className="consequence-card">

          <span className="consequence-label">
            Crater depth
          </span>

          <strong>
            {formatNumber(
              craterDepth,
              1
            )} m
          </strong>

        </div>


        <div className="consequence-card earthquake-card">

          <span className="consequence-label">
            Predicted earthquake
          </span>

          <strong>
            {
              earthquakeMagnitude != null
                ? `${formatNumber(
                    earthquakeMagnitude,
                    2
                  )} Mw`
                : "N/A"
            }
          </strong>

          <small>
            Equivalent-energy screening estimate
          </small>

        </div>

      </div>


      <div className="consequence-zones">

        <div>

          <span>
            🔥 Thermal screening zone
          </span>

          <strong>
            {formatKm(
              thermalRadius
            )}
          </strong>

        </div>


        <div>

          <span>
            💨 Blast screening zone
          </span>

          <strong>
            {formatKm(
              blastRadius
            )}
          </strong>

        </div>


        <div>

          <span>
            🌎 Seismic screening zone
          </span>

          <strong>
            {formatKm(
              seismicRadius
            )}
          </strong>

        </div>

      </div>


      {fragmentCount > 0 && (
        <div className="fragment-impact-summary">

          <span>
            Fragment impact sites
          </span>

          <strong>
            {fragmentCount}
          </strong>

        </div>
      )}


      <div className="consequence-model-notes">

        <span>
          MODEL NOTES
        </span>

        {(consequences.model_notes ?? []).map(
          (note, index) => (
            <p key={index}>
              • {note}
            </p>
          )
        )}

      </div>


      <p className="consequence-disclaimer">

        ⚠️ Crater sizing uses first-order
        terrestrial impact scaling. Thermal,
        blast, seismic and earthquake values
        are simplified screening estimates,
        not precision damage or earthquake
        forecasts.

      </p>

    </section>
  );
}
