
from physics.models import (
    AsteroidParameters,
    EntryConditions,
    SimulationConfig,
)
from physics.solver import simulate


asteroid = AsteroidParameters(
    diameter_m=20.0,
    bulk_density_kg_m3=3500.0,
    drag_coefficient=1.0,
    heat_transfer_coefficient=0.1,
    effective_heat_of_ablation_J_kg=8.0e6,
    material_strength_Pa=1.0e6,
)

entry = EntryConditions(
    initial_altitude_m=80_000.0,
    initial_velocity_m_s=20_000.0,
    entry_angle_rad=0.7853981633974483,
)

config = SimulationConfig(
    timestep_s=0.01,
    max_time_s=1000.0,
)


result = simulate(
    asteroid=asteroid,
    entry=entry,
    config=config,
)


print(f"Samples: {len(result.samples)}")
print(f"Events: {len(result.events)}")
print(f"Drag energy: {result.total_drag_energy_J:.3e} J")


for event in result.events:
    print()
    print("EVENT")
    print(f"  Type:     {event.type}")
    print(f"  Time:     {event.time_s:.3f} s")
    print(f"  Altitude: {event.altitude_m:.3f} m")
    print(f"  Velocity: {event.velocity_m_s:.3f} m/s")
    print(f"  Mass:     {event.mass_kg:.3f} kg")
    print(f"  Energy:   {event.energy_J:.3e} J")

