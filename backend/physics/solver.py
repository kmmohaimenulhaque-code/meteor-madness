from __future__ import annotations

import math
from dataclasses import dataclass

from physics.ablation import ablation_mass_derivative
from physics.atmosphere import state as atmosphere_state
from physics.drag import (
    drag_acceleration,
    drag_force,
    drag_power,
    dynamic_pressure,
)
from physics.energy import kinetic_energy
from physics.fragmentation import fragmentation_triggered
from physics.geometry import (
    equivalent_radius_from_mass,
    initial_mass,
    projected_area,
)
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    EventRecord,
    SimulationConfig,
    SimulationSample,
    SimulationState,
)


EARTH_RADIUS_M = 6_371_000.0
STANDARD_GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class SimulationResult:
    """Complete result of a single-body entry simulation."""

    samples: list[SimulationSample]
    events: list[EventRecord]
    total_drag_energy_J: float


def gravity_acceleration(altitude_m: float) -> float:
    """Return gravitational acceleration at altitude."""

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    return STANDARD_GRAVITY_M_S2 * (
        EARTH_RADIUS_M
        / (EARTH_RADIUS_M + altitude_m)
    ) ** 2


def state_derivative(
    state: SimulationState,
    asteroid: AsteroidParameters,
    entry: EntryConditions,
) -> SimulationState:
    """Return dh/dt, dv/dt, and dm/dt for the current state."""

    if state.altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    if state.velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    if state.mass_kg <= 0:
        raise ValueError("mass_kg must be greater than zero")

    asteroid.validate()
    entry.validate()

    atmosphere = atmosphere_state(state.altitude_m)

    radius = equivalent_radius_from_mass(
        mass_kg=state.mass_kg,
        density_kg_m3=asteroid.bulk_density_kg_m3,
    )

    area = projected_area(
        equivalent_radius_m=radius,
        shape_factor=asteroid.shape_factor,
    )

    force = drag_force(
        density_kg_m3=atmosphere.density_kg_m3,
        velocity_m_s=state.velocity_m_s,
        projected_area_m2=area,
        drag_coefficient=asteroid.drag_coefficient,
    )

    acceleration = drag_acceleration(
        drag_force_N=force,
        mass_kg=state.mass_kg,
    )

    mass_derivative = ablation_mass_derivative(
        density_kg_m3=atmosphere.density_kg_m3,
        velocity_m_s=state.velocity_m_s,
        projected_area_m2=area,
        heat_transfer_coefficient=asteroid.heat_transfer_coefficient,
        effective_heat_of_ablation_J_kg=(
            asteroid.effective_heat_of_ablation_J_kg
        ),
    )

    gamma = entry.entry_angle_rad

    altitude_derivative = (
        -state.velocity_m_s * math.sin(gamma)
    )

    velocity_derivative = (
        gravity_acceleration(state.altitude_m)
        * math.sin(gamma)
        - acceleration
    )

    return SimulationState(
        altitude_m=altitude_derivative,
        velocity_m_s=velocity_derivative,
        mass_kg=mass_derivative,
    )


def add_states(
    state_a: SimulationState,
    state_b: SimulationState,
    scale: float,
) -> SimulationState:
    """Return state_a + scale * state_b."""

    return SimulationState(
        altitude_m=(
            state_a.altitude_m
            + scale * state_b.altitude_m
        ),
        velocity_m_s=(
            state_a.velocity_m_s
            + scale * state_b.velocity_m_s
        ),
        mass_kg=(
            state_a.mass_kg
            + scale * state_b.mass_kg
        ),
    )


def rk4_step(
    state: SimulationState,
    time_s: float,
    timestep_s: float,
    asteroid: AsteroidParameters,
    entry: EntryConditions,
) -> SimulationState:
    """Advance the state by one fourth-order Runge-Kutta step."""

    if timestep_s <= 0:
        raise ValueError("timestep_s must be greater than zero")

    k1 = state_derivative(
        state,
        asteroid,
        entry,
    )

    k2_state = add_states(
        state,
        k1,
        timestep_s / 2.0,
    )

    k2 = state_derivative(
        k2_state,
        asteroid,
        entry,
    )

    k3_state = add_states(
        state,
        k2,
        timestep_s / 2.0,
    )

    k3 = state_derivative(
        k3_state,
        asteroid,
        entry,
    )

    k4_state = add_states(
        state,
        k3,
        timestep_s,
    )

    k4 = state_derivative(
        k4_state,
        asteroid,
        entry,
    )

    return SimulationState(
        altitude_m=(
            state.altitude_m
            + timestep_s
            / 6.0
            * (
                k1.altitude_m
                + 2.0 * k2.altitude_m
                + 2.0 * k3.altitude_m
                + k4.altitude_m
            )
        ),
        velocity_m_s=(
            state.velocity_m_s
            + timestep_s
            / 6.0
            * (
                k1.velocity_m_s
                + 2.0 * k2.velocity_m_s
                + 2.0 * k3.velocity_m_s
                + k4.velocity_m_s
            )
        ),
        mass_kg=(
            state.mass_kg
            + timestep_s
            / 6.0
            * (
                k1.mass_kg
                + 2.0 * k2.mass_kg
                + 2.0 * k3.mass_kg
                + k4.mass_kg
            )
        ),
    )


def _make_sample(
    time_s: float,
    current_state: SimulationState,
    asteroid: AsteroidParameters,
) -> SimulationSample:
    """Build one recorded simulation sample."""

    atmosphere = atmosphere_state(current_state.altitude_m)

    radius = equivalent_radius_from_mass(
        mass_kg=current_state.mass_kg,
        density_kg_m3=asteroid.bulk_density_kg_m3,
    )

    area = projected_area(
        equivalent_radius_m=radius,
        shape_factor=asteroid.shape_factor,
    )

    force = drag_force(
        density_kg_m3=atmosphere.density_kg_m3,
        velocity_m_s=current_state.velocity_m_s,
        projected_area_m2=area,
        drag_coefficient=asteroid.drag_coefficient,
    )

    acceleration = drag_acceleration(
        drag_force_N=force,
        mass_kg=current_state.mass_kg,
    )

    pressure = dynamic_pressure(
        density_kg_m3=atmosphere.density_kg_m3,
        velocity_m_s=current_state.velocity_m_s,
    )

    power = drag_power(
        drag_force_N=force,
        velocity_m_s=current_state.velocity_m_s,
    )

    mass_rate = ablation_mass_derivative(
        density_kg_m3=atmosphere.density_kg_m3,
        velocity_m_s=current_state.velocity_m_s,
        projected_area_m2=area,
        heat_transfer_coefficient=(
            asteroid.heat_transfer_coefficient
        ),
        effective_heat_of_ablation_J_kg=(
            asteroid.effective_heat_of_ablation_J_kg
        ),
    )

    return SimulationSample(
        time_s=time_s,
        altitude_m=current_state.altitude_m,
        velocity_m_s=current_state.velocity_m_s,
        mass_kg=current_state.mass_kg,
        density_kg_m3=atmosphere.density_kg_m3,
        temperature_K=atmosphere.temperature_K,
        pressure_Pa=atmosphere.pressure_Pa,
        equivalent_radius_m=radius,
        projected_area_m2=area,
        drag_force_N=force,
        drag_acceleration_m_s2=acceleration,
        drag_power_W=power,
        kinetic_energy_J=kinetic_energy(
            mass_kg=current_state.mass_kg,
            velocity_m_s=current_state.velocity_m_s,
        ),
        dynamic_pressure_Pa=pressure,
        mass_loss_rate_kg_s=mass_rate,
    )


def simulate(
    asteroid: AsteroidParameters,
    entry: EntryConditions,
    config: SimulationConfig,
) -> SimulationResult:
    """Run a single-body atmospheric-entry simulation."""

    asteroid.validate()
    entry.validate()
    config.validate()

    current_state = SimulationState(
        altitude_m=entry.initial_altitude_m,
        velocity_m_s=entry.initial_velocity_m_s,
        mass_kg=initial_mass(
            diameter_m=asteroid.diameter_m,
            density_kg_m3=asteroid.bulk_density_kg_m3,
        ),
    )

    samples: list[SimulationSample] = []
    events: list[EventRecord] = []

    total_drag_energy_J = 0.0
    time_s = 0.0

    samples.append(
        _make_sample(
            time_s=time_s,
            current_state=current_state,
            asteroid=asteroid,
        )
    )

    while time_s < config.max_time_s:

        if current_state.altitude_m <= 0.0:
            events.append(
                EventRecord(
                    type="ground_impact",
                    time_s=time_s,
                    altitude_m=0.0,
                    velocity_m_s=max(
                        current_state.velocity_m_s,
                        0.0,
                    ),
                    mass_kg=max(
                        current_state.mass_kg,
                        0.0,
                    ),
                    energy_J=kinetic_energy(
                        mass_kg=max(
                            current_state.mass_kg,
                            0.0,
                        ),
                        velocity_m_s=max(
                            current_state.velocity_m_s,
                            0.0,
                        ),
                    ),
                )
            )
            break

        if current_state.mass_kg <= config.min_mass_kg:
            events.append(
                EventRecord(
                    type="complete_ablation",
                    time_s=time_s,
                    altitude_m=current_state.altitude_m,
                    velocity_m_s=max(
                        current_state.velocity_m_s,
                        0.0,
                    ),
                    mass_kg=0.0,
                    energy_J=0.0,
                )
            )
            break

        sample = samples[-1]

        if fragmentation_triggered(
            dynamic_pressure_Pa=sample.dynamic_pressure_Pa,
            material_strength_Pa=asteroid.material_strength_Pa,
        ):
            if config.stop_on_fragmentation:
                events.append(
                    EventRecord(
                        type="fragmentation",
                        time_s=time_s,
                        altitude_m=current_state.altitude_m,
                        velocity_m_s=current_state.velocity_m_s,
                        mass_kg=current_state.mass_kg,
                        energy_J=sample.kinetic_energy_J,
                    )
                )
                break

        next_state = rk4_step(
            state=current_state,
            time_s=time_s,
            timestep_s=config.timestep_s,
            asteroid=asteroid,
            entry=entry,
        )

        if next_state.mass_kg < 0.0:
            next_state = SimulationState(
                altitude_m=next_state.altitude_m,
                velocity_m_s=next_state.velocity_m_s,
                mass_kg=0.0,
            )

        next_time = time_s + config.timestep_s

        next_sample = _make_sample(
            time_s=next_time,
            current_state=next_state,
            asteroid=asteroid,
        )

        total_drag_energy_J += (
            0.5
            * (
                sample.drag_power_W
                + next_sample.drag_power_W
            )
            * config.timestep_s
        )

        samples.append(next_sample)

        current_state = next_state
        time_s = next_time

    else:
        events.append(
            EventRecord(
                type="max_time",
                time_s=time_s,
                altitude_m=current_state.altitude_m,
                velocity_m_s=max(
                    current_state.velocity_m_s,
                    0.0,
                ),
                mass_kg=max(
                    current_state.mass_kg,
                    0.0,
                ),
                energy_J=kinetic_energy(
                    mass_kg=max(
                        current_state.mass_kg,
                        0.0,
                    ),
                    velocity_m_s=max(
                        current_state.velocity_m_s,
                        0.0,
                    ),
                ),
            )
        )

    return SimulationResult(
        samples=samples,
        events=events,
        total_drag_energy_J=total_drag_energy_J,
    )
