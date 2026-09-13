import math

import pytest

from physics.atmosphere import density, state


def test_sea_level_standard_atmosphere():
    atmosphere = state(0.0)

    assert math.isclose(
        atmosphere.temperature_K,
        288.15,
        rel_tol=1e-6,
    )

    assert math.isclose(
        atmosphere.pressure_Pa,
        101325.0,
        rel_tol=1e-6,
    )

    assert math.isclose(
        atmosphere.density_kg_m3,
        1.225,
        rel_tol=1e-3,
    )


def test_temperature_at_11_km():
    atmosphere = state(11_000.0)

    assert math.isclose(
        atmosphere.temperature_K,
        216.65,
        rel_tol=1e-6,
    )


def test_density_decreases_with_altitude():
    sea_level = density(0.0)
    ten_km = density(10_000.0)
    twenty_km = density(20_000.0)

    assert sea_level > ten_km > twenty_km


def test_density_is_positive():
    for altitude_m in (0.0, 10_000.0, 50_000.0, 80_000.0):
        assert density(altitude_m) > 0.0


def test_invalid_negative_altitude():
    with pytest.raises(ValueError):
        density(-1.0)


def test_invalid_altitude_above_model_boundary():
    with pytest.raises(ValueError):
        density(90_000.0)


def test_state_preserves_requested_altitude():
    atmosphere = state(25_000.0)

    assert atmosphere.altitude_m == 25_000.0
