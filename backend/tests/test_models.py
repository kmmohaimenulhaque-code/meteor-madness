import pytest

from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
)


def test_valid_asteroid_parameters():
    params = AsteroidParameters(
        diameter_m=50.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.01,
        effective_heat_of_ablation_J_kg=1e7,
        material_strength_Pa=1e6,
    )

    params.validate()


def test_invalid_diameter():
    params = AsteroidParameters(
        diameter_m=0.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.01,
        effective_heat_of_ablation_J_kg=1e7,
        material_strength_Pa=1e6,
    )

    with pytest.raises(ValueError):
        params.validate()


def test_valid_entry_conditions():
    entry = EntryConditions(
        initial_altitude_m=80_000.0,
        initial_velocity_m_s=20_000.0,
        entry_angle_rad=0.785,
    )

    entry.validate()


def test_simulation_config():
    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=1000.0,
    )

    config.validate()
