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

function buildContext({ environment, impactBranch, analyst, simulationData, asteroid }) {
  const surface =
    environment?.surface || environment?.surface_type || "unknown";
  const energyJ =
    Number(simulationData?.impact_energy_J) ||
    Number(simulationData?.parent_final_energy_J) ||
    0;
  return {
    surface,
    environment_class: surface,
    physics_branch: impactBranch?.branch || environment?.physics_branch,
    impact_energy_mt: energyJ / 4.184e15,
    risk_level: analyst?.risk_level,
    summary: analyst?.summary,
    elevation_m: environment?.elevation_m,
    bathymetry_m: environment?.bathymetry_m,
    terrain_source: environment?.terrain_source || environment?.source,
    data_status: environment?.data_status,
    asteroid: asteroid
      ? {
          id: asteroid.id,
          name: asteroid.name,
          diameter_km: asteroid.diameter_km,
          hazardous: asteroid.hazardous,
          miss_distance_km: asteroid.miss_distance_km,
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
      }),
    [environment, impactBranch, analyst, simulationData, asteroid]
  );

  const surface = context.surface || "unknown";
  const priorities = defaultPriorities(surface);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const intro = simulation
      ? [
          `Mitigation+ ready · surface **${surface}**.`,
          "",
          "Immediate priorities:",
          ...priorities.map((p, i) => `${i + 1}. ${p}`),
          "",
          "Ask about engines, NASA services, limitations, or mitigation steps.",
        ].join("\n")
      : [
          "Mitigation+ assistant online.",
          "",
          "Run a simulation for impact-specific advice, or ask:",
          "• How does this project work?",
          "• Which NASA services are used?",
          "• What are the limitations?",
          "• How does the environment engine work?",
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
            content: localReply(text, surface, priorities),
            source: "client",
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: localReply(text, surface, priorities),
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
                Defence · engines · NASA · limits · {surface}
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
            {busy && <div className="risk-bubble assistant">Thinking…</div>}
          </div>

          <div className="risk-quick">
            <button type="button" onClick={() => send("What are the immediate priorities?")}>
              Priorities
            </button>
            <button type="button" onClick={() => send("How does this project work?")}>
              Project
            </button>
            <button type="button" onClick={() => send("Which NASA services does this use?")}>
              NASA
            </button>
            <button type="button" onClick={() => send("Explain the working engines")}>
              Engines
            </button>
            <button type="button" onClick={() => send("What are the project limitations?")}>
              Limits
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
              placeholder="Ask mitigation, engines, NASA, limits…"
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

function localReply(message, surface, priorities) {
  const lower = message.toLowerCase();
  if (lower.includes("nasa")) {
    return [
      "Wired: NASA NeoWs (asteroids) + OpenTopoData GEBCO (elevation/bathymetry).",
      "Reference only: JPL Horizons, CNEOS Sentry/Fireballs, Earthdata.",
      "NeoWs needs NASA_API_KEY from https://api.nasa.gov/",
    ].join("\n");
  }
  if (lower.includes("limit")) {
    return [
      "Key limitations:",
      "• RK4 entry screening ≠ full hydrocode",
      "• Uncertain strength/density/ablation",
      "• Tsunami/crater are screening estimates",
      "• No data ⇒ no invented environment physics",
    ].join("\n");
  }
  if (lower.includes("engine") || lower.includes("project") || lower.includes("work")) {
    return [
      "Pipeline: NASA → entry RK4 → GEBCO environment → land/ocean/ice branch → report → AI.",
      "Engines: solver, location_engine, impact_environment, consequences, tsunami, ai_analyst.",
    ].join("\n");
  }
  return [
    `Surface=${surface}. Immediate priorities:`,
    ...priorities.map((p, i) => `${i + 1}. ${p}`),
  ].join("\n");
}
