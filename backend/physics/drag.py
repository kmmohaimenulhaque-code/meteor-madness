from __future__ import annotations


def dynamic_pressure(
    density_kg_m3: float,
    velocity_m_s: float,
) -> float:
    """Return aerodynamic dynamic pressure q = 1/2 rho v^2."""

    if density_kg_m3 < 0:
        raise ValueError("density_kg_m3 cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    return 0.5 * density_kg_m3 * velocity_m_s**2


def drag_force(
    density_kg_m3: float,
    velocity_m_s: float,
    projected_area_m2: float,
    drag_coefficient: float,
) -> float:
    """Return aerodynamic drag force."""

    if density_kg_m3 < 0:
        raise ValueError("density_kg_m3 cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    if projected_area_m2 <= 0:
        raise ValueError(
            "projected_area_m2 must be greater than zero"
        )

    if drag_coefficient < 0:
        raise ValueError(
            "drag_coefficient must be non-negative"
        )

    return (
        0.5
        * drag_coefficient
        * density_kg_m3
        * velocity_m_s**2
        * projected_area_m2
    )


def drag_acceleration(
    drag_force_N: float,
    mass_kg: float,
) -> float:
    """Return drag acceleration magnitude."""

    if drag_force_N < 0:
        raise ValueError("drag_force_N cannot be negative")

    if mass_kg <= 0:
        raise ValueError("mass_kg must be greater than zero")

    return drag_force_N / mass_kg


def drag_power(
    drag_force_N: float,
    velocity_m_s: float,
) -> float:
    """Return mechanical power removed by aerodynamic drag."""

    if drag_force_N < 0:
        raise ValueError("drag_force_N cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    return drag_force_N * velocity_m_s
