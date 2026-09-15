"""
How-each-calculation-works explainers.

Maps user topics → plain-language physics + concrete source files in this branch.
"""
from __future__ import annotations

from typing import Any

# topic keyword groups → explainer payloads
EXPLAINERS: dict[str, dict[str, Any]] = {
    "entry": {
        "title": "Atmospheric entry (RK4)",
        "files": [
            "backend/physics/solver.py",
            "backend/physics/atmosphere.py",
            "backend/physics/models.py",
        ],
        "body": (
            "The entry engine steps the meteoroid through the atmosphere with a "
            "classical RK4 integrator. At each step it updates velocity and mass from "
            "drag and ablation, can drop the flight-path angle, and may trigger "
            "fragmentation when dynamic pressure exceeds a strength threshold. Energy "
            "deposited along the path is tracked so airburst vs ground-impact outcomes "
            "fall out naturally.\n\n"
            "This is engineering screening physics — not a full hydrocode or radiative "
            "transfer model. Strength, density, and ablation coefficients carry large "
            "uncertainty, which is why the AI panel keeps confidence honest."
        ),
    },
    "environment": {
        "title": "Environment / GEBCO lookup",
        "files": [
            "backend/physics/location_engine.py",
            "backend/physics/place_lookup.py",
        ],
        "body": (
            "Coordinates go to OpenTopoData’s GEBCO 2020 dataset. Positive elevation "
            "→ land; negative → ocean (bathymetry = |elevation|). Material density is "
            "attached only after that classification. If the provider fails or returns "
            "null, surface becomes unknown with confidence 0 — and we refuse to invent "
            "crater or tsunami numbers.\n\n"
            "Place names (city/region/country) come from a separate Nominatim reverse "
            "geocode so Mitigation+ can say where the point is without guessing."
        ),
    },
    "branch": {
        "title": "Land / ocean / ice / unknown branching",
        "files": [
            "backend/physics/impact_environment.py",
            "backend/physics/enrichment.py",
        ],
        "body": (
            "After environment class is known, `resolve_impact_environment` picks one "
            "branch only:\n"
            "• land → crater, blast, thermal (and land consequences panel)\n"
            "• ocean → water displacement, tsunami screening, seafloor effects\n"
            "• ice → ice-response screening\n"
            "• unknown → models_run empty, refused=true\n\n"
            "That hierarchy is why an ocean run never shows a land crater next to a "
            "tsunami message — the frontend gates legacy consequences on branch=land."
        ),
    },
    "crater": {
        "title": "Crater / blast / thermal / seismic scaling",
        "files": [
            "backend/physics/consequences.py",
            "backend/physics/impact_environment.py",
        ],
        "body": (
            "On the land branch only, impact energy is mapped through first-order "
            "terrestrial crater scaling (transient → final diameter, depth) plus "
            "screening radii for thermal, blast, and seismic effects. Earthquake "
            "magnitude is an equivalent-energy sketch, not a seismic hazard model.\n\n"
            "If the branch is ocean or unknown, these functions are not applied to the "
            "user-facing environment story — by design."
        ),
    },
    "tsunami": {
        "title": "Tsunami screening",
        "files": [
            "backend/physics/tsunami.py",
            "backend/physics/impact_environment.py",
        ],
        "body": (
            "Ocean impacts feed impact energy and water depth into an energy-scaling "
            "tsunami screen: source amplitude and a coarse coastal run-up indicator. "
            "It is not a hydrodynamic inundation forecast and must not be treated as "
            "one. Without observed ocean environment (or with unknown surface), tsunami "
            "calculation is refused."
        ),
    },
    "analyst": {
        "title": "AI Analyst report",
        "files": [
            "backend/physics/ai_analyst.py",
            "backend/physics/enrichment.py",
        ],
        "body": (
            "The analyst turns outcome, surface, energy, fragmentation, and terrain "
            "confidence into risk level, summary, findings, limitations, and actions. "
            "If GEMINI_API_KEY is set it prefers Gemini; otherwise a transparent "
            "rule-based path keeps demos offline-safe. It narrates physics — it does "
            "not override the land/ocean branch decision."
        ),
    },
    "mitigation": {
        "title": "Mitigation+ chat",
        "files": [
            "backend/physics/mitigation_chat.py",
            "backend/physics/project_knowledge.py",
            "backend/physics/calc_explainers.py",
            "backend/mitigation_routes.py",
        ],
        "body": (
            "This chat adapts tone to the question, pulls full run context (asteroid, "
            "panel, place), and can explain calculations by pointing at the modules "
            "above. Planetary-defence priorities stay screening-level and "
            "environment-aware."
        ),
    },
    "nasa": {
        "title": "NASA / Earth data inputs",
        "files": [
            "backend/nasa_client.py",
            "backend/physics/location_engine.py",
        ],
        "body": (
            "Live wires: NASA NeoWs for the asteroid feed (diameter, velocity, miss "
            "distance, PHA, approach date) via NASA_API_KEY, and GEBCO through "
            "OpenTopoData for elevation/bathymetry. Horizons, Sentry, Fireballs, and "
            "Earthdata are reference context — explained, not called, in this MVP."
        ),
    },
}


def match_explainer(message: str) -> dict[str, Any] | None:
    lower = (message or "").lower()

    checks: list[tuple[str, tuple[str, ...]]] = [
        ("tsunami", ("tsunami", "run-up", "runup", "coastal wave")),
        ("crater", ("crater", "blast radius", "thermal radius", "seismic", "mw")),
        ("entry", ("entry", "rk4", "ablation", "fragment", "drag", "atmospheric solver")),
        ("environment", ("gebco", "elevation", "bathym", "environment engine", "terrain")),
        ("branch", ("branch", "land vs", "ocean vs", "why land", "why ocean", "hierarchy")),
        ("analyst", ("analyst", "risk level", "ai report", "confidence label")),
        ("mitigation", ("mitigation+", "this chat", "how do you work")),
        ("nasa", ("neows", "nasa api", "horizons", "sentry")),
    ]

    how_calc = any(
        k in lower
        for k in (
            "how does",
            "how do",
            "how is",
            "how are",
            "how we",
            "calculate",
            "calculation",
            "computed",
            "formula",
            "source code",
            "which file",
            "what module",
            "explain the",
            "walk me through",
        )
    )

    for key, needles in checks:
        if any(n in lower for n in needles) and (
            how_calc or "explain" in lower or "work" in lower or "source" in lower
        ):
            return EXPLAINERS[key]

    # broader "how does X work" without strong keyword → entry/pipeline
    if how_calc and any(
        k in lower for k in ("simulation", "physics", "model", "engine", "pipeline")
    ):
        return {
            "title": "End-to-end calculation path",
            "files": [
                "backend/main.py",
                "backend/physics/solver.py",
                "backend/physics/location_engine.py",
                "backend/physics/impact_environment.py",
                "backend/physics/enrichment.py",
            ],
            "body": (
                "Request hits FastAPI → NeoWs resolves the asteroid → entry RK4 runs → "
                "GEBCO classifies the surface → impact_environment selects land/ocean/ice/"
                "unknown → enrichment builds the unified report and AI analyst payload → "
                "React renders only the branch that applies.\n\n"
                "Ask about a specific step (entry, crater, tsunami, GEBCO) and I’ll point "
                "at the exact file and what it assumes."
            ),
        }

    if how_calc:
        # default gentle pointer
        return {
            "title": "Where the math lives",
            "files": ["backend/physics/"],
            "body": (
                "Almost every calculation sits under `backend/physics/`. Entry is "
                "`solver.py`, environment is `location_engine.py`, branching is "
                "`impact_environment.py`, land scaling is `consequences.py`, tsunami is "
                "`tsunami.py`. Tell me which number on the panel you care about and I’ll "
                "open that path specifically."
            ),
        }

    return None


def format_explainer(explainer: dict[str, Any]) -> str:
    files = explainer.get("files") or []
    file_lines = "\n".join(f"• `{f}`" for f in files)
    return (
        f"**{explainer.get('title', 'Calculation')}**\n\n"
        f"{explainer.get('body', '').strip()}\n\n"
        f"Source in this branch:\n{file_lines}"
    )
