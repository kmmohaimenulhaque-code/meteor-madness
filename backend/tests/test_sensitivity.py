from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
)
from physics.solver import simulate


BASE_ASTEROID = dict(
    diameter_m=20.0,
    bulk_density_kg_m3=3500.0,
    drag_coefficient=1.0,
    heat_transfer_coefficient=0.1,
    effective_heat_of_ablation_J_kg=8.0e6,
    material_strength_Pa=1.0e6,
    shape_factor=1.0,
)

BASE_ENTRY = dict(
    initial_altitude_m=80_000.0,
    initial_velocity_m_s=20_000.0,
    entry_angle_rad=0.7853981633974483,
)


def run_simulation(asteroid_overrides=None, entry_overrides=None):
    asteroid_values = BASE_ASTEROID.copy()

    if asteroid_overrides:
        asteroid_values.update(asteroid_overrides)

    entry_values = BASE_ENTRY.copy()

    if entry_overrides:
        entry_values.update(entry_overrides)

    return simulate(
        asteroid=AsteroidParameters(**asteroid_values),
        entry=EntryConditions(**entry_values),
        config=SimulationConfig(
            timestep_s=0.01,
            max_time_s=1000.0,
        ),
    )


def assert_valid_result(result):
    assert result.samples
    assert result.events

    for sample in result.samples:
        assert sample.altitude_m >= 0.0
        assert sample.velocity_m_s >= 0.0
        assert sample.mass_kg >= 0.0


def test_diameter_sensitivity():
    for diameter in (15.0, 20.0, 25.0):
        result = run_simulation(
            asteroid_overrides={"diameter_m": diameter}
        )
        assert_valid_result(result)


def test_density_sensitivity():
    for density in (2200.0, 3500.0, 8000.0):
        result = run_simulation(
            asteroid_overrides={
                "bulk_density_kg_m3": density
            }
        )
        assert_valid_result(result)


def test_velocity_sensitivity():
    for velocity in (15_000.0, 20_000.0, 25_000.0):
        result = run_simulation(
            entry_overrides={
                "initial_velocity_m_s": velocity
            }
        )
        assert_valid_result(result)


def test_entry_angle_sensitivity():
    for angle in (
        30.0 * 3.141592653589793 / 180.0,
        45.0 * 3.141592653589793 / 180.0,
        60.0 * 3.141592653589793 / 180.0,
    ):
        result = run_simulation(
            entry_overrides={
                "entry_angle_rad": angle
            }
        )
        assert_valid_result(result)


def test_drag_coefficient_sensitivity():
    for coefficient in (0.7, 1.0, 1.3):
        result = run_simulation(
            asteroid_overrides={
                "drag_coefficient": coefficient
            }
        )
        assert_valid_result(result)


def test_heat_transfer_sensitivity():
    for coefficient in (0.05, 0.1, 0.2):
        result = run_simulation(
            asteroid_overrides={
                "heat_transfer_coefficient": coefficient
            }
        )
        assert_valid_result(result)


def test_heat_of_ablation_sensitivity():
    for heat in (4.0e6, 8.0e6, 12.0e6):
        result = run_simulation(
            asteroid_overrides={
                "effective_heat_of_ablation_J_kg": heat
            }
        )
        assert_valid_result(result)


def test_material_strength_sensitivity():
    for strength in (0.5e6, 1.0e6, 5.0e6):
        result = run_simulation(
            asteroid_overrides={
                "material_strength_Pa": strength
            }
        )
        assert_valid_result(result)


def test_shape_factor_sensitivity():
    for shape_factor in (0.8, 1.0, 1.2):
        result = run_simulation(
            asteroid_overrides={
                "shape_factor": shape_factor
            }
        )
        assert_valid_result(result)
