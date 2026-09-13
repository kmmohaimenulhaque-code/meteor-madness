import math

import pytest

from physics.fragmentation import (
    fragmentation_pressure,
    fragmentation_triggered,
)


def test_fragmentation_pressure():
    pressure = fragmentation_pressure(
        density_kg_m3=2.0,
        velocity_m_s=10.0,
    )

    assert math.isclose(pressure, 100.0)


def test_pressure_scales_with_velocity_squared():
    q1 = fragmentation_pressure(1.0, 10.0)
    q2 = fragmentation_pressure(1.0, 20.0)

    assert math.isclose(q2 / q1, 4.0)


def test_fragmentation_triggers_at_strength():
    assert fragmentation_triggered(
        dynamic_pressure_Pa=1000.0,
        material_strength_Pa=1000.0,
    )


def test_fragmentation_triggers_above_strength():
    assert fragmentation_triggered(
        dynamic_pressure_Pa=1500.0,
        material_strength_Pa=1000.0,
    )


def test_fragmentation_does_not_trigger_below_strength():
    assert not fragmentation_triggered(
        dynamic_pressure_Pa=999.0,
        material_strength_Pa=1000.0,
    )


def test_invalid_pressure():
    with pytest.raises(ValueError):
        fragmentation_pressure(-1.0, 10.0)


def test_invalid_strength():
    with pytest.raises(ValueError):
        fragmentation_triggered(1000.0, 0.0)


from physics.fragmentation import create_fragments, split_mass


def test_split_mass_conserves_mass():
    fragments = split_mass(
        mass_kg=1000.0,
        fractions=(0.6, 0.4),
    )

    assert sum(fragments) == 1000.0


def test_create_fragments_conserves_mass():
    fragments = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )

    assert len(fragments) == 2
    assert sum(fragment.mass_kg for fragment in fragments) == 1000.0


def test_fragments_inherit_parent_velocity():
    fragments = create_fragments(
        mass_kg=1000.0,
        velocity_m_s=20_000.0,
    )

    for fragment in fragments:
        assert fragment.velocity_m_s == 20_000.0


def test_fragmentation_preserves_kinetic_energy():
    parent_mass = 1000.0
    velocity = 20_000.0

    parent_energy = 0.5 * parent_mass * velocity**2

    fragments = create_fragments(
        mass_kg=parent_mass,
        velocity_m_s=velocity,
    )

    fragment_energy = sum(
        0.5 * fragment.mass_kg * fragment.velocity_m_s**2
        for fragment in fragments
    )

    assert fragment_energy == parent_energy


