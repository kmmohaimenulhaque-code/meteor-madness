from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AtmosphericState:
    """Atmospheric properties at a given geometric altitude."""

    altitude_m: float
    temperature_K: float
    pressure_Pa: float
    density_kg_m3: float


# US Standard Atmosphere 1976 constants.
# Valid for the layer model used here up to 84.852 km.
_BASE_ALTITUDES_M = (
    0.0,
    11_000.0,
    20_000.0,
    32_000.0,
    47_000.0,
    51_000.0,
    71_000.0,
    84_852.0,
)

_BASE_TEMPERATURES_K = (
    288.15,
    216.65,
    216.65,
    228.65,
    270.65,
    270.65,
    214.65,
    186.946,
)

_BASE_PRESSURES_PA = (
    101_325.0,
    22_632.06,
    5_474.889,
    868.0187,
    110.9063,
    66.93887,
    3.956420,
    0.3734,
)

_LAPSE_RATES_K_M = (
    -0.0065,
    0.0,
    0.0010,
    0.0028,
    0.0,
    -0.0028,
    -0.0020,
)

_GAS_CONSTANT_J_KG_K = 287.05287
_GRAVITY_M_S2 = 9.80665


def _layer_index(altitude_m: float) -> int:
    """Return the standard-atmosphere layer containing the altitude."""

    for index in range(len(_BASE_ALTITUDES_M) - 1):
        if altitude_m < _BASE_ALTITUDES_M[index + 1]:
            return index

    return len(_LAPSE_RATES_K_M) - 1


def state(altitude_m: float) -> AtmosphericState:
    """Return temperature, pressure, and density at a given altitude.

    This implementation follows the geopotential-layer equations of the
    US Standard Atmosphere 1976 up to 84.852 km.

    The model is intentionally limited to this range rather than silently
    extrapolating beyond its documented validity.
    """

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    if altitude_m > _BASE_ALTITUDES_M[-1]:
        raise ValueError(
            "altitude_m exceeds the implemented standard-atmosphere "
            "model boundary of 84.852 km"
        )

    index = _layer_index(altitude_m)

    base_altitude = _BASE_ALTITUDES_M[index]
    base_temperature = _BASE_TEMPERATURES_K[index]
    base_pressure = _BASE_PRESSURES_PA[index]
    lapse_rate = _LAPSE_RATES_K_M[index]

    delta_h = altitude_m - base_altitude

    if lapse_rate == 0.0:
        temperature_K = base_temperature

        pressure_Pa = base_pressure * (
            2.718281828459045
            ** (
                -_GRAVITY_M_S2
                * delta_h
                / (_GAS_CONSTANT_J_KG_K * base_temperature)
            )
        )
    else:
        temperature_K = base_temperature + lapse_rate * delta_h

        pressure_Pa = base_pressure * (
            temperature_K / base_temperature
        ) ** (
            -_GRAVITY_M_S2
            / (_GAS_CONSTANT_J_KG_K * lapse_rate)
        )

    density_kg_m3 = (
        pressure_Pa
        / (_GAS_CONSTANT_J_KG_K * temperature_K)
    )

    return AtmosphericState(
        altitude_m=altitude_m,
        temperature_K=temperature_K,
        pressure_Pa=pressure_Pa,
        density_kg_m3=density_kg_m3,
    )


def density(altitude_m: float) -> float:
    """Return atmospheric density in kg/m³."""

    return state(altitude_m).density_kg_m3
