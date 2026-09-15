"""
Next Frontier hierarchical enrichment.

NASA → Asteroid → Entry Physics → Impact State → Earth Environment
  → Environment Class (LAND | OCEAN | ICE | UNKNOWN)
  → Environment-specific physics only
  → Unified Impact Report → AI Analyst
"""
from __future__ import annotations

from typing import Any

from physics.ai_analyst import generate_analyst_report
from physics.impact_environment import resolve_impact_environment
from physics.location_engine import classify_surface
from physics.models import ImpactScenario


def enrich_payload(
    *,
    scenario: ImpactScenario,
    simulation_response: Any,
) -> dict[str, Any]:
    """Attach hierarchical environment report. Never mix land crater with ocean."""
    environment = classify_surface(
        latitude_deg=scenario.latitude_deg,
        longitude_deg=scenario.longitude_deg,
        surface_hint=getattr(scenario, "surface_hint", None),
    )

    energy_for_secondary = (
        getattr(simulation_response, "impact_energy_J", None)
        or getattr(simulation_response, "parent_final_energy_J", None)
        or getattr(simulation_response, "ground_impact_energy_J", None)
        or 0.0
    )
    energy_for_secondary = float(energy_for_secondary or 0.0)

    raw_consequences = getattr(simulation_response, "consequences", None) or {}
    if not isinstance(raw_consequences, dict):
        raw_consequences = {}

    # Land-only inputs to land branch. Ocean/ice/unknown never see crater scaling.
    consequences_for_branch = (
        raw_consequences if environment.surface == "land" else None
    )

    resolved = resolve_impact_environment(
        environment=environment,
        impact_energy_J=energy_for_secondary,
        consequences=consequences_for_branch,
    )

    impact_branch = resolved["impact_branch"]
    env_dict = resolved["environment"]
    branch_name = impact_branch.get("branch", "undetermined")

    # Hierarchical effect blocks — only one is populated
    land_effects = impact_branch if branch_name == "land" else None
    ocean_effects = impact_branch if branch_name == "ocean" else None
    ice_effects = impact_branch if branch_name == "ice" else None

    tsunami = None
    if branch_name == "ocean":
        tsunami = impact_branch.get("tsunami")
    else:
        tsunami = {
            "applicable": False,
            "refused": branch_name in ("undetermined", "land", "ice"),
            "impact_energy_J": energy_for_secondary,
            "impact_energy_megatons_tnt": energy_for_secondary / 4.184e15,
            "estimated_source_amplitude_m": 0.0,
            "estimated_coastal_runup_indicator_m": 0.0,
            "notes": [
                "Tsunami only runs on the OCEAN branch with observed environment."
            ],
        }

    crater_diameter = None
    if branch_name == "land" and land_effects:
        crater = land_effects.get("crater") or {}
        crater_diameter = crater.get("final_diameter_m")

    has_tsunami = bool(tsunami and tsunami.get("applicable"))

    analyst = generate_analyst_report(
        outcome=str(getattr(simulation_response, "outcome", "completed")),
        surface_type=environment.surface,
        impact_energy_J=energy_for_secondary,
        impact_energy_mt=energy_for_secondary / 4.184e15,
        fragmentation_detected=bool(
            getattr(simulation_response, "fragmentation_detected", False)
        ),
        terrain_confidence=environment.surface_confidence,
        has_tsunami=has_tsunami,
        tsunami_amplitude_m=(
            tsunami.get("estimated_source_amplitude_m") if has_tsunami else None
        ),
        crater_diameter_m=crater_diameter,
        atmospheric_fraction=getattr(
            simulation_response, "atmospheric_fraction", None
        ),
    )

    entry_physics = {
        "outcome": getattr(simulation_response, "outcome", None),
        "fragmentation_detected": getattr(
            simulation_response, "fragmentation_detected", False
        ),
        "fragmentation_altitude_m": getattr(
            simulation_response, "fragmentation_altitude_m", None
        ),
        "atmospheric_fraction": getattr(
            simulation_response, "atmospheric_fraction", None
        ),
        "impact_energy_J": energy_for_secondary,
        "impact_energy_megatons_tnt": energy_for_secondary / 4.184e15,
        "parent_final_mass_kg": getattr(
            simulation_response, "parent_final_mass_kg", None
        ),
        "parent_final_velocity_m_s": getattr(
            simulation_response, "parent_final_velocity_m_s", None
        ),
    }

    unified_report = {
        "architecture": [
            "NASA",
            "Asteroid",
            "Entry Physics",
            "Impact State",
            "Earth Environment",
            "Environment Class",
            "Environment-specific Physics",
            "Unified Impact Report",
            "AI Analyst",
        ],
        "environment_class": environment.surface,
        "physics_branch": branch_name,
        "entry_physics": entry_physics,
        "environment": env_dict,
        "land_effects": land_effects,
        "ocean_effects": ocean_effects,
        "ice_effects": ice_effects,
        # Legacy land consequences ONLY when land branch is active
        "land_consequences": (
            raw_consequences if branch_name == "land" else None
        ),
    }

    return {
        "environment": env_dict,
        "impact_branch": impact_branch,
        "terrain": env_dict,
        "tsunami": tsunami,
        "unified_report": unified_report,
        "analyst": analyst.to_dict(),
        # Explicit flag for UI: never render land crater panel off-land
        "show_land_consequences": branch_name == "land",
    }
