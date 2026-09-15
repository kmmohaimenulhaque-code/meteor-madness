import { useEffect, useMemo, useState } from "react";
import "./App.css";
import "./analyst.css";
import ConsequencesPanel from "./components/ConsequencesPanel";
import EarthImpactMap from "./components/EarthImpactMap";
import AnalystPanel from "./components/AnalystPanel";
import { ensureEnrichment } from "./localEnrichment";

function App() {
  const [asteroids, setAsteroids] = useState([]);
  const [selectedId, setSelectedId] = useState("");

  // Strings so users can type negatives like -33.9 without the field resetting
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
  const terrain = simulation?.terrain ?? simulationData?.terrain ?? null;
  const tsunami = simulation?.tsunami ?? simulationData?.tsunami ?? null;

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

      // Fill terrain/tsunami/analyst if backend has not been patched yet
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
            Next Frontier — entry physics, location, tsunami, AI analyst
          </p>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="simulation-controls scenario-grid">
          <label>
            <span>Asteroid</span>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {asteroids.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name || a.id}
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
          <section className="asteroid-meta">
            <p>
              <strong>{selectedAsteroid.name}</strong> · id{" "}
              {selectedAsteroid.id}
            </p>
          </section>
        )}

        {simulation && (
          <>
            <section className="results-grid">
              <div className="result-card">
                <span>Outcome</span>
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
            </section>

            <ConsequencesPanel consequences={simulationData?.consequences} />

            <AnalystPanel
              analyst={analyst}
              terrain={terrain}
              tsunami={tsunami}
              hasSimulation={Boolean(simulation)}
            />

            {trajectory && (
              <EarthImpactMap
                trajectory={trajectory}
                consequences={simulationData?.consequences}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
