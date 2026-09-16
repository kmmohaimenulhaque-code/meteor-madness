"""
Mitigation+ mission analyst.

Gemini-powered conversational analyst for Meteor Madness.

Architecture:

    User question
          ↓
    Gemini understands intent
          ↓
    Gemini decides whether it needs a tool
          ↓
    Controlled backend tool
          ↓
    Current simulation/environment data
          ↓
    Gemini explains the result

IMPORTANT:
- Gemini does NOT replace the physics engine.
- Gemini does NOT calculate authoritative physics values.
- Backend simulation data remains the source of truth.
- Tools are read-only.
- The AI cannot modify simulation state.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from ai_tools import (
    get_simulation_summary,
    get_impact_data,
    get_environment_data,
    get_consequences_data,
    get_planetary_defence_context,
)

from physics.calc_explainers import (
    EXPLAINERS,
    format_explainer,
    match_explainer,
)

from physics.gemini_client import (
    GEMINI_MODEL,
    build_chat_contents,
    generate_content,
)

from physics.mitigation_system_prompt import (
    EXAMPLE_ENGINES,
    EXAMPLE_LIMITATIONS,
    MITIGATION_SYSTEM_PROMPT,
)

from physics.place_lookup import reverse_geocode

from physics.project_knowledge import (
    ENGINES,
    LIMITATIONS,
    NASA_SERVICES,
    PROJECT_OVERVIEW,
    knowledge_bundle,
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


# ============================================================
# CONTROLLED AI TOOL DISPATCHER
# ============================================================

def run_ai_tool(
    tool_name: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Controlled tool dispatcher.

    Only explicitly approved read-only tools can be executed.

    The model cannot:
    - write files
    - modify the simulation
    - execute arbitrary Python
    - access the filesystem
    - call arbitrary APIs
    """

    tools = {
        "get_simulation_summary": get_simulation_summary,
        "get_impact_data": get_impact_data,
        "get_environment_data": get_environment_data,
        "get_consequences_data": get_consequences_data,
    }

    if tool_name == "get_planetary_defence_context":
        return get_planetary_defence_context()

    tool = tools.get(tool_name)

    if tool is None:
        return {
            "error": f"Unknown AI tool: {tool_name}"
        }

    try:
        return tool(context)
    except Exception as exc:
        return {
            "error": (
                f"Tool '{tool_name}' failed: "
                f"{type(exc).__name__}: {exc}"
            )
        }


# ============================================================
# GEMINI TOOL WRAPPERS
# ============================================================

def _build_gemini_tools(
    context: dict[str, Any],
) -> list[Any]:
    """
    Build Python callables for Gemini native function calling.

    Each function closes over the current simulation context.

    Gemini therefore gets semantic access to the CURRENT RUN,
    without receiving arbitrary backend access.
    """

    def get_current_simulation_summary() -> dict[str, Any]:
        """
        Get the complete current Meteor Madness simulation summary.

        Use this when the user asks about their current run,
        asteroid, impact coordinates, environment, branch, outcome,
        or general simulation result.
        """
        return run_ai_tool(
            "get_simulation_summary",
            context,
        )

    def get_current_impact_data() -> dict[str, Any]:
        """
        Get authoritative impact-specific values from the current run.

        Includes impact energy, outcome, fragmentation, and the
        active impact branch.
        """
        return run_ai_tool(
            "get_impact_data",
            context,
        )

    def get_current_environment_data() -> dict[str, Any]:
        """
        Get the environment and GEBCO-derived information attached
        to the current simulation.

        Includes surface class, confidence, elevation,
        bathymetry, terrain source, and material when available.
        """
        return run_ai_tool(
            "get_environment_data",
            context,
        )

    def get_current_consequences_data() -> dict[str, Any]:
        """
        Get consequences produced by the current simulation.

        Includes crater, blast, thermal, tsunami and seismic
        outputs when those models were applicable.
        """
        return run_ai_tool(
            "get_consequences_data",
            context,
        )

    def get_planetary_defence_information() -> dict[str, Any]:
        """
        Get high-level educational planetary-defence concepts.

        Use this for questions about kinetic impactors,
        gravity tractors, reconnaissance, civil defence,
        laser ablation, or broad mitigation concepts.

        This tool provides educational context only and is not
        an operational mission planner.
        """
        return run_ai_tool(
            "get_planetary_defence_context",
            context,
        )

    return [
        get_current_simulation_summary,
        get_current_impact_data,
        get_current_environment_data,
        get_current_consequences_data,
        get_planetary_defence_information,
    ]


# ============================================================
# TONE DETECTION
# ============================================================

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

    if any(
        k in lower
        for k in (
            "tldr",
            "tl;dr",
            "briefly",
            "in one sentence",
            "short answer",
        )
    ):
        return "brief"

    if any(
        k in lower
        for k in (
            "worried",
            "scared",
            "dangerous",
            "are we safe",
            "should i panic",
        )
    ):
        return "empathetic"

    if any(
        k in lower
        for k in (
            "judge",
            "report",
            "formal",
            "for the judges",
            "documentation",
        )
    ):
        return "formal"

    if any(
        k in lower
        for k in (
            "lol",
            "haha",
            "bro",
            "dude",
        )
    ):
        return "playful"

    return "default"


def tone_instruction(
    tone: Tone,
) -> str:
    return {
        "curious": (
            "Explain gently, like to a smart friend "
            "new to the topic."
        ),
        "technical": (
            "Be precise. Name modules and assumptions. "
            "Still readable."
        ),
        "brief": (
            "Answer in 2–4 sentences max. "
            "Offer to go deeper."
        ),
        "empathetic": (
            "Calm. Stress educational screening, "
            "not a real alert."
        ),
        "formal": (
            "Judge-ready: what → how → limits."
        ),
        "playful": (
            "Warm, a bit witty, never sloppy on science."
        ),
        "default": (
            "Conversational teammate. "
            "Answer the question first."
        ),
    }[tone]


# ============================================================
# PRIORITIES
# ============================================================

def immediate_priorities(
    surface: str,
) -> list[str]:

    s = (
        surface or "unknown"
    ).lower()

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


# ============================================================
# HELPERS
# ============================================================

def _num(
    value: Any,
    digits: int = 2,
) -> str:

    try:
        n = float(value)

        if abs(n) >= 1000:
            return (
                f"{n:,.{min(digits, 1)}f}"
                .rstrip("0")
                .rstrip(".")
            )

        return (
            f"{n:.{digits}f}"
            .rstrip("0")
            .rstrip(".")
        )

    except (TypeError, ValueError):
        return "n/a"


def _surface_of(
    context: dict[str, Any],
) -> str:

    return str(
        context.get("surface")
        or context.get("environment_class")
        or (
            context.get("environment") or {}
        ).get("surface")
        or "unknown"
    ).lower()


def _branch_of(
    context: dict[str, Any],
) -> str:

    return str(
        context.get("physics_branch")
        or (
            context.get("impact_branch") or {}
        ).get("branch")
        or _surface_of(context)
    ).lower()


def _enrich_place(
    context: dict[str, Any],
) -> dict[str, Any]:

    if (
        context.get("place")
        and context["place"].get("display_name")
    ):
        return context

    lat = context.get("latitude")
    lon = context.get("longitude")

    if lat is None or lon is None:
        coords = (
            context.get("environment") or {}
        ).get("coordinates") or {}

        lat = coords.get(
            "latitude",
            lat,
        )

        lon = coords.get(
            "longitude",
            lon,
        )

    try:
        lat_f = float(lat)
        lon_f = float(lon)

    except (TypeError, ValueError):
        return context

    place = reverse_geocode(
        lat_f,
        lon_f,
    )

    enriched = dict(context)

    enriched["place"] = place
    enriched["latitude"] = lat_f
    enriched["longitude"] = lon_f

    return enriched


# ============================================================
# GROUNDING
# ============================================================

def _build_grounding(
    message: str,
    context: dict[str, Any],
    tone: Tone,
) -> dict[str, Any]:
    """
    Runtime grounding packet.

    This is context for the current request.
    It is NOT model training.
    """

    matched = match_explainer(
        message
    )

    return {
        "note": (
            "The following is grounding/context for this request only. "
            "It is not model training. "
            "Prefer CURRENT SIMULATION PAYLOAD numbers."
        ),

        "important_rule": (
            "Backend simulation values are authoritative. "
            "Do not invent or recalculate them."
        ),

        "tone": tone,

        "tone_guidance": tone_instruction(
            tone
        ),

        "available_tools": [
            "get_current_simulation_summary",
            "get_current_impact_data",
            "get_current_environment_data",
            "get_current_consequences_data",
            "get_planetary_defence_information",
        ],

        "project_knowledge": knowledge_bundle(),

        "calc_explainers_index": {
            key: {
                "title": meta.get("title"),
                "files": meta.get("files"),
            }
            for key, meta in EXPLAINERS.items()
        },

        "matched_calc_explainer": matched,

        "simulation_payload": context,
    }


# ============================================================
# PANEL SUMMARY
# ============================================================

def _panel_summary(
    context: dict[str, Any],
) -> str:

    env = (
        context.get("environment")
        or {}
    )

    branch = (
        context.get("impact_branch")
        or {}
    )

    analyst = (
        context.get("analyst")
        or {}
    )

    sim = (
        context.get("simulation")
        or {}
    )

    asteroid = (
        context.get("asteroid")
        or {}
    )

    place = (
        context.get("place")
        or {}
    )

    surface = _surface_of(context)

    conf = env.get(
        "surface_confidence",
        context.get("surface_confidence"),
    )

    source = (
        env.get("terrain_source")
        or env.get("source")
        or "n/a"
    )

    material = (
        env.get("material")
        or {}
    )

    elev = env.get(
        "elevation_m"
    )

    bathy = env.get(
        "bathymetry_m"
    )

    lat = context.get(
        "latitude"
    )

    lon = context.get(
        "longitude"
    )

    coords = (
        env.get("coordinates")
        or {}
    )

    if lat is None:
        lat = coords.get(
            "latitude"
        )

    if lon is None:
        lon = coords.get(
            "longitude"
        )

    place_line = ""

    if (
        place.get("short_name")
        or place.get("display_name")
    ):
        place_line = (
            f"Near **{place.get('short_name') or place.get('display_name')}**. "
        )

    elif (
        lat is not None
        and lon is not None
    ):
        place_line = (
            f"At {_num(lat, 4)}°, "
            f"{_num(lon, 4)}°. "
        )

    lines = [
        f"{place_line}"
        f"From the current payload: "
        f"environment **{surface}**"
        + (
            f", confidence {_num(conf, 2)}"
            if conf is not None
            else ""
        )
        + f", source **{source}** "
        f"({env.get('data_status') or 'n/a'})."
    ]

    if material.get("type"):

        dens = material.get(
            "density_kg_m3"
        )

        extra = []

        if dens is not None:
            extra.append(
                f"{dens} kg/m³"
            )

        if elev is not None:
            extra.append(
                f"elev {_num(elev, 1)} m"
            )

        if bathy is not None:
            extra.append(
                f"bathymetry {_num(bathy, 1)} m"
            )

        lines.append(
            f"Material {material['type']}"
            + (
                f" ({', '.join(extra)})"
                if extra
                else ""
            )
            + "."
        )

    branch_name = _branch_of(
        context
    )

    models = (
        branch.get("models_run")
        or []
    )

    lines.append(
        f"Physics branch **{branch_name}**"
        + (
            f" — models present: "
            f"{', '.join(models)}"
            if models
            else
            " — no environment models run"
        )
        + "."
    )

    if branch_name == "land":

        crater = (
            branch.get("crater")
            or {}
        ).get(
            "final_diameter_m"
        )

        blast = (
            branch.get("blast")
            or {}
        ).get(
            "radius_m"
        )

        thermal = (
            branch.get("thermal")
            or {}
        ).get(
            "radius_m"
        )

        bits = []

        if crater is not None:
            bits.append(
                "crater diameter "
                f"{_num(crater / 1000, 2)} km "
                "(screening)"
            )

        if blast is not None:
            bits.append(
                "blast radius "
                f"{_num(blast / 1000, 1)} km "
                "(screening)"
            )

        if thermal is not None:
            bits.append(
                "thermal radius "
                f"{_num(thermal / 1000, 1)} km "
                "(screening)"
            )

        if bits:
            lines.append(
                "Land branch values in payload: "
                + "; ".join(bits)
                + "."
            )

        else:
            lines.append(
                "Land branch is active but "
                "crater/blast/thermal fields are "
                "not populated in this payload."
            )

    elif branch_name == "ocean":

        lines.append(
            "Ocean branch is active — terrestrial "
            "crater/blast/thermal are not applicable "
            "consequences here."
        )

        ts = (
            branch.get("tsunami")
            or context.get("tsunami")
            or {}
        )

        amp = ts.get(
            "estimated_source_amplitude_m"
        )

        if amp is not None:
            lines.append(
                "Tsunami screening source amplitude "
                f"in payload: {_num(amp, 1)} m "
                "(energy-scaling screen, "
                "not a coastal forecast)."
            )

    elif (
        branch_name == "undetermined"
        or surface == "unknown"
    ):

        lines.append(
            "Surface is unknown or undetermined — "
            "environment-specific consequences were "
            "intentionally withheld."
        )

    if analyst.get("summary"):

        lines.append(
            f"Analyst (advisory): "
            f"risk {analyst.get('risk_level', 'n/a')}, "
            f"confidence "
            f"{analyst.get('confidence_label', 'n/a')} "
            f"({_num(analyst.get('confidence'), 2)}). "
            f"{analyst.get('summary')}"
        )

    if sim:

        frag = sim.get(
            "fragmentation_detected"
        )

        lines.append(
            f"Entry outcome in payload: "
            f"{sim.get('outcome') or 'n/a'}"
            + (
                "; fragmentation "
                + (
                    "detected"
                    if frag
                    else "not detected"
                )
                if frag is not None
                else ""
            )
            + "."
        )

    if (
        asteroid.get("name")
        or asteroid.get("id")
    ):

        lines.append(
            f"Selected asteroid ☄️ "
            f"{asteroid.get('name') or asteroid.get('id')}"
            + (
                f", diameter "
                f"{_num(asteroid.get('diameter_km'), 4)} km"
                if asteroid.get("diameter_km") is not None
                else ""
            )
            + (
                "; PHA"
                if asteroid.get("hazardous")
                else ""
            )
            + (
                f", miss distance "
                f"{_num(asteroid.get('miss_distance_km'), 0)} km"
                if asteroid.get("miss_distance_km") is not None
                else ""
            )
            + "."
        )

    return "\n\n".join(
        x
        for x in lines
        if x
    )


# ============================================================
# EXPLANATIONS
# ============================================================

def _explain_no_crater(
    surface: str,
    branch: str,
) -> str:

    if (
        surface == "ocean"
        or branch == "ocean"
    ):
        return (
            "Because the selected impact environment was ocean. "
            "The land-crater model was intentionally not applied; "
            "the simulation instead used the ocean branch for water "
            "displacement, tsunami screening and seafloor interaction."
        )

    if (
        surface == "unknown"
        or branch == "undetermined"
    ):
        return (
            "Because the environment class is unknown. "
            "Environment-specific consequences (including crater) "
            "were intentionally withheld — no data, no guess."
        )

    if (
        surface == "ice"
        or branch == "ice"
    ):
        return (
            "Ice was the environment class, so terrestrial "
            "land-crater scaling was not the active branch for this run."
        )

    return (
        "On the land branch the payload may include crater screening "
        "values. I only report numbers that appear in the simulation payload."
    )


def _human_priorities(
    surface: str,
    energy_mt: Any,
) -> str:

    priorities = immediate_priorities(
        surface
    )

    energy_bit = ""

    try:

        if energy_mt is not None:
            energy_bit = (
                f" Impact energy in the payload is "
                f"about {float(energy_mt):.3g} Mt TNT "
                "equivalent (screening scale)."
            )

    except (
        TypeError,
        ValueError,
    ):
        pass

    if surface == "ocean":

        lead = (
            "For this ocean-class result, cautious "
            "next steps would warrant further coastal "
            f"assessment rather than land-crater thinking."
            f"{energy_bit}"
        )

    elif surface == "land":

        lead = (
            "For this land-class result, screening "
            "priorities focus on exclusion and "
            f"blast/thermal/seismic exposure awareness."
            f"{energy_bit}"
        )

    elif surface == "ice":

        lead = (
            f"Ice-class result — treat the following "
            f"as orientation only.{energy_bit}"
        )

    else:

        lead = (
            "Surface is unknown in the payload, so I "
            "will not invent crater or tsunami mitigation "
            "as if those models had run."
        )

    body = "\n".join(
        f"{i}. {p}"
        for i, p in enumerate(
            priorities,
            1,
        )
    )

    return (
        f"{lead}\n\n"
        f"Screening-oriented priorities:\n"
        f"{body}\n\n"
        "A real assessment would require specialised "
        "agencies and higher-fidelity models. "
        "This is not an operational emergency instruction."
    )


# ============================================================
# TONE WRAPPER
# ============================================================

def _apply_tone_wrapper(
    text: str,
    tone: Tone,
) -> str:

    if tone == "brief":

        parts = [
            p.strip()
            for p in re.split(
                r"\n\n+",
                text,
            )
            if p.strip()
        ]

        return "\n\n".join(
            parts[:2]
        )

    if tone == "empathetic":

        return (
            "This app is an educational screen, "
            "not a live alert. Nothing here means "
            "an impact is happening to you right now.\n\n"
            + text
        )

    return text


# ============================================================
# RULE-BASED FALLBACK
# ============================================================

def _rule_reply(
    message: str,
    context: dict[str, Any],
    tone: Tone,
) -> str:

    surface = _surface_of(
        context
    )

    branch = _branch_of(
        context
    )

    energy_mt = context.get(
        "impact_energy_mt"
    )

    if (
        energy_mt is None
        and context.get("simulation")
    ):
        energy_mt = (
            context["simulation"]
            .get(
                "impact_energy_megatons_tnt"
            )
        )

    lower = (
        message or ""
    ).lower()

    explainer = match_explainer(
        message
    )

    if explainer:

        return _apply_tone_wrapper(
            format_explainer(
                explainer
            ),
            tone,
        )

    if any(
        k in lower
        for k in (
            "project limitation",
            "the limitation",
            "limitations",
            "what are the limit",
        )
    ):

        return _apply_tone_wrapper(
            EXAMPLE_LIMITATIONS,
            tone,
        )

    if (
        any(
            k in lower
            for k in (
                "explain the engine",
                "the engines",
                "working pieces",
                "working engine",
            )
        )
        or (
            "engine" in lower
            and "explain" in lower
        )
    ):

        return _apply_tone_wrapper(
            EXAMPLE_ENGINES,
            tone,
        )

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

        return _apply_tone_wrapper(
            _explain_no_crater(
                surface,
                branch,
            ),
            tone,
        )

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
            "coordinate",
            "asteroid",
            "selected",
            "☄️",
            "crater diameter",
            "blast radius",
            "risk",
            "energy",
            "fragment",
        )
    ):

        return _apply_tone_wrapper(
            _panel_summary(context),
            tone,
        )

    if (
        "nasa" in lower
        or "neows" in lower
    ):

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
            "From project context — live services:\n"
            + "\n".join(wired)
            + "\n\nReference only "
            "(not wired in this MVP):\n"
            + "\n".join(ref)
        )

        return _apply_tone_wrapper(
            text,
            tone,
        )

    if (
        "limit" in lower
        or "uncertain" in lower
    ):

        return _apply_tone_wrapper(
            EXAMPLE_LIMITATIONS,
            tone,
        )

    if any(
        k in lower
        for k in (
            "priorit",
            "immediate",
            "mitigat",
            "evacuat",
            "what should",
        )
    ):

        return _apply_tone_wrapper(
            _human_priorities(
                surface,
                energy_mt,
            ),
            tone,
        )

    if any(
        k in lower
        for k in (
            "how does this project",
            "what is this",
            "architecture",
            "pipeline",
        )
    ):

        return _apply_tone_wrapper(
            PROJECT_OVERVIEW.strip()
            + "\n\n"
            + EXAMPLE_ENGINES
            + "\n\n"
            "I explain the payload; "
            "I never recalculate or override it.",
            tone,
        )

    return _apply_tone_wrapper(
        _panel_summary(context)
        + "\n\n"
        "Ask about a number, a branch choice, "
        "the asteroid ☄️, the place, source modules, "
        "NASA services, or limitations — "
        "I'll answer from the payload first.",
        tone,
    )


# ============================================================
# GEMINI RESPONSE
# ============================================================

def _gemini_reply(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]],
    api_key: str,
    tone: Tone,
) -> str | None:
    """
    Gemini response with native tool calling.

    Gemini can now semantically decide things like:

        "what happened here?"
        "why isn't there a crater?"
        "what was the energy?"
        "what kind of terrain did it hit?"
        "what consequences did we model?"
        "what does the asteroid result mean?"

    It does not need exact keywords.

    The model may call one or more controlled tools.
    """

    grounding = _build_grounding(
        message,
        context,
        tone,
    )

    user_turn = (
        "GROUNDING CONTEXT FOR THIS TURN "
        "(not training; runtime reference only):\n"
        f"{json.dumps(grounding, indent=2)}\n\n"
        "USER QUESTION:\n"
        f"{message}"
    )

    # The frontend history contains the current user message.
    # Remove that latest message because user_turn already contains it.
    prior = [
        {
            "role": m.get(
                "role",
                "user",
            ),
            "content": m.get(
                "content",
                "",
            ),
        }
        for m in history[:-1]
    ]

    try:

        contents = build_chat_contents(
            prior,
            user_turn,
        )

    except Exception:

        contents = user_turn

    tools = _build_gemini_tools(
        context
    )

    # Strengthen the runtime instruction without replacing
    # the project's existing system prompt.
    system_instruction = (
        MITIGATION_SYSTEM_PROMPT
        + "\n\n"
        "TOOL-USAGE RULES:\n"
        "1. You have read-only tools for the current simulation.\n"
        "2. Use tools when the user asks about current-run data.\n"
        "3. Do not guess a numerical value if a tool can provide it.\n"
        "4. Backend simulation output is authoritative.\n"
        "5. Never invent crater, blast, thermal, tsunami, seismic, "
        "energy, coordinate, terrain, or asteroid values.\n"
        "6. If a requested value is absent from the tool result, "
        "say that it is unavailable.\n"
        "7. Distinguish screening models from real-world forecasts.\n"
        "8. You may combine multiple tools when a question spans "
        "impact physics, environment, and consequences.\n"
        "9. Planetary-defence information is educational context, "
        "not an operational mission planner.\n"
        "10. Answer the user's actual question first; do not dump "
        "all available simulation data unless asked."
    )

    return generate_content(
        contents=contents,
        api_key=api_key,
        system_instruction=system_instruction,
        max_output_tokens=2000,
        thinking_level="medium",
        model=GEMINI_MODEL,
        tools=tools,
    )


# ============================================================
# PUBLIC API
# ============================================================

def answer_mitigation(
    *,
    message: str,
    context: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:

    context = _enrich_place(
        context or {}
    )

    history = history or []

    tone = detect_tone(
        message
    )

    surface = _surface_of(
        context
    )

    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    reply = None

    source = "rule_based"

    if api_key:

        reply = _gemini_reply(
            message,
            context,
            history,
            api_key,
            tone,
        )

        if reply:
            source = "gemini"

    if not reply:

        reply = _rule_reply(
            message,
            context,
            tone,
        )

    return {
        "status": "ok",

        "reply": reply,

        "source": source,

        "model": (
            GEMINI_MODEL
            if source == "gemini"
            else None
        ),

        "tone": tone,

        "role": "mission_analyst",

        "immediate_priorities": immediate_priorities(
            surface
        ),

        "surface": surface,

        "place": context.get(
            "place"
        ),

        "matched_explainer": (
            match_explainer(message)
            or {}
        ).get("title"),

        "grounding": {
            "project_knowledge": True,
            "calc_explainers": True,
            "runtime_tools": True,
            "mode": "runtime_context_not_training",
        },

        "knowledge": {
            "engines": list(
                ENGINES.keys()
            ),

            "nasa_wired": [
                k
                for k, v in NASA_SERVICES.items()
                if v.get("used_in_project")
            ],

            "limitations_count": len(
                LIMITATIONS
            ),
        },
    }
