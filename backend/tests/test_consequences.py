import pytest

from physics.consequences import calculate_impact_consequences


def test_ground_impact_energy():
    result = calculate_impact_consequences(
        outcome="ground_impact",
        mass_kg=1000.0,
        velocity_m_s=1000.0,
    )

    assert result.outcome == "ground_impact"
    assert result.surviving_mass_kg == 1000.0
    assert result.impact_velocity_m_s == 1000.0
    assert result.impact_energy_J == 5.0e8


def test_zero_mass_has_zero_energy():
    result = calculate_impact_consequences(
        outcome="complete_ablation",
        mass_kg=0.0,
        velocity_m_s=1000.0,
    )

    assert result.impact_energy_J == 0.0


def test_negative_mass_rejected():
    with pytest.raises(ValueError):
        calculate_impact_consequences(
            outcome="ground_impact",
            mass_kg=-1.0,
            velocity_m_s=1000.0,
        )


def test_negative_velocity_rejected():
    with pytest.raises(ValueError):
        calculate_impact_consequences(
            outcome="ground_impact",
            mass_kg=1000.0,
            velocity_m_s=-1.0,
        )


def test_empty_outcome_rejected():
    with pytest.raises(ValueError):
        calculate_impact_consequences(
            outcome="",
            mass_kg=1000.0,
            velocity_m_s=1000.0,
        )
