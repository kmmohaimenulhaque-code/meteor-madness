import math

import pytest

from physics.ablation import (
    ablation_mass_derivative,
    heating_rate,
    mass_loss_rate,
)


def test_heating_rate():
    heating = heating_rate(
        density_kg_m3=1.0,
        velocity_m_s=10.0,
        projected_area_m2=2.0,
        heat_transfer_coefficient=1.0,
    )

    assert math.isclose(heating, 1000.0)


def test_heating_scales_with_velocity_cubed():
    q1 = heating_rate(1.0, 10.0, 1.0, 1.0)
    q2 = heating_rate(1.0, 20.0, 1.0, 1.0)

    assert math.isclose(q2 / q1, 8.0)


def test_mass_loss_rate():
    rate = mass_loss_rate(
        heating_rate_W=1000.0,
        effective_heat_of_ablation_J_kg=100.0,
    )

    assert math.isclose(rate, 10.0)


def test_ablation_mass_derivative_is_negative():
    derivative = ablation_mass_derivative(
        density_kg_m3=1.0,
        velocity_m_s=10.0,
        projected_area_m2=2.0,
        heat_transfer_coefficient=1.0,
        effective_heat_of_ablation_J_kg=100.0,
    )

    assert math.isclose(derivative, -10.0)


def test_zero_density_means_no_heating():
    assert heating_rate(
        density_kg_m3=0.0,
        velocity_m_s=20_000.0,
        projected_area_m2=10.0,
        heat_transfer_coefficient=1.0,
    ) == 0.0


def test_zero_heat_transfer_coefficient():
    assert heating_rate(
        density_kg_m3=1.0,
        velocity_m_s=20_000.0,
        projected_area_m2=10.0,
        heat_transfer_coefficient=0.0,
    ) == 0.0


def test_invalid_heat_of_ablation():
    with pytest.raises(ValueError):
        mass_loss_rate(
            heating_rate_W=1000.0,
            effective_heat_of_ablation_J_kg=0.0,
        )
