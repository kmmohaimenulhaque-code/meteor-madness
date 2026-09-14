from physics.event_energy import aggregate_event_energy


class FakeOutcome:
    def __init__(self, outcome):
        self.outcome = outcome


class FakeConsequences:
    def __init__(self, impact_energy_J):
        self.impact_energy_J = impact_energy_J


class FakeTrajectory:
    def __init__(
        self,
        outcome,
        impact_energy_J,
        energy_deposition_profile=(),
    ):
        self.outcome = FakeOutcome(outcome)
        self.consequences = FakeConsequences(
            impact_energy_J
        )
        self.energy_deposition_profile = (
            energy_deposition_profile
        )


def test_event_energy_aggregates_parent_deposition():
    profile = (
        {
            "altitude_m": 50000.0,
            "energy_deposited_J": 100.0,
        },
        {
            "altitude_m": 49000.0,
            "energy_deposited_J": 200.0,
        },
    )

    result = aggregate_event_energy(
        parent_deposition_profile=profile,
        fragment_trajectories=(),
    )

    assert result.atmospheric_drag_work_J == 300.0
    assert result.ground_impact_energy_J == 0.0
    assert result.total_modeled_energy_J == 300.0
    assert result.atmospheric_fraction == 1.0


def test_event_energy_aggregates_ground_impact_fragments():
    trajectory = FakeTrajectory(
        outcome="ground_impact",
        impact_energy_J=500.0,
    )

    result = aggregate_event_energy(
        parent_deposition_profile=(),
        fragment_trajectories=(trajectory,),
    )

    assert result.atmospheric_drag_work_J == 0.0
    assert result.ground_impact_energy_J == 500.0
    assert result.total_modeled_energy_J == 500.0
    assert result.atmospheric_fraction == 0.0


def test_event_energy_ignores_non_ground_fragments():
    trajectory = FakeTrajectory(
        outcome="complete_ablation",
        impact_energy_J=500.0,
    )

    result = aggregate_event_energy(
        parent_deposition_profile=(),
        fragment_trajectories=(trajectory,),
    )

    assert result.ground_impact_energy_J == 0.0


def test_event_energy_combines_atmospheric_and_ground_energy():
    profile = (
        {
            "altitude_m": 50000.0,
            "energy_deposited_J": 500.0,
        },
    )

    trajectory = FakeTrajectory(
        outcome="ground_impact",
        impact_energy_J=500.0,
    )

    result = aggregate_event_energy(
        parent_deposition_profile=profile,
        fragment_trajectories=(trajectory,),
    )

    assert result.atmospheric_drag_work_J == 500.0
    assert result.ground_impact_energy_J == 500.0
    assert result.total_modeled_energy_J == 1000.0
    assert result.atmospheric_fraction == 0.5


def test_fragment_deposition_is_included():
    parent_profile = (
        {
            "energy_deposited_J": 100.0,
        },
    )

    fragment_trajectory = FakeTrajectory(
        outcome="ground_impact",
        impact_energy_J=300.0,
        energy_deposition_profile=(
            {
                "energy_deposited_J": 50.0,
            },
        ),
    )

    result = aggregate_event_energy(
        parent_deposition_profile=parent_profile,
        fragment_trajectories=(fragment_trajectory,),
    )

    assert result.atmospheric_drag_work_J == 150.0
    assert result.ground_impact_energy_J == 300.0
