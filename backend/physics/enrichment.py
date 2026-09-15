"""Next Frontier response enrichment (terrain, tsunami, AI analyst)."""
from __future__ import annotations
from typing import Any

from physics.location_engine import classify_surface
from physics.tsunami import estimate_tsunami
from physics.ai_analyst import generate_analyst_report
from physics.models import ImpactScenario


def enrich_payload(
    *,
    scenario: ImpactScenario,
    simulation_response: Any,
) -> dict[str, Any]:
    """Attach terrain, tsunami, and analyst fields to a simulation payload."""
    terrain = classify_surface(
        latitude_deg=scenario.latitude_deg,
        longitude_deg=scenario.longitude_deg,
        surface_hint=getattr(scenario, "surface_hint", None),
    )

    energy_for_secondary = (
        getattr(simulation_response, "impact_energy_J", None)
        or getattr(simulation_response, "parent_final_energy_J", None)
        or 0.0
    )

    tsunami = estimate_tsunami(
        impact_energy_J=float(energy_for_secondary or 0.0),
        surface_is_ocean=(terrain.surface_type == "ocean"),
    )

    consequences = getattr(simulation_response, "consequences", None) or {}
    crater_diameter = None
    if isinstance(consequences, dict):
        largest = consequences.get("largest_crater") or consequences
        if isinstance(largest, dict):
            crater_diameter = largest.get("final_crater_diameter_m")

    analyst = generate_analyst_report(
        outcome=str(getattr(simulation_response, "outcome", "completed")),
        surface_type=terrain.surface_type,
        impact_energy_J=float(energy_for_secondary or 0.0),
        impact_energy_mt=float(energy_for_secondary or 0.0) / 4.184e15,
        fragmentation_detected=bool(
            getattr(simulation_response, "fragmentation_detected", False)
        ),
        terrain_confidence=terrain.confidence,
        has_tsunami=tsunami.applicable,
        tsunami_amplitude_m=(
            tsunami.estimated_source_amplitude_m if tsunami.applicable else None
        ),
        crater_diameter_m=crater_diameter,
        atmospheric_fraction=getattr(
            simulation_response, "atmospheric_fraction", None
        ),
    )

    return {
        "terrain": {
            "surface_type": terrain.surface_type,
            "target_density_kg_m3": terrain.target_density_kg_m3,
            "terrain_label": terrain.terrain_label,
            "material_notes": terrain.material_notes,
            "confidence": terrain.confidence,
        },
        "tsunami": tsunami.to_dict(),
        "analyst": analyst.to_dict(),
    }
