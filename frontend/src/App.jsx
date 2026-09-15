import { useEffect, useMemo, useState } from "react";
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
import ConsequencesPanel
  from "./components/ConsequencesPanel";
import EarthImpactMap
  from "./components/EarthImpactMap";

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
    let cancelled = false;

    async function loadAsteroids() {
      try {
        const response = await fetch("/api/neos");

        if (!response.ok) {
          throw new Error("Failed to fetch NASA asteroid data");
        }

        const data = await response.json();

        if (cancelled) {
          return;
        }

        const objects = Array.isArray(data.asteroids)
          ? data.asteroids
          : [];

        setAsteroids(objects);

        if (objects.length > 0) {
          setSelectedId(String(objects[0].id));
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to fetch NASA asteroid data"
          );
        }
      }
    }

    loadAsteroids();

    return () => {
      cancelled = true;
    };
  }, []);

  // ---------------------------------------------------------
  // Derived simulation data
  // ---------------------------------------------------------

  const selectedAsteroid = asteroids.find(
    (asteroid) => String(asteroid.id) === selectedId
  );

  const simulationData = simulation?.simulation ?? null;
  const trajectory = simulation?.trajectory ?? null;

  const fragmentationAltitude =
    simulationData?.fragmentation_altitude_m != null
      ? simulationData.fragmentation_altitude_m / 1000
      : null;

  // ---------------------------------------------------------
  // Simulation profile
  // ---------------------------------------------------------

  const profile = useMemo(() => {
    if (!Array.isArray(simulationData?.profile)) {
      return [];
    }

    return simulationData.profile.map((point) => ({
      time_s: point.time_s ?? 0,
      altitude_km: (point.altitude_m ?? 0) / 1000,
      velocity_km_s: (point.velocity_m_s ?? 0) / 1000,
      mass_tonnes: (point.mass_kg ?? 0) / 1000,
      dynamic_pressure_MPa:
        (point.dynamic_pressure_Pa ?? 0) / 1e6,
      energy_deposition_GJ_m:
        (point.energy_deposition_per_meter_J_m ?? 0) / 1e9,
      density_kg_m3: point.density_kg_m3 ?? 0,
      drag_force_N: point.drag_force_N ?? 0,
      drag_power_W: point.drag_power_W ?? 0,
    }));
  }, [simulationData]);

  const animationPoint =
    profile.length > 0
      ? profile[Math.min(animationIndex, profile.length - 1)]
      : null;

  // ---------------------------------------------------------
  // Actual simulation values
  // ---------------------------------------------------------

  const initialAltitudeKm =
    profile.length > 0 ? profile[0].altitude_km : 80;

  const finalAltitudeKm =
    profile.length > 0
      ? profile[profile.length - 1].altitude_km
      : 0;

  const altitudeRangeKm = Math.max(
    initialAltitudeKm - finalAltitudeKm,
    1
  );

  const animatedAltitude = animationPoint?.altitude_km ?? 0;

  const animatedVelocity =
    animationPoint?.velocity_km_s ?? 0;

  const animatedMass =
    animationPoint?.mass_tonnes ?? 0;

  const animatedPressure =
    animationPoint?.dynamic_pressure_MPa ?? 0;

  const animatedDensity =
    animationPoint?.density_kg_m3 ?? 0;

  const animatedDragPower =
    animationPoint?.drag_power_W ?? 0;

  // ---------------------------------------------------------
  // Visual progress
  // ---------------------------------------------------------

  const animatedProgress = Math.min(
    Math.max(
      (initialAltitudeKm - animatedAltitude) /
        altitudeRangeKm,
      0
    ),
    1
  );

  const initialMassTonnes =
    profile.length > 0 ? profile[0].mass_tonnes : 0;

  const massRatio =
    initialMassTonnes > 0
      ? Math.min(
          Math.max(animatedMass / initialMassTonnes, 0),
          1
        )
      : 1;

  // Meteor gets smaller as mass is lost.
  const meteorScale = 0.55 + massRatio * 0.45;

  // ---------------------------------------------------------
  // Atmospheric intensity
  // ---------------------------------------------------------

  const pressureIntensity = Math.min(
    Math.log10(1 + Math.max(animatedPressure, 0)) / 2,
    1
  );

  const densityIntensity = Math.min(
    Math.log10(1 + Math.max(animatedDensity, 0)) / 2,
    1
  );

  const dragIntensity = Math.min(
    Math.log10(1 + Math.max(animatedDragPower, 0)) / 16,
    1
  );

  const meteorIntensity = Math.min(
    pressureIntensity * 0.5 +
      densityIntensity * 0.25 +
      dragIntensity * 0.25,
    1
  );

  const meteorOpacity = 0.72 + meteorIntensity * 0.28;

  const trailScale = 0.8 + meteorIntensity * 1.8;

  // ---------------------------------------------------------
  // Atmospheric entry animation
  // ---------------------------------------------------------

  useEffect(() => {
    if (profile.length < 2) {
      setAnimationRunning(false);
      setAnimationIndex(0);
      return undefined;
    }

    setAnimationIndex(0);
    setAnimationRunning(true);

    const firstTime = profile[0].time_s ?? 0;

    const lastTime =
      profile[profile.length - 1].time_s ?? firstTime;

    const simulationDuration = Math.max(
      lastTime - firstTime,
      0.01
    );

    // Eight seconds keeps the animation presentation-friendly
    // while preserving the relative timing between samples.
    const animationDuration = 8000;

    const startTime = performance.now();

    let frameId;

    function animate(now) {
      const elapsed = now - startTime;

      const progress = Math.min(
        elapsed / animationDuration,
        1
      );

      const targetTime =
        firstTime +
        progress * simulationDuration;

      let index = 0;

      for (let i = 0; i < profile.length; i += 1) {
        if (profile[i].time_s <= targetTime) {
          index = i;
        } else {
          break;
        }
      }

      setAnimationIndex(index);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      } else {
        setAnimationRunning(false);
      }
    }

    frameId = requestAnimationFrame(animate);

    return () => {
      if (frameId) {
        cancelAnimationFrame(frameId);
      }
    };
  }, [profile]);

  // ---------------------------------------------------------
  // Atmospheric event state
  // ---------------------------------------------------------

  const fragmentationDetected =
    Boolean(simulationData?.fragmentation_detected) &&
    fragmentationAltitude != null;

  const fragmentationReached =
    fragmentationDetected &&
    animatedAltitude <= fragmentationAltitude;

  const animationStatus = fragmentationReached
    ? "💥 FRAGMENTATION DETECTED"
    : animationRunning
      ? "☄️ ATMOSPHERIC ENTRY IN PROGRESS"
      : "✓ SIMULATION COMPLETE";

  // ---------------------------------------------------------
  // Run simulation
  // ---------------------------------------------------------

  async function runSimulation() {
    if (!selectedId) {
      return;
    }

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

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error("Backend returned invalid JSON");
      }

      if (!response.ok || data.status === "error") {
        throw new Error(
          data.message || "Simulation failed"
        );
      }

      setSimulation(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Simulation failed"
      );
    } finally {
      setLoading(false);
    }
  }

  // ---------------------------------------------------------
  // Earth projection
  // ---------------------------------------------------------

  function projectEarthPoint(lat, lon) {
    const safeLat = Number(lat) || 0;
    const safeLon = Number(lon) || 0;

    const x = 50 + safeLon / 3.6;
    const y = 50 - safeLat / 1.8;

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

  const atmosphericFraction =
    simulationData?.atmospheric_fraction != null
      ? simulationData.atmospheric_fraction * 100
      : null;

  // ---------------------------------------------------------
  // Fragment visual positions
  // ---------------------------------------------------------

  /*
   * These are visual fragments only.
   *
   * The actual backend physics remains the source of truth.
   * We are not pretending that the frontend has calculated
   * independent fragment trajectories.
   */

  const fragmentProgress =
    fragmentationReached && fragmentationAltitude != null
      ? Math.min(
          Math.max(
            (fragmentationAltitude - animatedAltitude) /
              Math.max(fragmentationAltitude, 1),
            0
          ),
          1
        )
      : 0;

  const fragmentSpread =
    8 + fragmentProgress * 18;

  const fragmentVerticalSpread =
    3 + fragmentProgress * 8;

  // ---------------------------------------------------------
  // Render
  // ---------------------------------------------------------

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">
            NASA SPACE APPS • METEOR MADNESS
          </p>

          <h1>☄️ Meteor Madness</h1>

          <p className="subtitle">
            Atmospheric-entry physics driven by real NASA
            near-Earth asteroid data.
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

            <span className="badge">
              {asteroids.length} objects
            </span>
          </div>

          <div className="asteroid-grid">
            {asteroids.map((asteroid) => (
              <button
                key={asteroid.id}
                className={`asteroid-card ${
                  String(asteroid.id) === selectedId
                    ? "selected"
                    : ""
                }`}
                onClick={() => {
                  setSelectedId(String(asteroid.id));
                  setSimulation(null);
                  setAnimationIndex(0);
                  setAnimationRunning(false);
                  setError("");
                }}
              >
                <strong>{asteroid.name}</strong>

                <span>
                  Diameter:{" "}
                  {typeof asteroid.diameter_km === "number"
                    ? asteroid.diameter_km.toFixed(4)
                    : "N/A"}{" "}
                  km
                </span>

                <span>
                  Velocity:{" "}
                  {asteroid.velocity_kph
                    ? `${(
                        asteroid.velocity_kph / 3600
                      ).toFixed(2)} km/s`
                    : "N/A"}
                </span>

                <span>
                  Miss distance:{" "}
                  {asteroid.miss_distance_km
                    ? `${(
                        asteroid.miss_distance_km / 1e6
                      ).toFixed(2)} million km`
                    : "N/A"}
                </span>

                {asteroid.hazardous && (
                  <span className="hazard">
                    Potentially hazardous
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* =================================================
              V0.2 TRAJECTORY SCENARIO
          ================================================= */}

          <div className="scenario-panel">
            <div>
              <p className="section-label">
                V0.2 TRAJECTORY SCENARIO
              </p>

              <h3>Choose atmospheric-entry location</h3>

              <p className="scenario-note">
                These coordinates define the simulated
                geographic scenario. They are not derived from
                NASA orbital data yet.
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
              <p className="section-label">
                SELECTED OBJECT
              </p>

              <h3>
                {selectedAsteroid?.name ?? "None selected"}
              </h3>
            </div>

            <button
              className="simulate-button"
              onClick={runSimulation}
              disabled={!selectedId || loading}
            >
              {loading
                ? "Running physics..."
                : "Run Simulation →"}
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
                <div className="space-label">
                  ATMOSPHERIC ENTRY
                </div>

                <div className="entry-sky">
                  {/* SINGLE BODY BEFORE FRAGMENTATION */}

                  {!fragmentationReached && (
                    <div
                      className="meteor"
                      style={{
                        left: `${15 + animatedProgress * 70}%`,
                        top: `${8 + animatedProgress * 72}%`,
                        transform: `translate(-50%, -50%) scale(${meteorScale})`,
                        opacity: meteorOpacity,
                        filter: `brightness(${1 + meteorIntensity * 1.8})`,
                      }}
                    >
                      <div className="meteor-head">☄</div>

                      <div
                        className="meteor-trail"
                        style={{
                          transform: `scaleY(${trailScale})`,
                        }}
                      />
                    </div>
                  )}

                  {/* VISUAL FRAGMENTATION */}

                  {fragmentationReached && (
                    <>
                      <div
                        className="meteor"
                        style={{
                          left: `calc(${15 + animatedProgress * 70}% - ${fragmentSpread}px)`,
                          top: `calc(${8 + animatedProgress * 72}% - ${fragmentVerticalSpread}px)`,
                          transform: `translate(-50%, -50%) scale(${meteorScale * 0.65})`,
                          opacity: meteorOpacity,
                          filter: `brightness(${1 + meteorIntensity * 1.8})`,
                        }}
                      >
                        <div className="meteor-head">☄</div>

                        <div
                          className="meteor-trail"
                          style={{
                            transform: `scaleY(${trailScale * 0.7})`,
                          }}
                        />
                      </div>

                      <div
                        className="meteor"
                        style={{
                          left: `calc(${15 + animatedProgress * 70}% + ${fragmentSpread}px)`,
                          top: `calc(${8 + animatedProgress * 72}% + ${fragmentVerticalSpread}px)`,
                          transform: `translate(-50%, -50%) scale(${meteorScale * 0.5})`,
                          opacity: meteorOpacity,
                          filter: `brightness(${1 + meteorIntensity * 1.5})`,
                        }}
                      >
                        <div className="meteor-head">☄</div>

                        <div
                          className="meteor-trail"
                          style={{
                            transform: `scaleY(${trailScale * 0.55})`,
                          }}
                        />
                      </div>

                      {/* Small debris spark */}

                      <div
                        className="meteor"
                        style={{
                          left: `calc(${15 + animatedProgress * 70}% + ${fragmentSpread * 0.3}px)`,
                          top: `calc(${8 + animatedProgress * 72}% - ${fragmentVerticalSpread * 1.8}px)`,
                          transform:
                            "translate(-50%, -50%) scale(0.18)",
                          opacity: 0.9,
                        }}
                      >
                        <div className="meteor-head">•</div>
                      </div>
                    </>
                  )}

                  <div className="atmosphere-layer atmosphere-1" />

                  <div className="atmosphere-layer atmosphere-2" />

                  <div className="earth-horizon" />

                  <div className="entry-info">
                    <span>ALTITUDE</span>

                    <strong>
                      {animatedAltitude.toFixed(1)} km
                    </strong>

                    <span>VELOCITY</span>

                    <strong>
                      {animatedVelocity.toFixed(2)} km/s
                    </strong>

                    <span>MASS</span>

                    <strong>
                      {animatedMass.toFixed(0)} t
                    </strong>

                    <span>DYNAMIC PRESSURE</span>

                    <strong>
                      {animatedPressure.toFixed(3)} MPa
                    </strong>
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
                  <strong>{animationStatus}</strong>
                </div>
              </div>
            </section>

            {/* =================================================
                EARTH / LOCATION
            ================================================= */}

{/* =================================================
    EARTH IMPACT ANALYSIS
================================================= */}

<EarthImpactMap
  trajectory={trajectory}
  consequences={
    simulationData?.consequences
  }
  animationRunning={
    animationRunning
  }
  animationIndex={
    animationIndex
  }
/>
            {/* =================================================
                MODEL ASSUMPTIONS
            ================================================= */}

            <section className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-label">
                    MODEL ASSUMPTIONS
                  </p>

                  <h2>Physics Parameters</h2>
                </div>
              </div>

              <p className="assumption-note">
                These values are engineering assumptions used
                by the V0.1 model. They are not measured
                physical properties of the selected asteroid.
              </p>

              <div className="assumptions-grid">
                {Object.entries(
                  simulation.assumptions ?? {}
                ).map(([key, value]) => (
                  <div
                    className="assumption-card"
                    key={key}
                  >
                    <span>
                      {key
                        .replaceAll("_", " ")
                        .replace(
                          /\b\w/g,
                          (letter) =>
                            letter.toUpperCase()
                        )}
                    </span>

                    <strong>
                      {typeof value === "number"
                        ? value.toLocaleString()
                        : String(value)}
                    </strong>
                  </div>
                ))}
              </div>
            </section>

            {/* =================================================
                SCIENTIFIC SCOPE
            ================================================= */}

            <section className="panel scientific-note">
              <p className="section-label">
                SCIENTIFIC SCOPE
              </p>

              <h2>Model limitations</h2>

              <p>
                Meteor Madness V0.1 is a simplified
                engineering model for atmospheric-entry
                analysis. It is not a NASA-grade atmospheric
                entry, fragmentation, CFD, hydrocode, or
                consequence model.
              </p>

              <p>
                Results depend on uncertain asteroid
                properties and the engineering assumptions
                shown above. Fragmentation is represented
                using an effective dynamic-pressure threshold,
                and atmospheric energy deposition is based on
                modeled aerodynamic drag work.
              </p>
            </section>

            {/* =================================================
                SUMMARY
            ================================================= */}

            <section className="results-grid">
              <div className="result-card">
                <span>Outcome</span>

                <strong>
                  {simulationData?.outcome ?? "N/A"}
                </strong>
              </div>

              <div className="result-card">
                <span>Initial mass</span>

                <strong>
                  {typeof simulationData?.initial_mass_kg ===
                  "number"
                    ? (
                        simulationData.initial_mass_kg /
                        1e9
                      ).toFixed(2)
                    : "N/A"}{" "}
                  Mt
                </strong>
              </div>

              <div className="result-card">
                <span>Atmospheric drag work</span>

                <strong>
                  {typeof simulationData?.atmospheric_drag_work_J ===
                  "number"
                    ? (
                        simulationData.atmospheric_drag_work_J /
                        1e15
                      ).toFixed(3)
                    : "N/A"}{" "}
                  PJ
                </strong>
              </div>

              <div className="result-card">
                <span>Fragmentation</span>

                <strong>
                  {simulationData?.fragmentation_detected
                    ? "Detected"
                    : "Not detected"}
                </strong>
              </div>

              <div className="result-card">
                <span>Ground impact energy</span>

                <strong>
                  {typeof simulationData?.ground_impact_energy_J ===
                  "number"
                    ? (
                        simulationData.ground_impact_energy_J /
                        1e15
                      ).toFixed(3) + " PJ"
                    : "N/A"}
                </strong>
              </div>
<ConsequencesPanel
  consequences={
    simulationData?.consequences
  }
/>
              <div className="result-card">
                <span>
                  Atmospheric energy fraction
                </span>

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
                <p className="section-label">
                  FRAGMENTATION EVENT
                </p>

                <h2>Structural failure detected</h2>

                <p>
                  The simplified model detected fragmentation
                  when atmospheric dynamic pressure reached
                  the configured effective material strength.
                </p>

                <div className="event-details">
                  <div>
                    <span>Altitude</span>

                    <strong>
                      {fragmentationAltitude != null
                        ? `${fragmentationAltitude.toFixed(
                            2
                          )} km`
                        : "N/A"}
                    </strong>
                  </div>

                  <div>
                    <span>Velocity</span>

                    <strong>
                      {simulationData.profile?.length &&
                      simulationData.fragmentation_altitude_m !=
                        null
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
              {/* VELOCITY */}

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">
                      TRAJECTORY
                    </p>

                    <h2>Velocity vs Altitude</h2>
                  </div>
                </div>

                <ResponsiveContainer
                  width="100%"
                  height={320}
                >
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      type="number"
                      domain={["auto", "auto"]}
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

                    <Tooltip
                      formatter={(value) => [
                        `${Number(value).toFixed(3)} km/s`,
                        "Velocity",
                      ]}
                      labelFormatter={(value) =>
                        `Altitude: ${Number(value).toFixed(
                          2
                        )} km`
                      }
                    />

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
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* DYNAMIC PRESSURE */}

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">
                      ATMOSPHERIC INTERACTION
                    </p>

                    <h2>Dynamic Pressure</h2>
                  </div>
                </div>

                <ResponsiveContainer
                  width="100%"
                  height={320}
                >
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      type="number"
                      domain={["auto", "auto"]}
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

                    <Tooltip
                      formatter={(value) => [
                        `${Number(value).toFixed(4)} MPa`,
                        "Dynamic pressure",
                      ]}
                      labelFormatter={(value) =>
                        `Altitude: ${Number(value).toFixed(
                          2
                        )} km`
                      }
                    />

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
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            {/* =================================================
                MASS + ENERGY DEPOSITION
            ================================================= */}

            <section className="charts-grid">
              {/* MASS */}

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">
                      ABLATION
                    </p>

                    <h2>Mass vs Altitude</h2>
                  </div>
                </div>

                <ResponsiveContainer
                  width="100%"
                  height={320}
                >
                  <LineChart data={profile}>
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      type="number"
                      domain={["auto", "auto"]}
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

                    <Tooltip
                      formatter={(value) => [
                        `${Number(value).toFixed(2)} t`,
                        "Mass",
                      ]}
                      labelFormatter={(value) =>
                        `Altitude: ${Number(value).toFixed(
                          2
                        )} km`
                      }
                    />

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
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* ENERGY DEPOSITION */}

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">
                      ENERGY DEPOSITION
                    </p>

                    <h2>
                      Atmospheric Energy Deposition
                    </h2>
                  </div>
                </div>

                <ResponsiveContainer
                  width="100%"
                  height={320}
                >
                  <LineChart
                    data={profile}
                    margin={{
                      top: 10,
                      right: 20,
                      left: 20,
                      bottom: 25,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="altitude_km"
                      reversed
                      type="number"
                      domain={["auto", "auto"]}
                      label={{
                        value: "Altitude (km)",
                        position: "insideBottom",
                        offset: -15,
                      }}
                    />

                    <YAxis
                      type="number"
                      domain={["auto", "auto"]}
                      tickFormatter={(value) => {
                        if (value === 0) {
                          return "0";
                        }

                        if (Math.abs(value) >= 1000) {
                          return `${(
                            value / 1000
                          ).toFixed(1)}k`;
                        }

                        if (Math.abs(value) >= 1) {
                          return value.toFixed(1);
                        }

                        return value.toExponential(1);
                      }}
                      label={{
                        value: "Energy deposition (GJ/m)",
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />

                    <Tooltip
                      formatter={(value) => [
                        `${Number(value).toExponential(
                          3
                        )} GJ/m`,
                        "Energy deposition",
                      ]}
                      labelFormatter={(value) =>
                        `Altitude: ${Number(value).toFixed(
                          2
                        )} km`
                      }
                    />

                    {fragmentationAltitude != null && (
                      <ReferenceLine
                        x={fragmentationAltitude}
                        label="Fragmentation"
                      />
                    )}

                    <Line
                      type="monotone"
                      dataKey="energy_deposition_GJ_m"
                      strokeWidth={3}
                      dot={false}
                      connectNulls
                      isAnimationActive={false}
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
