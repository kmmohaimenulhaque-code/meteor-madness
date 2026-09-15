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

function buildContext({ environment, impactBranch, analyst, simulationData }) {
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
  };
}

export default function RiskMitigationChat({
  simulation,
  environment,
  impactBranch,
  analyst,
  simulationData,
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
      }),
    [environment, impactBranch, analyst, simulationData]
  );

  const surface = context.surface || "unknown";
  const priorities = defaultPriorities(surface);

  const [messages, setMessages] = useState([]);

  // Seed chat when simulation context changes
  useEffect(() => {
    if (!simulation) {
      setMessages([]);
      return;
    }
    const intro = [
      `🛡️ Risk Mitigation ready for **${surface}** impact.`,
      "",
      "Immediate priorities:",
      ...priorities.map((p, i) => `${i + 1}. ${p}`),
      "",
      "Ask about evacuation, exclusion zones, tsunami response, or infrastructure protection.",
    ].join("\n");
    setMessages([{ role: "assistant", content: intro, source: "priorities" }]);
  }, [simulation, surface]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, open]);

  async function send() {
    const text = input.trim();
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
        // Client fallback
        const local = localReply(text, surface, priorities);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: local, source: "client" },
        ]);
      }
    } catch {
      const local = localReply(text, surface, priorities);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: local, source: "client" },
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
        aria-label="Risk Mitigation"
      >
        🛡️ Risk Mitigation
      </button>

      {open && (
        <div className="risk-chat-panel" role="dialog" aria-label="Risk Mitigation chat">
          <header className="risk-chat-header">
            <div>
              <strong>Risk Mitigation</strong>
              <span className="risk-chat-sub">
                Planetary defence · {surface}
              </span>
            </div>
            <button type="button" className="risk-chat-close" onClick={() => setOpen(false)}>
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
            <button type="button" onClick={() => setInput("What are the immediate priorities?")}>
              Immediate priorities
            </button>
            <button type="button" onClick={() => setInput("How should we evacuate?")}>
              Evacuation
            </button>
            <button type="button" onClick={() => setInput("Tsunami response steps?")}>
              Tsunami
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
              placeholder="Ask about mitigation…"
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
    lower.includes("priorit") ||
    lower.includes("immediate") ||
    lower.includes("mitigat")
  ) {
    return [
      `Immediate priorities for ${surface}:`,
      ...priorities.map((p, i) => `${i + 1}. ${p}`),
      "",
      "Educational screening guidance only.",
    ].join("\n");
  }
  return [
    `Context: surface=${surface}.`,
    "Immediate priorities:",
    ...priorities.map((p) => `• ${p}`),
  ].join("\n");
}
