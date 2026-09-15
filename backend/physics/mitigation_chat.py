"""
Mitigation+ interactive AI — conversational, human tone.

Explains mitigation, engines, NASA services, and limitations using
simulation context. Gemini when GEMINI_API_KEY is set.
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

TONE_RULES = """
Write like a thoughtful teammate, not a manual.
- Short paragraphs, natural speech.
- Explain *why* decisions were made (e.g. ocean → no land crater).
- Avoid robotic lists unless the user asks for a checklist.
- No casualty inventing. Screening-level honesty.
- If surface is unknown, say so plainly and refuse invented crater/tsunami steps.
""".strip()


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


def _human_priorities(surface: str, branch: str, energy_mt: Any) -> str:
    priorities = immediate_priorities(surface)
    energy_bit = ""
    try:
        if energy_mt is not None:
            energy_bit = f" Energy scale is roughly {float(energy_mt):.3g} Mt TNT equivalent — screening only."
    except (TypeError, ValueError):
        pass

    if surface == "ocean":
        lead = (
            f"For an ocean impact (branch={branch}), I'd start with coastal protection, "
            f"not land-crater thinking.{energy_bit}"
        )
    elif surface == "land":
        lead = (
            f"For a land impact (branch={branch}), the first moves are exclusion and "
            f"blast/thermal/seismic awareness.{energy_bit}"
        )
    elif surface == "ice":
        lead = (
            f"Ice impacts are still screening-level here. Treat the list as orientation, "
            f"not a field plan.{energy_bit}"
        )
    else:
        lead = (
            "We don't have a trusted surface classification right now, so I won't invent "
            "crater or tsunami steps. Fix the environment data first."
        )

    body = "\n".join(f"{i}. {p}" for i, p in enumerate(priorities, 1))
    return f"{lead}\n\nImmediate priorities:\n{body}\n\nThat's educational guidance, not an operational emergency plan."


def _explain_no_crater(surface: str, branch: str) -> str:
    if surface == "ocean" or branch == "ocean":
        return (
            "Because the selected impact environment was ocean. The land-crater model "
            "was intentionally not applied; the simulation instead used the ocean branch "
            "for water displacement, tsunami screening and seafloor interaction.\n\n"
            "Showing a land crater next to an ocean result would be misleading, so the UI "
            "keeps those models on separate branches."
        )
    if surface == "unknown" or branch == "undetermined":
        return (
            "Because the environment engine couldn't confirm land vs ocean (or the data "
            "provider failed). When surface is unknown, Meteor Madness refuses to "
            "manufacture a crater or a tsunami — no data, no guess."
        )
    if surface == "ice":
        return (
            "This run classified the surface as ice, so the land-crater scaling path "
            "wasn't the primary branch. Ice uses its own screening response instead."
        )
    return (
        "On a land branch we *do* run crater scaling. If you're not seeing it, check "
        "that the physics branch is land and that the consequences panel isn't filtered out."
    )


def _explain_engines() -> str:
    return (
        "Here's how the working pieces fit together, in plain language.\n\n"
        "Entry physics (`solver.py`) integrates the asteroid through the atmosphere "
        "with an RK4 step — drag, ablation, possible fragmentation, energy left at the end.\n\n"
        "The environment engine (`location_engine.py`) asks GEBCO via OpenTopoData for "
        "real elevation or seafloor depth. Positive → land, negative → ocean. If that "
        "lookup fails, we mark surface unknown and stop inventing effects.\n\n"
        "`impact_environment.py` then picks a branch: land crater/blast/thermal, ocean "
        "displacement/tsunami/seafloor, ice screening, or refuse.\n\n"
        "Land consequence scaling lives in `consequences.py`; tsunami screening in "
        "`tsunami.py`. The AI analyst and this Mitigation+ chat sit on top and never "
        "override that hierarchy."
    )


def _explain_nasa() -> str:
    wired = [
        f"• {m['name']}: {m['purpose']}"
        for m in NASA_SERVICES.values()
        if m.get("used_in_project")
    ]
    ref = [
        f"• {m['name']}: {m['purpose']}"
        for m in NASA_SERVICES.values()
        if not m.get("used_in_project")
    ]
    return (
        "What we actually call live in this project:\n"
        + "\n".join(wired)
        + "\n\nWhat I can explain as NASA/planetary-defence context, but we haven't wired yet:\n"
        + "\n".join(ref)
        + "\n\nNeoWs needs a NASA_API_KEY from https://api.nasa.gov/. "
        "I don't push buttons on NASA systems for you — I help you understand what "
        "this app uses and what the results mean."
    )


def _explain_limitations() -> str:
    points = "\n".join(f"• {item}" for item in LIMITATIONS)
    return (
        "I'll be straight with you about the limits — this is a Space Apps screening demo, "
        "not a national crisis model.\n\n"
        f"{points}\n\n"
        "If a judge asks what's missing, lead with hydrocode, coastal inundation models, "
        "and operational decision authority — those are outside this MVP on purpose."
    )


def _explain_project() -> str:
    return (
        "Meteor Madness is our NASA Space Apps entry: an educational path from a real "
        "near-Earth object to a careful impact story.\n\n"
        f"{PROJECT_OVERVIEW.strip()}\n\n"
        "If you want the machinery under the hood, ask about the engines; if you want "
        "what to do after a run, ask for immediate priorities."
    )


def _rule_reply(message: str, context: dict[str, Any]) -> str:
    surface = str(
        context.get("surface")
        or context.get("environment_class")
        or "unknown"
    ).lower()
    branch = str(context.get("physics_branch") or surface).lower()
    energy_mt = context.get("impact_energy_mt")
    lower = (message or "").lower()

    if any(
        k in lower
        for k in (
            "why didn",
            "why did not",
            "no crater",
            "didn't calculate",
            "did not calculate",
            "surface crater",
            "land crater",
        )
    ):
        return _explain_no_crater(surface, branch)

    if any(
        k in lower
        for k in (
            "how does",
            "how do",
            "explain project",
            "what is this",
            "architecture",
            "pipeline",
            "source code",
            "codebase",
        )
    ):
        if "nasa" in lower:
            return _explain_nasa()
        if "limit" in lower:
            return _explain_limitations()
        if any(
            k in lower
            for k in ("engine", "solver", "gebco", "environment", "tsunami", "entry")
        ):
            return _explain_engines()
        return _explain_project()

    if any(k in lower for k in ("engine", "solver", "gebco", "working engine")):
        return _explain_engines()

    if "nasa" in lower or "neows" in lower or "api.nasa" in lower:
        return _explain_nasa()

    if "limit" in lower or "uncertain" in lower or "disclaimer" in lower:
        return _explain_limitations()

    if any(
        k in lower
        for k in ("priorit", "immediate", "mitigat", "evacuat", "what should")
    ):
        return _human_priorities(surface, branch, energy_mt)

    if "tsunami" in lower:
        if surface != "ocean":
            return (
                f"Tsunami steps only make sense when the environment is ocean. "
                f"This run looks like **{surface}**, so I wouldn't activate coastal "
                f"tsunami actions from the ocean branch.\n\n"
                + _explain_no_crater(surface, branch)
            )
        return _human_priorities("ocean", branch, energy_mt)

    if any(k in lower for k in ("crater", "blast", "seismic", "exclusion")):
        if surface != "land":
            return _explain_no_crater(surface, branch)
        return _human_priorities("land", branch, energy_mt)

    if "unknown" in lower or "no data" in lower or "refuse" in lower:
        return (
            "When GEBCO or the network fails, we set surface to unknown and stop. "
            "That's deliberate: better an honest gap than a fake crater or tsunami.\n\n"
            + _explain_limitations()
        )

    return (
        f"I've got this run as surface **{surface}** (branch **{branch}**). "
        "You can ask me why there is or isn't a crater, what to do first for mitigation, "
        "how the engines work, which NASA services we use, or what the limits are — "
        "I'll answer in plain language.\n\n"
        + _human_priorities(surface, branch, energy_mt)
    )


def _gemini_reply(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    api_key: str,
) -> str | None:
    knowledge = knowledge_bundle()
    system = (
        "You are Mitigation+ for Meteor Madness, a NASA Space Apps educational simulator. "
        "Sound human: warm, clear, concise — like a knowledgeable teammate. "
        "Explain decisions in prose when asked (example: if environment was ocean, say the "
        "land-crater model was intentionally not applied and the ocean branch handled "
        "displacement, tsunami screening, and seafloor interaction). "
        "Cover mitigation, architecture, engines, NASA services wired vs reference, and limits. "
        "Never invent casualties. Never invent crater/tsunami when surface is unknown. "
        "You advise and explain; you do not operate NASA systems."
    )
    hist_txt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-8:]
    )
    prompt = (
        f"{system}\n\n{TONE_RULES}\n\n"
        f"Project knowledge:\n{json.dumps(knowledge, indent=2)}\n\n"
        f"Simulation context:\n{json.dumps(context, indent=2)}\n\n"
        f"Recent chat:\n{hist_txt}\n\nUser: {message}\n\nAssistant:"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.45,
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
