from __future__ import annotations

import math


EARTH_RADIUS_M = 6_371_000.0


def dynamic_flight_path_angle_rate(
    altitude_m: float,
    velocity_m_s: float,
    flight_path_angle_rad: float,
    gravity_m_s2: float,
) -> float:
    """
    Compute d(gamma)/dt for a ballistic no-lift trajectory.

    gamma is positive downward from the local horizontal.

        dgamma/dt =
            (v / (R + h) - g / v) * cos(gamma)
    """

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    if velocity_m_s <= 1e-9:
        return 0.0

    radius = EARTH_RADIUS_M + altitude_m

    return (
        velocity_m_s / radius
        - gravity_m_s2 / velocity_m_s
    ) * math.cos(flight_path_angle_rad)


def downrange_rate(
    altitude_m: float,
    velocity_m_s: float,
    flight_path_angle_rad: float,
) -> float:
    """
    Compute surface downrange rate.

    s is measured as surface arc length.

        ds/dt =
            v cos(gamma) R / (R + h)
    """

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    radius = EARTH_RADIUS_M + altitude_m

    return (
        velocity_m_s
        * math.cos(flight_path_angle_rad)
        * EARTH_RADIUS_M
        / radius
    )


def normalise_longitude_deg(longitude_deg: float) -> float:
    """Normalise longitude into [-180, 180]."""

    longitude = (
        (longitude_deg + 180.0) % 360.0
    ) - 180.0

    # Avoid returning -180 when input is exactly +180.
    if math.isclose(longitude, -180.0, abs_tol=1e-12):
        return 180.0

    return longitude


def destination_from_downrange(
    latitude_deg: float,
    longitude_deg: float,
    azimuth_deg: float,
    downrange_m: float,
) -> tuple[float, float]:
    """
    Calculate a point on a spherical Earth after travelling
    downrange_m along the great circle defined by the initial
    azimuth.

    Azimuth is measured clockwise from north.
    """

    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError(
            "latitude_deg must be between -90 and 90"
        )

    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError(
            "longitude_deg must be between -180 and 180"
        )

    if not 0.0 <= azimuth_deg < 360.0:
        raise ValueError(
            "azimuth_deg must be between 0 and 360"
        )

    if downrange_m < 0:
        raise ValueError(
            "downrange_m cannot be negative"
        )

    latitude_1 = math.radians(latitude_deg)
    longitude_1 = math.radians(longitude_deg)
    azimuth = math.radians(azimuth_deg)

    sigma = downrange_m / EARTH_RADIUS_M

    sin_lat_1 = math.sin(latitude_1)
    cos_lat_1 = math.cos(latitude_1)

    sin_sigma = math.sin(sigma)
    cos_sigma = math.cos(sigma)

    latitude_2 = math.asin(
        sin_lat_1 * cos_sigma
        + cos_lat_1
        * sin_sigma
        * math.cos(azimuth)
    )

    longitude_2 = longitude_1 + math.atan2(
        math.sin(azimuth)
        * sin_sigma
        * cos_lat_1,
        cos_sigma
        - sin_lat_1 * math.sin(latitude_2),
    )

    latitude_2_deg = math.degrees(latitude_2)
    longitude_2_deg = normalise_longitude_deg(
        math.degrees(longitude_2)
    )

    return latitude_2_deg, longitude_2_deg
