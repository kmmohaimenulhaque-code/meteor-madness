from __future__ import annotations

import math
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from nasa_client import fetch_neos

from physics.consequences import (
    calculate_impact_consequences,
    consequences_to_dict,
)
from physics.location_engine import classify_surface
from physics.tsunami import estimate_tsunami
from physics.ai_analyst import generate_analyst_report
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    ImpactScenario,
    SimulationConfig,
)
from physics.parameter_resolver import (
    resolve_neo_to_physics,
)
from physics.solver import simulate
from physics.trajectory import (
    destination_from_downrange,
)


load_dotenv()


API_VERSION = "0.5.0"


app = FastAPI(
    title="Meteor Madness Physics API",
    version=API_VERSION,
)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================


class SimulationRequest(BaseModel):
    diameter_m: float = Field(gt=0)
    bulk_density_kg_m3: float = Field(gt=0)
    initial_velocity_m_s: float = Field(gt=0)

    entry_angle_rad: float = Field(
        gt=0,
        lt=math.pi / 2,
    )

    drag_coefficient: float = Field(
        ge=0
    )

    heat_transfer_coefficient: float = Field(
        ge=0
    )

    effective_heat_of_ablation_J_kg: float = Field(
        gt=0
    )

    material_strength_Pa: float = Field(
        gt=0
    )

    shape_factor: float = Field(
        gt=0
    )

    initial_altitude_m: float = Field(
        default=80_000.0,
        ge=0,
    )

    timestep_s: float = Field(
        default=0.01,
        gt=0,
    )

    max_time_s: float = Field(
        default=1000.0,
        gt=0,
    )

    latitude_deg: float = Field(
        default=0.0,
        ge=-90.0,
        le=90.0,
    )

    longitude_deg: float = Field(
        default=0.0,
        ge=-180.0,
        le=180.0,
    )

    entry_azimuth_deg: float = Field(
        default=90.0,
        ge=0.0,
        lt=360.0,
    )

    surface_hint: str | None = Field(
        default=None,
        description="Optional 'land' or 'ocean'. None = auto-classify.",
    )


class SimulationResponse(BaseModel):

    # V0.4
    consequences: dict[str, Any] | None = None

    # Status
    status: str
    outcome: str

    # Parent
    initial_mass_kg: float

    parent_final_mass_kg: float
    parent_final_altitude_m: float
    parent_final_velocity_m_s: float
    parent_final_energy_J: float

    # Impact
    impact_mass_kg: float | None = None
    impact_velocity_m_s: float | None = None
    impact_energy_J: float | None = None

    # Atmospheric
    total_drag_energy_J: float

    atmospheric_drag_work_J: float | None = None
    ground_impact_energy_J: float | None = None
    atmospheric_fraction: float | None = None

    # Fragmentation
    fragmentation_detected: bool
    fragmentation_altitude_m: float | None = None

    # Trajectory
    trajectory: dict[str, Any]

    # Profile
    profile: list[dict[str, Any]]


# ============================================================
# HELPERS
# ============================================================


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _get_optional_attribute(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:

    return getattr(
        obj,
        name,
        default,
    )


# ============================================================
# ROOT
# ============================================================


@app.get("/")
def root():

    return {
        "name": "Meteor Madness Physics API",
        "version": API_VERSION,
        "status": "online",
        "architecture": "Next Frontier (Location → Land/Ocean → Tsunami → AI Analyst)",
    }


# ============================================================
# NASA NEOWS
# ============================================================


@app.get("/api/neos")
async def get_neos(
    start_date: str | None = None,
    end_date: str | None = None,
):

    api_key = os.getenv(
        "NASA_API_KEY"
    )

    if not api_key:

        return {
            "status": "error",
            "message": (
                "NASA_API_KEY is not configured"
            ),
        }

    data = await fetch_neos(
        api_key=api_key,
        start_date=start_date,
        end_date=end_date,
    )

    return {
        "status": "ok",
        **data,
    }
