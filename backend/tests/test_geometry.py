import math

import pytest

from physics.geometry import (
    equivalent_radius_from_mass,
    initial_mass,
    mass_from_density_and_volume,
    projected_area,
    radius_from_diameter,
    sphere_volume,
)


def test_radius_from_diameter():
    assert radius_from_diameter(10.0) == 5.0


def test_sphere_volume():
    volume = sphere_volume(1.0)

    assert math.isclose(
        volume,
        4.0 / 3.0 * math.pi,
        rel_tol=1e-12,
    )


def test_mass_from_density_and_volume():
    assert mass_from_density_and_volume(
        1000.0,
        2.0,
    ) == 2000.0


def test_initial_mass():
    mass = initial_mass(
        diameter_m=2.0,
        density_kg_m3=1000.0,
    )

    expected = 1000.0 * (4.0 / 3.0) * math.pi

    assert math.isclose(
        mass,
        expected,
        rel_tol=1e-12,
    )


def test_equivalent_radius_recovers_original_radius():
    radius = equivalent_radius_from_mass(
        mass_kg=1000.0 * (4.0 / 3.0) * math.pi,
        density_kg_m3=1000.0,
    )

    assert math.isclose(
        radius,
        1.0,
        rel_tol=1e-12,
    )


def test_projected_area():
    area = projected_area(1.0)

    assert math.isclose(
        area,
        math.pi,
        rel_tol=1e-12,
    )


def test_shape_factor_changes_projected_area():
    area = projected_area(
        equivalent_radius_m=1.0,
        shape_factor=2.0,
    )

    assert math.isclose(
        area,
        2.0 * math.pi,
        rel_tol=1e-12,
    )


def test_invalid_diameter():
    with pytest.raises(ValueError):
        radius_from_diameter(0.0)


def test_invalid_density():
    with pytest.raises(ValueError):
        mass_from_density_and_volume(
            density_kg_m3=0.0,
            volume_m3=1.0,
        )


def test_invalid_radius():
    with pytest.raises(ValueError):
        sphere_volume(0.0)
