from __future__ import annotations

import math
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from nasa_client import fetch_neos

from physics.airburst import AirburstClassification
from physics.parameter_resolver import resolve_neo_to_physics
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    ImpactScenario,
    SimulationConfig,
)
from physics.solver import simulate


load_dotenv()


app = FastAPI(
    title="Meteor Madness Physics API",
    version="0.2.0",
)


class SimulationRequest(BaseModel):
    diameter_m: float = Field(gt=0)
    bulk_density_kg_m3: float = Field(gt=0)
    initial_velocity_m_s: float = Field(gt=0)
    entry_angle_rad: float = Field(gt=0, lt=math.pi / 2)

    drag_coefficient: float = Field(ge=0)
    heat_transfer_coefficient: float = Field(ge=0)
    effective_heat_of_ablation_J_kg: float = Field(gt=0)
    material_strength_Pa: float = Field(gt=0)
    shape_factor: float = Field(gt=0)

    initial_altitude_m: float = Field(default=80_000.0, ge=0)
    timestep_s: float = Field(default=0.01, gt=0)
    max_time_s: float = Field(default=1000.0, gt=0)

    # ---------------------------------------------------------
    # V0.2 geographic scenario
    #
    # These are scenario inputs, not values derived from NASA.
    # ---------------------------------------------------------

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
    status: str
    outcome: str

    initial_mass_kg: float

    parent_final_mass_kg: float
    parent_final_altitude_m: float
    parent_final_velocity_m_s: float
    parent_final_energy_J: float

    impact_mass_kg: float | None = None
    impact_velocity_m_s: float | None = None
    impact_energy_J: float | None = None

    total_drag_energy_J: float

    fragmentation_detected: bool
    fragmentation_altitude_m: float | None = None

    atmospheric_drag_work_J: float | None = None
    ground_impact_energy_J: float | None = None
    atmospheric_fraction: float | None = None

    # V0.2 geographic scenario.
    trajectory: dict

    profile: list[dict]


@app.get("/")
def root():
    return {
        "name": "Meteor Madness Physics API",
        "version": "0.2.0",
        "status": "online",
    }


@app.get("/api/neos")
async def get_neos(
    start_date: str | None = None,
    end_date: str | None = None,
):
    api_key = os.getenv("NASA_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "message": "NASA_API_KEY is not configured",
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


def _build_trajectory(
    *,
    scenario: ImpactScenario,
    entry: EntryConditions,
) -> dict:
    """
    Build the public V0.2 geographic trajectory contract.

    Geographic coordinates are scenario inputs. They are not
    derived from NASA NeoWs orbital data in V0.2.
    """

    scenario.validate()
    entry.validate()

    return {
        "entry_latitude_deg": scenario.latitude_deg,
        "entry_longitude_deg": scenario.longitude_deg,
        "entry_azimuth_deg": scenario.entry_azimuth_deg,
        "entry_angle_deg": math.degrees(entry.entry_angle_rad),

        "coordinate_source": "scenario_input",

        "note": (
            "Geographic coordinates are scenario inputs in V0.2 "
            "and are not derived from NASA NeoWs orbital geometry."
        ),
    }


def _build_simulation_response(
    result,
    *,
    scenario: ImpactScenario,
    entry: EntryConditions,
) -> SimulationResponse:
    """
    Convert the internal physics simulation result into the
    public API response schema.
    """

    initial_mass = result.samples[0].mass_kg
    parent_final_sample = result.samples[-1]

    # ---------------------------------------------------------
    # Ground-impact fragment aggregation
    # ---------------------------------------------------------

    impact_mass = None
    impact_velocity = None
    impact_energy = None

    if result.fragment_trajectories:
        impact_fragments = [
            trajectory
            for trajectory in result.fragment_trajectories
            if trajectory.outcome.outcome == "ground_impact"
        ]

        if impact_fragments:
            impact_mass = sum(
                trajectory.consequences.surviving_mass_kg
                for trajectory in impact_fragments
            )

            impact_energy = sum(
                trajectory.consequences.impact_energy_J
                for trajectory in impact_fragments
            )

            if impact_mass > 0:
                impact_velocity = math.sqrt(
                    2.0 * impact_energy / impact_mass
                )

    # ---------------------------------------------------------
    # Fragmentation detection
    # ---------------------------------------------------------

    fragmentation_events = [
        event
        for event in result.events
        if event.type == "fragmentation"
    ]

    fragmentation_detected = bool(fragmentation_events)

    fragmentation_altitude = (
        fragmentation_events[0].altitude_m
        if fragmentation_detected
        else None
    )

    # ---------------------------------------------------------
    # Event-energy summary
    # ---------------------------------------------------------

    event_energy = result.event_energy
    airburst = result.airburst_classification

    # ---------------------------------------------------------
    # Profile
    # ---------------------------------------------------------

    profile = [
        {
            "altitude_m": sample.altitude_m,
            "velocity_m_s": sample.velocity_m_s,
            "mass_kg": sample.mass_kg,
            "density_kg_m3": sample.density_kg_m3,
            "temperature_K": sample.temperature_K,
            "pressure_Pa": sample.pressure_Pa,
            "equivalent_radius_m": sample.equivalent_radius_m,
            "projected_area_m2": sample.projected_area_m2,
            "drag_force_N": sample.drag_force_N,
            "drag_acceleration_m_s2": (
                sample.drag_acceleration_m_s2
            ),
            "drag_power_W": sample.drag_power_W,
            "kinetic_energy_J": sample.kinetic_energy_J,
            "dynamic_pressure_Pa": sample.dynamic_pressure_Pa,
            "mass_loss_rate_kg_s": sample.mass_loss_rate_kg_s,

            # Energy-deposition data
            "energy_deposition_J": sample.energy_deposition_J,
            "energy_deposition_per_meter_J_m": (
                sample.energy_deposition_per_meter_J_m
            ),
        }
        for sample in result.samples
    ]

    # ---------------------------------------------------------
    # Final public response
    # ---------------------------------------------------------

    return SimulationResponse(
        status="completed",

        outcome=(
            airburst.outcome
            if airburst is not None
            else result.events[-1].type
        ),

        initial_mass_kg=initial_mass,

        parent_final_mass_kg=parent_final_sample.mass_kg,
        parent_final_altitude_m=parent_final_sample.altitude_m,
        parent_final_velocity_m_s=parent_final_sample.velocity_m_s,
        parent_final_energy_J=parent_final_sample.kinetic_energy_J,

        impact_mass_kg=impact_mass,
        impact_velocity_m_s=impact_velocity,
        impact_energy_J=impact_energy,

        total_drag_energy_J=result.total_drag_energy_J,

        fragmentation_detected=fragmentation_detected,
        fragmentation_altitude_m=fragmentation_altitude,

        atmospheric_drag_work_J=(
            event_energy.atmospheric_drag_work_J
            if event_energy is not None
            else None
        ),

        ground_impact_energy_J=(
            event_energy.ground_impact_energy_J
            if event_energy is not None
            else None
        ),

        atmospheric_fraction=(
            event_energy.atmospheric_fraction
            if event_energy is not None
            else None
        ),

        trajectory=_build_trajectory(
            scenario=scenario,
            entry=entry,
        ),

        profile=profile,
    )


@app.post(
    "/api/simulation/entry",
    response_model=SimulationResponse,
)
def run_entry_simulation(request: SimulationRequest):
    """
    Run a simulation directly from explicitly supplied
    asteroid, entry, and geographic scenario parameters.
    """

    asteroid = AsteroidParameters(
        diameter_m=request.diameter_m,
        bulk_density_kg_m3=request.bulk_density_kg_m3,
        drag_coefficient=request.drag_coefficient,
        heat_transfer_coefficient=request.heat_transfer_coefficient,
        effective_heat_of_ablation_J_kg=(
            request.effective_heat_of_ablation_J_kg
        ),
        material_strength_Pa=request.material_strength_Pa,
        shape_factor=request.shape_factor,
    )

    entry = EntryConditions(
        initial_altitude_m=request.initial_altitude_m,
        initial_velocity_m_s=request.initial_velocity_m_s,
        entry_angle_rad=request.entry_angle_rad,
    )

    scenario = ImpactScenario(
        latitude_deg=request.latitude_deg,
        longitude_deg=request.longitude_deg,
        entry_azimuth_deg=request.entry_azimuth_deg,
    )

    config = SimulationConfig(
        timestep_s=request.timestep_s,
        max_time_s=request.max_time_s,
    )

    # Validate the new scenario explicitly.
    scenario.validate()

    result = simulate(
        asteroid=asteroid,
        entry=entry,
        config=config,
    )

    return _build_simulation_response(
        result,
        scenario=scenario,
        entry=entry,
    )


@app.post("/api/simulation/from-neo")
async def simulate_from_neo(
    asteroid_id: str,
    latitude_deg: float = 0.0,
    longitude_deg: float = 0.0,
    entry_azimuth_deg: float = 90.0,
):
    """
    Fetch a real asteroid from the current NASA NeoWs feed,
    resolve its physical simulation parameters, and run the
    atmospheric-entry simulation.

    Geographic values are V0.2 scenario inputs. They are not
    derived from NASA NeoWs orbital geometry.
    """

    # ---------------------------------------------------------
    # Validate geographic scenario
    # ---------------------------------------------------------

    scenario = ImpactScenario(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        entry_azimuth_deg=entry_azimuth_deg,
    )

    scenario.validate()

    api_key = os.getenv("NASA_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "message": "NASA_API_KEY is not configured",
        }

    # ---------------------------------------------------------
    # Fetch current NASA NeoWs feed
    # ---------------------------------------------------------

    data = await fetch_neos(api_key=api_key)

    neo = next(
        (
            asteroid
            for asteroid in data["asteroids"]
            if str(asteroid["id"]) == asteroid_id
        ),
        None,
    )

    if neo is None:
        return {
            "status": "error",
            "message": (
                f"Asteroid {asteroid_id} was not found "
                "in the current NASA feed"
            ),
        }

    # ---------------------------------------------------------
    # Resolve NASA data into physics assumptions
    # ---------------------------------------------------------

    resolved = resolve_neo_to_physics(neo)

    # ---------------------------------------------------------
    # Run physics simulation
    # ---------------------------------------------------------

    result = simulate(
        asteroid=resolved.asteroid,
        entry=resolved.entry,
        config=SimulationConfig(),
    )

    simulation_response = _build_simulation_response(
        result,
        scenario=scenario,
        entry=resolved.entry,
    )

    # ---------------------------------------------------------
    # Return NASA metadata + assumptions + simulation
    # ---------------------------------------------------------

    return {
        "status": "completed",

        "asteroid": {
            "id": resolved.asteroid_id,
            "name": resolved.name,
            "hazardous": resolved.hazardous,
            "diameter_km": neo["diameter_km"],
            "approach_date": neo["approach_date"],
            "miss_distance_km": neo["miss_distance_km"],
            "velocity_kph": neo["velocity_kph"],
        },

        "assumptions": resolved.assumptions,

        "trajectory": simulation_response.trajectory,

        "simulation": simulation_response.model_dump(),
    }
