from __future__ import annotations

import math
import os

from dotenv import load_dotenv

from nasa_client import fetch_neos
from fastapi import FastAPI
from pydantic import BaseModel, Field

from physics.airburst import AirburstClassification
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
)
from physics.solver import simulate


app = FastAPI(
    title="Meteor Madness Physics API",
    version="0.1.0",
)
load_dotenv()

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

    profile: list[dict]


@app.get("/")
def root():
    return {
        "name": "Meteor Madness Physics API",
        "version": "0.1.0",
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
@app.post("/api/simulation/entry", response_model=SimulationResponse)
def run_entry_simulation(request: SimulationRequest):
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

    config = SimulationConfig(
        timestep_s=request.timestep_s,
        max_time_s=request.max_time_s,
    )

    result = simulate(
        asteroid=asteroid,
        entry=entry,
        config=config,
    )

    initial_mass = result.samples[0].mass_kg
    parent_final_sample = result.samples[-1]

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

    event_energy = result.event_energy
    airburst = result.airburst_classification

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
        profile=[
            {
                "altitude_m": sample.altitude_m,
                "velocity_m_s": sample.velocity_m_s,
                "mass_kg": sample.mass_kg,
                "density_kg_m3": sample.density_kg_m3,
                "drag_force_N": sample.drag_force_N,
                "drag_power_W": sample.drag_power_W,
                "kinetic_energy_J": sample.kinetic_energy_J,
                "dynamic_pressure_Pa": sample.dynamic_pressure_Pa,
                "mass_loss_rate_kg_s": sample.mass_loss_rate_kg_s,
            }
            for sample in result.samples
        ],
    )
