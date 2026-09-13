from __future__ import annotations
import math
from dataclasses import dataclass
from physics.consequences import (
    ImpactConsequences,
    calculate_impact_consequences,
)


from physics.ablation import ablation_mass_derivative
from physics.atmosphere import state as atmosphere_state
from physics.drag import (
    drag_acceleration,
    drag_force,
)
from physics.energy import kinetic_energy
from physics.fragmentation import Fragment
from physics.geometry import (
    equivalent_radius_from_mass,
    projected_area,
)
from physics.models import AsteroidParameters, SimulationConfig


@dataclass(frozen=True)
class FragmentState:
    """State of one atmospheric fragment."""

    altitude_m: float
    velocity_m_s: float
    mass_kg: float


@dataclass(frozen=True)
class FragmentSample:
    """Recorded state of a fragment during flight."""

    time_s: float
    altitude_m: float
    velocity_m_s: float
    mass_kg: float
    kinetic_energy_J: float


@dataclass(frozen=True)
class FragmentOutcome:
    """Final outcome of one fragment."""

    outcome: str
    altitude_m: float
    velocity_m_s: float
    mass_kg: float
    kinetic_energy_J: float


@dataclass(frozen=True)
class FragmentTrajectory:
    """Complete simulated trajectory of one fragment."""

    samples: tuple[FragmentSample, ...]
    outcome: FragmentOutcome
    consequences: ImpactConsequences

def fragment_kinetic_energy(
    mass_kg: float,
    velocity_m_s: float,
) -> float:
    """Return kinetic energy of a fragment."""

    return kinetic_energy(
        mass_kg=mass_kg,
        velocity_m_s=velocity_m_s,
    )


def initial_fragment_states(
    fragments: tuple[Fragment, ...],
    altitude_m: float,
) -> tuple[FragmentState, ...]:
    """Create atmospheric states immediately after breakup."""

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    return tuple(
        FragmentState(
            altitude_m=altitude_m,
            velocity_m_s=fragment.velocity_m_s,
            mass_kg=fragment.mass_kg,
        )
        for fragment in fragments
    )


def classify_fragment_outcome(
    altitude_m: float,
    velocity_m_s: float,
    mass_kg: float,
) -> FragmentOutcome:
    """Classify the final state of a fragment."""

    if altitude_m < 0:
        raise ValueError("altitude_m cannot be negative")

    if velocity_m_s < 0:
        raise ValueError("velocity_m_s cannot be negative")

    if mass_kg < 0:
        raise ValueError("mass_kg cannot be negative")

    if mass_kg == 0:
        outcome = "complete_ablation"
    elif altitude_m <= 0:
        outcome = "ground_impact"
    else:
        outcome = "airborne_fragment"

    return FragmentOutcome(
        outcome=outcome,
        altitude_m=altitude_m,
        velocity_m_s=velocity_m_s,
        mass_kg=mass_kg,
        kinetic_energy_J=fragment_kinetic_energy(
            mass_kg=mass_kg,
            velocity_m_s=velocity_m_s,
        ),
    )


def _fragment_derivative(
    state: FragmentState,
    asteroid: AsteroidParameters,
    entry_angle_rad: float,
) -> FragmentState:
    """Return d(state)/dt for one fragment."""

    atmosphere = atmosphere_state(max(state.altitude_m, 0.0))

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

    g0 = 9.80665
    earth_radius_m = 6_371_000.0

    gravity = g0 * (
        earth_radius_m / (earth_radius_m + state.altitude_m)
    ) ** 2

    altitude_derivative = -state.velocity_m_s * math.sin(
        entry_angle_rad
    )

    velocity_derivative = (
        gravity * math.sin(entry_angle_rad)
        - acceleration
    )

    return FragmentState(
        altitude_m=altitude_derivative,
        velocity_m_s=velocity_derivative,
        mass_kg=mass_derivative,
    )


def _add_states(
    state: FragmentState,
    derivative: FragmentState,
    scale: float,
) -> FragmentState:
    """Return state + scale * derivative."""

    return FragmentState(
        altitude_m=state.altitude_m
        + scale * derivative.altitude_m,
        velocity_m_s=state.velocity_m_s
        + scale * derivative.velocity_m_s,
        mass_kg=state.mass_kg
        + scale * derivative.mass_kg,
    )


def _rk4_step(
    state: FragmentState,
    dt: float,
    asteroid: AsteroidParameters,
    entry_angle_rad: float,
) -> FragmentState:
    """Advance one fragment using RK4."""

    k1 = _fragment_derivative(
        state,
        asteroid,
        entry_angle_rad,
    )

    k2_state = _add_states(state, k1, dt / 2.0)

    k2 = _fragment_derivative(
        k2_state,
        asteroid,
        entry_angle_rad,
    )

    k3_state = _add_states(state, k2, dt / 2.0)

    k3 = _fragment_derivative(
        k3_state,
        asteroid,
        entry_angle_rad,
    )

    k4_state = _add_states(state, k3, dt)

    k4 = _fragment_derivative(
        k4_state,
        asteroid,
        entry_angle_rad,
    )

    return FragmentState(
        altitude_m=state.altitude_m
        + dt / 6.0
        * (
            k1.altitude_m
            + 2.0 * k2.altitude_m
            + 2.0 * k3.altitude_m
            + k4.altitude_m
        ),
        velocity_m_s=state.velocity_m_s
        + dt / 6.0
        * (
            k1.velocity_m_s
            + 2.0 * k2.velocity_m_s
            + 2.0 * k3.velocity_m_s
            + k4.velocity_m_s
        ),
        mass_kg=state.mass_kg
        + dt / 6.0
        * (
            k1.mass_kg
            + 2.0 * k2.mass_kg
            + 2.0 * k3.mass_kg
            + k4.mass_kg
        ),
    )


def simulate_fragment(
    fragment: FragmentState,
    asteroid: AsteroidParameters,
    config: SimulationConfig,
    entry_angle_rad: float,
) -> FragmentTrajectory:
    """
    Simulate one fragment after breakup.

    Simplification:
    all fragments retain the parent's entry angle.
    """

    asteroid.validate()
    config.validate()

    if not 0.0 < entry_angle_rad < math.pi / 2.0:
        raise ValueError(
            "entry_angle_rad must be between 0 and pi/2"
        )

    if fragment.altitude_m < 0:
        raise ValueError("fragment altitude cannot be negative")

    if fragment.velocity_m_s < 0:
        raise ValueError("fragment velocity cannot be negative")

    if fragment.mass_kg <= 0:
        raise ValueError("fragment mass must be greater than zero")

    state = fragment
    time_s = 0.0

    samples: list[FragmentSample] = []

    while time_s <= config.max_time_s:

        samples.append(
            FragmentSample(
                time_s=time_s,
                altitude_m=state.altitude_m,
                velocity_m_s=state.velocity_m_s,
                mass_kg=state.mass_kg,
                kinetic_energy_J=fragment_kinetic_energy(
                    state.mass_kg,
                    state.velocity_m_s,
                ),
            )
        )

        if state.altitude_m <= 0.0:
            state = FragmentState(
                altitude_m=0.0,
                velocity_m_s=state.velocity_m_s,
                mass_kg=state.mass_kg,
            )

            break

        if state.mass_kg <= config.min_mass_kg:
            state = FragmentState(
                altitude_m=state.altitude_m,
                velocity_m_s=state.velocity_m_s,
                mass_kg=0.0,
            )

            break

        next_state = _rk4_step(
            state=state,
            dt=config.timestep_s,
            asteroid=asteroid,
            entry_angle_rad=entry_angle_rad,
        )

        state = FragmentState(
            altitude_m=max(next_state.altitude_m, 0.0),
            velocity_m_s=max(next_state.velocity_m_s, 0.0),
            mass_kg=max(next_state.mass_kg, 0.0),
        )

        time_s += config.timestep_s

    else:
        time_s = config.max_time_s

    if state.mass_kg <= config.min_mass_kg:
        state = FragmentState(
            altitude_m=state.altitude_m,
            velocity_m_s=state.velocity_m_s,
            mass_kg=0.0,
        )

    if state.mass_kg == 0.0:
        outcome = "complete_ablation"
    elif state.altitude_m <= 0.0:
        outcome = "ground_impact"
    else:
        outcome = "max_time"

    final_outcome = FragmentOutcome(
        outcome=outcome,
        altitude_m=state.altitude_m,
        velocity_m_s=state.velocity_m_s,
        mass_kg=state.mass_kg,
        kinetic_energy_J=fragment_kinetic_energy(
            state.mass_kg,
            state.velocity_m_s,
        ),
    )
    consequences = calculate_impact_consequences(
        outcome=final_outcome.outcome,
        mass_kg=final_outcome.mass_kg,
        velocity_m_s=final_outcome.velocity_m_s,
    )

    return FragmentTrajectory(
        samples=tuple(samples),
        outcome=final_outcome,
        consequences=consequences,
    )
