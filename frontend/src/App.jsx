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
import "./analyst.css";
import ConsequencesPanel
  from "./components/ConsequencesPanel";
import EarthImpactMap
  from "./components/EarthImpactMap";
import AnalystPanel
  from "./components/AnalystPanel";

function App() {
  const [animationIndex, setAnimationIndex] = useState(0);
  const [animationRunning, setAnimationRunning] = useState(false);

  const [asteroids, setAsteroids] = useState([]);
  const [selectedId, setSelectedId] = useState("");

  const [latitude, setLatitude] = useState(24.3745);
  const [longitude, setLongitude] = useState(88.6042);
  const [azimuth, setAzimuth] = useState(90);

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

  const selectedAsteroid = useMemo(() => {
    return asteroids.find((item) => String(item.id) === String(selectedId)) ?? null;
  }, [asteroids, selectedId]);

  const simulationData = simulation?.simulation ?? null;
  const trajectory = simulation?.trajectory ?? null;
  const analyst = simulation?.analyst ?? null;
  const terrain = simulation?.terrain ?? null;
  const tsunami = simulation?.tsunami ?? null;

  // NOTE: full UI body is large; this file is restored from main + Next Frontier hooks.
  // If you see this short version, re-run: git checkout main -- frontend/src/App.jsx
  // then: python frontend/apply_frontend_patch.py

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

      setSimulation(data);
      setAnimationRunning(true);
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
          <p>Next Frontier architecture — entry physics, location, tsunami, AI analyst</p>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <section className="simulation-controls">
          <label>
            Asteroid
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
            Latitude
            <input
              type="number"
              value={latitude}
              onChange={(e) => setLatitude(Number(e.target.value))}
            />
          </label>

          <label>
            Longitude
            <input
              type="number"
              value={longitude}
              onChange={(e) => setLongitude(Number(e.target.value))}
            />
          </label>

          <label>
            Azimuth
            <input
              type="number"
              value={azimuth}
              onChange={(e) => setAzimuth(Number(e.target.value))}
            />
          </label>

          <button type="button" onClick={runSimulation} disabled={loading || !selectedId}>
            {loading ? "Running…" : "Run simulation"}
          </button>
        </section>

        {selectedAsteroid && (
          <section className="asteroid-meta">
            <p>
              <strong>{selectedAsteroid.name}</strong> · id {selectedAsteroid.id}
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
                  {simulationData?.fragmentation_detected ? "Detected" : "Not detected"}
                </strong>
              </div>
            </section>

            <ConsequencesPanel consequences={simulationData?.consequences} />

            <AnalystPanel
              analyst={analyst}
              terrain={terrain}
              tsunami={tsunami}
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
