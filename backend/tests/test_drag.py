import math

import pytest

from physics.drag import (
    drag_acceleration,
    drag_force,
    drag_power,
    dynamic_pressure,
)


def test_dynamic_pressure():
    q = dynamic_pressure(
        density_kg_m3=1.0,
        velocity_m_s=10.0,
    )

    assert math.isclose(q, 50.0)


def test_dynamic_pressure_scales_with_velocity_squared():
    q1 = dynamic_pressure(1.0, 10.0)
    q2 = dynamic_pressure(1.0, 20.0)

    assert math.isclose(q2 / q1, 4.0)


def test_drag_force():
    force = drag_force(
        density_kg_m3=1.0,
        velocity_m_s=10.0,
        projected_area_m2=2.0,
        drag_coefficient=1.0,
    )

    assert math.isclose(force, 100.0)


def test_drag_acceleration():
    acceleration = drag_acceleration(
        drag_force_N=100.0,
        mass_kg=20.0,
    )

    assert math.isclose(acceleration, 5.0)


def test_drag_power():
    power = drag_power(
        drag_force_N=100.0,
        velocity_m_s=20.0,
    )

    assert math.isclose(power, 2000.0)


def test_zero_density_means_zero_drag():
    assert drag_force(
        density_kg_m3=0.0,
        velocity_m_s=20_000.0,
        projected_area_m2=10.0,
        drag_coefficient=1.0,
    ) == 0.0


def test_zero_drag_coefficient():
    assert drag_force(
        density_kg_m3=1.0,
        velocity_m_s=20_000.0,
        projected_area_m2=10.0,
        drag_coefficient=0.0,
    ) == 0.0


def test_invalid_mass():
    with pytest.raises(ValueError):
        drag_acceleration(
            drag_force_N=100.0,
            mass_kg=0.0,
        )


def test_invalid_area():
    with pytest.raises(ValueError):
        drag_force(
            density_kg_m3=1.0,
            velocity_m_s=10.0,
            projected_area_m2=0.0,
            drag_coefficient=1.0,
        )
