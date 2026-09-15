"""Next Frontier response enrichment (environment, impact branch, AI analyst)."""
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
    """Attach environment, impact_branch, tsunami, and analyst fields."""
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

    consequences = getattr(simulation_response, "consequences", None) or {}
    if not isinstance(consequences, dict):
        consequences = {}

    # If environment is unknown, strip land-specific consequences so we
    # do not present manufactured crater/blast numbers as environment truth.
    consequences_for_branch = consequences
    if environment.surface == "unknown":
        consequences_for_branch = None

    resolved = resolve_impact_environment(
        environment=environment,
        impact_energy_J=energy_for_secondary,
        consequences=consequences_for_branch,
    )

    impact_branch = resolved["impact_branch"]
    env_dict = resolved["environment"]

    tsunami = None
    if impact_branch.get("branch") == "ocean":
        tsunami = impact_branch.get("tsunami")
    else:
        tsunami = {
            "applicable": False,
            "refused": impact_branch.get("branch") == "undetermined",
            "impact_energy_J": energy_for_secondary,
            "impact_energy_megatons_tnt": energy_for_secondary / 4.184e15,
            "estimated_source_amplitude_m": 0.0,
            "estimated_coastal_runup_indicator_m": 0.0,
            "notes": [
                "Tsunami not computed: surface is not an observed ocean, "
                "or environment data is unavailable."
            ],
        }

    crater_diameter = None
    if environment.surface == "land" and isinstance(consequences, dict):
        largest = consequences.get("largest_crater") or consequences
        if isinstance(largest, dict):
            crater_diameter = largest.get("final_crater_diameter_m")

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

    return {
        "environment": env_dict,
        "impact_branch": impact_branch,
        "terrain": env_dict,
        "tsunami": tsunami,
        "analyst": analyst.to_dict(),
    }
