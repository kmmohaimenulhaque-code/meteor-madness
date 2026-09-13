import math

import pytest

from physics.energy import (
    drag_energy_rate,
    kinetic_energy,
)


def test_kinetic_energy():
    energy = kinetic_energy(
        mass_kg=10.0,
        velocity_m_s=20.0,
    )

    assert math.isclose(energy, 2000.0)


def test_kinetic_energy_scales_with_velocity_squared():
    e1 = kinetic_energy(1.0, 10.0)
    e2 = kinetic_energy(1.0, 20.0)

    assert math.isclose(e2 / e1, 4.0)


def test_drag_energy_rate():
    power = drag_energy_rate(
        drag_force_N=100.0,
        velocity_m_s=20.0,
    )

    assert math.isclose(power, 2000.0)


def test_zero_drag_means_zero_energy_removal():
    assert drag_energy_rate(0.0, 20_000.0) == 0.0


def test_zero_velocity_means_zero_energy_rate():
    assert drag_energy_rate(1000.0, 0.0) == 0.0


def test_invalid_mass():
    with pytest.raises(ValueError):
        kinetic_energy(-1.0, 10.0)


def test_invalid_drag_force():
    with pytest.raises(ValueError):
        drag_energy_rate(-1.0, 10.0)
