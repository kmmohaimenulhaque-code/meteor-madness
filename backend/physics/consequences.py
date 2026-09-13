from __future__ import annotations

from dataclasses import dataclass

from physics.energy import kinetic_energy


@dataclass(frozen=True)
class ImpactConsequences:
    """Energy consequences of a surviving fragment."""

    outcome: str
    surviving_mass_kg: float
    impact_velocity_m_s: float
    impact_energy_J: float


def calculate_impact_consequences(
    outcome: str,
    mass_kg: float,
    velocity_m_s: float,
) -> ImpactConsequences:
    """Calculate the kinetic energy remaining when a fragment finishes."""

    if mass_kg < 0:
        raise ValueError("mass_kg cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    if not outcome:
        raise ValueError("outcome cannot be empty")

    impact_energy = kinetic_energy(
        mass_kg=mass_kg,
        velocity_m_s=velocity_m_s,
    )

    return ImpactConsequences(
        outcome=outcome,
        surviving_mass_kg=mass_kg,
        impact_velocity_m_s=velocity_m_s,
        impact_energy_J=impact_energy,
    )
