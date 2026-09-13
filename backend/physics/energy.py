from __future__ import annotations


def kinetic_energy(
    mass_kg: float,
    velocity_m_s: float,
) -> float:
    """Return translational kinetic energy in joules."""

    if mass_kg < 0:
        raise ValueError("mass_kg cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    return 0.5 * mass_kg * velocity_m_s**2


def drag_energy_rate(
    drag_force_N: float,
    velocity_m_s: float,
) -> float:
    """Return mechanical energy removal rate due to drag."""

    if drag_force_N < 0: 
        raise ValueError("drag_force_N cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    return drag_force_N * velocity_m_s
