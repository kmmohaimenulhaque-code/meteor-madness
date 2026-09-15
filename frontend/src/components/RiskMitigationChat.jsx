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
          `Hey — Mitigation+ is in with this run as **${surface}**.`,
          "",
          surface === "ocean"
            ? "Ocean branch is active, so we won't invent a land crater. Ask me why, or what to do first on the coast."
            : surface === "land"
              ? "Land branch is active — crater/blast/thermal screening applies. Ask priorities or why a number looks the way it does."
              : "Ask about priorities, engines, NASA services, or limits — I'll answer in plain language.",
        ].join("\n")
      : [
          "Hey — Mitigation+ is online.",
          "",
          "Run a simulation for impact-specific advice, or just ask how the project works, which NASA services we use, or what the limits are.",
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
                Plain-language help · {surface}
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
            <button
              type="button"
              onClick={() => send("Why didn’t Meteor Madness calculate a surface crater?")}
            >
              Why no crater?
            </button>
            <button type="button" onClick={() => send("What are the immediate priorities?")}>
              Priorities
            </button>
            <button type="button" onClick={() => send("How does this project work?")}>
              Project
            </button>
            <button type="button" onClick={() => send("Which NASA services does this use?")}>
              NASA
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
              placeholder="Ask anything — crater, engines, NASA…"
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
  if (
    lower.includes("crater") ||
    lower.includes("didn") ||
    lower.includes("why")
  ) {
    if (surface === "ocean") {
      return (
        "Because the selected impact environment was ocean. The land-crater model was " +
        "intentionally not applied; the simulation instead used the ocean branch for " +
        "water displacement, tsunami screening and seafloor interaction."
      );
    }
    if (surface === "unknown") {
      return (
        "Because we couldn't confirm land vs ocean from the elevation service. " +
        "When surface is unknown, Meteor Madness refuses to invent a crater or tsunami."
      );
    }
  }
  if (lower.includes("nasa")) {
    return (
      "We call NASA NeoWs for the asteroid feed and GEBCO (via OpenTopoData) for " +
      "elevation/bathymetry. Other NASA services like Horizons or Sentry are useful " +
      "context, but they're not wired into this MVP yet."
    );
  }
  if (lower.includes("limit")) {
    return (
      "Honestly: this is screening, not hydrocode. Strength and ablation are uncertain, " +
      "tsunami and crater numbers are first-order, and with no Earth data we simply " +
      "won't invent environment-specific effects."
    );
  }
  return [
    `This run is sitting on **${surface}**. If I had to move first, it'd be:`,
    ...priorities.map((p, i) => `${i + 1}. ${p}`),
  ].join("\n");
}
