from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AirburstClassification:
    """Classification of the modeled atmospheric-entry outcome."""

    outcome: str
    atmospheric_energy_J: float
    ground_impact_energy_J: float
    atmospheric_fraction: float


def classify_airburst(
    atmospheric_energy_J: float,
    ground_impact_energy_J: float,
    minimum_atmospheric_fraction: float = 0.5,
) -> AirburstClassification:
    """
    Classify an entry using modeled atmospheric deposition and
    surviving ground-impact kinetic energy.

    The atmospheric energy is currently a drag-work proxy, not a
    complete thermodynamic atmospheric energy budget.
    """

    if atmospheric_energy_J < 0:
        raise ValueError("atmospheric_energy_J cannot be negative")

    if ground_impact_energy_J < 0:
        raise ValueError("ground_impact_energy_J cannot be negative")

    if not 0.0 <= minimum_atmospheric_fraction <= 1.0:
        raise ValueError(
            "minimum_atmospheric_fraction must be between 0 and 1"
        )

    total_energy = (
        atmospheric_energy_J
        + ground_impact_energy_J
    )

    if total_energy == 0.0:
        return AirburstClassification(
            outcome="no_significant_energy",
            atmospheric_energy_J=0.0,
            ground_impact_energy_J=0.0,
            atmospheric_fraction=0.0,
        )

    atmospheric_fraction = (
        atmospheric_energy_J / total_energy
    )

    if (
        atmospheric_fraction >= minimum_atmospheric_fraction
        and ground_impact_energy_J == 0.0
    ):
        outcome = "airburst"

    elif atmospheric_fraction >= minimum_atmospheric_fraction:
        outcome = "mixed"

    else:
        outcome = "ground_impact"

    return AirburstClassification(
        outcome=outcome,
        atmospheric_energy_J=atmospheric_energy_J,
        ground_impact_energy_J=ground_impact_energy_J,
        atmospheric_fraction=atmospheric_fraction,
    )
