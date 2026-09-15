"""
Location Engine — surface type, terrain and material context.

Part of the Next Frontier architecture:
Coordinates → Location Engine → Impact Environment (Land / Ocean)

This module is deliberately simple and offline-capable.
It does not call external GIS services so the demo remains
reproducible without network dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SurfaceType = Literal["land", "ocean", "unknown"]


@dataclass(frozen=True)
class TerrainContext:
    """Resolved surface and material context for consequence modelling."""

    surface_type: SurfaceType
    target_density_kg_m3: float
    terrain_label: str
    material_notes: str
    confidence: float  # 0–1, how certain we are about the surface classification


# Representative target densities (kg/m³)
LAND_CRYSTALLINE_DENSITY = 2700.0
LAND_SEDIMENTARY_DENSITY = 2200.0
OCEAN_WATER_DENSITY = 1025.0


def classify_surface(
    latitude_deg: float,
    longitude_deg: float,
    surface_hint: str | None = None,
) -> TerrainContext:
    """
    Resolve surface type and material context.

    Priority:
    1. Explicit surface_hint from the user/scenario ("land" or "ocean")
    2. Simple geographic heuristic (very coarse, for demo only)
    3. Default to land with reduced confidence

    The heuristic is intentionally transparent and limited.
    It is NOT a substitute for real bathymetry / land-cover data.
    """

    if surface_hint is not None:
        hint = surface_hint.strip().lower()
        if hint in ("land", "ocean"):
            if hint == "ocean":
                return TerrainContext(
                    surface_type="ocean",
                    target_density_kg_m3=OCEAN_WATER_DENSITY,
                    terrain_label="Open ocean (user-specified)",
                    material_notes="Water column; tsunami screening model applies",
                    confidence=0.95,
                )
            return TerrainContext(
                surface_type="land",
                target_density_kg_m3=LAND_CRYSTALLINE_DENSITY,
                terrain_label="Continental crust (user-specified)",
                material_notes="Assumed crystalline target density 2700 kg/m³",
                confidence=0.95,
            )

    # Very coarse offline heuristic for demo purposes only.
    # Real systems should use GEBCO / land-cover datasets.
    lat = abs(latitude_deg)
    lon = longitude_deg

    # Rough oceanic basins (simplified)
    is_likely_ocean = False
    if lat < 60:
        # Pacific-ish
        if (lon < -80 or lon > 120) and lat < 50:
            is_likely_ocean = True
        # Atlantic-ish
        if -60 < lon < -10 and lat < 55:
            is_likely_ocean = True
        # Indian Ocean-ish
        if 40 < lon < 110 and lat < 30:
            is_likely_ocean = True

    if is_likely_ocean:
        return TerrainContext(
            surface_type="ocean",
            target_density_kg_m3=OCEAN_WATER_DENSITY,
            terrain_label="Likely ocean (coarse geographic heuristic)",
            material_notes=(
                "Heuristic classification only. "
                "Replace with bathymetry for production use."
            ),
            confidence=0.55,
        )

    return TerrainContext(
        surface_type="land",
        target_density_kg_m3=LAND_CRYSTALLINE_DENSITY,
        terrain_label="Likely land (default / coarse heuristic)",
        material_notes="Assumed crystalline target density 2700 kg/m³",
        confidence=0.60,
    )
