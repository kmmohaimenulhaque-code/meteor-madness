from __future__ import annotations

import math
from dataclasses import dataclass

from physics.airburst import (
    AirburstClassification,
    classify_airburst,
)
from physics.event_energy import (
    EventEnergySummary,
    aggregate_event_energy,
)
from physics.deposition import (
    build_energy_deposition_profile,
)

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
from physics.fragmentation import create_fragments
from physics.fragment_solver import (
    FragmentTrajectory,
    initial_fragment_states,
    simulate_fragment,
)
from physics.geometry import (
    equivalent_radius_from_mass,
    initial_mass,
    projected_area,
)
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    EventRecord,
    ImpactScenario,
    SimulationConfig,
    SimulationSample,
    SimulationState,
)
from physics.trajectory import (
    EARTH_RADIUS_M,
    destination_from_downrange,
    downrange_rate,
    dynamic_flight_path_angle_rate,
)


STANDARD_GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True)
class SimulationResult:
    """Complete result of a single-body entry simulation."""

    samples: list[SimulationSample]
    events: list[EventRecord]
    total_drag_energy_J: float

    fragment_trajectories: tuple[
        FragmentTrajectory,
        ...
    ] = ()

    energy_deposition_profile: tuple[
        dict,
        ...
    ] = ()

    event_energy: EventEnergySummary | None = None

    airburst_classification: (
        AirburstClassification | None
    ) = None


def gravity_acceleration(
    altitude_m: float,
) -> float:
    """Return gravitational acceleration at altitude."""

    if altitude_m < 0:
        raise ValueError(
            "altitude_m cannot be negative"
        )

    return STANDARD_GRAVITY_M_S2 * (
        EARTH_RADIUS_M
        / (EARTH_RADIUS_M + altitude_m)
    ) ** 2


def state_derivative(
    state: SimulationState,
    asteroid: AsteroidParameters,
    entry: EntryConditions,
) -> SimulationState:
    """
    Return the V0.3 state derivative:

        dh/dt
        dv/dt
        dgamma/dt
        ds/dt
        dm/dt
    """

    if state.altitude_m < 0:
        raise ValueError(
            "altitude_m cannot be negative"
        )

    if state.velocity_m_s < 0:
        raise ValueError(
            "velocity_m_s cannot be negative"
        )

    if state.mass_kg <= 0:
        raise ValueError(
            "mass_kg must be greater than zero"
        )

    asteroid.validate()
    entry.validate()

    if state.flight_path_angle_rad is None:
        # Backwards-compatible fallback for callers that
        # construct a state without V0.3 information.
        gamma = entry.entry_angle_rad
    else:
        gamma = state.flight_path_angle_rad

    if not 0.0 < gamma < math.pi / 2.0:
        raise ValueError(
            "flight_path_angle_rad must be between 0 and pi/2"
        )

    atmosphere = atmosphere_state(
        state.altitude_m
    )

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
        heat_transfer_coefficient=(
            asteroid.heat_transfer_coefficient
        ),
        effective_heat_of_ablation_J_kg=(
            asteroid.effective_heat_of_ablation_J_kg
        ),
    )

    gravity = gravity_acceleration(
        state.altitude_m
    )

    altitude_derivative = (
        -state.velocity_m_s
        * math.sin(gamma)
    )

    velocity_derivative = (
        gravity * math.sin(gamma)
        - acceleration
    )

    gamma_derivative = (
        dynamic_flight_path_angle_rate(
            altitude_m=state.altitude_m,
            velocity_m_s=state.velocity_m_s,
            flight_path_angle_rad=gamma,
            gravity_m_s2=gravity,
        )
    )

    downrange_derivative = downrange_rate(
        altitude_m=state.altitude_m,
        velocity_m_s=state.velocity_m_s,
        flight_path_angle_rad=gamma,
    )

    return SimulationState(
        altitude_m=altitude_derivative,
        velocity_m_s=velocity_derivative,
        mass_kg=mass_derivative,
        flight_path_angle_rad=gamma_derivative,
        downrange_m=downrange_derivative,
    )


def add_states(
    state_a: SimulationState,
    state_b: SimulationState,
    scale: float,
) -> SimulationState:
    """Return state_a + scale * state_b."""

    gamma_a = (
        state_a.flight_path_angle_rad
        if state_a.flight_path_angle_rad is not None
        else 0.0
    )

    gamma_b = (
        state_b.flight_path_angle_rad
        if state_b.flight_path_angle_rad is not None
        else 0.0
    )

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
        flight_path_angle_rad=(
            gamma_a
            + scale * gamma_b
        ),
        downrange_m=(
            state_a.downrange_m
            + scale * state_b.downrange_m
        ),
    )


def rk4_step(
    state: SimulationState,
    time_s: float,
    timestep_s: float,
    asteroid: AsteroidParameters,
    entry: EntryConditions,
) -> SimulationState:
    """Advance the V0.3 state by one RK4 step."""

    if timestep_s <= 0:
        raise ValueError(
            "timestep_s must be greater than zero"
        )

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

    gamma = (
        state.flight_path_angle_rad
        if state.flight_path_angle_rad is not None
        else entry.entry_angle_rad
    )

    gamma_k1 = (
        k1.flight_path_angle_rad or 0.0
    )

    gamma_k2 = (
        k2.flight_path_angle_rad or 0.0
    )

    gamma_k3 = (
        k3.flight_path_angle_rad or 0.0
    )

    gamma_k4 = (
        k4.flight_path_angle_rad or 0.0
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
        flight_path_angle_rad=(
            gamma
            + timestep_s
            / 6.0
            * (
                gamma_k1
                + 2.0 * gamma_k2
                + 2.0 * gamma_k3
                + gamma_k4
            )
        ),
        downrange_m=(
            state.downrange_m
            + timestep_s
            / 6.0
            * (
                k1.downrange_m
                + 2.0 * k2.downrange_m
                + 2.0 * k3.downrange_m
                + k4.downrange_m
            )
        ),
    )


def _make_sample(
    time_s: float,
    current_state: SimulationState,
    asteroid: AsteroidParameters,
) -> SimulationSample:
    """Build one recorded simulation sample."""

    atmosphere = atmosphere_state(
        current_state.altitude_m
    )

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

    gamma = (
        current_state.flight_path_angle_rad
        if current_state.flight_path_angle_rad is not None
        else 0.0
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

        flight_path_angle_rad=gamma,
        downrange_m=current_state.downrange_m,
    )


def simulate(
    asteroid: AsteroidParameters,
    entry: EntryConditions,
    config: SimulationConfig,
    scenario: ImpactScenario | None = None,
) -> SimulationResult:
    """
    Run a V0.3 dynamic atmospheric-entry simulation.

    The parent body uses:

        [h, v, gamma, s, m]

    Geographic coordinates are derived from the scenario's
    initial latitude, longitude and azimuth.
    """

    asteroid.validate()
    entry.validate()
    config.validate()

    if scenario is not None:
        scenario.validate()

    initial_mass_kg = initial_mass(
        diameter_m=asteroid.diameter_m,
        density_kg_m3=asteroid.bulk_density_kg_m3,
    )

    current_state = SimulationState(
        altitude_m=entry.initial_altitude_m,
        velocity_m_s=entry.initial_velocity_m_s,
        mass_kg=initial_mass_kg,
        flight_path_angle_rad=entry.entry_angle_rad,
        downrange_m=0.0,
    )

    samples: list[SimulationSample] = []
    events: list[EventRecord] = []

    fragment_trajectories: tuple[
        FragmentTrajectory,
        ...
    ] = ()

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

        # ----------------------------------------------------
        # Ground impact
        # ----------------------------------------------------

        if current_state.altitude_m <= 0.0:

            impact_mass = max(
                current_state.mass_kg,
                0.0,
            )

            impact_velocity = max(
                current_state.velocity_m_s,
                0.0,
            )

            events.append(
                EventRecord(
                    type="ground_impact",
                    time_s=time_s,
                    altitude_m=0.0,
                    velocity_m_s=impact_velocity,
                    mass_kg=impact_mass,
                    energy_J=kinetic_energy(
                        mass_kg=impact_mass,
                        velocity_m_s=impact_velocity,
                    ),
                )
            )

            break

        # ----------------------------------------------------
        # Complete ablation
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Validate current gamma
        # ----------------------------------------------------

        gamma = (
            current_state.flight_path_angle_rad
            if current_state.flight_path_angle_rad
            is not None
            else entry.entry_angle_rad
        )

        if not 0.0 < gamma < math.pi / 2.0:

            events.append(
                EventRecord(
                    type="model_boundary",
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

            break

        # ----------------------------------------------------
        # Fragmentation
        # ----------------------------------------------------

        sample = samples[-1]

        if fragmentation_triggered(
            dynamic_pressure_Pa=sample.dynamic_pressure_Pa,
            material_strength_Pa=(
                asteroid.material_strength_Pa
            ),
        ):

            if config.stop_on_fragmentation:

                fragments = create_fragments(
                    mass_kg=current_state.mass_kg,
                    velocity_m_s=current_state.velocity_m_s,
                )

                fragment_states = initial_fragment_states(
                    fragments=fragments,
                    altitude_m=current_state.altitude_m,
                )

                # V0.3 improvement:
                # fragments inherit the parent's instantaneous
                # flight-path angle at breakup.
                breakup_gamma = (
                    current_state.flight_path_angle_rad
                    if current_state.flight_path_angle_rad
                    is not None
                    else entry.entry_angle_rad
                )

                fragment_trajectories = tuple(
                    simulate_fragment(
                        fragment=fragment_state,
                        asteroid=asteroid,
                        config=config,
                        entry_angle_rad=breakup_gamma,
                    )
                    for fragment_state
                    in fragment_states
                )

                events.append(
                    EventRecord(
                        type="fragmentation",
                        time_s=time_s,
                        altitude_m=(
                            current_state.altitude_m
                        ),
                        velocity_m_s=(
                            current_state.velocity_m_s
                        ),
                        mass_kg=(
                            current_state.mass_kg
                        ),
                        energy_J=(
                            sample.kinetic_energy_J
                        ),
                    )
                )

                break

        # ----------------------------------------------------
        # RK4 step
        # ----------------------------------------------------

        next_state = rk4_step(
            state=current_state,
            time_s=time_s,
            timestep_s=config.timestep_s,
            asteroid=asteroid,
            entry=entry,
        )

        # ----------------------------------------------------
        # Numerical safety
        # ----------------------------------------------------

        if next_state.mass_kg < 0.0:
            next_state.mass_kg = 0.0

        if next_state.velocity_m_s < 0.0:
            next_state.velocity_m_s = 0.0

        if (
            next_state.flight_path_angle_rad
            is not None
            and not math.isfinite(
                next_state.flight_path_angle_rad
            )
        ):
            events.append(
                EventRecord(
                    type="model_boundary",
                    time_s=time_s,
                    altitude_m=max(
                        next_state.altitude_m,
                        0.0,
                    ),
                    velocity_m_s=max(
                        next_state.velocity_m_s,
                        0.0,
                    ),
                    mass_kg=max(
                        next_state.mass_kg,
                        0.0,
                    ),
                    energy_J=0.0,
                )
            )

            break

        if not math.isfinite(
            next_state.downrange_m
        ):
            events.append(
                EventRecord(
                    type="model_boundary",
                    time_s=time_s,
                    altitude_m=max(
                        next_state.altitude_m,
                        0.0,
                    ),
                    velocity_m_s=max(
                        next_state.velocity_m_s,
                        0.0,
                    ),
                    mass_kg=max(
                        next_state.mass_kg,
                        0.0,
                    ),
                    energy_J=0.0,
                )
            )

            break

        next_time = (
            time_s + config.timestep_s
        )

        # ----------------------------------------------------
        # Ground crossing protection
        # ----------------------------------------------------

        if next_state.altitude_m < 0.0:

            next_state.altitude_m = 0.0

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

            continue

        # ----------------------------------------------------
        # Normal sample
        # ----------------------------------------------------

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

    # --------------------------------------------------------
    # Existing V0.2 post-processing
    # --------------------------------------------------------

    energy_deposition_profile = (
        build_energy_deposition_profile(
            samples
        )
    )

    event_energy = aggregate_event_energy(
        parent_deposition_profile=(
            energy_deposition_profile
        ),
        fragment_trajectories=(
            fragment_trajectories
        ),
    )

    airburst_classification = classify_airburst(
        atmospheric_energy_J=(
            event_energy.atmospheric_drag_work_J
        ),
        ground_impact_energy_J=(
            event_energy.ground_impact_energy_J
        ),
    )

    return SimulationResult(
        samples=samples,
        events=events,
        total_drag_energy_J=(
            total_drag_energy_J
        ),
        fragment_trajectories=(
            fragment_trajectories
        ),
        energy_deposition_profile=(
            energy_deposition_profile
        ),
        event_energy=event_energy,
        airburst_classification=(
            airburst_classification
        ),
    )
