import { useEffect, useMemo, useState } from "react";
import "./App.css";
import "./analyst.css";
import "./asteroid-picker.css";
import ConsequencesPanel from "./components/ConsequencesPanel";
import EarthImpactMap from "./components/EarthImpactMap";
import AnalystPanel from "./components/AnalystPanel";
import RiskMitigationChat from "./components/RiskMitigationChat";
import StoryMode from "./components/StoryMode";
import { ensureEnrichment } from "./localEnrichment";

function formatAsteroidOption(a) {
  const name = a.name || a.id || "Unknown";
  const diam =
    a.diameter_km != null
      ? `${Number(a.diameter_km).toFixed(3)} km`
      : a.estimated_diameter_km != null
        ? `${Number(a.estimated_diameter_km).toFixed(3)} km`
        : "⌀ ?";
  const haz = a.hazardous || a.is_potentially_hazardous_asteroid ? "PHA" : "safe";
  const miss =
    a.miss_distance_km != null
      ? `miss ${Number(a.miss_distance_km).toLocaleString()} km`
      : "";
  return `${name} · ${diam} · ${haz}${miss ? ` · ${miss}` : ""}`;
}

function App() {
  const [asteroids, setAsteroids] = useState([]);
  const [selectedId, setSelectedId] = useState("");

  const [latitude, setLatitude] = useState("24.3745");
  const [longitude, setLongitude] = useState("88.6042");
  const [azimuth, setAzimuth] = useState("90");

  const [simulation, setSimulation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadAsteroids() {
      try {
        const response = await fetch("/api/neos");
        if (!response.ok) {
          throw new Error("Failed to fetch NASA asteroid data");
        }
        const data = await response.json();
        if (cancelled) return;

        const objects = Array.isArray(data.asteroids) ? data.asteroids : [];
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

  const selectedAsteroid = useMemo(() => {
    return (
      asteroids.find((item) => String(item.id) === String(selectedId)) ?? null
    );
  }, [asteroids, selectedId]);

  const simulationData = simulation?.simulation ?? null;
  const trajectory = simulation?.trajectory ?? null;
  const analyst = simulation?.analyst ?? simulationData?.analyst ?? null;
  const environment =
    simulation?.environment ??
    simulation?.terrain ??
    simulationData?.environment ??
    simulationData?.terrain ??
    null;
  const terrain = environment;
  const tsunami = simulation?.tsunami ?? simulationData?.tsunami ?? null;
  const impactBranch =
    simulation?.impact_branch ?? simulationData?.impact_branch ?? null;
  const unifiedReport = simulation?.unified_report ?? null;

  const branch = impactBranch?.branch || environment?.physics_branch || null;
  const isLand = branch === "land";
  const isOcean = branch === "ocean";
  const isIce = branch === "ice";

  const landConsequences =
    isLand
      ? unifiedReport?.land_consequences ??
        simulationData?.consequences ??
        null
      : null;

  function onCoordinateChange(setter) {
    return (event) => {
      const v = event.target.value.trim();
      if (v === "" || /^-?\d*\.?\d*$/.test(v)) {
        setter(v);
      }
    };
  }

  async function runSimulation() {
    if (!selectedId) return;

    setLoading(true);
    setError("");
    setSimulation(null);

    try {
      const latNum = Number(latitude);
      const lonNum = Number(longitude);
      const azNum = Number(azimuth);

      if (Number.isNaN(latNum) || latNum < -90 || latNum > 90) {
        throw new Error("Latitude must be a number between -90 and 90");
      }
      if (Number.isNaN(lonNum) || lonNum < -180 || lonNum > 180) {
        throw new Error("Longitude must be a number between -180 and 180");
      }
      if (Number.isNaN(azNum) || azNum < 0 || azNum >= 360) {
        throw new Error("Azimuth must be a number between 0 and 360");
      }

      const params = new URLSearchParams({
        asteroid_id: selectedId,
        latitude_deg: String(latNum),
        longitude_deg: String(lonNum),
        entry_azimuth_deg: String(azNum),
      });

      const response = await fetch(
        `/api/simulation/from-neo?${params.toString()}`,
        { method: "POST" }
      );

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("Backend returned invalid JSON");
      }

      if (!response.ok || data.status === "error") {
        throw new Error(data.message || "Simulation failed");
      }

      data = ensureEnrichment(data, latNum, lonNum);
      setSimulation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <main>
        <header className="hero-header">
          <h1>Meteor Madness</h1>
          <p>
            Hierarchical pipeline — NASA → entry → environment → physics branch
            → AI analyst → Mitigation and more · Story Mode
          </p>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="simulation-controls scenario-grid">
          <label className="asteroid-select-label">
            <span>Asteroid ☄️</span>
            <select
              className="asteroid-select"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              size={Math.min(8, Math.max(4, asteroids.length || 4))}
            >
              {asteroids.length === 0 && (
                <option value="">Loading NASA NeoWs…</option>
              )}
              {asteroids.map((a) => (
                <option key={a.id} value={a.id}>
                  {formatAsteroidOption(a)}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Latitude (°)</span>
            <input
              type="text"
              inputMode="decimal"
              placeholder="-90 to 90"
              value={latitude}
              onChange={onCoordinateChange(setLatitude)}
            />
          </label>

          <label>
            <span>Longitude (°)</span>
            <input
              type="text"
              inputMode="decimal"
              placeholder="-180 to 180"
              value={longitude}
              onChange={onCoordinateChange(setLongitude)}
            />
          </label>

          <label>
            <span>Entry azimuth (°)</span>
            <input
              type="text"
              inputMode="decimal"
              placeholder="0 to 359"
              value={azimuth}
              onChange={(e) => {
                const v = e.target.value.trim();
                if (v === "" || /^\d*\.?\d*$/.test(v)) {
                  setAzimuth(v);
                }
              }}
            />
          </label>

          <button
            type="button"
            className="simulate-button"
            onClick={runSimulation}
            disabled={loading || !selectedId}
          >
            {loading ? "Running…" : "Run simulation"}
          </button>
        </section>

        {selectedAsteroid && (
          <section className="asteroid-meta asteroid-detail-card">
            <h3>{selectedAsteroid.name || selectedAsteroid.id}</h3>
            <ul>
              <li>
                <span>ID</span>
                <strong>{selectedAsteroid.id}</strong>
              </li>
              <li>
                <span>Diameter</span>
                <strong>
                  {selectedAsteroid.diameter_km != null
                    ? `${Number(selectedAsteroid.diameter_km).toFixed(4)} km`
                    : selectedAsteroid.estimated_diameter_km != null
                      ? `${Number(
                          selectedAsteroid.estimated_diameter_km
                        ).toFixed(4)} km`
                      : "N/A"}
                </strong>
              </li>
              <li>
                <span>Hazardous</span>
                <strong>
                  {selectedAsteroid.hazardous ||
                  selectedAsteroid.is_potentially_hazardous_asteroid
                    ? "Yes (PHA)"
                    : "No"}
                </strong>
              </li>
              <li>
                <span>Miss distance</span>
                <strong>
                  {selectedAsteroid.miss_distance_km != null
                    ? `${Number(
                        selectedAsteroid.miss_distance_km
                      ).toLocaleString()} km`
                    : "N/A"}
                </strong>
              </li>
              <li>
                <span>Velocity</span>
                <strong>
                  {selectedAsteroid.velocity_kph != null
                    ? `${Number(
                        selectedAsteroid.velocity_kph
                      ).toLocaleString()} km/h`
                    : "N/A"}
                </strong>
              </li>
              <li>
                <span>Approach date</span>
                <strong>{selectedAsteroid.approach_date || "N/A"}</strong>
              </li>
            </ul>
          </section>
        )}

        {simulation && (
          <>
            <section className="results-grid">
              <div className="result-card">
                <span>Entry outcome</span>
                <strong>{simulationData?.outcome ?? "N/A"}</strong>
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
                <span>Environment class</span>
                <strong>
                  {environment?.surface || environment?.surface_type || "N/A"}
                </strong>
              </div>
              <div className="result-card">
                <span>Physics branch</span>
                <strong>{branch ?? "N/A"}</strong>
              </div>
            </section>

            {isLand && landConsequences && (
              <ConsequencesPanel consequences={landConsequences} />
            )}

            {isOcean && (
              <section className="panel consequences-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">OCEAN BRANCH</p>
                    <h2>Ocean impact physics</h2>
                  </div>
                  <span className="badge">No land crater</span>
                </div>
                <p className="muted">
                  Land crater / blast / seismic panels are suppressed. Ocean
                  branch owns displacement, tsunami, and seafloor interaction.
                </p>
              </section>
            )}

            {isIce && (
              <section className="panel consequences-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">ICE BRANCH</p>
                    <h2>Ice impact physics</h2>
                  </div>
                </div>
              </section>
            )}

            {branch === "undetermined" && (
              <section className="panel consequences-panel">
                <div className="panel-header">
                  <div>
                    <p className="section-label">UNKNOWN ENVIRONMENT</p>
                    <h2>No environment-specific physics</h2>
                  </div>
                </div>
                <p className="muted">
                  Entry physics still ran. Crater and tsunami were refused
                  because Earth environment data was unavailable.
                </p>
              </section>
            )}

            <AnalystPanel
              analyst={analyst}
              terrain={terrain}
              environment={environment}
              impactBranch={impactBranch}
              tsunami={tsunami}
              hasSimulation={Boolean(simulation)}
            />

            {trajectory && (
              <EarthImpactMap
                trajectory={trajectory}
                consequences={isLand ? landConsequences : null}
              />
            )}
          </>
        )}
      </main>

      <StoryMode
        asteroids={asteroids}
        selectedAsteroid={selectedAsteroid}
        simulation={simulation}
        simulationData={simulationData}
        environment={environment}
        impactBranch={impactBranch}
        analyst={analyst}
        latitude={latitude}
        longitude={longitude}
        tsunami={tsunami}
      />

      <RiskMitigationChat
        simulation={simulation}
        environment={environment}
        impactBranch={impactBranch}
        analyst={analyst}
        simulationData={simulationData}
        asteroid={selectedAsteroid}
        tsunami={tsunami}
        latitude={latitude}
        longitude={longitude}
        azimuth={azimuth}
      />
    </div>
  );
}

export default App;
