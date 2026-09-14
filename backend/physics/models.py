from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AsteroidParameters:
    """Physical and material properties of the incoming body."""

    diameter_m: float
    bulk_density_kg_m3: float

    drag_coefficient: float
    heat_transfer_coefficient: float
    effective_heat_of_ablation_J_kg: float
    material_strength_Pa: float

    shape_factor: float = 1.0

    def validate(self) -> None:
        if self.diameter_m <= 0:
            raise ValueError("diameter_m must be greater than zero")

        if self.bulk_density_kg_m3 <= 0:
            raise ValueError(
                "bulk_density_kg_m3 must be greater than zero"
            )

        if self.drag_coefficient < 0:
            raise ValueError(
                "drag_coefficient must be non-negative"
            )

        if self.heat_transfer_coefficient < 0:
            raise ValueError(
                "heat_transfer_coefficient must be non-negative"
            )

        if self.effective_heat_of_ablation_J_kg <= 0:
            raise ValueError(
                "effective_heat_of_ablation_J_kg must be greater than zero"
            )

        if self.material_strength_Pa <= 0:
            raise ValueError(
                "material_strength_Pa must be greater than zero"
            )

        if self.shape_factor <= 0:
            raise ValueError(
                "shape_factor must be greater than zero"
            )


@dataclass(frozen=True)
class EntryConditions:
    """Initial atmospheric-entry conditions."""

    initial_altitude_m: float
    initial_velocity_m_s: float
    entry_angle_rad: float

    def validate(self) -> None:
        if self.initial_altitude_m < 0:
            raise ValueError(
                "initial_altitude_m cannot be negative"
            )

        if self.initial_velocity_m_s <= 0:
            raise ValueError(
                "initial_velocity_m_s must be greater than zero"
            )

        if not 0 < self.entry_angle_rad < 3.141592653589793 / 2:
            raise ValueError(
                "entry_angle_rad must be between 0 and pi/2"
            )


@dataclass(frozen=True)
class ImpactScenario:
    """Geographic scenario for the atmospheric-entry trajectory.

    V0.2 treats these values as scenario inputs. They are not inferred
    from NASA NeoWs asteroid data.
    """

    latitude_deg: float
    longitude_deg: float
    entry_azimuth_deg: float

    def validate(self) -> None:
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError(
                "latitude_deg must be between -90 and 90"
            )

        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError(
                "longitude_deg must be between -180 and 180"
            )

        if not 0.0 <= self.entry_azimuth_deg < 360.0:
            raise ValueError(
                "entry_azimuth_deg must be between 0 and 360"
            )


@dataclass(frozen=True)
class SimulationConfig:
    """Numerical settings for a simulation."""

    timestep_s: float = 0.01
    max_time_s: float = 1000.0
    min_mass_kg: float = 1e-6

    # V0.1 stops the single-body model when fragmentation is detected.
    stop_on_fragmentation: bool = True

    def validate(self) -> None:
        if self.timestep_s <= 0:
            raise ValueError(
                "timestep_s must be greater than zero"
            )

        if self.max_time_s <= 0:
            raise ValueError(
                "max_time_s must be greater than zero"
            )

        if self.min_mass_kg <= 0:
            raise ValueError(
                "min_mass_kg must be greater than zero"
            )


@dataclass
class SimulationState:
    """Dynamic state integrated by RK4."""

    altitude_m: float
    velocity_m_s: float
    mass_kg: float


@dataclass(frozen=True)
class SimulationSample:
    """One recorded point in the simulation profile."""

    time_s: float

    altitude_m: float
    velocity_m_s: float
    mass_kg: float

    density_kg_m3: float
    temperature_K: float
    pressure_Pa: float

    equivalent_radius_m: float
    projected_area_m2: float

    drag_force_N: float
    drag_acceleration_m_s2: float
    drag_power_W: float

    kinetic_energy_J: float
    dynamic_pressure_Pa: float

    mass_loss_rate_kg_s: float
    energy_deposition_J: float = 0.0
    energy_deposition_per_meter_J_m: float = 0.0


@dataclass(frozen=True)
class EventRecord:
    """A discrete event detected during simulation."""

    type: Literal[
        "ground_impact",
        "complete_ablation",
        "fragmentation",
        "model_boundary",
        "max_time",
    ]

    time_s: float
    altitude_m: float
    velocity_m_s: float
    mass_kg: float
    energy_J: float
