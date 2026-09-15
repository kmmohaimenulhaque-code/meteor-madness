"""
Mitigation+ — adaptive tone, full context, source-linked explainers.

Integrates:
- Human conversational style
- Simulation / asteroid / AI panel / place context
- Planetary-defence priorities by environment class
- How-calculation-works → points at source files
- General NASA / project knowledge beyond a single run
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

import httpx

from physics.calc_explainers import format_explainer, match_explainer
from physics.place_lookup import reverse_geocode
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

Tone = Literal[
    "curious",
    "technical",
    "brief",
    "empathetic",
    "formal",
    "playful",
    "default",
]


def detect_tone(message: str) -> Tone:
    lower = (message or "").lower()
    if any(
        k in lower
        for k in (
            "eli5",
            "simply",
            "simple terms",
            "like i'm five",
            "like i am five",
            "in plain english",
            "plain language",
        )
    ):
        return "curious"
    if any(
        k in lower
        for k in (
            "source code",
            "module",
            "equation",
            "derive",
            "rk4",
            "formula",
            "implementation",
            "which file",
            "technical",
        )
    ):
        return "technical"
    if any(k in lower for k in ("tldr", "tl;dr", "briefly", "in one sentence", "short answer")):
        return "brief"
    if any(
        k in lower
        for k in ("worried", "scared", "dangerous", "are we safe", "should i panic")
    ):
        return "empathetic"
    if any(
        k in lower
        for k in ("judge", "report", "formal", "for the judges", "documentation")
    ):
        return "formal"
    if any(k in lower for k in ("lol", "haha", "bro", "dude", "level up")):
        return "playful"
    return "default"


def tone_instruction(tone: Tone) -> str:
    return {
        "curious": "Explain gently, like to a smart friend new to the topic. Short analogies OK.",
        "technical": "Be precise. Name modules, fields, and assumptions. Still readable.",
        "brief": "Answer in 2–4 sentences max. Offer to go deeper.",
        "empathetic": "Calm and grounding. Stress this is educational screening, not a real alert.",
        "formal": "Clear, judge-ready prose. Structure: what → how → limits.",
        "playful": "Warm and a bit witty, but never sloppy on the science.",
        "default": "Thoughtful teammate voice: natural paragraphs, honest, concrete.",
    }[tone]


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


def _num(value: Any, digits: int = 2) -> str:
    try:
        n = float(value)
        if abs(n) >= 1000:
            return f"{n:,.{min(digits, 1)}f}".rstrip("0").rstrip(".")
        return f"{n:.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "n/a"


def _enrich_place(context: dict[str, Any]) -> dict[str, Any]:
    if context.get("place") and context["place"].get("display_name"):
        return context
    lat = context.get("latitude")
    lon = context.get("longitude")
    if lat is None or lon is None:
        coords = (context.get("environment") or {}).get("coordinates") or {}
        lat = coords.get("latitude", lat)
        lon = coords.get("longitude", lon)
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return context
    place = reverse_geocode(lat_f, lon_f)
    enriched = dict(context)
    enriched["place"] = place
    enriched["latitude"] = lat_f
    enriched["longitude"] = lon_f
    return enriched


def _panel_summary(context: dict[str, Any]) -> str:
    env = context.get("environment") or {}
    branch = context.get("impact_branch") or {}
    analyst = context.get("analyst") or {}
    sim = context.get("simulation") or {}
    asteroid = context.get("asteroid") or {}
    place = context.get("place") or {}

    surface = (
        env.get("surface")
        or context.get("surface")
        or context.get("environment_class")
        or "unknown"
    )
    conf = env.get("surface_confidence", context.get("surface_confidence"))
    source = env.get("terrain_source") or env.get("source") or "n/a"
    material = env.get("material") or {}
    elev = env.get("elevation_m")
    bathy = env.get("bathymetry_m")
    lat = context.get("latitude")
    lon = context.get("longitude")
    coords = env.get("coordinates") or {}
    if lat is None:
        lat = coords.get("latitude")
    if lon is None:
        lon = coords.get("longitude")

    place_line = ""
    if place.get("short_name") or place.get("display_name"):
        place_line = f"Near **{place.get('short_name') or place.get('display_name')}**. "
    elif lat is not None and lon is not None:
        place_line = f"At {_num(lat, 4)}°, {_num(lon, 4)}°. "

    lines = [
        f"{place_line}Environment panel: **{surface}**"
        + (f", confidence {_num(conf, 2)}" if conf is not None else "")
        + f", source **{source}** ({env.get('data_status') or 'n/a'})."
    ]
    if material.get("type"):
        dens = material.get("density_kg_m3")
        lines.append(
            f"Material {material['type']}"
            + (f" ({dens} kg/m³)" if dens is not None else "")
            + (
                f"; elevation ~{_num(elev, 1)} m"
                if elev is not None
                else ""
            )
            + (
                f"; bathymetry ~{_num(bathy, 1)} m"
                if bathy is not None
                else ""
            )
            + "."
        )

    branch_name = branch.get("branch") or context.get("physics_branch") or surface
    models = branch.get("models_run") or []
    lines.append(
        f"Physics branch **{branch_name}**"
        + (f" — {', '.join(models)}" if models else "")
        + "."
    )

    if branch_name == "land":
        crater = (branch.get("crater") or {}).get("final_diameter_m")
        blast = (branch.get("blast") or {}).get("radius_m")
        thermal = (branch.get("thermal") or {}).get("radius_m")
        bits = []
        if crater is not None:
            bits.append(f"crater ~{_num(crater / 1000, 2)} km")
        if blast is not None:
            bits.append(f"blast ~{_num(blast / 1000, 1)} km")
        if thermal is not None:
            bits.append(f"thermal ~{_num(thermal / 1000, 1)} km")
        if bits:
            lines.append("Land screening: " + "; ".join(bits) + ".")
    elif branch_name == "ocean":
        ts = branch.get("tsunami") or context.get("tsunami") or {}
        amp = ts.get("estimated_source_amplitude_m")
        if amp is not None:
            lines.append(
                f"Tsunami screen source amplitude ~{_num(amp, 1)} m (not a coastal forecast)."
            )
    elif branch_name == "undetermined":
        lines.append("Crater/tsunami physics refused — no environment data, no guess.")

    if analyst:
        lines.append(
            f"AI report: risk **{analyst.get('risk_level', 'n/a')}**, "
            f"confidence {analyst.get('confidence_label', 'n/a')} "
            f"({_num(analyst.get('confidence'), 2)}). "
            f"{analyst.get('summary') or ''}"
        )

    if sim:
        frag = sim.get("fragmentation_detected")
        lines.append(
            f"Entry outcome {sim.get('outcome') or 'n/a'}"
            + (
                f"; fragmentation {'yes' if frag else 'no'}"
                if frag is not None
                else ""
            )
            + "."
        )
        if sim.get("atmospheric_fraction") is not None:
            try:
                lines.append(
                    f"~{float(sim['atmospheric_fraction']) * 100:.1f}% atmospheric energy fraction in this screen."
                )
            except (TypeError, ValueError):
                pass

    if asteroid.get("name") or asteroid.get("id"):
        lines.append(
            f"Asteroid {asteroid.get('name') or asteroid.get('id')}"
            + (
                f", ⌀ {_num(asteroid.get('diameter_km'), 4)} km"
                if asteroid.get("diameter_km") is not None
                else ""
            )
            + ("; PHA" if asteroid.get("hazardous") else "")
            + (
                f", miss {_num(asteroid.get('miss_distance_km'), 0)} km"
                if asteroid.get("miss_distance_km") is not None
                else ""
            )
            + "."
        )

    return "\n\n".join(x for x in lines if x)


def _explain_no_crater(surface: str, branch: str) -> str:
    if surface == "ocean" or branch == "ocean":
        return (
            "Because the selected impact environment was ocean. The land-crater model "
            "was intentionally not applied; the simulation instead used the ocean branch "
            "for water displacement, tsunami screening and seafloor interaction."
        )
    if surface == "unknown" or branch == "undetermined":
        return (
            "Because the environment engine couldn't confirm land vs ocean. Unknown "
            "surface means we refuse to manufacture a crater or tsunami."
        )
    if surface == "ice":
        return (
            "Ice was the environment class, so land-crater scaling wasn't the primary branch."
        )
    return (
        "On land we do run crater scaling — check the land consequences / impact branch panel."
    )


def _human_priorities(surface: str, branch: str, energy_mt: Any) -> str:
    priorities = immediate_priorities(surface)
    energy_bit = ""
    try:
        if energy_mt is not None:
            energy_bit = f" Energy scale ~{float(energy_mt):.3g} Mt TNT (screening)."
    except (TypeError, ValueError):
        pass
    leads = {
        "ocean": f"Ocean impact — think coastlines first, not land craters.{energy_bit}",
        "land": f"Land impact — exclusion and blast/thermal/seismic awareness first.{energy_bit}",
        "ice": f"Ice impact — screening-level orientation only.{energy_bit}",
        "unknown": "No trusted surface yet — I won't invent crater or tsunami actions.",
    }
    lead = leads.get(surface, leads["unknown"])
    body = "\n".join(f"{i}. {p}" for i, p in enumerate(priorities, 1))
    return f"{lead}\n\nImmediate priorities:\n{body}\n\nEducational guidance, not an operational emergency plan."


def _apply_tone_wrapper(text: str, tone: Tone) -> str:
    if tone == "brief":
        # keep first ~2 paragraphs
        parts = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        return "\n\n".join(parts[:2])
    if tone == "empathetic":
        prefix = (
            "First: this app is an educational screen, not a real-time alert system. "
            "Nothing here should be read as ‘something is happening to you right now.’\n\n"
        )
        return prefix + text
    if tone == "formal":
        return text  # already structured; Gemini gets formal instruction
    return text


def _rule_reply(message: str, context: dict[str, Any], tone: Tone) -> str:
    surface = str(
        context.get("surface")
        or context.get("environment_class")
        or (context.get("environment") or {}).get("surface")
        or "unknown"
    ).lower()
    branch = str(
        context.get("physics_branch")
        or (context.get("impact_branch") or {}).get("branch")
        or surface
    ).lower()
    energy_mt = context.get("impact_energy_mt")
    if energy_mt is None and context.get("simulation"):
        energy_mt = context["simulation"].get("impact_energy_megatons_tnt")
    lower = (message or "").lower()

    explainer = match_explainer(message)
    if explainer:
        return _apply_tone_wrapper(format_explainer(explainer), tone)

    if any(
        k in lower
        for k in (
            "why didn",
            "why did not",
            "no crater",
            "didn't calculate",
            "did not calculate",
            "surface crater",
        )
    ):
        return _apply_tone_wrapper(_explain_no_crater(surface, branch), tone)

    if any(
        k in lower
        for k in (
            "panel",
            "this run",
            "this simulation",
            "my result",
            "summar",
            "environment engine",
            "impact branch",
            "where is",
            "what place",
            "location",
            "asteroid",
            "selected",
            "crater diameter",
            "blast radius",
            "risk",
            "energy",
            "fragment",
        )
    ):
        return _apply_tone_wrapper(_panel_summary(context), tone)

    if "nasa" in lower or "neows" in lower:
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
        text = (
            "Live in this project:\n"
            + "\n".join(wired)
            + "\n\nReference only for now:\n"
            + "\n".join(ref)
        )
        return _apply_tone_wrapper(text, tone)

    if "limit" in lower or "uncertain" in lower:
        text = "Honest limits:\n" + "\n".join(f"• {x}" for x in LIMITATIONS)
        return _apply_tone_wrapper(text, tone)

    if any(
        k in lower
        for k in ("priorit", "immediate", "mitigat", "evacuat", "what should")
    ):
        return _apply_tone_wrapper(
            _human_priorities(surface, branch, energy_mt), tone
        )

    if any(
        k in lower
        for k in ("how does this project", "what is this", "architecture", "pipeline")
    ):
        return _apply_tone_wrapper(
            PROJECT_OVERVIEW.strip()
            + "\n\nEngines: "
            + ", ".join(ENGINES.keys())
            + ". Ask how any calculation works and I’ll point at the source file.",
            tone,
        )

    # default: orient on run + invite depth
    return _apply_tone_wrapper(
        _panel_summary(context)
        + "\n\nI can go technical (source files), plain-language, mitigation priorities, "
        "or general NASA context — tell me which lane you want.",
        tone,
    )


def _gemini_reply(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    api_key: str,
    tone: Tone,
) -> str | None:
    knowledge = knowledge_bundle()
    explainer = match_explainer(message)
    system = (
        "You are Mitigation+ for Meteor Madness (NASA Space Apps educational simulator). "
        "Adapt your tone to the user. You have full run context: inputs, asteroid, "
        "environment panel, impact branch, AI analyst, optional place name. "
        "You also have general project knowledge and calculation explainers with source "
        "file paths — when asked how a calculation works, cite those modules. "
        "Be human. Never invent casualties. Never invent crater/tsunami when surface is unknown. "
        "You explain; you do not operate NASA systems."
    )
    hist_txt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-10:]
    )
    explainer_block = (
        json.dumps(explainer, indent=2) if explainer else "null"
    )
    prompt = (
        f"{system}\n\nTone mode: {tone}\nTone guidance: {tone_instruction(tone)}\n\n"
        f"Matched calculation explainer (use if relevant):\n{explainer_block}\n\n"
        f"Project knowledge:\n{json.dumps(knowledge, indent=2)}\n\n"
        f"Full run context:\n{json.dumps(context, indent=2)}\n\n"
        f"Recent chat:\n{hist_txt}\n\nUser: {message}\n\nAssistant:"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5 if tone in ("playful", "curious") else 0.35,
            "maxOutputTokens": 1800,
        },
    }
    try:
        with httpx.Client(timeout=35.0) as client:
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
    context = _enrich_place(context or {})
    history = history or []
    tone = detect_tone(message)
    surface = str(
        context.get("surface")
        or context.get("environment_class")
        or (context.get("environment") or {}).get("surface")
        or "unknown"
    ).lower()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    reply = None
    source = "rule_based"
    if api_key:
        reply = _gemini_reply(message, context, history, api_key, tone)
        if reply:
            source = "gemini"

    if not reply:
        reply = _rule_reply(message, context, tone)

    return {
        "status": "ok",
        "reply": reply,
        "source": source,
        "tone": tone,
        "immediate_priorities": immediate_priorities(surface),
        "surface": surface,
        "place": context.get("place"),
        "matched_explainer": (match_explainer(message) or {}).get("title"),
        "knowledge": {
            "engines": list(ENGINES.keys()),
            "nasa_wired": [
                k for k, v in NASA_SERVICES.items() if v.get("used_in_project")
            ],
            "limitations_count": len(LIMITATIONS),
        },
    }
