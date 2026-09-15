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


API_VERSION = "0.4.0"


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


# ============================================================
# TRAJECTORY
# ============================================================


def _build_trajectory(
    *,
    scenario: ImpactScenario,
    entry: EntryConditions,
    result: Any,
) -> dict[str, Any]:

    scenario.validate()
    entry.validate()

    samples = getattr(
        result,
        "samples",
        [],
    )

    if not samples:
        raise RuntimeError(
            "Simulation returned no samples."
        )

    initial_sample = samples[0]
    final_sample = samples[-1]

    initial_downrange_m = _safe_float(
        getattr(
            initial_sample,
            "downrange_m",
            0.0,
        )
    )

    final_downrange_m = _safe_float(
        getattr(
            final_sample,
            "downrange_m",
            0.0,
        )
    )

    initial_gamma = getattr(
        initial_sample,
        "flight_path_angle_rad",
        entry.entry_angle_rad,
    )

    final_gamma = getattr(
        final_sample,
        "flight_path_angle_rad",
        entry.entry_angle_rad,
    )

    final_altitude_m = _safe_float(
        getattr(
            final_sample,
            "altitude_m",
            0.0,
        )
    )

    destination = (
        destination_from_downrange(
            latitude_deg=(
                scenario.latitude_deg
            ),
            longitude_deg=(
                scenario.longitude_deg
            ),
            azimuth_deg=(
                scenario.entry_azimuth_deg
            ),
            downrange_m=(
                final_downrange_m
            ),
        )
    )

    return {

        "entry_latitude_deg": (
            scenario.latitude_deg
        ),

        "entry_longitude_deg": (
            scenario.longitude_deg
        ),

        "entry_azimuth_deg": (
            scenario.entry_azimuth_deg
        ),

        "entry_angle_deg": math.degrees(
            entry.entry_angle_rad
        ),

        "initial_downrange_m": (
            initial_downrange_m
        ),

        "final_downrange_m": (
            final_downrange_m
        ),

        "initial_flight_path_angle_deg": (
            math.degrees(
                _safe_float(
                    initial_gamma
                )
            )
        ),

        "final_flight_path_angle_deg": (
            math.degrees(
                _safe_float(
                    final_gamma
                )
            )
        ),

        "final_altitude_m": (
            final_altitude_m
        ),

        "final_latitude_deg": (
            _safe_float(
                destination[0]
            )
        ),

        "final_longitude_deg": (
            _safe_float(
                destination[1]
            )
        ),

        "coordinate_source": (
            "scenario_input_plus_dynamic_downrange"
        ),

        "model": (
            "V0.3 ballistic dynamic "
            "trajectory on a spherical Earth"
        ),

        "note": (
            "Geographic coordinates begin from "
            "scenario inputs. Final position is "
            "calculated from dynamically integrated "
            "surface downrange distance and entry "
            "azimuth. NASA NeoWs orbital geometry "
            "is not used."
        ),
    }


# ============================================================
# PROFILE
# ============================================================


def _build_profile(
    result: Any,
) -> list[dict[str, Any]]:

    samples = getattr(
        result,
        "samples",
        [],
    )

    profile = []

    for sample in samples:

        gamma_rad = getattr(
            sample,
            "flight_path_angle_rad",
            None,
        )

        downrange_m = getattr(
            sample,
            "downrange_m",
            None,
        )

        profile.append({

            "time_s": _safe_float(
                getattr(
                    sample,
                    "time_s",
                    0.0,
                )
            ),

            "altitude_m": _safe_float(
                getattr(
                    sample,
                    "altitude_m",
                    0.0,
                )
            ),

            "velocity_m_s": _safe_float(
                getattr(
                    sample,
                    "velocity_m_s",
                    0.0,
                )
            ),

            "mass_kg": _safe_float(
                getattr(
                    sample,
                    "mass_kg",
                    0.0,
                )
            ),

            "flight_path_angle_rad": (
                _safe_float(
                    gamma_rad
                )
                if gamma_rad is not None
                else None
            ),

            "flight_path_angle_deg": (
                math.degrees(
                    _safe_float(
                        gamma_rad
                    )
                )
                if gamma_rad is not None
                else None
            ),

            "downrange_m": (
                _safe_float(
                    downrange_m
                )
                if downrange_m is not None
                else None
            ),

            "density_kg_m3": _safe_float(
                getattr(
                    sample,
                    "density_kg_m3",
                    0.0,
                )
            ),

            "temperature_K": _safe_float(
                getattr(
                    sample,
                    "temperature_K",
                    0.0,
                )
            ),

            "pressure_Pa": _safe_float(
                getattr(
                    sample,
                    "pressure_Pa",
                    0.0,
                )
            ),

            "equivalent_radius_m": _safe_float(
                getattr(
                    sample,
                    "equivalent_radius_m",
                    0.0,
                )
            ),

            "projected_area_m2": _safe_float(
                getattr(
                    sample,
                    "projected_area_m2",
                    0.0,
                )
            ),

            "drag_force_N": _safe_float(
                getattr(
                    sample,
                    "drag_force_N",
                    0.0,
                )
            ),

            "drag_acceleration_m_s2": _safe_float(
                getattr(
                    sample,
                    "drag_acceleration_m_s2",
                    0.0,
                )
            ),

            "drag_power_W": _safe_float(
                getattr(
                    sample,
                    "drag_power_W",
                    0.0,
                )
            ),

            "kinetic_energy_J": _safe_float(
                getattr(
                    sample,
                    "kinetic_energy_J",
                    0.0,
                )
            ),

            "dynamic_pressure_Pa": _safe_float(
                getattr(
                    sample,
                    "dynamic_pressure_Pa",
                    0.0,
                )
            ),

            "mass_loss_rate_kg_s": _safe_float(
                getattr(
                    sample,
                    "mass_loss_rate_kg_s",
                    0.0,
                )
            ),

            "energy_deposition_J": _safe_float(
                getattr(
                    sample,
                    "energy_deposition_J",
                    0.0,
                )
            ),

            "energy_deposition_per_meter_J_m": (
                _safe_float(
                    getattr(
                        sample,
                        "energy_deposition_per_meter_J_m",
                        0.0,
                    )
                )
            ),
        })

    return profile


# ============================================================
# IMPACT SUMMARY
# ============================================================


def _build_impact_summary(
    result: Any,
) -> tuple[
    float | None,
    float | None,
    float | None,
]:

    trajectories = getattr(
        result,
        "fragment_trajectories",
        [],
    )

    if not trajectories:
        return None, None, None

    impact_mass = 0.0
    impact_energy = 0.0
    impact_count = 0

    for trajectory in trajectories:

        outcome = getattr(
            trajectory,
            "outcome",
            None,
        )

        if outcome is None:
            continue

        if getattr(
            outcome,
            "outcome",
            None,
        ) != "ground_impact":
            continue

        mass_kg = _safe_float(
            getattr(
                outcome,
                "mass_kg",
                0.0,
            )
        )

        energy_J = _safe_float(
            getattr(
                outcome,
                "kinetic_energy_J",
                0.0,
            )
        )

        if mass_kg <= 0.0:
            continue

        impact_mass += mass_kg
        impact_energy += max(
            energy_J,
            0.0,
        )

        impact_count += 1

    if (
        impact_count == 0
        or impact_mass <= 0.0
    ):
        return None, None, None

    if impact_energy <= 0.0:
        return (
            impact_mass,
            0.0,
            0.0,
        )

    impact_velocity = math.sqrt(
        2.0
        * impact_energy
        / impact_mass
    )

    return (
        impact_mass,
        impact_velocity,
        impact_energy,
    )


# ============================================================
# FRAGMENTATION
# ============================================================


def _build_fragmentation_summary(
    result: Any,
) -> tuple[
    bool,
    float | None,
]:

    events = getattr(
        result,
        "events",
        [],
    )

    for event in events:

        if getattr(
            event,
            "type",
            None,
        ) != "fragmentation":
            continue

        altitude = getattr(
            event,
            "altitude_m",
            None,
        )

        return (
            True,
            (
                _safe_float(altitude)
                if altitude is not None
                else None
            ),
        )

    return False, None


# ============================================================
# V0.4 CONSEQUENCES
# ============================================================


def _build_consequences_summary(
    *,
    result: Any,
    asteroid: AsteroidParameters,
    entry: EntryConditions,
) -> dict[str, Any] | None:

    trajectories = getattr(
        result,
        "fragment_trajectories",
        [],
    )

    fragment_consequences = []

    # ---------------------------------------------------------
    # Fragmented impact
    # ---------------------------------------------------------

    for trajectory in trajectories:

        outcome = getattr(
            trajectory,
            "outcome",
            None,
        )

        if outcome is None:
            continue

        if getattr(
            outcome,
            "outcome",
            None,
        ) != "ground_impact":
            continue

        consequence = getattr(
            trajectory,
            "consequences",
            None,
        )

        if consequence is not None:
            fragment_consequences.append(
                consequence
            )

    if fragment_consequences:

        total_mass_kg = sum(
            float(
                consequence
                .surviving_mass_kg
            )
            for consequence
            in fragment_consequences
        )

        total_energy_J = sum(
            float(
                consequence
                .impact_energy_J
            )
            for consequence
            in fragment_consequences
        )

        if (
            total_mass_kg > 0.0
            and total_energy_J > 0.0
        ):
            aggregate_velocity = math.sqrt(
                2.0
                * total_energy_J
                / total_mass_kg
            )
        else:
            aggregate_velocity = 0.0

        largest = max(
            fragment_consequences,
            key=lambda item: (
                item.final_crater_diameter_m
            ),
        )

        combined_crater_area_m2 = sum(
            math.pi
            * (
                consequence
                .final_crater_diameter_m
                / 2.0
            ) ** 2
            for consequence
            in fragment_consequences
        )

        return {

            "scenario": (
                "fragmented_ground_impacts"
            ),

            "fragment_count": len(
                fragment_consequences
            ),

            "crater_count": len(
                fragment_consequences
            ),

            "surviving_mass_kg": (
                total_mass_kg
            ),

            "impact_velocity_m_s": (
                aggregate_velocity
            ),

            "impact_energy_J": (
                total_energy_J
            ),

            "impact_energy_megatons_tnt": (
                total_energy_J
                / 4.184e15
            ),

            "largest_crater": (
                consequences_to_dict(
                    largest
                )
            ),

            "combined_crater_area_m2": (
                combined_crater_area_m2
            ),

            "maximum_thermal_radius_m": max(
                consequence
                .thermal_radius_m
                for consequence
                in fragment_consequences
            ),

            "maximum_blast_radius_m": max(
                consequence
                .blast_radius_m
                for consequence
                in fragment_consequences
            ),

            "maximum_seismic_radius_m": max(
                consequence
                .seismic_radius_m
                for consequence
                in fragment_consequences
            ),

            "fragment_consequences": [
                consequences_to_dict(
                    consequence
                )
                for consequence
                in fragment_consequences
            ],

            "model_notes": [
                (
                    "Fragment consequences are "
                    "calculated independently."
                ),
                (
                    "Largest crater is reported "
                    "as the primary crater visual."
                ),
                (
                    "Combined crater area is the "
                    "sum of individual crater areas."
                ),
                (
                    "Thermal, blast and seismic "
                    "radii are screening estimates."
                ),
            ],
        }

    # ---------------------------------------------------------
    # Single-body impact
    # ---------------------------------------------------------

    samples = getattr(
        result,
        "samples",
        [],
    )

    if samples:

        final = samples[-1]

        altitude = _safe_float(
            getattr(
                final,
                "altitude_m",
                0.0,
            )
        )

        if altitude <= 0.0:

            mass = max(
                _safe_float(
                    getattr(
                        final,
                        "mass_kg",
                        0.0,
                    )
                ),
                0.0,
            )

            velocity = max(
                _safe_float(
                    getattr(
                        final,
                        "velocity_m_s",
                        0.0,
                    )
                ),
                0.0,
            )

            consequence = (
                calculate_impact_consequences(
                    outcome="ground_impact",
                    mass_kg=mass,
                    velocity_m_s=velocity,
                    bulk_density_kg_m3=(
                        asteroid.bulk_density_kg_m3
                    ),
                    impact_angle_rad=(
                        entry.entry_angle_rad
                    ),
                )
            )

            return {
                "scenario": (
                    "single_body_ground_impact"
                ),

                **consequences_to_dict(
                    consequence
                ),

                "fragment_count": 0,
                "crater_count": 1,
            }

    return None


# ============================================================
# RESPONSE BUILDER
# ============================================================


def _build_simulation_response(
    result: Any,
    *,
    scenario: ImpactScenario,
    entry: EntryConditions,
    asteroid: AsteroidParameters,
) -> SimulationResponse:

    samples = getattr(
        result,
        "samples",
        [],
    )

    if not samples:
        raise RuntimeError(
            "Physics solver returned no samples."
        )

    initial = samples[0]
    final = samples[-1]

    initial_mass = _safe_float(
        getattr(
            initial,
            "mass_kg",
            0.0,
        )
    )

    (
        impact_mass,
        impact_velocity,
        impact_energy,
    ) = _build_impact_summary(
        result
    )

    (
        fragmentation_detected,
        fragmentation_altitude,
    ) = _build_fragmentation_summary(
        result
    )

    event_energy = getattr(
        result,
        "event_energy",
        None,
    )

    airburst = getattr(
        result,
        "airburst_classification",
        None,
    )

    outcome = getattr(
        airburst,
        "outcome",
        None,
    )

    if outcome is None:

        events = getattr(
            result,
            "events",
            [],
        )

        if events:

            outcome = getattr(
                events[-1],
                "type",
                "completed",
            )

        else:
            outcome = "completed"

    atmospheric_drag_work = None
    ground_impact_energy = None
    atmospheric_fraction = None

    if event_energy is not None:

        value = getattr(
            event_energy,
            "atmospheric_drag_work_J",
            None,
        )

        if value is not None:
            atmospheric_drag_work = (
                _safe_float(value)
            )

        value = getattr(
            event_energy,
            "ground_impact_energy_J",
            None,
        )

        if value is not None:
            ground_impact_energy = (
                _safe_float(value)
            )

        value = getattr(
            event_energy,
            "atmospheric_fraction",
            None,
        )

        if value is not None:
            atmospheric_fraction = (
                _safe_float(value)
            )

    consequences = (
        _build_consequences_summary(
            result=result,
            asteroid=asteroid,
            entry=entry,
        )
    )

    return SimulationResponse(

        status="completed",

        outcome=str(
            outcome
        ),

        initial_mass_kg=(
            initial_mass
        ),

        parent_final_mass_kg=(
            _safe_float(
                getattr(
                    final,
                    "mass_kg",
                    0.0,
                )
            )
        ),

        parent_final_altitude_m=(
            _safe_float(
                getattr(
                    final,
                    "altitude_m",
                    0.0,
                )
            )
        ),

        parent_final_velocity_m_s=(
            _safe_float(
                getattr(
                    final,
                    "velocity_m_s",
                    0.0,
                )
            )
        ),

        parent_final_energy_J=(
            _safe_float(
                getattr(
                    final,
                    "kinetic_energy_J",
                    0.0,
                )
            )
        ),

        impact_mass_kg=(
            impact_mass
        ),

        impact_velocity_m_s=(
            impact_velocity
        ),

        impact_energy_J=(
            impact_energy
        ),

        total_drag_energy_J=(
            _safe_float(
                getattr(
                    result,
                    "total_drag_energy_J",
                    0.0,
                )
            )
        ),

        atmospheric_drag_work_J=(
            atmospheric_drag_work
        ),

        ground_impact_energy_J=(
            ground_impact_energy
        ),

        atmospheric_fraction=(
            atmospheric_fraction
        ),

        fragmentation_detected=(
            fragmentation_detected
        ),

        fragmentation_altitude_m=(
            fragmentation_altitude
        ),

        consequences=(
            consequences
        ),

        trajectory=_build_trajectory(
            scenario=scenario,
            entry=entry,
            result=result,
        ),

        profile=_build_profile(
            result
        ),
    )


# ============================================================
# DIRECT SIMULATION
# ============================================================


@app.post(
    "/api/simulation/entry",
    response_model=SimulationResponse,
)
def run_entry_simulation(
    request: SimulationRequest,
):

    asteroid = AsteroidParameters(
        diameter_m=request.diameter_m,
        bulk_density_kg_m3=(
            request.bulk_density_kg_m3
        ),
        drag_coefficient=(
            request.drag_coefficient
        ),
        heat_transfer_coefficient=(
            request.heat_transfer_coefficient
        ),
        effective_heat_of_ablation_J_kg=(
            request.effective_heat_of_ablation_J_kg
        ),
        material_strength_Pa=(
            request.material_strength_Pa
        ),
        shape_factor=(
            request.shape_factor
        ),
    )

    entry = EntryConditions(
        initial_altitude_m=(
            request.initial_altitude_m
        ),
        initial_velocity_m_s=(
            request.initial_velocity_m_s
        ),
        entry_angle_rad=(
            request.entry_angle_rad
        ),
    )

    scenario = ImpactScenario(
        latitude_deg=(
            request.latitude_deg
        ),
        longitude_deg=(
            request.longitude_deg
        ),
        entry_azimuth_deg=(
            request.entry_azimuth_deg
        ),
    )

    config = SimulationConfig(
        timestep_s=request.timestep_s,
        max_time_s=request.max_time_s,
    )

    asteroid.validate()
    entry.validate()
    scenario.validate()
    config.validate()

    result = simulate(
        asteroid=asteroid,
        entry=entry,
        config=config,
        scenario=scenario,
    )

    return _build_simulation_response(
        result,
        scenario=scenario,
        entry=entry,
        asteroid=asteroid,
    )


# ============================================================
# NASA -> SIMULATION
# ============================================================


@app.post(
    "/api/simulation/from-neo"
)
async def simulate_from_neo(
    asteroid_id: str,
    latitude_deg: float = 0.0,
    longitude_deg: float = 0.0,
    entry_azimuth_deg: float = 90.0,
):

    scenario = ImpactScenario(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        entry_azimuth_deg=entry_azimuth_deg,
    )

    scenario.validate()

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
        api_key=api_key
    )

    asteroids = data.get(
        "asteroids",
        [],
    )

    neo = next(
        (
            asteroid
            for asteroid in asteroids
            if str(
                asteroid.get("id")
            )
            == str(asteroid_id)
        ),
        None,
    )

    if neo is None:

        return {
            "status": "error",
            "message": (
                f"Asteroid {asteroid_id} "
                "was not found in the "
                "current NASA feed"
            ),
        }

    resolved = resolve_neo_to_physics(
        neo
    )

    result = simulate(
        asteroid=resolved.asteroid,
        entry=resolved.entry,
        config=SimulationConfig(),
        scenario=scenario,
    )

    simulation_response = (
        _build_simulation_response(
            result,
            scenario=scenario,
            entry=resolved.entry,
            asteroid=resolved.asteroid,
        )
    )

    return {

        "status": "completed",

        "asteroid": {
            "id": (
                resolved.asteroid_id
            ),

            "name": (
                resolved.name
            ),

            "hazardous": (
                resolved.hazardous
            ),

            "diameter_km": (
                neo["diameter_km"]
            ),

            "approach_date": (
                neo["approach_date"]
            ),

            "miss_distance_km": (
                neo["miss_distance_km"]
            ),

            "velocity_kph": (
                neo["velocity_kph"]
            ),
        },

        "assumptions": (
            resolved.assumptions
        ),

        "trajectory": (
            simulation_response.trajectory
        ),

        "simulation": (
            simulation_response.model_dump()
        ),
    }
