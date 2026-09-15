import { useEffect, useMemo, useRef, useState } from "react";
import "./RiskMitigationChat.css";

function defaultPriorities(surface) {
  const s = (surface || "unknown").toLowerCase();
  if (s === "ocean") {
    return [
      "Identify potentially exposed coastlines.",
      "Monitor tsunami observations and models.",
      "Establish coastal evacuation thresholds.",
      "Move populations away from vulnerable low-lying areas.",
      "Coordinate emergency communications.",
    ];
  }
  if (s === "land") {
    return [
      "Establish an exclusion zone.",
      "Assess blast / thermal / seismic exposure.",
      "Evacuate high-risk areas.",
      "Protect critical infrastructure.",
      "Coordinate emergency services.",
    ];
  }
  if (s === "ice") {
    return [
      "Assess ice disruption potential.",
      "Monitor downstream flood or surge pathways.",
      "Protect polar logistics assets if relevant.",
      "Coordinate regional emergency communications.",
      "Treat effects as screening-level only.",
    ];
  }
  return [
    "Environment unknown — do not invent crater or tsunami actions.",
    "Re-run GEBCO lookup or set surface_hint.",
    "Communicate uncertainty clearly.",
  ];
}

function buildContext({
  environment,
  impactBranch,
  analyst,
  simulationData,
  asteroid,
  tsunami,
  latitude,
  longitude,
  azimuth,
}) {
  const surface =
    environment?.surface || environment?.surface_type || "unknown";
  const energyJ =
    Number(simulationData?.impact_energy_J) ||
    Number(simulationData?.parent_final_energy_J) ||
    Number(simulationData?.ground_impact_energy_J) ||
    0;

  return {
    // User inputs
    latitude: latitude != null && latitude !== "" ? Number(latitude) : null,
    longitude: longitude != null && longitude !== "" ? Number(longitude) : null,
    entry_azimuth_deg:
      azimuth != null && azimuth !== "" ? Number(azimuth) : null,

    // Environment / panel
    surface,
    environment_class: surface,
    surface_confidence: environment?.surface_confidence ?? environment?.confidence,
    physics_branch: impactBranch?.branch || environment?.physics_branch,
    environment: environment || null,
    impact_branch: impactBranch || null,
    tsunami: tsunami || null,
    analyst: analyst || null,

    // Simulation
    simulation: simulationData
      ? {
          outcome: simulationData.outcome,
          fragmentation_detected: simulationData.fragmentation_detected,
          fragmentation_altitude_m: simulationData.fragmentation_altitude_m,
          atmospheric_fraction: simulationData.atmospheric_fraction,
          impact_energy_J: energyJ,
          impact_energy_megatons_tnt: energyJ / 4.184e15,
          parent_final_mass_kg: simulationData.parent_final_mass_kg,
          parent_final_velocity_m_s: simulationData.parent_final_velocity_m_s,
        }
      : null,
    impact_energy_mt: energyJ / 4.184e15,

    // Asteroid
    asteroid: asteroid
      ? {
          id: asteroid.id,
          name: asteroid.name,
          diameter_km:
            asteroid.diameter_km ?? asteroid.estimated_diameter_km ?? null,
          hazardous:
            asteroid.hazardous ||
            asteroid.is_potentially_hazardous_asteroid ||
            false,
          miss_distance_km: asteroid.miss_distance_km ?? null,
          velocity_kph: asteroid.velocity_kph ?? null,
          approach_date: asteroid.approach_date ?? null,
        }
      : null,
  };
}

export default function RiskMitigationChat({
  simulation,
  environment,
  impactBranch,
  analyst,
  simulationData,
  asteroid,
  tsunami,
  latitude,
  longitude,
  azimuth,
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);

  const context = useMemo(
    () =>
      buildContext({
        environment,
        impactBranch,
        analyst,
        simulationData,
        asteroid,
        tsunami,
        latitude,
        longitude,
        azimuth,
      }),
    [
      environment,
      impactBranch,
      analyst,
      simulationData,
      asteroid,
      tsunami,
      latitude,
      longitude,
      azimuth,
    ]
  );

  const surface = context.surface || "unknown";
  const priorities = defaultPriorities(surface);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const intro = simulation
      ? [
          `Hey — I've got this run loaded as **${surface}**.`,
          "",
          "I can talk through the environment panel, crater/blast numbers, the asteroid you picked, or the place at these coordinates. What do you want to dig into?",
        ].join("\n")
      : [
          "Hey — Mitigation+ is online.",
          "",
          "Pick an asteroid, set coordinates, run a simulation, then ask me about the results, the place, or how the engines work.",
        ].join("\n");
    setMessages([{ role: "assistant", content: intro, source: "intro" }]);
  }, [simulation, surface]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, open]);

  async function send(prefill) {
    const text = (prefill ?? input).trim();
    if (!text || busy) return;

    const nextHistory = [...messages, { role: "user", content: text }];
    setMessages(nextHistory);
    setInput("");
    setBusy(true);

    try {
      const response = await fetch("/api/mitigation/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          context,
          history: nextHistory.map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.reply || "No reply.",
            source: data.source || "api",
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: localReply(text, surface, priorities, context),
            source: "client",
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: localReply(text, surface, priorities, context),
          source: "client",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="risk-fab"
        onClick={() => setOpen((v) => !v)}
        aria-label="Mitigation and more"
      >
        Mitigation and more
      </button>

      {open && (
        <div className="risk-chat-panel" role="dialog" aria-label="Mitigation and more">
          <header className="risk-chat-header">
            <div>
              <strong>Mitigation and more</strong>
              <span className="risk-chat-sub">
                Results · place · asteroid · {surface}
              </span>
            </div>
            <button
              type="button"
              className="risk-chat-close"
              onClick={() => setOpen(false)}
            >
              ✕
            </button>
          </header>

          <div className="risk-chat-messages" ref={listRef}>
            {messages.map((m, i) => (
              <div
                key={`m-${i}`}
                className={`risk-bubble ${m.role === "user" ? "user" : "assistant"}`}
              >
                <pre>{m.content}</pre>
                {m.source && m.role === "assistant" && (
                  <span className="risk-source">{m.source}</span>
                )}
              </div>
            ))}
            {busy && <div className="risk-bubble assistant">One moment…</div>}
          </div>

          <div className="risk-quick">
            <button type="button" onClick={() => send("Summarise this simulation and the AI panel")}>
              This run
            </button>
            <button type="button" onClick={() => send("Where is this impact location?")}>
              Place
            </button>
            <button type="button" onClick={() => send("Tell me about the selected asteroid")}>
              Asteroid
            </button>
            <button
              type="button"
              onClick={() => send("Why didn’t Meteor Madness calculate a surface crater?")}
            >
              Why no crater?
            </button>
            <button type="button" onClick={() => send("What are the immediate priorities?")}>
              Priorities
            </button>
          </div>

          <form
            className="risk-chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about results, place, asteroid…"
              disabled={busy}
            />
            <button type="submit" disabled={busy || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </>
  );
}

function localReply(message, surface, priorities, context) {
  const lower = message.toLowerCase();
  const env = context.environment || {};
  const branch = context.impact_branch || {};
  const asteroid = context.asteroid || {};
  const analyst = context.analyst || {};

  if (lower.includes("asteroid") || lower.includes("selected")) {
    if (!asteroid.name && !asteroid.id) {
      return "No asteroid is selected yet — pick one from the NASA list first.";
    }
    return [
      `You're looking at ${asteroid.name || asteroid.id}.`,
      asteroid.diameter_km != null
        ? `Diameter about ${Number(asteroid.diameter_km).toFixed(4)} km.`
        : null,
      asteroid.hazardous ? "It's flagged as potentially hazardous (PHA)." : "Not flagged as a PHA in this feed.",
      asteroid.miss_distance_km != null
        ? `Miss distance about ${Number(asteroid.miss_distance_km).toLocaleString()} km.`
        : null,
    ]
      .filter(Boolean)
      .join(" ");
  }

  if (
    lower.includes("place") ||
    lower.includes("where") ||
    lower.includes("location")
  ) {
    const lat = context.latitude;
    const lon = context.longitude;
    return `Coordinates are ${lat}, ${lon}. The backend reverse-geocoder names the place when the mitigation API is up — restart uvicorn after pull if needed.`;
  }

  if (
    lower.includes("crater") &&
    (lower.includes("didn") || lower.includes("why") || surface !== "land")
  ) {
    if (surface === "ocean") {
      return (
        "Because the selected impact environment was ocean. The land-crater model was " +
        "intentionally not applied; the simulation used the ocean branch instead."
      );
    }
  }

  if (lower.includes("summar") || lower.includes("panel") || lower.includes("run")) {
    const crater = branch.crater?.final_diameter_m;
    return [
      `Environment: ${surface} (source ${env.terrain_source || env.source || "n/a"}).`,
      `Branch: ${branch.branch || surface}.`,
      crater != null ? `Crater diameter ~${(crater / 1000).toFixed(2)} km.` : null,
      analyst.summary || null,
    ]
      .filter(Boolean)
      .join(" ");
  }

  return [
    `This run is on **${surface}**. First moves I'd consider:`,
    ...priorities.map((p, i) => `${i + 1}. ${p}`),
  ].join("\n");
}
