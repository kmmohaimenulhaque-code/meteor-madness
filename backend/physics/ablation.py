from __future__ import annotations


def heating_rate(
    density_kg_m3: float,
    velocity_m_s: float,
    projected_area_m2: float,
    heat_transfer_coefficient: float,
) -> float:
    """Return aerodynamic heating rate in watts."""

    if density_kg_m3 < 0:
        raise ValueError("density_kg_m3 cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    if projected_area_m2 <= 0:
        raise ValueError(
            "projected_area_m2 must be greater than zero"
        )

    if heat_transfer_coefficient < 0:
        raise ValueError(
            "heat_transfer_coefficient must be non-negative"
        )

    return (
        0.5
        * heat_transfer_coefficient
        * density_kg_m3
        * velocity_m_s**3
        * projected_area_m2
    )


def mass_loss_rate(
    heating_rate_W: float,
    effective_heat_of_ablation_J_kg: float,
) -> float:
    """Return mass-loss rate magnitude in kg/s."""

    if heating_rate_W < 0:
        raise ValueError("heating_rate_W cannot be negative")

    if effective_heat_of_ablation_J_kg <= 0:
        raise ValueError(
            "effective_heat_of_ablation_J_kg must be greater than zero"
        )

    return heating_rate_W / effective_heat_of_ablation_J_kg


def ablation_mass_derivative(
    density_kg_m3: float,
    velocity_m_s: float,
    projected_area_m2: float,
    heat_transfer_coefficient: float,
    effective_heat_of_ablation_J_kg: float,
) -> float:
    """Return dm/dt for the effective ablation model."""

    heating = heating_rate(
        density_kg_m3=density_kg_m3,
        velocity_m_s=velocity_m_s,
        projected_area_m2=projected_area_m2,
        heat_transfer_coefficient=heat_transfer_coefficient,
    )

    return -mass_loss_rate(
        heating_rate_W=heating,
        effective_heat_of_ablation_J_kg=effective_heat_of_ablation_J_kg,
    )
