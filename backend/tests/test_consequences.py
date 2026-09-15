import math

import pytest

from physics.consequences import (
    calculate_impact_consequences,
)


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
    assert result.final_crater_diameter_m == 0.0
    assert result.crater_depth_m == 0.0


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


def test_ground_impact_gets_crater():

    result = calculate_impact_consequences(
        outcome="ground_impact",
        mass_kg=1.0e6,
        velocity_m_s=12_000.0,
        bulk_density_kg_m3=3000.0,
        target_density_kg_m3=2700.0,
        impact_angle_rad=math.radians(
            45.0
        ),
    )

    assert (
        result.transient_crater_diameter_m
        > 0.0
    )

    assert (
        result.final_crater_diameter_m
        > 0.0
    )

    assert (
        result.crater_depth_m
        > 0.0
    )

    assert result.crater_type in {
        "simple",
        "complex",
    }


def test_simple_crater_scaling():

    result = calculate_impact_consequences(
        outcome="ground_impact",
        mass_kg=1.0e5,
        velocity_m_s=11_000.0,
        bulk_density_kg_m3=3000.0,
        target_density_kg_m3=2700.0,
        impact_angle_rad=math.radians(
            45.0
        ),
    )

    if result.crater_type == "simple":

        assert (
            result.final_crater_diameter_m
            == pytest.approx(
                1.25
                * result.transient_crater_diameter_m
            )
        )


def test_energy_conversion():

    result = calculate_impact_consequences(
        outcome="ground_impact",
        mass_kg=1000.0,
        velocity_m_s=1000.0,
    )

    assert (
        result.impact_energy_megatons_tnt
        == pytest.approx(
            result.impact_energy_J
            / 4.184e15
        )
    )


def test_screening_zones_exist():

    result = calculate_impact_consequences(
        outcome="ground_impact",
        mass_kg=1000.0,
        velocity_m_s=1000.0,
    )

    assert (
        result.thermal_radius_m
        >= 0.0
    )

    assert (
        result.blast_radius_m
        >= 0.0
    )

    assert (
        result.seismic_radius_m
        >= 0.0
    )

    assert (
        len(
            result.consequence_zones
        )
        == 3
    )


def test_non_impacting_object_has_no_crater():

    result = calculate_impact_consequences(
        outcome="airborne_fragment",
        mass_kg=1000.0,
        velocity_m_s=1000.0,
    )

    assert (
        result.final_crater_diameter_m
        == 0.0
    )

    assert (
        result.crater_depth_m
        == 0.0
    )

    assert (
        result.crater_type
        == "none"
    )
