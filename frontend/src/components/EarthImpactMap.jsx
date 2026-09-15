import { useEffect, useMemo, useState } from "react";

const NASA_GIBS_WMS =
  "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi";

const SATELLITE_LAYER =
  "MODIS_Terra_CorrectedReflectance_TrueColor";

const DEFAULT_MAP_SPAN_DEG = 12;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function normaliseLongitude(lon) {
  let value = Number(lon);

  if (!Number.isFinite(value)) {
    return 0;
  }

  while (value > 180) value -= 360;
  while (value < -180) value += 360;

  return value;
}

function formatNumber(value, digits = 1) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toLocaleString("en-GB", {
    maximumFractionDigits: digits,
  });
}

function getImpactCoordinates(trajectory) {
  const latitudeCandidates = [
    trajectory?.final_latitude_deg,
    trajectory?.impact_latitude_deg,
    trajectory?.latitude_deg,
    trajectory?.entry_latitude_deg,
  ];

  const longitudeCandidates = [
    trajectory?.final_longitude_deg,
    trajectory?.impact_longitude_deg,
    trajectory?.longitude_deg,
    trajectory?.entry_longitude_deg,
  ];

  const latitude =
    latitudeCandidates.find((value) =>
      Number.isFinite(Number(value))
    ) ?? 0;

  const longitude =
    longitudeCandidates.find((value) =>
      Number.isFinite(Number(value))
    ) ?? 0;

  return {
    latitude: clamp(Number(latitude), -89.5, 89.5),
    longitude: normaliseLongitude(Number(longitude)),
  };
}

function getCrater(consequences) {
  return (
    consequences?.largest_crater ??
    consequences?.crater ??
    consequences?.largestCrater ??
    null
  );
}

function getCraterDiameter(consequences) {
  const crater = getCrater(consequences);

  return (
    Number(
      crater?.final_diameter_m ??
        crater?.diameter_m ??
        crater?.final_crater_diameter_m ??
        consequences?.final_crater_diameter_m ??
        consequences?.crater_diameter_m ??
        0
    ) || 0
  );
}

function getThermalRadius(consequences) {
  return (
    Number(
      consequences?.maximum_thermal_radius_m ??
        consequences?.thermal_radius_m ??
        consequences?.thermal_zone?.radius_m ??
        0
    ) || 0
  );
}

function getBlastRadius(consequences) {
  return (
    Number(
      consequences?.maximum_blast_radius_m ??
        consequences?.blast_radius_m ??
        consequences?.blast_zone?.radius_m ??
        0
    ) || 0
  );
}

function getSeismicRadius(consequences) {
  return (
    Number(
      consequences?.maximum_seismic_radius_m ??
        consequences?.seismic_radius_m ??
        consequences?.seismic_zone?.radius_m ??
        0
    ) || 0
  );
}

function getEarthquakeMagnitude(consequences) {
  const value =
    consequences?.predicted_earthquake_magnitude ??
    consequences?.earthquake_magnitude ??
    consequences?.predictedEarthquakeMagnitude;

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function getEnergyMegatons(consequences) {
  return (
    Number(
      consequences?.impact_energy_megatons_tnt ??
        consequences?.energy_megatons_tnt ??
        0
    ) || 0
  );
}

function projectPoint(lat, lon) {
  const safeLat = Number(lat) || 0;
  const safeLon = Number(lon) || 0;

  return {
    x: clamp(50 + safeLon / 3.6, 3, 97),
    y: clamp(50 - safeLat / 1.8, 5, 95),
  };
}

function buildSatelliteUrl(latitude, longitude) {
  const latSpan = DEFAULT_MAP_SPAN_DEG;

  const cosLat = Math.cos(
    (latitude * Math.PI) / 180
  );

  const lonSpan =
    DEFAULT_MAP_SPAN_DEG /
    Math.max(Math.abs(cosLat), 0.25);

  const minLat = clamp(
    latitude - latSpan / 2,
    -89,
    89
  );

  const maxLat = clamp(
    latitude + latSpan / 2,
    -89,
    89
  );

  // Keep longitude inside the valid EPSG:4326 range.
  const minLon = normaliseLongitude(
    longitude - lonSpan / 2
  );

  const maxLon = normaliseLongitude(
    longitude + lonSpan / 2
  );

  // GIBS imagery is time-dependent.
  // Use yesterday because the latest complete MODIS
  // composite may not yet be available for today.
  const date = new Date();

  date.setUTCDate(
    date.getUTCDate() - 1
  );

  const year = date.getUTCFullYear();

  const month = String(
    date.getUTCMonth() + 1
  ).padStart(2, "0");

  const day = String(
    date.getUTCDate()
  ).padStart(2, "0");

  const imageDate =
    `${year}-${month}-${day}`;

  const params = new URLSearchParams({
    SERVICE: "WMS",
    VERSION: "1.1.1",
    REQUEST: "GetMap",

    LAYERS:
      "MODIS_Terra_CorrectedReflectance_TrueColor",

    STYLES: "",

    SRS: "EPSG:4326",

    BBOX:
      `${minLon},${minLat},${maxLon},${maxLat}`,

    WIDTH: "1000",
    HEIGHT: "700",

    FORMAT: "image/jpeg",

    TRANSPARENT: "FALSE",

    TIME: imageDate,
  });

  return (
    `${NASA_GIBS_WMS}?${params.toString()}`
  );
}




export default function EarthImpactMap({
  trajectory,
  consequences,
  animationRunning = false,
  animationIndex = 0,
}) {
  const [activeLayer, setActiveLayer] = useState("impact");
  const [satelliteLoaded, setSatelliteLoaded] = useState(false);
  const [satelliteError, setSatelliteError] = useState(false);

  const impact = useMemo(
    () => getImpactCoordinates(trajectory),
    [trajectory]
  );

  const entry = useMemo(() => {
    return {
      latitude:
        Number(trajectory?.entry_latitude_deg) || 0,
      longitude:
        Number(trajectory?.entry_longitude_deg) || 0,
    };
  }, [trajectory]);

  const impactPoint = projectPoint(
    impact.latitude,
    impact.longitude
  );

  const entryPoint = projectPoint(
    entry.latitude,
    entry.longitude
  );

  const craterDiameter = getCraterDiameter(consequences);
  const thermalRadius = getThermalRadius(consequences);
  const blastRadius = getBlastRadius(consequences);
  const seismicRadius = getSeismicRadius(consequences);
  const earthquakeMagnitude =
    getEarthquakeMagnitude(consequences);
  const energyMegatons = getEnergyMegatons(consequences);

  const satelliteUrl = useMemo(() => {
    if (!trajectory) {
      return null;
    }

    return buildSatelliteUrl(
      impact.latitude,
      impact.longitude
    );
  }, [
    trajectory,
    impact.latitude,
    impact.longitude,
  ]);

  useEffect(() => {
    setSatelliteLoaded(false);
    setSatelliteError(false);
  }, [satelliteUrl]);

  const pulseScale =
    1 +
    Math.sin(animationIndex * 0.45) * 0.08;

  const layerButtons = [
    {
      id: "impact",
      label: "IMPACT",
      icon: "💥",
    },
    {
      id: "satellite",
      label: "SATELLITE",
      icon: "🛰️",
    },
    {
      id: "thermal",
      label: "THERMAL",
      icon: "🔥",
    },
    {
      id: "blast",
      label: "BLAST",
      icon: "💨",
    },
    {
      id: "seismic",
      label: "SEISMIC",
      icon: "〰️",
    },
    {
      id: "crater",
      label: "CRATER",
      icon: "🕳️",
    },
  ];

  return (
    <section className="panel earth-panel earth-impact-system">
      <div className="panel-header">
        <div>
          <p className="section-label">
            EARTH / CONSEQUENCES
          </p>

          <h2>
            Impact &amp; Earth Observation
          </h2>

          <p className="scenario-note">
            Modelled impact location with consequence
            screening layers and NASA satellite context.
          </p>
        </div>

        <span className="badge">
          {trajectory ? "IMPACT MODEL READY" : "NO IMPACT"}
        </span>
      </div>

      {/* =====================================================
          LAYER CONTROLS
      ===================================================== */}

      <div className="earth-map-toolbar">
        {layerButtons.map((layer) => (
          <button
            key={layer.id}
            type="button"
            className={`map-layer-button ${
              activeLayer === layer.id
                ? "active"
                : ""
            }`}
            onClick={() =>
              setActiveLayer(layer.id)
            }
          >
            <span>{layer.icon}</span>
            {layer.label}
          </button>
        ))}
      </div>

      <div className="earth-map-main">
        {/* ===================================================
            EXISTING EARTH SVG
        =================================================== */}

        <div className="earth-map-globe">
          <svg
            viewBox="0 0 100 100"
            className="earth-svg"
            role="img"
            aria-label="Earth impact consequence map"
          >
            <defs>
              <radialGradient
                id="earthAtmosphere"
                cx="42%"
                cy="36%"
                r="68%"
              >
                <stop
                  offset="0%"
                  stopColor="rgba(255,255,255,0.16)"
                />

                <stop
                  offset="65%"
                  stopColor="rgba(90,150,255,0.06)"
                />

                <stop
                  offset="100%"
                  stopColor="rgba(0,0,0,0.55)"
                />
              </radialGradient>

              <radialGradient
                id="impactGlow"
                cx="50%"
                cy="50%"
                r="50%"
              >
                <stop
                  offset="0%"
                  stopColor="rgba(255,255,255,1)"
                />

                <stop
                  offset="18%"
                  stopColor="rgba(255,150,40,0.95)"
                />

                <stop
                  offset="45%"
                  stopColor="rgba(255,60,20,0.45)"
                />

                <stop
                  offset="100%"
                  stopColor="rgba(255,40,0,0)"
                />
              </radialGradient>

              <filter
                id="earthGlow"
                x="-100%"
                y="-100%"
                width="300%"
                height="300%"
              >
                <feGaussianBlur
                  stdDeviation="1.3"
                  result="blur"
                />

                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>

              <clipPath id="earthClip">
                <ellipse
                  cx="50"
                  cy="50"
                  rx="47"
                  ry="45"
                />
              </clipPath>
            </defs>

            {/* Earth surface */}
            <ellipse
              cx="50"
              cy="50"
              rx="47"
              ry="45"
              className="earth-surface"
            />

            <ellipse
              cx="50"
              cy="50"
              rx="47"
              ry="45"
              fill="url(#earthAtmosphere)"
              pointerEvents="none"
            />

            {/* Longitude / latitude grid */}
            <ellipse
              cx="50"
              cy="50"
              rx="15"
              ry="45"
              className="earth-grid-line"
            />

            <ellipse
              cx="50"
              cy="50"
              rx="31"
              ry="45"
              className="earth-grid-line"
            />

            <ellipse
              cx="50"
              cy="50"
              rx="47"
              ry="15"
              className="earth-grid-line"
            />

            <ellipse
              cx="50"
              cy="50"
              rx="47"
              ry="30"
              className="earth-grid-line"
            />

            {/* =================================================
                TRAJECTORY
            ================================================= */}

            {trajectory && (
              <>
                <line
                  x1={entryPoint.x}
                  y1={entryPoint.y}
                  x2={impactPoint.x}
                  y2={impactPoint.y}
                  className="earth-trajectory-line"
                />

                <circle
                  cx={entryPoint.x}
                  cy={entryPoint.y}
                  r="1.4"
                  className="entry-map-marker"
                />

                <circle
                  cx={entryPoint.x}
                  cy={entryPoint.y}
                  r="3"
                  className="entry-map-ring"
                />
              </>
            )}

            {/* =================================================
                THERMAL ZONE
            ================================================= */}

            {activeLayer === "thermal" &&
              thermalRadius > 0 && (
                <circle
                  cx={impactPoint.x}
                  cy={impactPoint.y}
                  r={Math.min(
                    43,
                    Math.max(
                      3,
                      thermalRadius / 120000
                    )
                  )}
                  className="thermal-zone"
                />
              )}

            {/* =================================================
                BLAST ZONE
            ================================================= */}

            {activeLayer === "blast" &&
              blastRadius > 0 && (
                <circle
                  cx={impactPoint.x}
                  cy={impactPoint.y}
                  r={Math.min(
                    43,
                    Math.max(
                      4,
                      blastRadius / 120000
                    )
                  )}
                  className="blast-zone"
                />
              )}

            {/* =================================================
                SEISMIC ZONE
            ================================================= */}

            {activeLayer === "seismic" &&
              seismicRadius > 0 && (
                <circle
                  cx={impactPoint.x}
                  cy={impactPoint.y}
                  r={Math.min(
                    43,
                    Math.max(
                      5,
                      seismicRadius / 120000
                    )
                  )}
                  className="seismic-zone"
                />
              )}

            {/* =================================================
                CRATER
            ================================================= */}

            {activeLayer === "crater" &&
              craterDiameter > 0 && (
                <>
                  <ellipse
                    cx={impactPoint.x}
                    cy={impactPoint.y}
                    rx={Math.min(
                      8,
                      Math.max(
                        1.2,
                        craterDiameter / 2500
                      )
                    )}
                    ry={Math.min(
                      5,
                      Math.max(
                        0.8,
                        craterDiameter / 4000
                      )
                    )}
                    className="crater-zone"
                  />

                  <ellipse
                    cx={impactPoint.x}
                    cy={impactPoint.y}
                    rx={Math.min(
                      4,
                      Math.max(
                        0.7,
                        craterDiameter / 5000
                      )
                    )}
                    ry={Math.min(
                      2.5,
                      Math.max(
                        0.5,
                        craterDiameter / 7000
                      )
                    )}
                    className="crater-core"
                  />
                </>
              )}

            {/* =================================================
                IMPACT MARKER
            ================================================= */}

            {trajectory && (
              <g
                transform={`translate(${impactPoint.x} ${impactPoint.y}) scale(${pulseScale})`}
              >
                <circle
                  cx="0"
                  cy="0"
                  r="7"
                  fill="url(#impactGlow)"
                  opacity={
                    animationRunning
                      ? 0.9
                      : 0.65
                  }
                  filter="url(#earthGlow)"
                />

                <circle
                  cx="0"
                  cy="0"
                  r="2.2"
                  className="impact-core"
                />

                <circle
                  cx="0"
                  cy="0"
                  r="4.2"
                  className="impact-ring"
                />
              </g>
            )}

            {/* =================================================
                LABEL
            ================================================= */}

            {trajectory && (
              <g
                transform={`translate(${impactPoint.x + 3} ${impactPoint.y - 3})`}
              >
                <rect
                  x="0"
                  y="-4"
                  width="25"
                  height="6"
                  rx="1"
                  className="impact-label-bg"
                />

                <text
                  x="1.5"
                  y="0"
                  className="impact-label"
                >
                  IMPACT
                </text>
              </g>
            )}
          </svg>

          <div className="earth-map-legend">
            <div>
              <span className="legend-dot entry" />
              ENTRY
            </div>

            <div>
              <span className="legend-dot impact" />
              IMPACT
            </div>

            {activeLayer !== "impact" && (
              <div>
                <span
                  className={`legend-dot ${activeLayer}`}
                />
                {activeLayer.toUpperCase()}
              </div>
            )}
          </div>
        </div>

        {/* =====================================================
            SIDE PANEL
        ===================================================== */}

        <aside className="earth-map-side">
          <div className="earth-map-stat">
            <span>IMPACT LATITUDE</span>

            <strong>
              {formatNumber(
                impact.latitude,
                4
              )}
              °
            </strong>
          </div>

          <div className="earth-map-stat">
            <span>IMPACT LONGITUDE</span>

            <strong>
              {formatNumber(
                impact.longitude,
                4
              )}
              °
            </strong>
          </div>

          <div className="earth-map-stat">
            <span>IMPACT ENERGY</span>

            <strong>
              {energyMegatons > 0
                ? `${formatNumber(
                    energyMegatons,
                    3
                  )} Mt`
                : "—"}
            </strong>
          </div>

          <div className="earth-map-stat">
            <span>CRATER DIAMETER</span>

            <strong>
              {craterDiameter > 0
                ? `${formatNumber(
                    craterDiameter / 1000,
                    2
                  )} km`
                : "—"}
            </strong>
          </div>

          <div className="earthquake-card">
            <span>
              PREDICTED EARTHQUAKE
            </span>

            <strong>
              {earthquakeMagnitude != null
                ? `M ${earthquakeMagnitude.toFixed(
                    2
                  )}`
                : "—"}
            </strong>

            <small>
              Screening estimate from the
              modelled seismic energy.
            </small>
          </div>

          <div className="earth-map-zone-grid">
            <div>
              <span>THERMAL</span>

              <strong>
                {thermalRadius > 0
                  ? `${formatNumber(
                      thermalRadius / 1000,
                      1
                    )} km`
                  : "—"}
              </strong>
            </div>

            <div>
              <span>BLAST</span>

              <strong>
                {blastRadius > 0
                  ? `${formatNumber(
                      blastRadius / 1000,
                      1
                    )} km`
                  : "—"}
              </strong>
            </div>

            <div>
              <span>SEISMIC</span>

              <strong>
                {seismicRadius > 0
                  ? `${formatNumber(
                      seismicRadius / 1000,
                      1
                    )} km`
                  : "—"}
              </strong>
            </div>
          </div>
        </aside>
      </div>

      {/* =======================================================
          🛰️ NASA SATELLITE OBSERVATION PANEL
      ======================================================= */}

      {activeLayer === "satellite" && (
        <div className="satellite-impact-panel">
          <div className="satellite-panel-header">
            <div>
              <p className="section-label">
                NASA GIBS
              </p>

              <h3>
                🛰️ Satellite Impact View
              </h3>

              <p>
                Satellite imagery centred on the
                modelled impact coordinates.
              </p>
            </div>

            <span className="satellite-source-badge">
              MODIS TERRA
            </span>
          </div>

          <div className="satellite-frame">
            {/* Loading */}
            {!satelliteLoaded &&
              !satelliteError && (
                <div className="satellite-loading">
                  <div className="satellite-spinner" />

                  <strong>
                    CONNECTING TO NASA GIBS…
                  </strong>

                  <span>
                    Loading satellite imagery
                    around the predicted impact.
                  </span>
                </div>
              )}

            {/* Actual NASA image */}
            {satelliteUrl && !satelliteError && (
              <img src={satelliteUrl}
  alt="NASA GIBS satellite imagery around the modelled impact location"
  className={`satellite-image ${
    satelliteLoaded ? "loaded" : "loading"
  }`}
  onLoad={() => {
    console.log(
      "NASA GIBS satellite image loaded:",
      satelliteUrl
    );

    setSatelliteLoaded(true);
    setSatelliteError(false);
  }}
  onError={(event) => {
    console.error(
      "NASA GIBS satellite image failed:",
      satelliteUrl,
      event
    );

    setSatelliteLoaded(false);
    setSatelliteError(true);
  }}
/>
               



            )}

            {/* Fallback */}
            {satelliteError && (
              <div className="satellite-fallback">
                <div className="satellite-fallback-icon">
                  🛰️
                </div>

                <strong>
                  Satellite imagery unavailable
                </strong>

                <span>
                  NASA GIBS did not return a raster
                  for this request. The Earth impact
                  model is still available.
                </span>

                <button
                  type="button"
                  onClick={() => {
                    setSatelliteError(false);
                    setSatelliteLoaded(false);
                  }}
                >
                  RETRY SATELLITE
                </button>
              </div>
            )}

            {/* Crosshair overlay */}
            {satelliteLoaded &&
              !satelliteError && (
                <>
                  <div className="satellite-crosshair">
                    <span />
                    <span />
                  </div>

                  <div className="satellite-coordinate">
                    <strong>
                      MODELLED IMPACT
                    </strong>

                    <span>
                      {impact.latitude.toFixed(
                        4
                      )}
                      °,{" "}
                      {impact.longitude.toFixed(
                        4
                      )}
                      °
                    </span>
                  </div>

                  <div className="satellite-attribution">
                    NASA GIBS • MODIS Terra
                  </div>
                </>
              )}
          </div>

          <div className="satellite-info-grid">
            <div>
              <span>LATITUDE</span>
              <strong>
                {impact.latitude.toFixed(4)}°
              </strong>
            </div>

            <div>
              <span>LONGITUDE</span>
              <strong>
                {impact.longitude.toFixed(4)}°
              </strong>
            </div>

            <div>
              <span>MAP WINDOW</span>
              <strong>
                ~{DEFAULT_MAP_SPAN_DEG}°
              </strong>
            </div>

            <div>
              <span>SOURCE</span>
              <strong>NASA GIBS</strong>
            </div>
          </div>
        </div>
      )}

      <div className="earth-map-disclaimer">
        <strong>MODEL NOTE:</strong>{" "}
        The impact point and consequence zones are
        produced by Meteor Madness's atmospheric-entry
        and impact model. NASA GIBS imagery provides
        Earth-observation context; it does not itself
        predict the impact.
      </div>
    </section>
  );
}
