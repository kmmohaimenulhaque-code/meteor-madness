from physics.deposition import total_deposited_energy
from physics.fragment_solver import (
    FragmentState,
    simulate_fragment,
)
from physics.models import (
    AsteroidParameters,
    SimulationConfig,
)


def test_fragment_has_energy_deposition_profile():
    asteroid = AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )

    fragment = FragmentState(
        altitude_m=50000.0,
        velocity_m_s=20000.0,
        mass_kg=1.0e6,
    )

    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=0.1,
    )

    trajectory = simulate_fragment(
        fragment=fragment,
        asteroid=asteroid,
        config=config,
        entry_angle_rad=0.7853981633974483,
    )

    assert trajectory.energy_deposition_profile


def test_fragment_deposition_energy_is_non_negative():
    asteroid = AsteroidParameters(
        diameter_m=20.0,
        bulk_density_kg_m3=3500.0,
        drag_coefficient=1.0,
        heat_transfer_coefficient=0.1,
        effective_heat_of_ablation_J_kg=8.0e6,
        material_strength_Pa=1.0e6,
    )

    fragment = FragmentState(
        altitude_m=50000.0,
        velocity_m_s=20000.0,
        mass_kg=1.0e6,
    )

    config = SimulationConfig(
        timestep_s=0.01,
        max_time_s=0.1,
    )

    trajectory = simulate_fragment(
        fragment=fragment,
        asteroid=asteroid,
        config=config,
        entry_angle_rad=0.7853981633974483,
    )

    total_energy = total_deposited_energy(
        trajectory.energy_deposition_profile
    )

    assert total_energy >= 0.0
