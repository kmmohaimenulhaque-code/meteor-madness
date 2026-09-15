"""
Impact Environment branch selector.

Land  → crater / blast / thermal
Ocean → water displacement / tsunami / seafloor
Ice   → ice response screening
else  → refuse environment-specific calculation
"""

from __future__ import annotations

from typing import Any

from physics.location_engine import EnvironmentContext
from physics.tsunami import estimate_tsunami


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_land_effects(
    *,
    impact_energy_J: float,
    consequences: dict[str, Any] | None,
) -> dict[str, Any]:
    """Land branch: crater, blast, thermal (reuse existing consequence fields)."""
    consequences = consequences or {}
    largest = consequences.get("largest_crater") or consequences

    crater_m = None
    blast_m = None
    thermal_m = None
    if isinstance(largest, dict):
        crater_m = largest.get("final_crater_diameter_m") or largest.get(
            "transient_crater_diameter_m"
        )
        blast_m = largest.get("blast_radius_m") or consequences.get(
            "maximum_blast_radius_m"
        )
        thermal_m = largest.get("thermal_radius_m") or consequences.get(
            "maximum_thermal_radius_m"
        )

    return {
        "branch": "land",
        "models_run": ["crater", "blast", "thermal"],
        "crater": {
            "final_diameter_m": crater_m,
            "status": "computed" if crater_m is not None else "unavailable",
        },
        "blast": {
            "radius_m": blast_m,
            "status": "computed" if blast_m is not None else "unavailable",
        },
        "thermal": {
            "radius_m": thermal_m,
            "status": "computed" if thermal_m is not None else "unavailable",
        },
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": impact_energy_J / 4.184e15,
    }


def calculate_ocean_effects(
    *,
    impact_energy_J: float,
    environment: EnvironmentContext,
) -> dict[str, Any]:
    """Ocean branch: water displacement, tsunami screening, seafloor effects."""
    depth = environment.bathymetry_m or 4000.0
    tsunami = estimate_tsunami(
        impact_energy_J=impact_energy_J,
        surface_is_ocean=True,
        water_depth_m=float(depth),
    )

    # Very rough displaced water volume proxy (screening only)
    mt = max(impact_energy_J, 0.0) / 4.184e15
    displacement_km3 = 0.02 * (max(mt, 1e-9) ** 0.4)

    seafloor = {
        "water_depth_m": depth,
        "estimated_crater_on_seafloor_m": round(
            80.0 * (max(mt, 1e-9) ** 0.25), 1
        ),
        "status": "screening",
        "notes": [
            "Seafloor crater estimate is order-of-magnitude only.",
            "Depends strongly on water depth and substrate.",
        ],
    }

    return {
        "branch": "ocean",
        "models_run": [
            "water_displacement",
            "tsunami_screening",
            "seafloor_effects",
        ],
        "water_displacement": {
            "estimated_volume_km3": round(displacement_km3, 4),
            "status": "screening",
        },
        "tsunami": tsunami.to_dict(),
        "seafloor_effects": seafloor,
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": mt,
    }


def calculate_ice_effects(
    *,
    impact_energy_J: float,
    environment: EnvironmentContext,
) -> dict[str, Any]:
    """Ice branch: ice response screening (excavation / melt proxy)."""
    mt = max(impact_energy_J, 0.0) / 4.184e15
    # Screening excavation diameter in ice (not a full hydrocode)
    excavation_m = 60.0 * (max(mt, 1e-9) ** 0.28)
    melt_volume_m3 = 5.0e5 * (max(mt, 1e-9) ** 0.5)

    return {
        "branch": "ice",
        "models_run": ["ice_response"],
        "ice_response": {
            "estimated_excavation_diameter_m": round(excavation_m, 1),
            "estimated_melt_volume_m3": round(melt_volume_m3, 1),
            "ice_density_kg_m3": environment.material.density_kg_m3,
            "status": "screening",
            "notes": [
                "Ice response is a transparent screening estimate.",
                "Not a full multi-phase ice / ocean model.",
            ],
        },
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": mt,
    }


def refuse_environment_specific_calculation(
    *,
    surface: str,
    impact_energy_J: float,
) -> dict[str, Any]:
    return {
        "branch": "refused",
        "models_run": [],
        "reason": f"Unknown or unsupported surface type: {surface!r}",
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": impact_energy_J / 4.184e15,
    }


def resolve_impact_environment(
    *,
    environment: EnvironmentContext,
    impact_energy_J: float,
    consequences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Select the physics branch from environment.surface.

    if surface == land  → crater / blast / thermal
    if surface == ocean → displacement / tsunami / seafloor
    if surface == ice   → ice response
    else                → refuse
    """
    energy = _safe_float(impact_energy_J, 0.0)
    surface = environment.surface

    if surface == "land":
        branch = calculate_land_effects(
            impact_energy_J=energy,
            consequences=consequences,
        )
    elif surface == "ocean":
        branch = calculate_ocean_effects(
            impact_energy_J=energy,
            environment=environment,
        )
    elif surface == "ice":
        branch = calculate_ice_effects(
            impact_energy_J=energy,
            environment=environment,
        )
    else:
        branch = refuse_environment_specific_calculation(
            surface=surface,
            impact_energy_J=energy,
        )

    return {
        "environment": environment.to_dict(),
        "impact_branch": branch,
    }
