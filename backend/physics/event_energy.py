from __future__ import annotations

from dataclasses import dataclass

from physics.deposition import total_deposited_energy


@dataclass(frozen=True)
class EventEnergySummary:
    """Combined energy summary for an atmospheric-entry event."""

    atmospheric_drag_work_J: float
    ground_impact_energy_J: float
    total_modeled_energy_J: float
    atmospheric_fraction: float


def aggregate_event_energy(
    parent_deposition_profile,
    fragment_trajectories,
) -> EventEnergySummary:
    """
    Aggregate atmospheric drag-work deposition and surviving
    ground-impact kinetic energy across the complete event.

    Atmospheric energy is currently a drag-work proxy, not a
    complete thermodynamic atmospheric energy budget.
    """

    # Atmospheric drag work before fragmentation.
    atmospheric_drag_work_J = total_deposited_energy(
        parent_deposition_profile
    )

    ground_impact_energy_J = 0.0

    for trajectory in fragment_trajectories:
        # Add atmospheric drag work after fragmentation.
        atmospheric_drag_work_J += total_deposited_energy(
            trajectory.energy_deposition_profile
        )

        # Add surviving kinetic energy at ground impact.
        if trajectory.outcome.outcome == "ground_impact":
            ground_impact_energy_J += (
                trajectory.consequences.impact_energy_J
            )

    total_modeled_energy_J = (
        atmospheric_drag_work_J
        + ground_impact_energy_J
    )

    if total_modeled_energy_J == 0.0:
        atmospheric_fraction = 0.0
    else:
        atmospheric_fraction = (
            atmospheric_drag_work_J
            / total_modeled_energy_J
        )

    return EventEnergySummary(
        atmospheric_drag_work_J=atmospheric_drag_work_J,
        ground_impact_energy_J=ground_impact_energy_J,
        total_modeled_energy_J=total_modeled_energy_J,
        atmospheric_fraction=atmospheric_fraction,
    )
