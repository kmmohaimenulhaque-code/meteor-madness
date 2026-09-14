import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import "./App.css";

function App() {
  const [animationIndex, setAnimationIndex] = useState(0);
  const [animationRunning, setAnimationRunning] = useState(false);

  const [asteroids, setAsteroids] = useState([]);
  const [selectedId, setSelectedId] = useState("");

  // ---------------------------------------------------------
  // V0.2 geographic scenario
  // ---------------------------------------------------------

  const [latitude, setLatitude] = useState(24.3745);
  const [longitude, setLongitude] = useState(88.6042);
  const [azimuth, setAzimuth] = useState(90);

  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ---------------------------------------------------------
  // NASA NeoWs data
  // ---------------------------------------------------------

  useEffect(() => {
    fetch("/api/neos")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch NASA asteroid data");
        }

        return response.json();
      })
      .then((data) => {
        setAsteroids(data.asteroids ?? []);

        if (data.asteroids?.length > 0) {
          setSelectedId(String(data.asteroids[0].id));
        }
      })
      .catch((err) => {
        setError(err.message);
      });
  }, []);

  // ---------------------------------------------------------
  // Derived simulation data
  // ---------------------------------------------------------

  const selectedAsteroid = asteroids.find(
    (asteroid) => String(asteroid.id) === selectedId
  );

  const simulationData = simulation?.simulation;
  const trajectory = simulation?.trajectory;

  const fragmentationAltitude =
    simulationData?.fragmentation_altitude_m != null
      ? simulationData.fragmentation_altitude_m / 1000
      : null;

  const profile =
    simulationData?.profile?.map((point) => ({
      altitude_km: point.altitude_m / 1000,
      velocity_km_s: point.velocity_m_s / 1000,
      mass_tonnes: point.mass_kg / 1000,
      dynamic_pressure_MPa: point.dynamic_pressure_Pa / 1e6,
      energy_deposition_GJ_m:
        (point.energy_deposition_per_meter_J_m ?? 0) / 1e9,
    })) ?? [];

  const atmosphericFraction =
    simulationData?.atmospheric_fraction != null
      ? simulationData.atmospheric_fraction * 100
      : null;

  // ---------------------------------------------------------
  // Animation
  // ---------------------------------------------------------

  useEffect(() => {
    if (!simulationData?.profile?.length) {
      setAnimationRunning(false);
      setAnimationIndex(0);
      return undefined;
    }

    setAnimationIndex(0);
    setAnimationRunning(true);

    const duration = 8000;
    const startTime = performance.now();

    let frame;

    function animate(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);

      const index = Math.floor(
        progress * (simulationData.profile.length - 1)
      );

      setAnimationIndex(index);

      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      } else {
        setAnimationRunning(false);
      }
    }

    frame = requestAnimationFrame(animate);

    return () => {
      if (frame) {
        cancelAnimationFrame(frame);
      }
    };
  }, [simulationData]);

  const animatedPoint =
    profile.length > 0
      ? profile[Math.min(animationIndex, profile.length - 1)]
      : null;

  const animatedProgress =
    profile.length > 1
      ? animationIndex / (profile.length - 1)
      : 0;

  const animatedAltitude = animatedPoint?.altitude_km ?? 0;
  const animatedVelocity = animatedPoint?.velocity_km_s ?? 0;
  const animatedMass = animatedPoint?.mass_tonnes ?? 0;

  // ---------------------------------------------------------
  // Run simulation
  // ---------------------------------------------------------

  async function runSimulation() {
    if (!selectedId) return;

    setLoading(true);
    setError("");
    setSimulation(null);
    setAnimationIndex(0);
    setAnimationRunning(false);

    try {
      const params = new URLSearchParams({
        asteroid_id: selectedId,
        latitude_deg: String(latitude),
        longitude_deg: String(longitude),
        entry_azimuth_deg: String(azimuth),
      });

      const response = await fetch(
        `/api/simulation/from-neo?${params.toString()}`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        throw new Error(data.message || "Simulation failed");
      }

      setSimulation(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------------------------
  // Earth projection
  // ---------------------------------------------------------

  function projectEarthPoint(lat, lon) {
    const x = 50 + lon / 3.6;
    const y = 50 - lat / 1.8;

    return {
      x: Math.max(3, Math.min(97, x)),
      y: Math.max(5, Math.min(95, y)),
    };
  }

  const marker =
    trajectory != null
      ? projectEarthPoint(
          trajectory.entry_latitude_deg,
          trajectory.entry_longitude_deg
        )
      : null;

  const markerScale = animationRunning
    ? 1 + Math.sin(animationIndex * 0.4) * 0.15
    : 1;

  // ---------------------------------------------------------
  // Render
  // ---------------------------------------------------------

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">NASA SPACE APPS • METEOR MADNESS</p>

          <h1>☄️ Meteor Madness</h1>

          <p className="subtitle">
            Atmospheric-entry physics driven by real NASA near-Earth asteroid
            data.
          </p>
        </div>
      </header>

      <main>
        {error && <div className="error">{error}</div>}

        {/* =================================================
            NASA ASTEROID SELECTION
        ================================================= */}

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="section-label">NASA NEOWS</p>
              <h2>Near-Earth Asteroids</h2>
            </div>

            <span className="badge">{asteroids.length} objects</span>
          </div>

          <div className="asteroid-grid">
            {asteroids.slice(0, 12).map((asteroid) => (
              <button
                key={asteroid.id}
                className={`asteroid-card ${
                  String(asteroid.id) === selectedId ? "selected" : ""
                }`}
                onClick={() => {
                  setSelectedId(String(asteroid.id));
                  setSimulation(null);
                  setAnimationIndex(0);
                  setAnimationRunning(false);
                }}
              >
                <strong>{asteroid.name}</strong>

                <span>
                  Diameter: {asteroid.diameter_km?.toFixed(4) ?? "N/A"} km
                </span>

                <span>
                  Velocity:{" "}
                  {asteroid.velocity_kph
                    ? `${(asteroid.velocity_kph / 3600).toFixed(2)} km/s`
                    : "N/A"}
                </span>

                <span>
                  Miss distance:{" "}
                  {asteroid.miss_distance_km
                    ? `${(asteroid.miss_distance_km / 1e6).toFixed(
                        2
                      )} million km`
                    : "N/A"}
                </span>

                {asteroid.hazardous && (
                  <span className="hazard">Potentially hazardous</span>
                )}
              </button>
            ))}
          </div>

          {/* =================================================
              V0.2 TRAJECTORY SCENARIO
          ================================================= */}

          <div className="scenario-panel">
            <div>
              <p className="section-label">V0.2 TRAJECTORY SCENARIO</p>

              <h3>Choose atmospheric-entry location</h3>

              <p className="scenario-note">
                These coordinates define the simulated geographic scenario.
                They are not derived from NASA orbital data yet.
              </p>
            </div>

            <div className="scenario-grid">
              <label>
                <span>Latitude (°)</span>

                <input
                  type="number"
                  min="-90"
                  max="90"
                  step="0.0001"
                  value={latitude}
                  onChange={(event) =>
                    setLatitude(Number(event.target.value))
                  }
                />
              </label>

              <label>
                <span>Longitude (°)</span>

                <input
                  type="number"
                  min="-180"
                  max="180"
                  step="0.0001"
                  value={longitude}
                  onChange={(event) =>
                    setLongitude(Number(event.target.value))
                  }
                />
              </label>

              <label>
                <span>Entry azimuth (°)</span>

                <input
                  type="number"
                  min="0"
                  max="359.999"
                  step="1"
                  value={azimuth}
                  onChange={(event) =>
                    setAzimuth(Number(event.target.value))
                  }
                />
              </label>
            </div>
          </div>

          <div className="simulation-controls">
            <div>
              <p className="section-label">SELECTED OBJECT</p>

              <h3>{selectedAsteroid?.name ?? "None selected"}</h3>
            </div>

            <button
              className="simulate-button"
              onClick={runSimulation}
              disabled={!selectedId || loading}
            >
              {loading ? "Running physics..." : "Run Simulation →"}
            </button>
          </div>
        </section>

        {/* =================================================
            SIMULATION RESULTS
        ================================================= */}

        {simulation && (
          <>
            {/* =================================================
                ATMOSPHERIC ENTRY ANIMATION
            ================================================= */}

            <section className="panel entry-panel">
              <div className="entry-animation">
                <div className="space-label">ATMOSPHERIC ENTRY</div>

                <div className="entry-sky">
                  <div
                    className="meteor"
                    style={{
                      left: `${15 + animatedProgress * 70}%`,
                      top: `${8 + animatedProgress * 72}%`,
                    }}
                  >
                    <div className="meteor-head">☄</div>

                    <div className="meteor-trail" />
                  </div>

                  <div className="atmosphere-layer atmosphere-1" />
                  <div className="atmosphere-layer atmosphere-2" />

                  <div className="earth-horizon" />

                  <div className="entry-info">
                    <span>ALTITUDE</span>
                    <strong>{animatedAltitude.toFixed(1)} km</strong>

                    <span>VELOCITY</span>
                    <strong>{animatedVelocity.toFixed(2)} km/s</strong>

                    <span>MASS</span>
                    <strong>{animatedMass.toFixed(0)} t</strong>
                  </div>
                </div>

                <div className="animation-progress">
                  <div
                    className="animation-progress-bar"
                    style={{
                      width: `${animatedProgress * 100}%`,
                    }}
                  />
                </div>

                <div className="animation-status">
                  {simulationData?.fragmentation_detected &&
                  simulationData?.fragmentation_altitude_m != null &&
                  animatedAltitude <=
                    simulationData.fragmentation_altitude_m / 1000 ? (
                    <strong>💥 FRAGMENTATION DETECTED</strong>
                  ) : animationRunning ? (
                    <strong>☄️ ATMOSPHERIC ENTRY IN PROGRESS</strong>
                  ) : (
                    <strong>✓ SIMULATION COMPLETE</strong>
                  )}
                </div>
              </div>
            </section>

            {/* =================================================
                EARTH / LOCATION
            ================================================= */}

            <section className="panel earth-panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">EARTH SCENARIO</p>

                  <h2>Simulated Entry Location</h2>
                </div>

                <span className="badge">V0.2</span>
              </div>

              <div className="earth-layout">
                <div className="earth-visual">
                  <svg
                    className="earth-svg"
                    viewBox="0 0 100 100"
                    role="img"
                    aria-label="Simplified Earth projection showing the simulated entry location"
                  >
                    <defs>
                      <radialGradient
                        id="earthGradient"
                        cx="38%"
                        cy="35%"
                        r="70%"
                      >
                        <stop offset="0%" />
                        <stop offset="100%" />
                      </radialGradient>
                    </defs>

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

                    {marker && (
                      <>
                        <circle
                          cx={marker.x}
                          cy={marker.y}
                          r={2.2 * markerScale}
                          className="impact-marker"
                        />

                        <circle
                          cx={marker.x}
                          cy={marker.y}
                          r={5 * markerScale}
                          className="impact-pulse"
                        />
                      </>
                    )}
                  </svg>
                </div>

                <div className="trajectory-details">
                  <p className="section-label">SCENARIO COORDINATES</p>

                  <div className="coordinate-grid">
                    <div>
                      <span>Latitude</span>

                      <strong>
                        {trajectory?.entry_latitude_deg?.toFixed(4)}°
                      </strong>
                    </div>

                    <div>
                      <span>Longitude</span>

                      <strong>
                        {trajectory?.entry_longitude_deg?.toFixed(4)}°
                      </strong>
                    </div>

                    <div>
                      <span>Azimuth</span>

                      <strong>
                        {trajectory?.entry_azimuth_deg?.toFixed(1)}°
                      </strong>
                    </div>

                    <div>
                      <span>Entry angle</span>

                      <strong>
                        {trajectory?.entry_angle_deg?.toFixed(1)}°
                      </strong>
                    </div>
                  </div>

                  <p className="coordinate-source">
                    📍 {trajectory?.coordinate_source}
                  </p>

                  <p className="scenario-note">{trajectory?.note}</p>
                </div>
              </div>
            </section>

            {/* =================================================
                MODEL ASSUMPTIONS
            ================================================= */}

            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">MODEL ASSUMPTIONS</p>

                  <h2>Physics Parameters</h2>
                </div>
              </div>

              <p className="assumption-note">
                These values are engineering assumptions used by the V0.1
                model. They are not measured physical properties of the
                selected asteroid.
              </p>

              <div className="assumptions-grid">
                {Object.entries(simulation.assumptions ?? {}).map(
                  ([key, value]) => (
                    <div className="assumption-card" key={key}>
                      <span>
                        {key
                          .replaceAll("_", " ")
                          .replace(/\b\w/g, (letter) => letter.toUpperCase())}
                      </span>

                      <strong>
                        {typeof value === "number"
                          ? value.toLocaleString()
                          : String(value)}
                      </strong>
                    </div>
                  )
                )}
              </div>
            </section>

            {/* =================================================
                SCIENTIFIC SCOPE
            ================================================= */}

            <section className="panel scientific-note">
              <p className="section-label">SCIENTIFIC SCOPE</p>

              <h2>Model limitations</h2>

              <p>
                Meteor Madness V0.1 is a simplified engineering model for
                atmospheric-entry analysis. It is not a NASA-grade
                atmospheric entry, fragmentation, CFD, hydrocode, or
                consequence model.
              </p>

              <p>
                Results depend on uncertain asteroid properties and the
                engineering assumptions shown above. Fragmentation is
                represented using an effective dynamic-pressure threshold,
                and atmospheric energy deposition is based on modeled
                aerodynamic drag work.
              </p>
            </section>

            {/* =================================================
                SUMMARY
            ================================================= */}

            <section className="results-grid">
              <div className="result-card">
                <span>Outcome</span>

                <strong>{simulationData.outcome}</strong>
              </div>

              <div className="result-card">
                <span>Initial mass</span>

                <strong>
                  {(simulationData.initial_mass_kg / 1e6).toFixed(2)} Mt
                </strong>
              </div>

              <div className="result-card">
                <span>Atmospheric drag work</span>

                <strong>
                  {(
                    simulationData.atmospheric_drag_work_J / 1e15
                  ).toFixed(3)}{" "}
                  PJ
                </strong>
              </div>

              <div className="result-card">
                <span>Fragmentation</span>

                <strong>
                  {simulationData.fragmentation_detected
                    ? "Detected"
                    : "Not detected"}
                </strong>
              </div>

              <div className="result-card">
                <span>Ground impact energy</span>

                <strong>
                  {simulationData.ground_impact_energy_J != null
                    ? (
                        simulationData.ground_impact_energy_J / 1e15
                      ).toFixed(3) + " PJ"
                    : "N/A"}
                </strong>
              </div>

              <div className="result-card">
                <span>Atmospheric energy fraction</span>

                <strong>
                  {atmosphericFraction != null
                    ? `${atmosphericFraction.toFixed(1)}%`
                    : "N/A"}
                </strong>
              </div>
            </section>

            {/* =================================================
                FRAGMENTATION EVENT
            ================================================= */}

            {simulationData.fragmentation_detected && (
              <section className="panel event-panel">
                <p className="section-label">FRAGMENTATION EVENT</p>

                <h2>Structural failure detected</h2>

                <p>
                  The simplified model detected fragmentation when atmospheric
                  dynamic pressure reached the configured effective material
                  strength.
                </p>

                <div className="event-details">
                  <div>
                    <span>Altitude</span>

                    <strong>
                      {fragmentationAltitude?.toFixed(2)} km
                    </strong>
                  </div>

                  <div>
                    <span>Velocity</span>

                    <strong>
                      {simulationData.profile?.length
                        ? (
                            simulationData.profile.reduce(
                              (closest, point) =>
                                Math.abs(
                                  point.altitude_m -
                                    simulationData.fragmentation_altitude_m
                                ) <
                                Math.abs(
                                  closest.altitude_m -
                                    simulationData.fragmentation_altitude_m
                                )
                                  ? point
                                  : closest,
                              simulationData.profile[0]
                            ).velocity_m_s / 1000
                          ).toFixed(2)
                        : "N/A"}{" "}
                      km/s
                    </strong>
                  </div>
                </div>
              </section>
            )}

            {/* =================================================
                TRAJECTORY + ATMOSPHERIC INTERACTION
            ================================================= */}

            <section className="charts-grid">
              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">TRAJECTORY</p>

                    <h2>Velocity vs Altitude</h2>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      label={{
                        value: "Altitude (km)",
                        position: "insideBottom",
                        offset: -5,
                      }}
                    />

                    <YAxis
                      label={{
                        value: "Velocity (km/s)",
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />

                    <Tooltip />

                    {fragmentationAltitude != null && (
                      <ReferenceLine
                        x={fragmentationAltitude}
                        label="Fragmentation"
                      />
                    )}

                    <Line
                      type="monotone"
                      dataKey="velocity_km_s"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">
                      ATMOSPHERIC INTERACTION
                    </p>

                    <h2>Dynamic Pressure</h2>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      label={{
                        value: "Altitude (km)",
                        position: "insideBottom",
                        offset: -5,
                      }}
                    />

                    <YAxis
                      label={{
                        value: "Pressure (MPa)",
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />

                    <Tooltip />

                    {fragmentationAltitude != null && (
                      <ReferenceLine
                        x={fragmentationAltitude}
                        label="Fragmentation"
                      />
                    )}

                    <Line
                      type="monotone"
                      dataKey="dynamic_pressure_MPa"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* =================================================
                MASS + ENERGY DEPOSITION
            ================================================= */}

            <section className="charts-grid">
              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">ABLATION</p>

                    <h2>Mass vs Altitude</h2>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      label={{
                        value: "Altitude (km)",
                        position: "insideBottom",
                        offset: -5,
                      }}
                    />

                    <YAxis
                      label={{
                        value: "Mass (tonnes)",
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />

                    <Tooltip />

                    {fragmentationAltitude != null && (
                      <ReferenceLine
                        x={fragmentationAltitude}
                        label="Fragmentation"
                      />
                    )}

                    <Line
                      type="monotone"
                      dataKey="mass_tonnes"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">ENERGY DEPOSITION</p>

                    <h2>Atmospheric Energy Deposition</h2>
                  </div>
                </div>

                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      label={{
                        value: "Altitude (km)",
                        position: "insideBottom",
                        offset: -5,
                      }}
                    />

                    <YAxis
                      label={{
                        value: "Energy / metre (GJ/m)",
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />

                    <Tooltip />

                    {fragmentationAltitude != null && (
                      <ReferenceLine
                        x={fragmentationAltitude}
                        label="Fragmentation"
                      />
                    )}

                    <Line
                      type="monotone"
                      dataKey="energy_deposition_GJ_m"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
