"""
Mitigation+ interactive AI.

Answers planetary-defence mitigation questions, explains project engines,
NASA services in use vs reference-only, and limitations — using simulation
context + project knowledge. Gemini when GEMINI_API_KEY is set.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

from physics.project_knowledge import (
    ENGINES,
    LIMITATIONS,
    NASA_SERVICES,
    PROJECT_OVERVIEW,
    knowledge_bundle,
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def immediate_priorities(surface: str) -> list[str]:
    s = (surface or "unknown").lower()
    if s == "ocean":
        return [
            "Identify potentially exposed coastlines.",
            "Monitor tsunami observations and models.",
            "Establish coastal evacuation thresholds.",
            "Move populations away from vulnerable low-lying areas.",
            "Coordinate emergency communications.",
        ]
    if s == "land":
        return [
            "Establish an exclusion zone.",
            "Assess blast / thermal / seismic exposure.",
            "Evacuate high-risk areas.",
            "Protect critical infrastructure.",
            "Coordinate emergency services.",
        ]
    if s == "ice":
        return [
            "Assess ice-sheet / sea-ice disruption potential.",
            "Monitor downstream flood or surge pathways.",
            "Protect polar logistics and research assets if relevant.",
            "Coordinate regional emergency communications.",
            "Treat energy and effects as screening-level only.",
        ]
    return [
        "Environment class is unknown — do not invent crater or tsunami actions.",
        "Re-run environment lookup (GEBCO) or set an explicit surface_hint.",
        "Focus on uncertainty communication and public information hygiene.",
        "Escalate only with observed Earth-environment data.",
        "Keep entry-physics results separate from environment-specific advice.",
    ]


def _explain_engines() -> str:
    lines = ["Working engines in this branch:", ""]
    for key, meta in ENGINES.items():
        lines.append(f"• **{key}** (`{meta.get('module')}`)")
        lines.append(f"  {meta.get('role')}")
        if meta.get("rule"):
            lines.append(f"  Rule: {meta['rule']}")
        lines.append("")
    return "\n".join(lines).strip()


def _explain_nasa() -> str:
    lines = [
        "NASA / Earth-data services relevant to Meteor Madness:",
        "",
        "**Wired into this project:**",
    ]
    for key, meta in NASA_SERVICES.items():
        if meta.get("used_in_project"):
            lines.append(
                f"• {meta['name']}: {meta['purpose']} "
                f"({meta.get('url')})"
            )
    lines.append("")
    lines.append("**Reference / not yet wired (awareness only):**")
    for key, meta in NASA_SERVICES.items():
        if not meta.get("used_in_project"):
            lines.append(
                f"• {meta['name']}: {meta['purpose']}"
                + (f" — {meta['note']}" if meta.get("note") else "")
            )
    lines.append("")
    lines.append(
        "NASA Open APIs hub: https://api.nasa.gov/ — NeoWs uses NASA_API_KEY."
    )
    return "\n".join(lines)


def _explain_limitations() -> str:
    lines = ["Project limitations (be honest with judges and users):", ""]
    for i, item in enumerate(LIMITATIONS, 1):
        lines.append(f"{i}. {item}")
    return "\n".join(lines)


def _explain_project() -> str:
    return PROJECT_OVERVIEW.strip() + "\n\n" + _explain_engines()


def _rule_reply(message: str, context: dict[str, Any]) -> str:
    surface = str(
        context.get("surface")
        or context.get("environment_class")
        or "unknown"
    ).lower()
    priorities = immediate_priorities(surface)
    branch = context.get("physics_branch") or surface
    energy_mt = context.get("impact_energy_mt")
    lower = (message or "").lower()

    if any(
        k in lower
        for k in (
            "how does", "how do", "explain project", "what is this",
            "architecture", "pipeline", "source code", "codebase", "engine",
        )
    ):
        if "nasa" in lower:
            return _explain_nasa()
        if "limit" in lower:
            return _explain_limitations()
        if any(k in lower for k in ("engine", "solver", "gebco", "environment", "tsunami", "entry")):
            return _explain_engines()
        return _explain_project()

    if "nasa" in lower or "neows" in lower or "api.nasa" in lower:
        return _explain_nasa()

    if "limit" in lower or "uncertain" in lower or "disclaimer" in lower:
        return _explain_limitations()

    if any(k in lower for k in ("priorit", "immediate", "mitigat", "evacuat", "what should")):
        lines = [
            f"Immediate priorities for **{surface}** "
            f"(branch={branch}"
            + (f", ~{float(energy_mt):.3g} Mt" if energy_mt is not None else "")
            + "):",
            "",
        ]
        for i, item in enumerate(priorities, 1):
            lines.append(f"{i}. {item}")
        lines.append("")
        lines.append(
            "Educational planetary-defence screening only — not an operational emergency plan."
        )
        return "\n".join(lines)

    if "tsunami" in lower:
        if surface != "ocean":
            return (
                "Tsunami mitigation applies only when environment class is observed **ocean**. "
                f"Current surface is **{surface}** — tsunami actions are not activated.\n\n"
                + _explain_limitations()
            )
        return "Ocean-impact tsunami screening priorities:\n" + "\n".join(
            f"• {p}" for p in priorities
        )

    if any(k in lower for k in ("crater", "blast", "seismic", "exclusion")):
        if surface != "land":
            return (
                "Land impact actions (exclusion zone, blast/thermal/seismic) apply only on the "
                f"**land** branch. Current surface is **{surface}**."
            )
        return "Land-impact mitigation priorities:\n" + "\n".join(
            f"• {p}" for p in priorities
        )

    if "unknown" in lower or "no data" in lower or "refuse" in lower:
        return (
            "If GEBCO/OpenTopoData fails, surface=unknown, confidence=0, "
            "physics_branch=undetermined. The simulator refuses to manufacture crater or tsunami.\n\n"
            + _explain_limitations()
        )

    return (
        f"Mitigation+ context: surface=**{surface}**, branch=**{branch}**.\n\n"
        "You can ask about:\n"
        "• Immediate mitigation priorities\n"
        "• How entry / environment / tsunami engines work\n"
        "• NASA services (NeoWs, GEBCO, reference CNEOS/Horizons)\n"
        "• Project limitations\n\n"
        "Default immediate priorities:\n"
        + "\n".join(f"• {p}" for p in priorities)
    )


def _gemini_reply(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    api_key: str,
) -> str | None:
    knowledge = knowledge_bundle()
    system = (
        "You are Mitigation+ for Meteor Madness (NASA Space Apps educational demo). "
        "Be interactive, clear, and honest. You help with: (1) planetary-defence mitigation, "
        "(2) explaining this project's architecture and engines from the knowledge base, "
        "(3) which NASA services are wired vs reference-only, (4) limitations. "
        "Use simulation context. Never invent casualty counts. "
        "If surface is unknown, refuse environment-specific crater/tsunami actions. "
        "You do not have live write access to NASA systems; you explain and advise only."
    )
    hist_txt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-8:]
    )
    prompt = (
        f"{system}\n\nProject knowledge:\n{json.dumps(knowledge, indent=2)}\n\n"
        f"Simulation context:\n{json.dumps(context, indent=2)}\n\n"
        f"Recent chat:\n{hist_txt}\n\nUser: {message}\n\nAssistant:"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 1400,
        },
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                GEMINI_API_URL,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()
        parts = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        text = "".join(str(p.get("text", "")) for p in parts).strip()
        return text or None
    except Exception:
        return None


def answer_mitigation(
    *,
    message: str,
    context: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    context = context or {}
    history = history or []
    surface = str(
        context.get("surface")
        or context.get("environment_class")
        or "unknown"
    ).lower()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    reply = None
    source = "rule_based"
    if api_key:
        reply = _gemini_reply(message, context, history, api_key)
        if reply:
            source = "gemini"

    if not reply:
        reply = _rule_reply(message, context)

    return {
        "status": "ok",
        "reply": reply,
        "source": source,
        "immediate_priorities": immediate_priorities(surface),
        "surface": surface,
        "knowledge": {
            "engines": list(ENGINES.keys()),
            "nasa_wired": [
                k for k, v in NASA_SERVICES.items() if v.get("used_in_project")
            ],
            "limitations_count": len(LIMITATIONS),
        },
    }
