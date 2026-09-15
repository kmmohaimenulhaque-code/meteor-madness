from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from physics.energy import kinetic_energy


# ============================================================
# CONSTANTS
# ============================================================

EARTH_GRAVITY_M_S2 = 9.80665

JOULES_PER_MEGATON_TNT = 4.184e15

DEFAULT_TARGET_DENSITY_KG_M3 = 2700.0

SIMPLE_TO_COMPLEX_TRANSIENT_M = 2560.0


# ------------------------------------------------------------
# Screening-model coupling assumptions.
#
# These are deliberately transparent engineering estimates.
# They are NOT full blast/fireball/seismic propagation models.
# ------------------------------------------------------------

THERMAL_COUPLING_FRACTION = 0.10
BLAST_COUPLING_FRACTION = 0.20
SEISMIC_COUPLING_FRACTION = 0.001

THERMAL_THRESHOLD_J_M2 = 1.0e5
BLAST_THRESHOLD_J_M2 = 1.0e6
SEISMIC_THRESHOLD_J_M2 = 1.0e1


# ============================================================
# DATA MODELS
# ============================================================


@dataclass(frozen=True)
class ConsequenceZone:
    """One display-oriented consequence zone."""

    type: str
    radius_m: float
    radius_km: float
    basis: str


@dataclass(frozen=True)
class ImpactConsequences:
    """
    Complete V0.4 impact-consequence estimate.

    The crater calculation is based on first-order terrestrial
    impact scaling.

    Thermal, blast and seismic radii are deliberately labelled
    screening estimates rather than precision damage boundaries.
    """

    # Existing V0.2/V0.3 contract.
    outcome: str
    surviving_mass_kg: float
    impact_velocity_m_s: float
    impact_energy_J: float

    # V0.4.
    impact_energy_megatons_tnt: float = 0.0

    equivalent_impactor_diameter_m: float = 0.0

    transient_crater_diameter_m: float = 0.0
    final_crater_diameter_m: float = 0.0
    crater_depth_m: float = 0.0
    crater_type: str = "none"

    thermal_radius_m: float = 0.0
    blast_radius_m: float = 0.0
    seismic_radius_m: float = 0.0

    consequence_zones: tuple[
        ConsequenceZone,
        ...
    ] = ()

    model_notes: tuple[str, ...] = ()


# ============================================================
# VALIDATION
# ============================================================


def _validate_inputs(
    *,
    outcome: str,
    mass_kg: float,
    velocity_m_s: float,
    bulk_density_kg_m3: float,
    target_density_kg_m3: float,
    impact_angle_rad: float,
) -> None:

    if not outcome:
        raise ValueError(
            "outcome cannot be empty"
        )

    if mass_kg < 0.0:
        raise ValueError(
            "mass_kg cannot be negative"
        )

    if velocity_m_s < 0.0:
        raise ValueError(
            "velocity_m_s cannot be negative"
        )

    if bulk_density_kg_m3 <= 0.0:
        raise ValueError(
            "bulk_density_kg_m3 must be greater than zero"
        )

    if target_density_kg_m3 <= 0.0:
        raise ValueError(
            "target_density_kg_m3 must be greater than zero"
        )

    if not (
        0.0 < impact_angle_rad <= math.pi / 2.0
    ):
        raise ValueError(
            "impact_angle_rad must be between 0 and pi/2"
        )


# ============================================================
# BASIC IMPACT GEOMETRY
# ============================================================


def _diameter_from_mass(
    *,
    mass_kg: float,
    density_kg_m3: float,
) -> float:
    """Equivalent spherical diameter."""

    if mass_kg <= 0.0:
        return 0.0

    volume_m3 = (
        mass_kg
        / density_kg_m3
    )

    return (
        6.0
        * volume_m3
        / math.pi
    ) ** (1.0 / 3.0)


# ============================================================
# CRATER SCALING
# ============================================================


def _transient_crater_diameter(
    *,
    impactor_diameter_m: float,
    impactor_density_kg_m3: float,
    target_density_kg_m3: float,
    velocity_m_s: float,
    impact_angle_rad: float,
) -> float:
    """
    Gravity-regime transient crater scaling.

    First-order Earth impact model:

        Dtc ∝
        density_ratio^(1/3)
        × L^0.78
        × v^0.44
        × g^-0.22
        × sin(theta)^(1/3)

    This is an engineering-scale approximation.
    """

    if (
        impactor_diameter_m <= 0.0
        or velocity_m_s <= 0.0
    ):
        return 0.0

    density_ratio = (
        impactor_density_kg_m3
        / target_density_kg_m3
    )

    angle_factor = max(
        math.sin(impact_angle_rad),
        1.0e-12,
    )

    result = (
        1.161
        * density_ratio ** (1.0 / 3.0)
        * impactor_diameter_m ** 0.78
        * velocity_m_s ** 0.44
        * EARTH_GRAVITY_M_S2 ** -0.22
        * angle_factor ** (1.0 / 3.0)
    )

    return max(
        result,
        0.0,
    )


def _final_crater_diameter(
    transient_diameter_m: float,
) -> tuple[float, str]:
    """Estimate final crater diameter and morphology."""

    if transient_diameter_m <= 0.0:
        return 0.0, "none"

    if (
        transient_diameter_m
        <= SIMPLE_TO_COMPLEX_TRANSIENT_M
    ):
        return (
            1.25 * transient_diameter_m,
            "simple",
        )

    transient_km = (
        transient_diameter_m / 1000.0
    )

    transition_km = 3.2

    final_km = (
        1.17
        * transient_km ** 1.13
        / transition_km ** 0.13
    )

    return (
        max(final_km * 1000.0, 0.0),
        "complex",
    )


def _crater_depth(
    *,
    final_crater_diameter_m: float,
    crater_type: str,
) -> float:
    """Estimate final crater depth."""

    if final_crater_diameter_m <= 0.0:
        return 0.0

    diameter_km = (
        final_crater_diameter_m / 1000.0
    )

    if crater_type == "simple":
        depth_km = (
            0.13
            * diameter_km ** 1.06
        )

    elif crater_type == "complex":
        depth_km = (
            0.20
            * diameter_km ** 0.40
        )

    else:
        depth_km = 0.0

    return max(
        depth_km * 1000.0,
        0.0,
    )


# ============================================================
# SCREENING ZONE MODEL
# ============================================================


def _screening_radius(
    *,
    energy_J: float,
    coupling_fraction: float,
    threshold_J_m2: float,
) -> float:
    """
    Simple spherical energy-fluence screening radius.

        E / (4*pi*r^2) = threshold

    This intentionally does NOT model atmospheric blast physics.
    """

    if energy_J <= 0.0:
        return 0.0

    coupled_energy = (
        energy_J
        * coupling_fraction
    )

    denominator = (
        4.0
        * math.pi
        * threshold_J_m2
    )

    radius_squared = (
        coupled_energy
        / denominator
    )

    return math.sqrt(
        max(radius_squared, 0.0)
    )


# ============================================================
# MAIN CONSEQUENCE ENGINE
# ============================================================


def calculate_impact_consequences(
    outcome: str,
    mass_kg: float,
    velocity_m_s: float,
    *,
    bulk_density_kg_m3: float = 3000.0,
    target_density_kg_m3: float = (
        DEFAULT_TARGET_DENSITY_KG_M3
    ),
    impact_angle_rad: float = (
        math.pi / 4.0
    ),
) -> ImpactConsequences:
    """
    Calculate V0.4 impact consequences.

    Existing callers remain compatible because all V0.4-specific
    physical parameters have defaults.
    """

    _validate_inputs(
        outcome=outcome,
        mass_kg=mass_kg,
        velocity_m_s=velocity_m_s,
        bulk_density_kg_m3=(
            bulk_density_kg_m3
        ),
        target_density_kg_m3=(
            target_density_kg_m3
        ),
        impact_angle_rad=(
            impact_angle_rad
        ),
    )

    impact_energy = kinetic_energy(
        mass_kg=mass_kg,
        velocity_m_s=velocity_m_s,
    )

    impact_energy_megatons = (
        impact_energy
        / JOULES_PER_MEGATON_TNT
    )

    equivalent_diameter = (
        _diameter_from_mass(
            mass_kg=mass_kg,
            density_kg_m3=(
                bulk_density_kg_m3
            ),
        )
    )

    # --------------------------------------------------------
    # Crater
    # --------------------------------------------------------

    if (
        outcome != "ground_impact"
        or impact_energy <= 0.0
    ):
        transient_crater = 0.0
        final_crater = 0.0
        crater_type = "none"
        crater_depth = 0.0

    else:
        transient_crater = (
            _transient_crater_diameter(
                impactor_diameter_m=(
                    equivalent_diameter
                ),
                impactor_density_kg_m3=(
                    bulk_density_kg_m3
                ),
                target_density_kg_m3=(
                    target_density_kg_m3
                ),
                velocity_m_s=(
                    velocity_m_s
                ),
                impact_angle_rad=(
                    impact_angle_rad
                ),
            )
        )

        (
            final_crater,
            crater_type,
        ) = _final_crater_diameter(
            transient_crater
        )

        crater_depth = _crater_depth(
            final_crater_diameter_m=(
                final_crater
            ),
            crater_type=crater_type,
        )

    # --------------------------------------------------------
    # Screening radii
    # --------------------------------------------------------

    thermal_radius = _screening_radius(
        energy_J=impact_energy,
        coupling_fraction=(
            THERMAL_COUPLING_FRACTION
        ),
        threshold_J_m2=(
            THERMAL_THRESHOLD_J_M2
        ),
    )

    blast_radius = _screening_radius(
        energy_J=impact_energy,
        coupling_fraction=(
            BLAST_COUPLING_FRACTION
        ),
        threshold_J_m2=(
            BLAST_THRESHOLD_J_M2
        ),
    )

    seismic_radius = _screening_radius(
        energy_J=impact_energy,
        coupling_fraction=(
            SEISMIC_COUPLING_FRACTION
        ),
        threshold_J_m2=(
            SEISMIC_THRESHOLD_J_M2
        ),
    )

    # --------------------------------------------------------
    # Public zones
    # --------------------------------------------------------

    zones = (
        ConsequenceZone(
            type="thermal_screening",
            radius_m=thermal_radius,
            radius_km=(
                thermal_radius / 1000.0
            ),
            basis=(
                "10% coupled-energy "
                "spherical-fluence "
                "screening estimate"
            ),
        ),
        ConsequenceZone(
            type="blast_screening",
            radius_m=blast_radius,
            radius_km=(
                blast_radius / 1000.0
            ),
            basis=(
                "20% coupled-energy "
                "spherical-fluence "
                "screening estimate"
            ),
        ),
        ConsequenceZone(
            type="seismic_screening",
            radius_m=seismic_radius,
            radius_km=(
                seismic_radius / 1000.0
            ),
            basis=(
                "0.1% coupled-energy "
                "spherical-fluence "
                "screening estimate"
            ),
        ),
    )

    # --------------------------------------------------------
    # Notes
    # --------------------------------------------------------

    notes = (
        "Crater sizing uses first-order terrestrial impact scaling.",
        "Thermal, blast and seismic radii are screening estimates.",
        "Results carry substantial physical-model uncertainty.",
        "This is an educational engineering model, not a hydrocode.",
    )

    return ImpactConsequences(
        outcome=outcome,
        surviving_mass_kg=mass_kg,
        impact_velocity_m_s=velocity_m_s,
        impact_energy_J=impact_energy,

        impact_energy_megatons_tnt=(
            impact_energy_megatons
        ),

        equivalent_impactor_diameter_m=(
            equivalent_diameter
        ),

        transient_crater_diameter_m=(
            transient_crater
        ),

        final_crater_diameter_m=(
            final_crater
        ),

        crater_depth_m=(
            crater_depth
        ),

        crater_type=(
            crater_type
        ),

        thermal_radius_m=(
            thermal_radius
        ),

        blast_radius_m=(
            blast_radius
        ),

        seismic_radius_m=(
            seismic_radius
        ),

        consequence_zones=zones,

        model_notes=notes,
    )


# ============================================================
# SERIALISATION
# ============================================================


def consequences_to_dict(
    consequences: ImpactConsequences,
) -> dict[str, Any]:
    """Convert consequence model into JSON-safe data."""

    data = asdict(
        consequences
    )

    data["consequence_zones"] = [
        asdict(zone)
        for zone
        in consequences.consequence_zones
    ]

    data["model_notes"] = list(
        consequences.model_notes
    )

    return data
