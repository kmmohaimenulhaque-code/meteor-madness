from __future__ import annotations

import math

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


VALID_REQUEST = {
    "diameter_m": 20.0,
    "bulk_density_kg_m3": 3500.0,
    "initial_velocity_m_s": 20000.0,
    "entry_angle_rad": 0.7853981633974483,
    "drag_coefficient": 1.0,
    "heat_transfer_coefficient": 0.1,
    "effective_heat_of_ablation_J_kg": 8.0e6,
    "material_strength_Pa": 1.0e6,
    "shape_factor": 1.0,
    "initial_altitude_m": 80000.0,
    "timestep_s": 0.01,
    "max_time_s": 1000.0,
    "min_mass_kg": 1e-6,
}


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_simulation_endpoint_returns_completed_result():
    response = client.post(
        "/api/simulation/entry",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["outcome"] in {
        "ground_impact",
        "complete_ablation",
        "fragmentation",
        "model_boundary",
        "max_time",
    }


def test_simulation_response_contains_required_fields():
    response = client.post(
        "/api/simulation/entry",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200

    data = response.json()

    required_fields = {
        "status",
        "outcome",
        "initial_mass_kg",
        "parent_final_mass_kg",
        "parent_final_altitude_m",
        "parent_final_velocity_m_s",
        "parent_final_energy_J",
        "impact_mass_kg",
        "impact_velocity_m_s",
        "impact_energy_J",
        "total_drag_energy_J",
        "fragmentation_detected",
        "fragmentation_altitude_m",
        "atmospheric_drag_work_J",
        "ground_impact_energy_J",
        "atmospheric_fraction",
        "profile",
    }

    assert required_fields.issubset(data.keys())


def test_simulation_values_are_finite_and_non_negative():
    response = client.post(
        "/api/simulation/entry",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200

    data = response.json()

    numeric_fields = [
        "initial_mass_kg",
        "parent_final_mass_kg",
        "parent_final_altitude_m",
        "parent_final_velocity_m_s",
        "parent_final_energy_J",
        "impact_mass_kg",
        "impact_velocity_m_s",
        "impact_energy_J",
        "total_drag_energy_J",
        "fragmentation_altitude_m",
        "atmospheric_drag_work_J",
        "ground_impact_energy_J",
        "atmospheric_fraction",
    ]

    for field in numeric_fields:
        value = data[field]

        if value is not None:
            assert math.isfinite(value)
            assert value >= 0


def test_fragmentation_result_contains_impact_data():
    response = client.post(
        "/api/simulation/entry",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["fragmentation_detected"] is True
    assert data["fragmentation_altitude_m"] is not None

    assert data["impact_mass_kg"] is not None
    assert data["impact_velocity_m_s"] is not None
    assert data["impact_energy_J"] is not None

    assert data["impact_mass_kg"] > 0
    assert data["impact_energy_J"] > 0


def test_profile_contains_simulation_samples():
    response = client.post(
        "/api/simulation/entry",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200

    profile = response.json()["profile"]

    assert isinstance(profile, list)
    assert len(profile) > 1

    first_sample = profile[0]

    expected_fields = {
        "altitude_m",
        "velocity_m_s",
        "mass_kg",
        "density_kg_m3",
        "drag_force_N",
        "drag_power_W",
        "kinetic_energy_J",
        "dynamic_pressure_Pa",
        "mass_loss_rate_kg_s",
    }

    assert expected_fields.issubset(first_sample.keys())


def test_invalid_diameter_is_rejected():
    payload = {
        **VALID_REQUEST,
        "diameter_m": -1.0,
    }

    response = client.post(
        "/api/simulation/entry",
        json=payload,
    )

    assert response.status_code == 422


def test_invalid_velocity_is_rejected():
    payload = {
        **VALID_REQUEST,
        "initial_velocity_m_s": 0,
    }

    response = client.post(
        "/api/simulation/entry",
        json=payload,
    )

    assert response.status_code == 422


def test_invalid_entry_angle_is_rejected():
    payload = {
        **VALID_REQUEST,
        "entry_angle_rad": 0,
    }

    response = client.post(
        "/api/simulation/entry",
        json=payload,
    )

    assert response.status_code == 422


def test_invalid_timestep_is_rejected():
    payload = {
        **VALID_REQUEST,
        "timestep_s": 0,
    }

    response = client.post(
        "/api/simulation/entry",
        json=payload,
    )

    assert response.status_code == 422
