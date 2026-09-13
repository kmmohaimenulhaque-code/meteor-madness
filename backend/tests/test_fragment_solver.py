
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

