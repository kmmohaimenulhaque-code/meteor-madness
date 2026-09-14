from __future__ import annotations

import math
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from nasa_client import fetch_neos

from physics.parameter_resolver import resolve_neo_to_physics
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    ImpactScenario,
    SimulationConfig,
)
from physics.solver import simulate
from physics.trajectory import destination_from_downrange


load_dotenv()


app = FastAPI(
    title="Meteor Madness Physics API",
    version="0.3.0",
)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================


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

    # Geographic scenario inputs.
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

    trajectory: dict[str, Any]

    # Public atmospheric-entry profile.
    profile: list[dict[str, Any]]


# ============================================================
# BASIC HELPERS
# ============================================================


def _safe_float(value: Any, default: float = 0.0) -> float:
    """
    Convert a numeric value safely to float.

    This prevents one malformed optional physics value from
    taking down the entire API response.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_optional_attribute(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve an optional attribute from a simulation object.
    """
    return getattr(obj, name, default)


# ============================================================
# ROOT
# ============================================================


@app.get("/")
def root():
    return {
        "name": "Meteor Madness Physics API",
        "version": "0.3.0",
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


# ============================================================
# GEOGRAPHIC TRAJECTORY
# ============================================================


def _build_trajectory(
    *,
    scenario: ImpactScenario,
    entry: EntryConditions,
    result: Any,
) -> dict[str, Any]:
    """
    Build the public V0.3 geographic trajectory contract.

    V0.3 uses the dynamically integrated parent trajectory:

        [altitude, velocity, flight-path angle, downrange, mass]

    Geographic position is calculated from:

        initial latitude
        initial longitude
        entry azimuth
        integrated surface downrange distance

    The trajectory is still a scenario model. It is NOT derived
    from the actual orbital state of the NASA NeoWs asteroid.
    """

    scenario.validate()
    entry.validate()

    samples = _get_optional_attribute(
        result,
        "samples",
        [],
    )

    if not samples:
        raise RuntimeError(
            "Cannot build trajectory because the simulation "
            "returned no samples."
        )

    initial_sample = samples[0]
    final_sample = samples[-1]

    # ---------------------------------------------------------
    # Initial trajectory state
    # ---------------------------------------------------------

    initial_downrange_m = _safe_float(
        _get_optional_attribute(
            initial_sample,
            "downrange_m",
            0.0,
        )
    )

    initial_gamma_rad = _get_optional_attribute(
        initial_sample,
        "flight_path_angle_rad",
        None,
    )

    if initial_gamma_rad is None:
        initial_gamma_rad = entry.entry_angle_rad

    # ---------------------------------------------------------
    # Final trajectory state
    # ---------------------------------------------------------

    final_downrange_m = _safe_float(
        _get_optional_attribute(
            final_sample,
            "downrange_m",
            0.0,
        )
    )

    final_gamma_rad = _get_optional_attribute(
        final_sample,
        "flight_path_angle_rad",
        None,
    )

    if final_gamma_rad is None:
        final_gamma_rad = entry.entry_angle_rad

    final_altitude_m = _safe_float(
        _get_optional_attribute(
            final_sample,
            "altitude_m",
            0.0,
        )
    )

    # ---------------------------------------------------------
    # Calculate geographic destination
    # ---------------------------------------------------------

    destination = destination_from_downrange(
        latitude_deg=scenario.latitude_deg,
        longitude_deg=scenario.longitude_deg,
        azimuth_deg=scenario.entry_azimuth_deg,
        downrange_m=final_downrange_m,
    )

    final_latitude_deg = _safe_float(
        destination[0]
    )

    final_longitude_deg = _safe_float(
        destination[1]
    )

    # ---------------------------------------------------------
    # Public trajectory contract
    # ---------------------------------------------------------

    return {
        "entry_latitude_deg": scenario.latitude_deg,
        "entry_longitude_deg": scenario.longitude_deg,
        "entry_azimuth_deg": scenario.entry_azimuth_deg,

        "entry_angle_deg": math.degrees(
            entry.entry_angle_rad
        ),

        "initial_downrange_m": initial_downrange_m,
        "final_downrange_m": final_downrange_m,

        "initial_flight_path_angle_deg": math.degrees(
            _safe_float(initial_gamma_rad)
        ),

        "final_flight_path_angle_deg": math.degrees(
            _safe_float(final_gamma_rad)
        ),

        "final_altitude_m": final_altitude_m,

        "final_latitude_deg": final_latitude_deg,
        "final_longitude_deg": final_longitude_deg,

        "coordinate_source": "scenario_input_plus_dynamic_downrange",

        "model": (
            "V0.3 ballistic dynamic trajectory on a spherical Earth"
        ),

        "note": (
            "Geographic coordinates begin from scenario inputs. "
            "Final position is calculated from dynamically "
            "integrated surface downrange distance and the "
            "specified entry azimuth. The trajectory is not "
            "derived from NASA NeoWs orbital geometry."
        ),
    }


# ============================================================
# PROFILE SERIALISATION
# ============================================================


def _build_profile(result: Any) -> list[dict[str, Any]]:
    """
    Convert SimulationResult.samples into the public profile.

    IMPORTANT:
    SimulationResult does NOT expose `profile`.
    The solver records atmospheric-entry points in `samples`.

    V0.3 adds:
        flight_path_angle_rad
        flight_path_angle_deg
        downrange_m
    """

    samples = _get_optional_attribute(
        result,
        "samples",
        [],
    )

    if samples is None:
        samples = []

    profile: list[dict[str, Any]] = []

    for sample in samples:

        gamma_rad = _get_optional_attribute(
            sample,
            "flight_path_angle_rad",
            None,
        )

        downrange_m = _get_optional_attribute(
            sample,
            "downrange_m",
            None,
        )

        profile.append(
            {
                "time_s": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "time_s",
                    )
                ),

                "altitude_m": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "altitude_m",
                    )
                ),

                "velocity_m_s": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "velocity_m_s",
                    )
                ),

                "mass_kg": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "mass_kg",
                    )
                ),

                # -------------------------------------------------
                # V0.3 dynamic trajectory
                # -------------------------------------------------

                "flight_path_angle_rad": (
                    _safe_float(gamma_rad)
                    if gamma_rad is not None
                    else None
                ),

                "flight_path_angle_deg": (
                    math.degrees(
                        _safe_float(gamma_rad)
                    )
                    if gamma_rad is not None
                    else None
                ),

                "downrange_m": (
                    _safe_float(downrange_m)
                    if downrange_m is not None
                    else None
                ),

                # -------------------------------------------------
                # Atmospheric state
                # -------------------------------------------------

                "density_kg_m3": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "density_kg_m3",
                    )
                ),

                "temperature_K": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "temperature_K",
                    )
                ),

                "pressure_Pa": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "pressure_Pa",
                    )
                ),

                # -------------------------------------------------
                # Geometry
                # -------------------------------------------------

                "equivalent_radius_m": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "equivalent_radius_m",
                    )
                ),

                "projected_area_m2": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "projected_area_m2",
                    )
                ),

                # -------------------------------------------------
                # Drag
                # -------------------------------------------------

                "drag_force_N": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "drag_force_N",
                    )
                ),

                "drag_acceleration_m_s2": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "drag_acceleration_m_s2",
                    )
                ),

                "drag_power_W": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "drag_power_W",
                    )
                ),

                # -------------------------------------------------
                # Energy
                # -------------------------------------------------

                "kinetic_energy_J": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "kinetic_energy_J",
                    )
                ),

                "dynamic_pressure_Pa": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "dynamic_pressure_Pa",
                    )
                ),

                "mass_loss_rate_kg_s": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "mass_loss_rate_kg_s",
                    )
                ),

                "energy_deposition_J": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "energy_deposition_J",
                    )
                ),

                "energy_deposition_per_meter_J_m": _safe_float(
                    _get_optional_attribute(
                        sample,
                        "energy_deposition_per_meter_J_m",
                    )
                ),
            }
        )

    return profile


# ============================================================
# IMPACT / FRAGMENTATION HELPERS
# ============================================================


def _build_impact_summary(result: Any) -> tuple[float | None, float | None, float | None]:
    """
    Aggregate surviving fragment ground-impact data.

    Fragment trajectories expose their terminal impact state through
    FragmentOutcome. For ground impacts we aggregate:
      - mass
      - kinetic energy

    Impact velocity is reconstructed from the total kinetic energy and
    total surviving mass.
    """
    fragment_trajectories = getattr(result, "fragment_trajectories", [])

    if not fragment_trajectories:
        return None, None, None

    impact_mass = 0.0
    impact_energy = 0.0
    impact_fragment_count = 0

    for trajectory in fragment_trajectories:
        outcome = getattr(trajectory, "outcome", None)

        if outcome is None:
            continue

        if getattr(outcome, "outcome", None) != "ground_impact":
            continue

        mass_kg = float(getattr(outcome, "mass_kg", 0.0))
        kinetic_energy_J = float(
            getattr(outcome, "kinetic_energy_J", 0.0)
        )

        if mass_kg <= 0.0:
            continue

        impact_mass += mass_kg
        impact_energy += max(kinetic_energy_J, 0.0)
        impact_fragment_count += 1

    if impact_fragment_count == 0 or impact_mass <= 0.0:
        return None, None, None

    if impact_energy <= 0.0:
        return impact_mass, None, impact_energy

    impact_velocity = math.sqrt(
        2.0 * impact_energy / impact_mass
    )

    return impact_mass, impact_velocity, impact_energy


def _build_fragmentation_summary(result: Any) -> tuple[
    bool,
    float | None,
]:
    """
    Extract the first fragmentation event.
    """

    events = _get_optional_attribute(
        result,
        "events",
        [],
    )

    if not events:
        return False, None

    fragmentation_events = [
        event
        for event in events
        if _get_optional_attribute(
            event,
            "type",
            None,
        ) == "fragmentation"
    ]

    if not fragmentation_events:
        return False, None

    altitude = _get_optional_attribute(
        fragmentation_events[0],
        "altitude_m",
        None,
    )

    return True, (
        _safe_float(altitude)
        if altitude is not None
        else None
    )


# ============================================================
# PUBLIC SIMULATION RESPONSE
# ============================================================


def _build_simulation_response(
    result: Any,
    *,
    scenario: ImpactScenario,
    entry: EntryConditions,
) -> SimulationResponse:
    """
    Convert the internal SimulationResult into the public API
    response.

    This function intentionally works with the actual solver
    contract:

        result.samples

    rather than the nonexistent:

        result.profile
    """

    # ---------------------------------------------------------
    # Validate result
    # ---------------------------------------------------------

    samples = _get_optional_attribute(
        result,
        "samples",
        [],
    )

    if not samples:
        raise RuntimeError(
            "Physics solver returned no simulation samples."
        )

    # ---------------------------------------------------------
    # Initial / final parent state
    # ---------------------------------------------------------

    initial_sample = samples[0]
    parent_final_sample = samples[-1]

    initial_mass = _safe_float(
        _get_optional_attribute(
            initial_sample,
            "mass_kg",
        )
    )

    # ---------------------------------------------------------
    # Ground-impact fragment aggregation
    # ---------------------------------------------------------

    (
        impact_mass,
        impact_velocity,
        impact_energy,
    ) = _build_impact_summary(result)

    # ---------------------------------------------------------
    # Fragmentation detection
    # ---------------------------------------------------------

    (
        fragmentation_detected,
        fragmentation_altitude,
    ) = _build_fragmentation_summary(result)

    # ---------------------------------------------------------
    # Event-energy summary
    # ---------------------------------------------------------

    event_energy = _get_optional_attribute(
        result,
        "event_energy",
        None,
    )

    airburst = _get_optional_attribute(
        result,
        "airburst_classification",
        None,
    )

    # ---------------------------------------------------------
    # Outcome
    # ---------------------------------------------------------

    outcome = _get_optional_attribute(
        airburst,
        "outcome",
        None,
    )

    if outcome is None:
        events = _get_optional_attribute(
            result,
            "events",
            [],
        )

        if events:
            outcome = _get_optional_attribute(
                events[-1],
                "type",
                "completed",
            )
        else:
            outcome = "completed"

    # ---------------------------------------------------------
    # Atmospheric profile
    # ---------------------------------------------------------

    profile = _build_profile(result)

    # ---------------------------------------------------------
    # Total drag energy
    # ---------------------------------------------------------

    total_drag_energy = _safe_float(
        _get_optional_attribute(
            result,
            "total_drag_energy_J",
            0.0,
        )
    )

    # ---------------------------------------------------------
    # Event-energy values
    # ---------------------------------------------------------

    atmospheric_drag_work = None
    ground_impact_energy = None
    atmospheric_fraction = None

    if event_energy is not None:

        value = _get_optional_attribute(
            event_energy,
            "atmospheric_drag_work_J",
            None,
        )

        if value is not None:
            atmospheric_drag_work = _safe_float(value)

        value = _get_optional_attribute(
            event_energy,
            "ground_impact_energy_J",
            None,
        )

        if value is not None:
            ground_impact_energy = _safe_float(value)

        value = _get_optional_attribute(
            event_energy,
            "atmospheric_fraction",
            None,
        )

        if value is not None:
            atmospheric_fraction = _safe_float(value)

    # ---------------------------------------------------------
    # Final response
    # ---------------------------------------------------------

    return SimulationResponse(
        status="completed",

        outcome=str(outcome),

        initial_mass_kg=initial_mass,

        parent_final_mass_kg=_safe_float(
            _get_optional_attribute(
                parent_final_sample,
                "mass_kg",
            )
        ),

        parent_final_altitude_m=_safe_float(
            _get_optional_attribute(
                parent_final_sample,
                "altitude_m",
            )
        ),

        parent_final_velocity_m_s=_safe_float(
            _get_optional_attribute(
                parent_final_sample,
                "velocity_m_s",
            )
        ),

        parent_final_energy_J=_safe_float(
            _get_optional_attribute(
                parent_final_sample,
                "kinetic_energy_J",
            )
        ),

        impact_mass_kg=impact_mass,
        impact_velocity_m_s=impact_velocity,
        impact_energy_J=impact_energy,

        total_drag_energy_J=total_drag_energy,

        fragmentation_detected=fragmentation_detected,
        fragmentation_altitude_m=fragmentation_altitude,

        atmospheric_drag_work_J=atmospheric_drag_work,
        ground_impact_energy_J=ground_impact_energy,
        atmospheric_fraction=atmospheric_fraction,

        trajectory=_build_trajectory(
            scenario=scenario,
            entry=entry,
            result=result,
        ),

        profile=profile,
    )


# ============================================================
# DIRECT PHYSICS SIMULATION
# ============================================================


@app.post(
    "/api/simulation/entry",
    response_model=SimulationResponse,
)
def run_entry_simulation(
    request: SimulationRequest,
):
    """
    Run a simulation directly from explicitly supplied asteroid,
    entry, and geographic scenario parameters.
    """

    asteroid = AsteroidParameters(
        diameter_m=request.diameter_m,
        bulk_density_kg_m3=request.bulk_density_kg_m3,
        drag_coefficient=request.drag_coefficient,
        heat_transfer_coefficient=(
            request.heat_transfer_coefficient
        ),
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
    )


# ============================================================
# NASA ASTEROID -> PHYSICS SIMULATION
# ============================================================


@app.post("/api/simulation/from-neo")
async def simulate_from_neo(
    asteroid_id: str,
    latitude_deg: float = 0.0,
    longitude_deg: float = 0.0,
    entry_azimuth_deg: float = 90.0,
):
    """
    Fetch a real asteroid from the current NASA NeoWs feed,
    resolve physical parameters, and run the atmospheric-entry
    simulation.

    Geographic values are scenario inputs.

    V0.3 dynamically integrates:
        flight-path angle
        downrange distance
    """

    # ---------------------------------------------------------
    # Geographic scenario
    # ---------------------------------------------------------

    scenario = ImpactScenario(
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        entry_azimuth_deg=entry_azimuth_deg,
    )

    scenario.validate()

    # ---------------------------------------------------------
    # NASA API key
    # ---------------------------------------------------------

    api_key = os.getenv("NASA_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "message": "NASA_API_KEY is not configured",
        }

    # ---------------------------------------------------------
    # Fetch current NASA feed
    # ---------------------------------------------------------

    data = await fetch_neos(
        api_key=api_key,
    )

    asteroids = data.get(
        "asteroids",
        [],
    )

    neo = next(
        (
            asteroid
            for asteroid in asteroids
            if str(asteroid.get("id")) == str(asteroid_id)
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
    # Resolve NASA asteroid into physics parameters
    # ---------------------------------------------------------

    resolved = resolve_neo_to_physics(neo)

    # ---------------------------------------------------------
    # Run atmospheric-entry simulation
    # ---------------------------------------------------------

    result = simulate(
        asteroid=resolved.asteroid,
        entry=resolved.entry,
        config=SimulationConfig(),
        scenario=scenario,
    )

    # ---------------------------------------------------------
    # Convert solver result into API contract
    # ---------------------------------------------------------

    simulation_response = _build_simulation_response(
        result,
        scenario=scenario,
        entry=resolved.entry,
    )

    # ---------------------------------------------------------
    # Return complete payload
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
