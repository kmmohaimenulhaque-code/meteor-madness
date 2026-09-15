"""
Impact Environment branch selector.

Land  → crater / blast / thermal
Ocean → water displacement / tsunami / seafloor
Ice   → ice response screening
unknown / undetermined → REFUSE (no manufactured crater or tsunami)
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
    depth = environment.bathymetry_m
    if depth is None or depth <= 0:
        # Observed ocean without usable depth → still screen tsunami but flag
        depth = 4000.0
        depth_status = "assumed_default_depth"
    else:
        depth_status = "observed"

    tsunami = estimate_tsunami(
        impact_energy_J=impact_energy_J,
        surface_is_ocean=True,
        water_depth_m=float(depth),
    )

    mt = max(impact_energy_J, 0.0) / 4.184e15
    displacement_km3 = 0.02 * (max(mt, 1e-9) ** 0.4)

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
        "seafloor_effects": {
            "water_depth_m": depth,
            "depth_status": depth_status,
            "estimated_crater_on_seafloor_m": round(
                80.0 * (max(mt, 1e-9) ** 0.25), 1
            ),
            "status": "screening",
            "notes": [
                "Seafloor crater estimate is order-of-magnitude only.",
            ],
        },
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": mt,
    }


def calculate_ice_effects(
    *,
    impact_energy_J: float,
    environment: EnvironmentContext,
) -> dict[str, Any]:
    mt = max(impact_energy_J, 0.0) / 4.184e15
    excavation_m = 60.0 * (max(mt, 1e-9) ** 0.28)
    melt_volume_m3 = 5.0e5 * (max(mt, 1e-9) ** 0.5)
    density = (
        environment.material.density_kg_m3
        if environment.material
        else 917.0
    )

    return {
        "branch": "ice",
        "models_run": ["ice_response"],
        "ice_response": {
            "estimated_excavation_diameter_m": round(excavation_m, 1),
            "estimated_melt_volume_m3": round(melt_volume_m3, 1),
            "ice_density_kg_m3": density,
            "status": "screening",
            "notes": [
                "Ice response is a transparent screening estimate.",
            ],
        },
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": mt,
    }


def refuse_environment_specific_calculation(
    *,
    surface: str,
    impact_energy_J: float,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "branch": "undetermined",
        "physics_branch": "undetermined",
        "models_run": [],
        "refused": True,
        "reason": reason
        or (
            f"No observed environment data for surface={surface!r}. "
            "Crater and tsunami calculations are refused."
        ),
        "impact_energy_J": impact_energy_J,
        "impact_energy_megatons_tnt": impact_energy_J / 4.184e15,
        "crater": None,
        "tsunami": None,
    }


def resolve_impact_environment(
    *,
    environment: EnvironmentContext,
    impact_energy_J: float,
    consequences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Select physics branch from observed environment only.

    if surface == land  → crater / blast / thermal
    if surface == ocean → displacement / tsunami / seafloor
    if surface == ice   → ice response
    else                → refuse (undetermined)
    """
    energy = _safe_float(impact_energy_J, 0.0)
    surface = environment.surface
    branch_hint = environment.physics_branch

    if surface == "unknown" or branch_hint == "undetermined":
        branch = refuse_environment_specific_calculation(
            surface=surface,
            impact_energy_J=energy,
            reason=(
                "Earth-data provider unavailable or returned no elevation. "
                "Simulator will not invent crater or tsunami results."
            ),
        )
    elif surface == "land":
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
