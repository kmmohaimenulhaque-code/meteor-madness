"""
Location / Environment Engine

Coordinates → surface classification → material + elevation context

Offline-capable demo. Real systems should replace heuristics with
GEBCO / land-cover / cryosphere datasets (terrain_source field).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


SurfaceType = Literal["land", "ocean", "ice", "unknown"]


@dataclass(frozen=True)
class MaterialContext:
    type: str
    density_kg_m3: float


@dataclass(frozen=True)
class EnvironmentContext:
    """Full environment payload for consequence branching."""

    latitude: float
    longitude: float
    surface: SurfaceType
    surface_confidence: float
    elevation_m: float | None
    bathymetry_m: float | None
    terrain_source: str
    material: MaterialContext
    data_status: str  # observed_model | heuristic | user_specified
    terrain_label: str
    material_notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinates": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "surface": self.surface,
            "surface_confidence": self.surface_confidence,
            "elevation_m": self.elevation_m,
            "bathymetry_m": self.bathymetry_m,
            "terrain_source": self.terrain_source,
            "material": {
                "type": self.material.type,
                "density_kg_m3": self.material.density_kg_m3,
            },
            "data_status": self.data_status,
            # Back-compat aliases used by older UI / enrichment
            "surface_type": self.surface,
            "confidence": self.surface_confidence,
            "target_density_kg_m3": self.material.density_kg_m3,
            "terrain_label": self.terrain_label,
            "material_notes": self.material_notes,
        }


# Representative densities (kg/m³)
LAND_CRYSTALLINE_DENSITY = 2700.0
LAND_SEDIMENTARY_DENSITY = 2200.0
OCEAN_WATER_DENSITY = 1025.0
ICE_DENSITY = 917.0


def classify_surface(
    latitude_deg: float,
    longitude_deg: float,
    surface_hint: str | None = None,
) -> EnvironmentContext:
    """
    Resolve surface type, material, and elevation/bathymetry context.

    Priority:
    1. Explicit surface_hint ("land" | "ocean" | "ice")
    2. Coarse geographic heuristic (demo only)
    3. Default land with reduced confidence
    """

    lat = float(latitude_deg)
    lon = float(longitude_deg)

    if surface_hint is not None:
        hint = surface_hint.strip().lower()
        if hint == "ocean":
            return EnvironmentContext(
                latitude=lat,
                longitude=lon,
                surface="ocean",
                surface_confidence=0.99,
                elevation_m=None,
                bathymetry_m=4000.0,
                terrain_source="user_specified",
                material=MaterialContext(
                    type="seawater",
                    density_kg_m3=OCEAN_WATER_DENSITY,
                ),
                data_status="user_specified",
                terrain_label="Open ocean (user-specified)",
                material_notes="Water column; tsunami + seafloor screening applies",
            )
        if hint == "ice":
            return EnvironmentContext(
                latitude=lat,
                longitude=lon,
                surface="ice",
                surface_confidence=0.99,
                elevation_m=50.0,
                bathymetry_m=None,
                terrain_source="user_specified",
                material=MaterialContext(
                    type="ice",
                    density_kg_m3=ICE_DENSITY,
                ),
                data_status="user_specified",
                terrain_label="Ice sheet / sea ice (user-specified)",
                material_notes="Ice response screening model applies",
            )
        if hint == "land":
            return EnvironmentContext(
                latitude=lat,
                longitude=lon,
                surface="land",
                surface_confidence=0.99,
                elevation_m=200.0,
                bathymetry_m=None,
                terrain_source="user_specified",
                material=MaterialContext(
                    type="crystalline_crust",
                    density_kg_m3=LAND_CRYSTALLINE_DENSITY,
                ),
                data_status="user_specified",
                terrain_label="Continental crust (user-specified)",
                material_notes="Assumed crystalline target density 2700 kg/m³",
            )

    abs_lat = abs(lat)

    # Polar ice heuristic
    if abs_lat >= 70.0:
        return EnvironmentContext(
            latitude=lat,
            longitude=lon,
            surface="ice",
            surface_confidence=0.65,
            elevation_m=100.0 if abs_lat >= 75 else 20.0,
            bathymetry_m=None,
            terrain_source="polar_heuristic_v1",
            material=MaterialContext(
                type="ice",
                density_kg_m3=ICE_DENSITY,
            ),
            data_status="heuristic",
            terrain_label="Likely ice (polar heuristic)",
            material_notes="Heuristic only. Replace with cryosphere datasets.",
        )

    is_likely_ocean = False
    if abs_lat < 60:
        if (lon < -80 or lon > 120) and abs_lat < 50:
            is_likely_ocean = True
        if -60 < lon < -10 and abs_lat < 55:
            is_likely_ocean = True
        if 40 < lon < 110 and abs_lat < 30:
            is_likely_ocean = True

    if is_likely_ocean:
        # Placeholder bathymetry until GEBCO is wired
        depth = 3500.0 if abs_lat < 40 else 2500.0
        return EnvironmentContext(
            latitude=lat,
            longitude=lon,
            surface="ocean",
            surface_confidence=0.55,
            elevation_m=-depth,
            bathymetry_m=depth,
            terrain_source="GEBCO_placeholder_heuristic",
            material=MaterialContext(
                type="seawater",
                density_kg_m3=OCEAN_WATER_DENSITY,
            ),
            data_status="heuristic",
            terrain_label="Likely ocean (coarse geographic heuristic)",
            material_notes=(
                "Heuristic classification only. "
                "Replace with GEBCO bathymetry for production."
            ),
        )

    return EnvironmentContext(
        latitude=lat,
        longitude=lon,
        surface="land",
        surface_confidence=0.60,
        elevation_m=150.0,
        bathymetry_m=None,
        terrain_source="land_heuristic_v1",
        material=MaterialContext(
            type="crystalline_crust",
            density_kg_m3=LAND_CRYSTALLINE_DENSITY,
        ),
        data_status="heuristic",
        terrain_label="Likely land (default / coarse heuristic)",
        material_notes="Assumed crystalline target density 2700 kg/m³",
    )


# Back-compat alias
TerrainContext = EnvironmentContext
