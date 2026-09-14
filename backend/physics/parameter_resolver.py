from __future__ import annotations

from dataclasses import dataclass

from physics.models import AsteroidParameters, EntryConditions


@dataclass(frozen=True)
class ResolvedAsteroid:
    asteroid_id: str
    name: str
    hazardous: bool

    asteroid: AsteroidParameters
    entry: EntryConditions

    assumptions: dict[str, str]


def resolve_neo_to_physics(neo: dict) -> ResolvedAsteroid:
    """
    Convert NASA NeoWs data into the inputs required by the
    Meteor Madness physics engine.

    NeoWs does not provide every physical parameter required by
    our simplified atmospheric-entry model, so missing values
    are explicit engineering assumptions.
    """

    diameter_km = neo["diameter_km"]
    velocity_kph = neo["velocity_kph"]

    if diameter_km is None:
        raise ValueError("NASA asteroid is missing diameter data")

    if velocity_kph is None:
        raise ValueError("NASA asteroid is missing velocity data")

    diameter_m = float(diameter_km) * 1000.0
    velocity_m_s = float(velocity_kph) / 3.6

    # Explicit V0.1 engineering assumptions.
    bulk_density_kg_m3 = 3500.0
    drag_coefficient = 1.0
    heat_transfer_coefficient = 0.1
    effective_heat_of_ablation_J_kg = 8.0e6
    material_strength_Pa = 1.0e6
    shape_factor = 1.0

    asteroid = AsteroidParameters(
        diameter_m=diameter_m,
        bulk_density_kg_m3=bulk_density_kg_m3,
        drag_coefficient=drag_coefficient,
        heat_transfer_coefficient=heat_transfer_coefficient,
        effective_heat_of_ablation_J_kg=effective_heat_of_ablation_J_kg,
        material_strength_Pa=material_strength_Pa,
        shape_factor=shape_factor,
    )

    entry = EntryConditions(
        initial_altitude_m=80_000.0,
        initial_velocity_m_s=velocity_m_s,
        entry_angle_rad=0.7853981633974483,
    )

    assumptions = {
        "bulk_density_kg_m3": "Engineering assumption; not provided by NeoWs.",
        "drag_coefficient": "Engineering assumption for V0.1.",
        "heat_transfer_coefficient": "Engineering assumption for V0.1.",
        "effective_heat_of_ablation_J_kg": (
            "Engineering assumption; material-dependent."
        ),
        "material_strength_Pa": (
            "Engineering assumption; actual asteroid strength is uncertain."
        ),
        "shape_factor": "Assumed spherical/projected-area factor for V0.1.",
        "entry_angle_rad": "Assumed 45 degrees for V0.1.",
        "initial_altitude_m": (
            "Simulation boundary assumption; not supplied by NeoWs."
        ),
    }

    return ResolvedAsteroid(
        asteroid_id=str(neo["id"]),
        name=neo.get("name", "Unknown"),
        hazardous=bool(neo.get("hazardous", False)),
        asteroid=asteroid,
        entry=entry,
        assumptions=assumptions,
    )
