import pytest

from physics.deposition import (
    build_energy_deposition_profile,
    energy_deposited_between_samples,
    energy_deposition_per_altitude,
)
from physics.models import SimulationSample


def test_energy_deposited_with_trapezoidal_integration():
    assert energy_deposited_between_samples(
        energy_rate_start_W=1000.0,
        energy_rate_end_W=2000.0,
        timestep_s=2.0,
    ) == 3000.0


def test_zero_timestep():
    assert energy_deposited_between_samples(
        energy_rate_start_W=1000.0,
        energy_rate_end_W=2000.0,
        timestep_s=0.0,
    ) == 0.0


def test_negative_start_energy_rate_rejected():
    with pytest.raises(ValueError):
        energy_deposited_between_samples(-1.0, 1000.0, 1.0)


def test_negative_end_energy_rate_rejected():
    with pytest.raises(ValueError):
        energy_deposited_between_samples(1000.0, -1.0, 1.0)


def test_energy_per_altitude():
    assert energy_deposition_per_altitude(
        energy_deposited_J=1000.0,
        altitude_change_m=100.0,
    ) == 10.0


def test_zero_altitude_change_rejected():
    with pytest.raises(ValueError):
        energy_deposition_per_altitude(1000.0, 0.0)


def make_sample(time_s, altitude_m, drag_power_W):
    return SimulationSample(
        time_s=time_s,
        altitude_m=altitude_m,
        velocity_m_s=1000.0,
        mass_kg=1000.0,
        density_kg_m3=1.0,
        temperature_K=250.0,
        pressure_Pa=50000.0,
        equivalent_radius_m=1.0,
        projected_area_m2=3.14,
        drag_force_N=drag_power_W / 1000.0,
        drag_acceleration_m_s2=1.0,
        drag_power_W=drag_power_W,
        kinetic_energy_J=1e9,
        dynamic_pressure_Pa=500000.0,
        mass_loss_rate_kg_s=0.0,
    )


def test_build_energy_deposition_profile():
    samples = (
        make_sample(0.0, 10000.0, 1000.0),
        make_sample(1.0, 9000.0, 2000.0),
    )

    profile = build_energy_deposition_profile(samples)

    assert len(profile) == 1
    assert profile[0]["altitude_m"] == 9500.0
    assert profile[0]["energy_deposited_J"] == 1500.0
    assert profile[0]["energy_deposition_per_meter_J_m"] == 1.5

def test_bin_energy_deposition():
    from physics.deposition import bin_energy_deposition

    profile = (
        {
            "altitude_m": 9500.0,
            "energy_deposited_J": 100.0,
        },
        {
            "altitude_m": 9200.0,
            "energy_deposited_J": 200.0,
        },
        {
            "altitude_m": 8500.0,
            "energy_deposited_J": 300.0,
        },
    )

    bins = bin_energy_deposition(profile, 1000.0)

    assert len(bins) == 2
    assert bins[0]["energy_deposited_J"] == 300.0
    assert bins[1]["energy_deposited_J"] == 300.0

def test_total_deposited_energy():
    from physics.deposition import total_deposited_energy

    profile = (
        {"altitude_m": 50000.0, "energy_deposited_J": 100.0},
        {"altitude_m": 49000.0, "energy_deposited_J": 250.0},
        {"altitude_m": 48000.0, "energy_deposited_J": 150.0},
    )

    assert total_deposited_energy(profile) == 500.0
