from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
)
from physics.solver import simulate


ASTEROID = AsteroidParameters(
    diameter_m=20.0,
    bulk_density_kg_m3=3500.0,
    drag_coefficient=1.0,
    heat_transfer_coefficient=0.1,
    effective_heat_of_ablation_J_kg=8.0e6,
    material_strength_Pa=1.0e6,
)

ENTRY = EntryConditions(
    initial_altitude_m=80_000.0,
    initial_velocity_m_s=20_000.0,
    entry_angle_rad=0.7853981633974483,
)


def run_with_timestep(timestep_s):
    return simulate(
        asteroid=ASTEROID,
        entry=ENTRY,
        config=SimulationConfig(
            timestep_s=timestep_s,
            max_time_s=1000.0,
        ),
    )


def final_event(result):
    assert result.events
    return result.events[-1]


def relative_difference(value_a, value_b):
    scale = max(abs(value_a), abs(value_b))

    if scale == 0.0:
        return 0.0

    return abs(value_a - value_b) / scale


def test_timestep_convergence():
    coarse = run_with_timestep(0.01)
    medium = run_with_timestep(0.005)
    fine = run_with_timestep(0.0025)

    coarse_event = final_event(coarse)
    medium_event = final_event(medium)
    fine_event = final_event(fine)

    assert coarse_event.type == medium_event.type
    assert medium_event.type == fine_event.type

    quantities = (
        (
            "fragmentation altitude",
            coarse_event.altitude_m,
            medium_event.altitude_m,
            fine_event.altitude_m,
        ),
        (
            "fragmentation velocity",
            coarse_event.velocity_m_s,
            medium_event.velocity_m_s,
            fine_event.velocity_m_s,
        ),
        (
            "fragmentation mass",
            coarse_event.mass_kg,
            medium_event.mass_kg,
            fine_event.mass_kg,
        ),
        (
            "fragmentation energy",
            coarse_event.energy_J,
            medium_event.energy_J,
            fine_event.energy_J,
        ),
        (
            "total drag work",
            coarse.total_drag_energy_J,
            medium.total_drag_energy_J,
            fine.total_drag_energy_J,
        ),
    )

    for name, coarse_value, medium_value, fine_value in quantities:
        coarse_to_medium = relative_difference(
            coarse_value,
            medium_value,
        )

        medium_to_fine = relative_difference(
            medium_value,
            fine_value,
        )

        assert medium_to_fine < coarse_to_medium, (
            f"{name} did not converge: "
            f"{coarse_to_medium=}, "
            f"{medium_to_fine=}"
        )
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
)
from physics.solver import simulate


ASTEROID = AsteroidParameters(
    diameter_m=20.0,
    bulk_density_kg_m3=3500.0,
    drag_coefficient=1.0,
    heat_transfer_coefficient=0.1,
    effective_heat_of_ablation_J_kg=8.0e6,
    material_strength_Pa=1.0e6,
)

ENTRY = EntryConditions(
    initial_altitude_m=80_000.0,
    initial_velocity_m_s=20_000.0,
    entry_angle_rad=0.7853981633974483,
)


def run_with_timestep(timestep_s):
    config = SimulationConfig(
        timestep_s=timestep_s,
        max_time_s=1000.0,
    )

    return simulate(
        asteroid=ASTEROID,
        entry=ENTRY,
        config=config,
    )


def final_event(result):
    assert result.events
    return result.events[-1]


def test_timestep_convergence():
    coarse = run_with_timestep(0.01)
    medium = run_with_timestep(0.005)
    fine = run_with_timestep(0.0025)

    coarse_event = final_event(coarse)
    medium_event = final_event(medium)
    fine_event = final_event(fine)

    # The physical event should remain the same.
    assert coarse_event.type == medium_event.type
    assert medium_event.type == fine_event.type

    # Differences should shrink as the timestep is reduced.
    altitude_coarse_medium = abs(
        coarse_event.altitude_m - medium_event.altitude_m
    )
    altitude_medium_fine = abs(
        medium_event.altitude_m - fine_event.altitude_m
    )

    velocity_coarse_medium = abs(
        coarse_event.velocity_m_s - medium_event.velocity_m_s
    )
    velocity_medium_fine = abs(
        medium_event.velocity_m_s - fine_event.velocity_m_s
    )

    mass_coarse_medium = abs(
        coarse_event.mass_kg - medium_event.mass_kg
    )
    mass_medium_fine = abs(
        medium_event.mass_kg - fine_event.mass_kg
    )

    energy_coarse_medium = abs(
        coarse_event.energy_J - medium_event.energy_J
    )
    energy_medium_fine = abs(
        medium_event.energy_J - fine_event.energy_J
    )

    assert altitude_medium_fine <= altitude_coarse_medium
    assert velocity_medium_fine <= velocity_coarse_medium
    assert mass_medium_fine <= mass_coarse_medium
    assert energy_medium_fine <= energy_coarse_medium
