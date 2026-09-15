"""
Project knowledge base for the interactive Mitigation+ AI.

Summarises architecture, engines, NASA services, and limitations
so the assistant can explain the system without inventing behaviour.
"""
from __future__ import annotations

PROJECT_OVERVIEW = """
Meteor Madness (NASA Space Apps — The Next Frontier) is an educational
asteroid atmospheric-entry and impact-screening simulator.

Strict pipeline:
  NASA NeoWs → Asteroid parameters → Entry Physics (RK4) → Impact State
  → Earth Environment (GEBCO via OpenTopoData) → Environment Class
  → LAND | OCEAN | ICE | UNKNOWN physics branch
  → Unified Impact Report → AI Analyst → Mitigation+ interactive assistant

Rule: No Earth-environment data ⇒ no invented crater or tsunami.
"""

ENGINES = {
    "entry_physics": {
        "module": "backend/physics/solver.py",
        "role": "RK4 atmospheric entry: drag, ablation, dynamic flight-path angle, fragmentation, energy deposition",
        "inputs": "diameter, density, velocity, entry angle, material strength, ablation parameters",
        "outputs": "altitude/velocity/mass profiles, fragmentation events, impact or airburst outcome",
    },
    "environment_engine": {
        "module": "backend/physics/location_engine.py",
        "role": "Live elevation/bathymetry lookup (OpenTopoData GEBCO 2020); classifies land vs ocean",
        "rule": "Provider failure → surface=unknown, confidence=0, physics refused",
        "source": "api.opentopodata.org/v1/gebco2020",
    },
    "impact_environment": {
        "module": "backend/physics/impact_environment.py",
        "role": "Branch selector: land crater/blast/thermal; ocean displacement/tsunami/seafloor; ice response; unknown refuses",
    },
    "consequences": {
        "module": "backend/physics/consequences.py",
        "role": "Land screening: crater scaling, thermal, blast, seismic radii",
        "note": "Only used on LAND branch; never mixed into ocean UI",
    },
    "tsunami": {
        "module": "backend/physics/tsunami.py",
        "role": "Energy-scaling tsunami screening for ocean impacts only",
    },
    "ai_analyst": {
        "module": "backend/physics/ai_analyst.py",
        "role": "Risk summary via Gemini (if GEMINI_API_KEY) or rule-based fallback",
    },
    "mitigation_chat": {
        "module": "backend/physics/mitigation_chat.py",
        "role": "Interactive planetary-defence mitigation dialogue with simulation context",
    },
    "enrichment": {
        "module": "backend/physics/enrichment.py",
        "role": "Builds hierarchical unified_report and attaches environment + analyst",
    },
    "nasa_client": {
        "module": "backend/nasa_client.py",
        "role": "Fetches near-Earth objects from NASA NeoWs",
    },
}

NASA_SERVICES = {
    "NeoWs": {
        "name": "Near Earth Object Web Service",
        "url": "https://api.nasa.gov/neo/rest/v1",
        "used_in_project": True,
        "purpose": "Live asteroid feed: diameter, velocity, miss distance, hazardous flag, close-approach date",
        "auth": "NASA_API_KEY (api.nasa.gov)",
        "docs": "https://api.nasa.gov/",
    },
    "OpenTopoData_GEBCO": {
        "name": "OpenTopoData GEBCO 2020",
        "url": "https://api.opentopodata.org/v1/gebco2020",
        "used_in_project": True,
        "purpose": "Global elevation and bathymetry for land/ocean classification",
        "auth": "None (public rate limits apply)",
        "docs": "https://www.opentopodata.org/",
    },
    "SSD_JPL_Horizons": {
        "name": "JPL Horizons",
        "url": "https://ssd.jpl.nasa.gov/horizons/",
        "used_in_project": False,
        "purpose": "High-precision ephemerides; not wired in this demo",
        "note": "Could refine approach geometry beyond NeoWs close-approach summary",
    },
    "CNEOS_Sentry": {
        "name": "CNEOS Sentry",
        "url": "https://cneos.jpl.nasa.gov/sentry/",
        "used_in_project": False,
        "purpose": "Impact monitoring and Palermo/Torino scale risk tables",
        "note": "Reference for real threat process; not an API dependency here",
    },
    "CNEOS_Fireballs": {
        "name": "CNEOS Fireballs",
        "url": "https://cneos.jpl.nasa.gov/fireballs/",
        "used_in_project": False,
        "purpose": "Observed bolide energy and location archive",
    },
    "Earthdata": {
        "name": "NASA Earthdata",
        "url": "https://www.earthdata.nasa.gov/",
        "used_in_project": False,
        "purpose": "Land cover, DEM, ocean products for higher-fidelity environment",
    },
    "DONKI": {
        "name": "Space Weather Database Of Notifications, Knowledge, Information",
        "url": "https://api.nasa.gov/DONKI",
        "used_in_project": False,
        "purpose": "Space weather events — out of scope for asteroid entry screening",
    },
}

LIMITATIONS = [
    "Entry model is engineering RK4 screening, not full hydrocode or radiative transfer.",
    "Material strength, density, and ablation parameters are highly uncertain.",
    "GEBCO lookup can fail (rate limit / network) → surface unknown and environment physics refused.",
    "Tsunami amplitudes are energy-scaling estimates, not hydrodynamic coastal forecasts.",
    "Crater / blast / thermal / seismic numbers are first-order terrestrial scaling only.",
    "NeoWs provides close-approach summary, not a full impact orbit redesign.",
    "Gemini analyst/mitigation replies are advisory; never operational emergency authority.",
    "No casualty, insurance, or legal conclusions should be drawn from demo outputs.",
]

HOWTO_ASK = [
    "How does the entry physics engine work?",
    "What NASA services does this project use?",
    "Why is there no crater on an ocean impact?",
    "What are the immediate mitigation priorities?",
    "What are the project limitations?",
    "Explain the environment engine and GEBCO.",
    "What happens when surface is unknown?",
]


def knowledge_bundle() -> dict:
    return {
        "project_overview": PROJECT_OVERVIEW.strip(),
        "engines": ENGINES,
        "nasa_services": NASA_SERVICES,
        "limitations": LIMITATIONS,
        "suggested_questions": HOWTO_ASK,
    }
