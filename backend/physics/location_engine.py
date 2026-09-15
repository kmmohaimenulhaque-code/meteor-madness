"""
Environment Engine — REAL elevation / bathymetry lookup only.

Pipeline:
  lat/lon → OpenTopoData GEBCO 2020 → land/ocean → material → physics branch

CRITICAL RULE:
  No data = NO GUESS.
  If the Earth-data provider fails or returns null elevation:
    surface = unknown
    confidence = 0.0
    source = unavailable
    physics_branch must be undetermined (handled by impact_environment).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

import httpx


SurfaceType = Literal["land", "ocean", "ice", "unknown"]

# Public GEBCO 2020 via OpenTopoData (global land elevation + bathymetry)
DEFAULT_ELEVATION_URL = (
    "https://api.opentopodata.org/v1/gebco2020"
)
ELEVATION_DATASET = "gebco2020"


@dataclass(frozen=True)
class MaterialContext:
    type: str
    density_kg_m3: float


@dataclass(frozen=True)
class EnvironmentContext:
    latitude: float
    longitude: float
    surface: SurfaceType
    surface_confidence: float
    elevation_m: float | None
    bathymetry_m: float | None
    terrain_source: str
    material: MaterialContext | None
    data_status: str  # observed_model | user_specified | unavailable
    terrain_label: str
    material_notes: str
    physics_branch: str  # land | ocean | ice | undetermined

    def to_dict(self) -> dict[str, Any]:
        material_dict = None
        if self.material is not None:
            material_dict = {
                "type": self.material.type,
                "density_kg_m3": self.material.density_kg_m3,
            }

        return {
            "coordinates": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "surface": self.surface,
            "surface_confidence": self.surface_confidence,
            "confidence": self.surface_confidence,
            "elevation_m": self.elevation_m,
            "bathymetry_m": self.bathymetry_m,
            "terrain_source": self.terrain_source,
            "source": self.terrain_source,
            "material": material_dict,
            "data_status": self.data_status,
            "physics_branch": self.physics_branch,
            # Back-compat aliases
            "surface_type": self.surface,
            "target_density_kg_m3": (
                self.material.density_kg_m3 if self.material else None
            ),
            "terrain_label": self.terrain_label,
            "material_notes": self.material_notes,
        }


LAND_DENSITY = 2700.0
OCEAN_DENSITY = 1025.0
ICE_DENSITY = 917.0


def _unavailable(
    lat: float,
    lon: float,
    reason: str,
) -> EnvironmentContext:
    return EnvironmentContext(
        latitude=lat,
        longitude=lon,
        surface="unknown",
        surface_confidence=0.0,
        elevation_m=None,
        bathymetry_m=None,
        terrain_source="unavailable",
        material=None,
        data_status="unavailable",
        terrain_label=f"Environment data unavailable ({reason})",
        material_notes=(
            "No elevation/bathymetry observation. "
            "Environment-specific physics is refused."
        ),
        physics_branch="undetermined",
    )


def _from_elevation(
    lat: float,
    lon: float,
    elevation_m: float,
    dataset: str,
) -> EnvironmentContext:
    """Map observed elevation to land/ocean (no geographic guessing)."""

    # GEBCO: positive ≈ land/ice surface elevation, negative ≈ seafloor depth
    if elevation_m < 0.0:
        depth = abs(elevation_m)
        return EnvironmentContext(
            latitude=lat,
            longitude=lon,
            surface="ocean",
            surface_confidence=0.95,
            elevation_m=elevation_m,
            bathymetry_m=depth,
            terrain_source=dataset,
            material=MaterialContext(
                type="seawater",
                density_kg_m3=OCEAN_DENSITY,
            ),
            data_status="observed_model",
            terrain_label=f"Ocean (observed {dataset})",
            material_notes=f"Seafloor depth {depth:.1f} m from {dataset}",
            physics_branch="ocean",
        )

    # elevation >= 0 → land (or ice surface elevation in polar regions).
    # Without a dedicated cryosphere product we do NOT invent "ice".
    # User may still force ice via surface_hint.
    return EnvironmentContext(
        latitude=lat,
        longitude=lon,
        surface="land",
        surface_confidence=0.95,
        elevation_m=elevation_m,
        bathymetry_m=None,
        terrain_source=dataset,
        material=MaterialContext(
            type="crystalline_crust",
            density_kg_m3=LAND_DENSITY,
        ),
        data_status="observed_model",
        terrain_label=f"Land (observed {dataset})",
        material_notes=(
            f"Surface elevation {elevation_m:.1f} m from {dataset}. "
            f"Assumed crust density {LAND_DENSITY} kg/m³."
        ),
        physics_branch="land",
    )


def _fetch_gebco_elevation(
    latitude_deg: float,
    longitude_deg: float,
) -> tuple[float | None, str]:
    """
    Query OpenTopoData GEBCO 2020.

    Returns (elevation_m, status_note).
    elevation_m is None when the provider fails or returns null.
    """
    base = os.getenv("ELEVATION_API_URL", DEFAULT_ELEVATION_URL).rstrip("/")
    # Allow either full path .../gebco2020 or base host
    if base.endswith("/v1") or base.rstrip("/").endswith("opentopodata.org"):
        url = f"{base.rstrip('/')}/gebco2020"
    elif "gebco" in base:
        url = base
    else:
        url = DEFAULT_ELEVATION_URL

    params = {
        "locations": f"{latitude_deg},{longitude_deg}",
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # network / timeout / HTTP
        return None, f"provider_error:{type(exc).__name__}"

    if not isinstance(payload, dict):
        return None, "invalid_payload"

    if str(payload.get("status", "")).upper() not in ("OK", ""):
        return None, f"status:{payload.get('status')}"

    results = payload.get("results") or []
    if not results:
        return None, "empty_results"

    first = results[0] or {}
    elevation = first.get("elevation")
    if elevation is None:
        return None, "null_elevation"

    try:
        return float(elevation), ELEVATION_DATASET
    except (TypeError, ValueError):
        return None, "non_numeric_elevation"


def classify_surface(
    latitude_deg: float,
    longitude_deg: float,
    surface_hint: str | None = None,
) -> EnvironmentContext:
    """
    Resolve environment from REAL data only.

    Priority:
    1. Explicit surface_hint ("land" | "ocean" | "ice") — user override
    2. Live GEBCO elevation/bathymetry lookup
    3. Unavailable → unknown (NO heuristic guess)
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
                bathymetry_m=None,
                terrain_source="user_specified",
                material=MaterialContext(
                    type="seawater",
                    density_kg_m3=OCEAN_DENSITY,
                ),
                data_status="user_specified",
                terrain_label="Ocean (user-specified)",
                material_notes="User forced ocean surface; bathymetry not observed.",
                physics_branch="ocean",
            )
        if hint == "land":
            return EnvironmentContext(
                latitude=lat,
                longitude=lon,
                surface="land",
                surface_confidence=0.99,
                elevation_m=None,
                bathymetry_m=None,
                terrain_source="user_specified",
                material=MaterialContext(
                    type="crystalline_crust",
                    density_kg_m3=LAND_DENSITY,
                ),
                data_status="user_specified",
                terrain_label="Land (user-specified)",
                material_notes="User forced land surface; elevation not observed.",
                physics_branch="land",
            )
        if hint == "ice":
            return EnvironmentContext(
                latitude=lat,
                longitude=lon,
                surface="ice",
                surface_confidence=0.99,
                elevation_m=None,
                bathymetry_m=None,
                terrain_source="user_specified",
                material=MaterialContext(
                    type="ice",
                    density_kg_m3=ICE_DENSITY,
                ),
                data_status="user_specified",
                terrain_label="Ice (user-specified)",
                material_notes="User forced ice surface; no cryosphere product used.",
                physics_branch="ice",
            )
        # Invalid hint → do not guess; fall through to live lookup

    elevation, note = _fetch_gebco_elevation(lat, lon)
    if elevation is None:
        return _unavailable(lat, lon, note)

    return _from_elevation(lat, lon, elevation, note)


# Back-compat alias
TerrainContext = EnvironmentContext
