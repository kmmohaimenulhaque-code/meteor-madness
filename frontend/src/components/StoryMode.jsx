import { useMemo, useState } from "react";
import SolarSystemScene from "./SolarSystemScene";
import "./StoryMode.css";

const STAGES = [
  {
    id: "detect",
    label: "DETECT",
    title: "Near-Earth object detected",
    blurb:
      "NASA NeoWs supplies the asteroid identity, size, speed, and close-approach context.",
  },
  {
    id: "enter",
    label: "ENTER",
    title: "Atmospheric entry",
    blurb:
      "The body meets Earth’s atmosphere. Screening physics tracks drag, ablation, and fragmentation.",
  },
  {
    id: "impact",
    label: "IMPACT",
    title: "Impact point",
    blurb: "Coordinates fix the scenario location — where the story meets the surface.",
  },
  {
    id: "earth",
    label: "EARTH",
    title: "Earth environment",
    blurb:
      "GEBCO elevation/bathymetry decides land or ocean. No data means no invented effects.",
  },
  {
    id: "consequences",
    label: "RISK",
    title: "Consequences",
    blurb:
      "Only the active physics branch appears — land crater/blast or ocean tsunami screening.",
  },
  {
    id: "mitigation",
    label: "NEXT",
    title: "Mitigation+",
    blurb:
      "AI explains what happened, what is uncertain, and what would warrant further assessment.",
  },
];

function KnowTip({ children }) {
  return (
    <span className="story-know" title={children}>
      ⓘ How do we know?
      <span className="story-know-pop">{children}</span>
    </span>
  );
}

function fmt(n, d = 2) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
}

export default function StoryMode({
  asteroids,
  selectedAsteroid,
  simulation,
  simulationData,
  environment,
  impactBranch,
  analyst,
  latitude,
  longitude,
  tsunami,
}) {
  const [open, setOpen] = useState(false);
  const [stage, setStage] = useState(0);

  const surface =
    environment?.surface || environment?.surface_type || impactBranch?.branch || "—";
  const diamKm =
    selectedAsteroid?.diameter_km ?? selectedAsteroid?.estimated_diameter_km;
  const diamM = diamKm != null ? Number(diamKm) * 1000 : null;
  const velKph = selectedAsteroid?.velocity_kph;
  const velKms = velKph != null ? Number(velKph) / 3600 : null;

  const branch = impactBranch?.branch || surface;
  const craterM = impactBranch?.crater?.final_diameter_m;
  const energyMt =
    simulationData?.impact_energy_J != null
      ? Number(simulationData.impact_energy_J) / 4.184e15
      : null;

  const missionNo = String(stage + 1).padStart(2, "0");

  const hero = useMemo(() => {
    if (stage === 0) {
      return (
        <div className="story-hero story-hero-space">
          <SolarSystemScene
            asteroids={asteroids}
            selectedId={selectedAsteroid?.id}
          />
        </div>
      );
    }
    if (stage === 1) {
      return (
        <div className="story-hero story-hero-entry">
          <div className="story-entry-visual">
            <div className="story-earth-disc" />
            <div className="story-meteor-trail" />
            <div className="story-meteor-body">☄️</div>
          </div>
          <p className="story-hero-caption">
            Outcome: {simulationData?.outcome || "Run a simulation to animate entry"}
            {simulationData?.fragmentation_detected ? " · fragmentation detected" : ""}
          </p>
        </div>
      );
    }
    if (stage === 2 || stage === 3) {
      const lat = Number(latitude);
      const lon = Number(longitude);
      // Simple equirectangular pin on a dark Earth plate (GIBS-inspired frame)
      const x = ((lon + 180) / 360) * 100;
      const y = ((90 - lat) / 180) * 100;
      return (
        <div className="story-hero story-hero-earth">
          <div className="story-gibs-frame">
            <div className="story-gibs-grid" />
            <div className="story-impact-pin" style={{ left: `${x}%`, top: `${y}%` }}>
              <span />
            </div>
            <div className="story-gibs-label">Earth view · impact coordinates</div>
          </div>
          <p className="story-hero-caption">
            {fmt(lat, 2)}°N/S · {fmt(lon, 2)}°E/W · environment {String(surface)}
          </p>
        </div>
      );
    }
    if (stage === 4) {
      return (
        <div className="story-hero story-hero-risk">
          <div className="story-risk-orb">{String(branch).toUpperCase()}</div>
          <p className="story-hero-caption">
            {branch === "land" && craterM != null
              ? `Land screening crater ~${fmt(craterM / 1000, 2)} km`
              : branch === "ocean"
                ? "Ocean branch — tsunami screening, not land crater"
                : branch === "undetermined" || surface === "unknown"
                  ? "Environment unknown — consequences withheld"
                  : "Relevant physics only for this branch"}
          </p>
        </div>
      );
    }
    return (
      <div className="story-hero story-hero-ai">
        <p className="story-ai-quote">
          {analyst?.summary ||
            "Mitigation+ will explain the run, uncertainty, and what to investigate next."}
        </p>
        <p className="story-hero-caption">
          Risk {analyst?.risk_level || "—"} · {analyst?.confidence_label || "advisory"}
        </p>
      </div>
    );
  }, [
    stage,
    asteroids,
    selectedAsteroid,
    simulationData,
    latitude,
    longitude,
    surface,
    branch,
    craterM,
    analyst,
  ]);

  return (
    <>
      <button
        type="button"
        className="story-fab"
        onClick={() => setOpen(true)}
        aria-label="Story Mode"
      >
        Story Mode
      </button>

      {open && (
        <div className="story-overlay" role="dialog" aria-label="Story Mode mission">
          <div className="story-shell">
            <header className="story-topbar">
              <div>
                <p className="story-brand">METEOR MADNESS</p>
                <h1>
                  MISSION {missionNo} / 06
                </h1>
              </div>
              <button type="button" className="story-close" onClick={() => setOpen(false)}>
                Close
              </button>
            </header>

            <nav className="story-pipeline" aria-label="Mission stages">
              {STAGES.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  className={`story-pipe-step ${i === stage ? "active" : ""} ${
                    i < stage ? "done" : ""
                  }`}
                  onClick={() => setStage(i)}
                >
                  {s.label}
                </button>
              ))}
            </nav>

            <section className="story-main">
              <div className="story-stage-copy">
                <p className="story-stage-kicker">Stage {missionNo}</p>
                <h2>{STAGES[stage].title}</h2>
                <p>{STAGES[stage].blurb}</p>
              </div>
              {hero}
            </section>

            <footer className="story-evidence">
              <div className="story-ev-card">
                <span>ASTEROID</span>
                <strong>
                  {diamM != null ? `${fmt(diamM, 0)} m` : "—"}
                </strong>
                <small>
                  {velKms != null ? `${fmt(velKms, 1)} km/s` : selectedAsteroid?.name || "NeoWs"}
                </small>
                <KnowTip>
                  Engine: NASA NeoWs via nasa_client. Inputs: live feed. Kind: observed catalogue
                  values (diameter/velocity estimates). Limit: close-approach summary, not full
                  orbit redesign.
                </KnowTip>
              </div>
              <div className="story-ev-card">
                <span>LOCATION</span>
                <strong>
                  {fmt(Number(latitude), 2)}°
                </strong>
                <small>{fmt(Number(longitude), 2)}°</small>
                <KnowTip>
                  Engine: user scenario coordinates. Earth class from GEBCO via location_engine.
                  Kind: user input + observed/modelled elevation. Limit: place names English via
                  Nominatim; GEBCO can fail → unknown.
                </KnowTip>
              </div>
              <div className="story-ev-card">
                <span>STATUS</span>
                <strong>{String(surface).toUpperCase()}</strong>
                <small>
                  {simulation
                    ? energyMt != null
                      ? `~${fmt(energyMt, 2)} Mt screen`
                      : branch || "ready"
                    : "awaiting run"}
                </small>
                <KnowTip>
                  Engine: impact_environment branch after entry solver. Kind: calculated screening.
                  Limit: not hydrocode; ocean never shows land crater.
                </KnowTip>
              </div>
            </footer>

            <div className="story-nav-row">
              <button
                type="button"
                disabled={stage === 0}
                onClick={() => setStage((s) => Math.max(0, s - 1))}
              >
                ← Back
              </button>
              <button
                type="button"
                className="story-next"
                disabled={stage === STAGES.length - 1}
                onClick={() => setStage((s) => Math.min(STAGES.length - 1, s + 1))}
              >
                Continue →
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
