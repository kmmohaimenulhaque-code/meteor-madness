from physics.models import AsteroidParameters, SimulationConfig
from physics.fragment_solver import simulate_fragment
from physics.fragmentation import create_fragments
from physics.fragment_solver import (
    classify_fragment_outcome,
    fragment_kinetic_energy,
    initial_fragment_states,
)


def test_initial_fragment_states_preserve_mass():
    fragments = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )

    states = initial_fragment_states(
        fragments=fragments,
        altitude_m=38_000.0,
    )

    assert sum(state.mass_kg for state in states) == 1000.0


def test_initial_fragment_states_preserve_velocity():
    fragments = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )

    states = initial_fragment_states(
        fragments=fragments,
        altitude_m=38_000.0,
    )

    for state in states:
        assert state.velocity_m_s == 20_000.0


def test_initial_fragment_states_preserve_altitude():
    fragments = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )

    states = initial_fragment_states(
        fragments=fragments,
        altitude_m=38_000.0,
    )

    for state in states:
        assert state.altitude_m == 38_000.0


def test_fragment_kinetic_energy():
    energy = fragment_kinetic_energy(
        mass_kg=1000.0,
        velocity_m_s=1000.0,
    )

    assert energy == 500_000_000.0


def test_ground_impact_classification():
    result = classify_fragment_outcome(
        altitude_m=0.0,
        velocity_m_s=1000.0,
        mass_kg=100.0,
    )

    assert result.outcome == "ground_impact"


def test_complete_ablation_classification():
    result = classify_fragment_outcome(
        altitude_m=10_000.0,
        velocity_m_s=1000.0,
        mass_kg=0.0,
    )

    assert result.outcome == "complete_ablation"


def test_airborne_fragment_classification():
    result = classify_fragment_outcome(
        altitude_m=10_000.0,
        velocity_m_s=1000.0,
        mass_kg=100.0,
    )

    assert result.outcome == "airborne_fragment"

def test_fragment_simulation_produces_samples():
    fragment = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )[0]

    state = initial_fragment_states(
        fragments=(fragment,),
        altitude_m=38_000.0,
    )[0]

    asteroid = AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )

    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=10.0,
    )

    result = simulate_fragment(
        fragment=state,
        asteroid=asteroid,
        config=config,
        entry_angle_rad=0.7853981633974483,
    )

    assert len(result.samples) > 1


def test_fragment_altitude_decreases():
    fragment = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )[0]

    state = initial_fragment_states(
        fragments=(fragment,),
        altitude_m=38_000.0,
    )[0]

    asteroid = AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )

    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=1.0,
    )

    result = simulate_fragment(
        fragment=state,
        asteroid=asteroid,
        config=config,
        entry_angle_rad=0.7853981633974483,
    )

    assert result.samples[-1].altitude_m < result.samples[0].altitude_m


def test_fragment_mass_does_not_increase():
    fragment = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )[0]

    state = initial_fragment_states(
        fragments=(fragment,),
        altitude_m=38_000.0,
    )[0]

    asteroid = AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )

    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=1.0,
    )

    result = simulate_fragment(
        fragment=state,
        asteroid=asteroid,
        config=config,
        entry_angle_rad=0.7853981633974483,
    )

    masses = [sample.mass_kg for sample in result.samples]

    assert all(
        later <= earlier
        for earlier, later in zip(masses, masses[1:])
    )


def test_fragment_simulation_has_valid_outcome():
    fragment = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )[0]

    state = initial_fragment_states(
        fragments=(fragment,),
        altitude_m=38_000.0,
    )[0]

    asteroid = AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )

    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=1.0,
    )

    result = simulate_fragment(
        fragment=state,
        asteroid=asteroid,
        config=config,
        entry_angle_rad=0.7853981633974483,
    )

    assert result.outcome.outcome in {
        "ground_impact",
        "complete_ablation",
        "max_time",
    }
