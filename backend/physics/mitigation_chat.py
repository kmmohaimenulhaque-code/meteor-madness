"""
Risk Mitigation interactive AI.

Uses simulation context. Gemini when GEMINI_API_KEY is set;
otherwise structured planetary-defence priorities by environment class.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

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
        "Focus on public information hygiene and uncertainty communication.",
        "Escalate only with observed Earth-environment data.",
        "Keep entry-physics results separate from environment-specific advice.",
    ]


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
    if any(k in lower for k in ("priorit", "immediate", "mitigat", "evacuat", "what should")):
        lines = [
            f"Immediate priorities for **{surface}** impact "
            f"(branch={branch}"
            + (f", ~{energy_mt} Mt" if energy_mt is not None else "")
            + "):",
            "",
        ]
        for i, item in enumerate(priorities, 1):
            lines.append(f"{i}. {item}")
        lines.append("")
        lines.append(
            "This is educational planetary-defence screening guidance, "
            "not an operational emergency plan."
        )
        return "\n".join(lines)

    if "tsunami" in lower:
        if surface != "ocean":
            return (
                "Tsunami mitigation applies only when the environment class is "
                "observed ocean. Current surface is "
                f"**{surface}** — tsunami actions are not activated."
            )
        return (
            "Ocean-impact tsunami screening priorities:\n"
            + "\n".join(f"• {p}" for p in priorities)
        )

    if any(k in lower for k in ("crater", "blast", "seismic", "exclusion")):
        if surface != "land":
            return (
                "Land impact actions (exclusion zone, blast/thermal/seismic) "
                f"apply only on the **land** branch. Current surface is **{surface}**."
            )
        return (
            "Land-impact mitigation priorities:\n"
            + "\n".join(f"• {p}" for p in priorities)
        )

    return (
        f"Planetary-defence context: surface=**{surface}**, branch=**{branch}**.\n\n"
        "Ask about immediate priorities, evacuation, tsunami (ocean), "
        "or exclusion zones (land).\n\n"
        "Default immediate priorities:\n"
        + "\n".join(f"• {p}" for p in priorities)
    )


def _gemini_reply(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    api_key: str,
) -> str | None:
    system = (
        "You are a planetary-defence Risk Mitigation assistant for a NASA Space Apps "
        "educational simulator (Meteor Madness). Answer primarily about risk mitigation, "
        "civil protection priorities, and screening-level planetary defence. "
        "Use the simulation context. Do not invent precise casualty counts. "
        "If surface is unknown, refuse environment-specific crater/tsunami actions. "
        "Be concise and actionable."
    )
    hist_txt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-6:]
    )
    prompt = (
        f"{system}\n\nSimulation context:\n{json.dumps(context, indent=2)}\n\n"
        f"Recent chat:\n{hist_txt}\n\nUser: {message}\n\nAssistant:"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        },
    }
    try:
        with httpx.Client(timeout=25.0) as client:
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
    }
