
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fragment:
    """A fragment produced by breakup of the parent body."""

    mass_kg: float
    velocity_m_s: float


def fragmentation_pressure(
    density_kg_m3: float,
    velocity_m_s: float,
) -> float:
    """Return dynamic pressure."""

    if density_kg_m3 < 0:
        raise ValueError("density_kg_m3 cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    return 0.5 * density_kg_m3 * velocity_m_s**2


def fragmentation_triggered(
    dynamic_pressure_Pa: float,
    material_strength_Pa: float,
) -> bool:
    """Return True when dynamic pressure reaches material strength."""

    if dynamic_pressure_Pa < 0:
        raise ValueError("dynamic_pressure_Pa cannot be negative")

    if material_strength_Pa <= 0:
        raise ValueError("material_strength_Pa must be greater than zero")

    return dynamic_pressure_Pa >= material_strength_Pa


def split_mass(
    mass_kg: float,
    fractions: tuple[float, ...] = (0.6, 0.4),
) -> tuple[float, ...]:
    """Split parent mass into fragments while conserving total mass."""

    if mass_kg <= 0:
        raise ValueError("mass_kg must be greater than zero")

    if not fractions:
        raise ValueError("fractions cannot be empty")

    if any(f <= 0 for f in fractions):
        raise ValueError("fragment fractions must be positive")

    total = sum(fractions)

    return tuple(
        mass_kg * fraction / total
        for fraction in fractions
    )


def create_fragments(
    mass_kg: float,
    velocity_m_s: float,
    fractions: tuple[float, ...] = (0.6, 0.4),
) -> tuple[Fragment, ...]:
    """
    Create fragments with the parent's velocity.

    Equal velocity means linear momentum and kinetic energy
    remain conserved at the instant of idealized breakup.
    """

    masses = split_mass(
        mass_kg=mass_kg,
        fractions=fractions,
    )

    return tuple(
        Fragment(
            mass_kg=fragment_mass,
            velocity_m_s=velocity_m_s,
        )
        for fragment_mass in masses
    )

