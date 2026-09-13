
from __future__ import annotations

from dataclasses import dataclass

from physics.fragmentation import Fragment


@dataclass(frozen=True)
class FragmentState:
    """State of one atmospheric fragment."""

    altitude_m: float
    velocity_m_s: float
    mass_kg: float


@dataclass(frozen=True)
class FragmentOutcome:
    """Final outcome of one fragment."""

    outcome: str
    altitude_m: float
    velocity_m_s: float
    mass_kg: float
    kinetic_energy_J: float


def fragment_kinetic_energy(
    mass_kg: float,
    velocity_m_s: float,
) -> float:
    """Return kinetic energy of a fragment."""

    if mass_kg < 0:
        raise ValueError("mass_kg cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    return 0.5 * mass_kg * velocity_m_s**2


def initial_fragment_states(
    fragments: tuple[Fragment, ...],
    altitude_m: float,
) -> tuple[FragmentState, ...]:
    """Create atmospheric states immediately after breakup."""

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    return tuple(
        FragmentState(
            altitude_m=altitude_m,
            velocity_m_s=fragment.velocity_m_s,
            mass_kg=fragment.mass_kg,
        )
        for fragment in fragments
    )


def classify_fragment_outcome(
    altitude_m: float,
    velocity_m_s: float,
    mass_kg: float,
) -> FragmentOutcome:
    """
    Classify a fragment at the end of its tracked trajectory.

    This function intentionally does not claim to model detailed
    crater formation or ground damage.
    """

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    if mass_kg < 0:
        raise ValueError("mass_kg cannot be negative")

    if mass_kg == 0:
        outcome = "complete_ablation"
    elif altitude_m <= 0:
        outcome = "ground_impact"
    else:
        outcome = "airborne_fragment"

    return FragmentOutcome(
        outcome=outcome,
        altitude_m=altitude_m,
        velocity_m_s=velocity_m_s,
        mass_kg=mass_kg,
        kinetic_energy_J=fragment_kinetic_energy(
            mass_kg=mass_kg,
            velocity_m_s=velocity_m_s,
        ),
    )

