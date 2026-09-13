
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
    SimulationState,
)
from physics.solver import (
    gravity_acceleration,
    simulate,
    state_derivative,
)


def make_asteroid():
    return AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )


def make_entry():
    return EntryConditions(
        initial_altitude_m=80_000.0,
        initial_velocity_m_s=20_000.0,
        entry_angle_rad=0.7853981633974483,
    )


def test_gravity_decreases_with_altitude():
    g0 = gravity_acceleration(0.0)
    g80 = gravity_acceleration(80_000.0)

    assert g0 > g80
    assert g0 > 9.0
    assert g80 > 9.0


def test_state_derivative_has_correct_entry_direction():
    asteroid = make_asteroid()
    entry = make_entry()

    state = SimulationState(
        altitude_m=80_000.0,
        velocity_m_s=20_000.0,
        mass_kg=1.0e7,
    )

    derivative = state_derivative(
        state=state,
        asteroid=asteroid,
        entry=entry,
    )

    # Positive downward entry angle means altitude decreases.
    assert derivative.altitude_m < 0.0


def test_state_derivative_does_not_create_mass():
    asteroid = make_asteroid()
    entry = make_entry()

    state = SimulationState(
        altitude_m=80_000.0,
        velocity_m_s=20_000.0,
        mass_kg=1.0e7,
    )

    derivative = state_derivative(
        state=state,
        asteroid=asteroid,
        entry=entry,
    )

    # Ablation can only remove mass.
    assert derivative.mass_kg <= 0.0


def test_simulation_produces_samples():
    result = simulate(
        asteroid=make_asteroid(),
        entry=make_entry(),
        config=SimulationConfig(
            timestep_s=0.01,
            max_time_s=1000.0,
        ),
    )

    assert len(result.samples) > 1


def test_simulation_records_an_event():
    result = simulate(
        asteroid=make_asteroid(),
        entry=make_entry(),
        config=SimulationConfig(
            timestep_s=0.01,
            max_time_s=1000.0,
        ),
    )

    assert len(result.events) >= 1


def test_simulation_stops_at_fragmentation():
    result = simulate(
        asteroid=make_asteroid(),
        entry=make_entry(),
        config=SimulationConfig(
            timestep_s=0.01,
            max_time_s=1000.0,
            stop_on_fragmentation=True,
        ),
    )

    assert result.events[-1].type == "fragmentation"


def test_mass_does_not_increase():
    result = simulate(
        asteroid=make_asteroid(),
        entry=make_entry(),
        config=SimulationConfig(
            timestep_s=0.01,
            max_time_s=1000.0,
        ),
    )

    masses = [sample.mass_kg for sample in result.samples]

    for previous, current in zip(masses, masses[1:]):
        assert current <= previous + 1e-6


def test_kinetic_energy_is_non_negative():
    result = simulate(
        asteroid=make_asteroid(),
        entry=make_entry(),
        config=SimulationConfig(
            timestep_s=0.01,
            max_time_s=1000.0,
        ),
    )

    for sample in result.samples:
        assert sample.kinetic_energy_J >= 0.0

