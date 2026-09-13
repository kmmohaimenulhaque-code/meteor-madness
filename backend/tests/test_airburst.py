from physics.airburst import classify_airburst


def test_pure_airburst():
    result = classify_airburst(
        atmospheric_energy_J=1000.0,
        ground_impact_energy_J=0.0,
    )

    assert result.outcome == "airburst"
    assert result.atmospheric_fraction == 1.0


def test_mixed_event():
    result = classify_airburst(
        atmospheric_energy_J=1000.0,
        ground_impact_energy_J=500.0,
    )

    assert result.outcome == "mixed"


def test_ground_impact():
    result = classify_airburst(
        atmospheric_energy_J=100.0,
        ground_impact_energy_J=900.0,
    )

    assert result.outcome == "ground_impact"


def test_no_significant_energy():
    result = classify_airburst(
        atmospheric_energy_J=0.0,
        ground_impact_energy_J=0.0,
    )

    assert result.outcome == "no_significant_energy"


def test_custom_atmospheric_threshold():
    result = classify_airburst(
        atmospheric_energy_J=400.0,
        ground_impact_energy_J=600.0,
        minimum_atmospheric_fraction=0.4,
    )

    assert result.outcome == "mixed"


def test_negative_atmospheric_energy_rejected():
    try:
        classify_airburst(
            atmospheric_energy_J=-1.0,
            ground_impact_energy_J=0.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_negative_ground_energy_rejected():
    try:
        classify_airburst(
            atmospheric_energy_J=0.0,
            ground_impact_energy_J=-1.0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")
