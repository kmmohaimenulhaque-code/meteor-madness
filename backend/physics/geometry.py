from __future__ import annotations

import math


def radius_from_diameter(diameter_m: float) -> float:
    """Return the radius of a spherical body from its diameter."""

    if diameter_m <= 0:
        raise ValueError("diameter_m must be greater than zero")

    return diameter_m / 2.0


def sphere_volume(radius_m: float) -> float:
    """Return the volume of a sphere."""

    if radius_m <= 0:
        raise ValueError("radius_m must be greater than zero")

    return (4.0 / 3.0) * math.pi * radius_m**3


def mass_from_density_and_volume(
    density_kg_m3: float,
    volume_m3: float,
) -> float:
    """Return mass from density and volume."""

    if density_kg_m3 <= 0:
        raise ValueError("density_kg_m3 must be greater than zero")

    if volume_m3 <= 0:
        raise ValueError("volume_m3 must be greater than zero")

    return density_kg_m3 * volume_m3


def initial_mass(
    diameter_m: float,
    density_kg_m3: float,
) -> float:
    """Return the initial mass of an equivalent spherical asteroid."""

    radius_m = radius_from_diameter(diameter_m)
    volume_m3 = sphere_volume(radius_m)

    return mass_from_density_and_volume(
        density_kg_m3,
        volume_m3,
    )


def equivalent_radius_from_mass(
    mass_kg: float,
    density_kg_m3: float,
) -> float:
    """Return equivalent spherical radius for a given mass and density."""

    if mass_kg <= 0:
        raise ValueError("mass_kg must be greater than zero")

    if density_kg_m3 <= 0:
        raise ValueError("density_kg_m3 must be greater than zero")

    return (
        (3.0 * mass_kg)
        / (4.0 * math.pi * density_kg_m3)
    ) ** (1.0 / 3.0)


def projected_area(
    equivalent_radius_m: float,
    shape_factor: float = 1.0,
) -> float:
    """Return projected cross-sectional area."""

    if equivalent_radius_m <= 0:
        raise ValueError(
            "equivalent_radius_m must be greater than zero"
        )

    if shape_factor <= 0:
        raise ValueError(
            "shape_factor must be greater than zero"
        )

    return shape_factor * math.pi * equivalent_radius_m**2
