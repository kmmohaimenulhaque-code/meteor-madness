"""
Mitigation+ interactive AI — human tone, full run context aware.

Can discuss: user inputs, selected asteroid, simulation outputs,
Environment / Impact Branch / AI Report panel data, and place name
from coordinates (Nominatim).
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

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

TONE_RULES = """
Write like a thoughtful teammate, not a manual.
- Short paragraphs, natural speech.
- Use the actual numbers from simulation context when the user asks about the run.
- Explain *why* (e.g. ocean → no land crater).
- If surface is unknown, refuse invented crater/tsunami steps.
- When coordinates resolve to a place, name it; if not, say the coords plainly.
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


def _num(value: Any, digits: int = 2) -> str:
    try:
        n = float(value)
        if abs(n) >= 1000:
            return f"{n:,.{digits}f}".rstrip("0").rstrip(".")
        return f"{n:.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "n/a"


def _enrich_place(context: dict[str, Any]) -> dict[str, Any]:
    """Attach place label from coordinates if not already present."""
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
    """Human summary of Environment / Impact Branch / AI Report panel."""
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
        place_line = f"At coordinates {_num(lat, 4)}°, {_num(lon, 4)}°. "

    lines = [
        f"{place_line}Environment panel says **{surface}**"
        + (f" with confidence {_num(conf, 2)}" if conf is not None else "")
        + f" ({env.get('data_status') or 'n/a'}), source **{source}**."
    ]

    mat_txt = ""
    if material.get("type"):
        mat_txt = (
            f" Material: {material.get('type')}"
            + (
                f" ({material.get('density_kg_m3')} kg/m³)"
                if material.get("density_kg_m3") is not None
                else ""
            )
            + "."
        )
    elev_txt = ""
    if elev is not None:
        elev_txt = f" Elevation about {_num(elev, 1)} m."
    if bathy is not None:
        elev_txt += f" Bathymetry about {_num(bathy, 1)} m."
    if mat_txt or elev_txt:
        lines.append(mat_txt.strip() + elev_txt)

    branch_name = branch.get("branch") or context.get("physics_branch") or surface
    models = branch.get("models_run") or []
    lines.append(
        f"Physics branch is **{branch_name}**"
        + (f" (models: {', '.join(models)})" if models else "")
        + "."
    )

    if branch_name == "land":
        crater = (branch.get("crater") or {}).get("final_diameter_m")
        blast = (branch.get("blast") or {}).get("radius_m")
        thermal = (branch.get("thermal") or {}).get("radius_m")
        bits = []
        if crater is not None:
            bits.append(f"crater diameter ~{_num(crater / 1000, 2)} km")
        if blast is not None:
            bits.append(f"blast radius ~{_num(blast / 1000, 1)} km")
        if thermal is not None:
            bits.append(f"thermal radius ~{_num(thermal / 1000, 1)} km")
        if bits:
            lines.append("Land effects: " + "; ".join(bits) + ".")
    elif branch_name == "ocean":
        ts = branch.get("tsunami") or context.get("tsunami") or {}
        amp = ts.get("estimated_source_amplitude_m")
        if amp is not None:
            lines.append(
                f"Ocean screening tsunami source amplitude on the order of {_num(amp, 1)} m "
                "(not a coastal forecast)."
            )
    elif branch_name == "undetermined":
        lines.append(
            "Environment-specific crater/tsunami physics was refused — no data, no guess."
        )

    if analyst:
        lines.append(
            f"AI report marks risk **{analyst.get('risk_level', 'n/a')}** "
            f"with confidence {analyst.get('confidence_label', 'n/a')} "
            f"({_num(analyst.get('confidence'), 2)}). "
            f"{analyst.get('summary') or ''}"
        )

    if sim.get("outcome") or sim.get("fragmentation_detected") is not None:
        frag = sim.get("fragmentation_detected")
        lines.append(
            f"Entry outcome: {sim.get('outcome') or 'n/a'}"
            + (
                f"; fragmentation {'detected' if frag else 'not detected'}."
                if frag is not None
                else "."
            )
        )
        if sim.get("atmospheric_fraction") is not None:
            try:
                lines.append(
                    f"About {float(sim['atmospheric_fraction']) * 100:.1f}% of the energy "
                    "looks atmospheric in this screening run."
                )
            except (TypeError, ValueError):
                pass

    if asteroid.get("name") or asteroid.get("id"):
        lines.append(
            f"Selected asteroid: {asteroid.get('name') or asteroid.get('id')}"
            + (
                f", diameter ~{_num(asteroid.get('diameter_km'), 4)} km"
                if asteroid.get("diameter_km") is not None
                else ""
            )
            + (
                ", flagged PHA"
                if asteroid.get("hazardous")
                else ""
            )
            + (
                f", miss distance ~{_num(asteroid.get('miss_distance_km'), 0)} km"
                if asteroid.get("miss_distance_km") is not None
                else ""
            )
            + "."
        )

    return "\n\n".join(line for line in lines if line)


def _explain_no_crater(surface: str, branch: str) -> str:
    if surface == "ocean" or branch == "ocean":
        return (
            "Because the selected impact environment was ocean. The land-crater model "
            "was intentionally not applied; the simulation instead used the ocean branch "
            "for water displacement, tsunami screening and seafloor interaction.\n\n"
            "Showing a land crater next to an ocean result would be misleading, so those "
            "models stay on separate branches."
        )
    if surface == "unknown" or branch == "undetermined":
        return (
            "Because the environment engine couldn't confirm land vs ocean. When surface "
            "is unknown, Meteor Madness refuses to manufacture a crater or a tsunami — "
            "no data, no guess."
        )
    if surface == "ice":
        return (
            "This run classified the surface as ice, so land-crater scaling wasn't the "
            "primary branch. Ice uses its own screening response instead."
        )
    return (
        "On a land branch we do run crater scaling. If the panel shows land with crater "
        "numbers, those are the screening values from this run."
    )


def _human_priorities(surface: str, branch: str, energy_mt: Any) -> str:
    priorities = immediate_priorities(surface)
    energy_bit = ""
    try:
        if energy_mt is not None:
            energy_bit = f" Energy scale is roughly {float(energy_mt):.3g} Mt TNT equivalent — screening only."
    except (TypeError, ValueError):
        pass

    if surface == "ocean":
        lead = f"For an ocean impact, I'd start with coastal protection, not land-crater thinking.{energy_bit}"
    elif surface == "land":
        lead = f"For a land impact, first moves are exclusion and blast/thermal/seismic awareness.{energy_bit}"
    elif surface == "ice":
        lead = f"Ice impacts stay screening-level here.{energy_bit}"
    else:
        lead = (
            "We don't have a trusted surface classification, so I won't invent crater or "
            "tsunami steps. Fix the environment data first."
        )

    body = "\n".join(f"{i}. {p}" for i, p in enumerate(priorities, 1))
    return f"{lead}\n\nImmediate priorities:\n{body}\n\nEducational guidance only — not an operational emergency plan."


def _explain_engines() -> str:
    return (
        "Entry physics integrates the body through the atmosphere (RK4 — drag, ablation, "
        "possible fragmentation). The environment engine asks GEBCO for real elevation or "
        "depth; land and ocean then take different physics branches. Land gets crater/blast/"
        "thermal screening; ocean gets displacement and tsunami screening; unknown refuses "
        "to invent either. The AI panel and this chat only narrate that hierarchy — they "
        "don't override it."
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
        "What this app actually calls live:\n"
        + "\n".join(wired)
        + "\n\nUseful NASA context we haven't wired yet:\n"
        + "\n".join(ref)
        + "\n\nNeoWs uses NASA_API_KEY from api.nasa.gov. I explain results; I don't operate "
        "NASA systems for you."
    )


def _explain_limitations() -> str:
    points = "\n".join(f"• {item}" for item in LIMITATIONS)
    return (
        "Straight talk on limits — this is a Space Apps screening demo:\n\n"
        f"{points}"
    )


def _explain_project() -> str:
    return (
        "Meteor Madness walks a real near-Earth object from NASA NeoWs through entry "
        "physics, a GEBCO environment check, and a strict land/ocean/ice/unknown branch "
        "before the AI panel and this chat.\n\n"
        f"{PROJECT_OVERVIEW.strip()}"
    )


def _rule_reply(message: str, context: dict[str, Any]) -> str:
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

    # Panel / numbers / place / asteroid / simulation questions
    if any(
        k in lower
        for k in (
            "panel",
            "environment engine",
            "impact branch",
            "this run",
            "this simulation",
            "my result",
            "the results",
            "what did",
            "summar",
            "crater diameter",
            "blast radius",
            "thermal",
            "elev",
            "bathym",
            "confidence",
            "risk",
            "where is",
            "what place",
            "location",
            "coordinate",
            "asteroid",
            "selected",
            "neo",
            "diameter",
            "hazard",
            "miss distance",
            "fragment",
            "energy",
            "mt",
            "megaton",
        )
    ):
        return _panel_summary(context)

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
            "explain project",
            "what is this",
            "architecture",
            "pipeline",
        )
    ):
        if "nasa" in lower:
            return _explain_nasa()
        if "limit" in lower:
            return _explain_limitations()
        if any(k in lower for k in ("engine", "solver", "gebco", "environment")):
            return _explain_engines()
        return _explain_project()

    if any(k in lower for k in ("engine", "solver", "gebco")):
        return _explain_engines()
    if "nasa" in lower or "neows" in lower:
        return _explain_nasa()
    if "limit" in lower or "uncertain" in lower:
        return _explain_limitations()

    if any(
        k in lower for k in ("priorit", "immediate", "mitigat", "evacuat", "what should")
    ):
        return _human_priorities(surface, branch, energy_mt)

    if "tsunami" in lower:
        if surface != "ocean":
            return (
                f"Tsunami steps only make sense for an ocean environment. This run is "
                f"**{surface}**.\n\n" + _explain_no_crater(surface, branch)
            )
        return _human_priorities("ocean", branch, energy_mt)

    if any(k in lower for k in ("crater", "blast", "seismic", "exclusion")):
        if surface != "land":
            return _explain_no_crater(surface, branch)
        return _panel_summary(context) + "\n\n" + _human_priorities(
            "land", branch, energy_mt
        )

    # Default: orient on this run
    return (
        _panel_summary(context)
        + "\n\n"
        + "Ask me about the crater numbers, the place at these coordinates, the asteroid, "
        "mitigation priorities, engines, NASA services, or limits."
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
        "Sound human. You can see the full simulation context: user lat/lon/azimuth, "
        "selected asteroid, environment panel, impact branch, AI analyst report, and "
        "optional reverse-geocoded place name. Quote real numbers from that context. "
        "If the user asks where the impact is, use place.display_name or coordinates. "
        "Explain ocean vs land branching clearly. Never invent casualties or fake "
        "environment physics when surface is unknown."
    )
    hist_txt = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-8:]
    )
    prompt = (
        f"{system}\n\n{TONE_RULES}\n\n"
        f"Project knowledge:\n{json.dumps(knowledge, indent=2)}\n\n"
        f"Full run context:\n{json.dumps(context, indent=2)}\n\n"
        f"Recent chat:\n{hist_txt}\n\nUser: {message}\n\nAssistant:"
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1600,
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
    context = _enrich_place(context or {})
    history = history or []
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
        "place": context.get("place"),
        "knowledge": {
            "engines": list(ENGINES.keys()),
            "nasa_wired": [
                k for k, v in NASA_SERVICES.items() if v.get("used_in_project")
            ],
            "limitations_count": len(LIMITATIONS),
        },
    }
