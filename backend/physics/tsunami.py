"""
Tsunami screening model for ocean impacts.

Engineering approximation only.
Not a full hydrodynamic tsunami simulation.

Based on simple energy-to-wave-height scaling used in
planetary-defense screening literature.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


JOULES_PER_MEGATON_TNT = 4.184e15


@dataclass(frozen=True)
class TsunamiEstimate:
    """Screening-level tsunami metrics for an ocean impact."""

    applicable: bool
    impact_energy_J: float
    impact_energy_megatons_tnt: float

    # Very approximate deep-water wave amplitude near source
    estimated_source_amplitude_m: float

    # Order-of-magnitude coastal run-up indicator (highly uncertain)
    estimated_coastal_runup_indicator_m: float

    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applicable": self.applicable,
            "impact_energy_J": self.impact_energy_J,
            "impact_energy_megatons_tnt": self.impact_energy_megatons_tnt,
            "estimated_source_amplitude_m": self.estimated_source_amplitude_m,
            "estimated_coastal_runup_indicator_m": (
                self.estimated_coastal_runup_indicator_m
            ),
            "notes": list(self.notes),
        }


def estimate_tsunami(
    *,
    impact_energy_J: float,
    surface_is_ocean: bool,
    water_depth_m: float = 4000.0,
) -> TsunamiEstimate:
    """
    Produce a transparent screening tsunami estimate.

    Assumptions (explicit):
    - Only applied when surface is classified as ocean.
    - Energy coupling to the water column is a small fraction.
    - Source amplitude scales roughly with the cube-root of energy
      (order-of-magnitude only).
    - Coastal run-up is a highly uncertain multiplier of source amplitude.

    This is an educational / screening tool, not a forecast.
    """

    notes = [
        "Tsunami model is a first-order energy-scaling screening estimate.",
        "It is not a hydrodynamic simulation.",
        "Real tsunami height depends strongly on bathymetry, distance and local topography.",
        "Use only for relative risk illustration.",
    ]

    if not surface_is_ocean or impact_energy_J <= 0.0:
        return TsunamiEstimate(
            applicable=False,
            impact_energy_J=max(impact_energy_J, 0.0),
            impact_energy_megatons_tnt=max(impact_energy_J, 0.0)
            / JOULES_PER_MEGATON_TNT,
            estimated_source_amplitude_m=0.0,
            estimated_coastal_runup_indicator_m=0.0,
            notes=tuple(notes + ["Not applicable (land impact or zero energy)."]),
        )

    # Very rough coupling fraction of kinetic energy into the water column
    water_coupling = 0.05
    coupled = impact_energy_J * water_coupling

    # Order-of-magnitude source amplitude (m)
    # Scaled so that ~1 Mt class events produce metres-scale waves near source
    # in deep water. Purely illustrative.
    mt = coupled / JOULES_PER_MEGATON_TNT
    source_amplitude = 0.8 * (max(mt, 1e-6) ** (1.0 / 3.0))

    # Coastal run-up indicator (even more uncertain)
    runup_indicator = source_amplitude * 2.5

    # Mild depth dependence (deeper water → slightly lower amplitude for same energy)
    depth_factor = math.sqrt(4000.0 / max(water_depth_m, 500.0))
    source_amplitude *= depth_factor
    runup_indicator *= depth_factor

    return TsunamiEstimate(
        applicable=True,
        impact_energy_J=impact_energy_J,
        impact_energy_megatons_tnt=impact_energy_J / JOULES_PER_MEGATON_TNT,
        estimated_source_amplitude_m=round(source_amplitude, 2),
        estimated_coastal_runup_indicator_m=round(runup_indicator, 2),
        notes=tuple(notes),
    )
