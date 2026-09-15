#!/usr/bin/env python3
"""Idempotent one-shot patch: wire Next Frontier enrichment into main.py.

Run from repo root or backend/:
  python backend/apply_next_frontier_patch.py
"""
from __future__ import annotations

from pathlib import Path

MAIN = Path(__file__).resolve().parent / "main.py"


def patch(text: str) -> str:
    if "from physics.enrichment import enrich_payload" in text and "extra = enrich_payload" in text:
        print("Already fully patched")
        return text

    if "from physics.enrichment import enrich_payload" not in text:
        text = text.replace(
            "from physics.consequences import (\n"
            "    calculate_impact_consequences,\n"
            "    consequences_to_dict,\n"
            ")",
            "from physics.consequences import (\n"
            "    calculate_impact_consequences,\n"
            "    consequences_to_dict,\n"
            ")\n"
            "from physics.enrichment import enrich_payload",
            1,
        )

    text = text.replace('API_VERSION = "0.4.0"', 'API_VERSION = "0.5.0"', 1)

    if "surface_hint: str | None = Field" not in text:
        text = text.replace(
            "    entry_azimuth_deg: float = Field(\n"
            "        default=90.0,\n"
            "        ge=0.0,\n"
            "        lt=360.0,\n"
            "    )\n\n\n"
            "class SimulationResponse",
            "    entry_azimuth_deg: float = Field(\n"
            "        default=90.0,\n"
            "        ge=0.0,\n"
            "        lt=360.0,\n"
            "    )\n\n"
            "    surface_hint: str | None = Field(\n"
            "        default=None,\n"
            '        description="Optional land or ocean. None = auto-classify.",\n'
            "    )\n\n\n"
            "class SimulationResponse",
            1,
        )

    if "request.surface_hint" not in text:
        text = text.replace(
            "    scenario = ImpactScenario(\n"
            "        latitude_deg=(\n"
            "            request.latitude_deg\n"
            "        ),\n"
            "        longitude_deg=(\n"
            "            request.longitude_deg\n"
            "        ),\n"
            "        entry_azimuth_deg=(\n"
            "            request.entry_azimuth_deg\n"
            "        ),\n"
            "    )\n\n"
            "    config = SimulationConfig(\n"
            "        timestep_s=request.timestep_s,\n"
            "        max_time_s=request.max_time_s,\n"
            "    )",
            "    scenario = ImpactScenario(\n"
            "        latitude_deg=(\n"
            "            request.latitude_deg\n"
            "        ),\n"
            "        longitude_deg=(\n"
            "            request.longitude_deg\n"
            "        ),\n"
            "        entry_azimuth_deg=(\n"
            "            request.entry_azimuth_deg\n"
            "        ),\n"
            "        surface_hint=(\n"
            "            request.surface_hint\n"
            "        ),\n"
            "    )\n\n"
            "    config = SimulationConfig(\n"
            "        timestep_s=request.timestep_s,\n"
            "        max_time_s=request.max_time_s,\n"
            "    )",
            1,
        )

    if "surface_hint: str | None = None" not in text:
        text = text.replace(
            "async def simulate_from_neo(\n"
            "    asteroid_id: str,\n"
            "    latitude_deg: float = 0.0,\n"
            "    longitude_deg: float = 0.0,\n"
            "    entry_azimuth_deg: float = 90.0,\n"
            "):\n\n"
            "    scenario = ImpactScenario(\n"
            "        latitude_deg=latitude_deg,\n"
            "        longitude_deg=longitude_deg,\n"
            "        entry_azimuth_deg=entry_azimuth_deg,\n"
            "    )",
            "async def simulate_from_neo(\n"
            "    asteroid_id: str,\n"
            "    latitude_deg: float = 0.0,\n"
            "    longitude_deg: float = 0.0,\n"
            "    entry_azimuth_deg: float = 90.0,\n"
            "    surface_hint: str | None = None,\n"
            "):\n\n"
            "    scenario = ImpactScenario(\n"
            "        latitude_deg=latitude_deg,\n"
            "        longitude_deg=longitude_deg,\n"
            "        entry_azimuth_deg=entry_azimuth_deg,\n"
            "        surface_hint=surface_hint,\n"
            "    )",
            1,
        )

    if "extra = enrich_payload" not in text:
        old_return = (
            "    return {\n\n"
            '        "status": "completed",\n\n'
            '        "asteroid": {\n'
            '            "id": (\n'
            "                resolved.asteroid_id\n"
            "            ),\n\n"
            '            "name": (\n'
            "                resolved.name\n"
            "            ),\n\n"
            '            "hazardous": (\n'
            "                resolved.hazardous\n"
            "            ),\n\n"
            '            "diameter_km": (\n'
            '                neo["diameter_km"]\n'
            "            ),\n\n"
            '            "approach_date": (\n'
            '                neo["approach_date"]\n'
            "            ),\n\n"
            '            "miss_distance_km": (\n'
            '                neo["miss_distance_km"]\n'
            "            ),\n\n"
            '            "velocity_kph": (\n'
            '                neo["velocity_kph"]\n'
            "            ),\n"
            "        },\n\n"
            '        "assumptions": (\n'
            "            resolved.assumptions\n"
            "        ),\n\n"
            '        "trajectory": (\n'
            "            simulation_response.trajectory\n"
            "        ),\n\n"
            '        "simulation": (\n'
            "            simulation_response.model_dump()\n"
            "        ),\n"
            "    }\n"
        )
        new_return = (
            "    extra = enrich_payload(\n"
            "        scenario=scenario,\n"
            "        simulation_response=simulation_response,\n"
            "    )\n\n"
            "    return {\n\n"
            '        "status": "completed",\n\n'
            '        "asteroid": {\n'
            '            "id": (\n'
            "                resolved.asteroid_id\n"
            "            ),\n\n"
            '            "name": (\n'
            "                resolved.name\n"
            "            ),\n\n"
            '            "hazardous": (\n'
            "                resolved.hazardous\n"
            "            ),\n\n"
            '            "diameter_km": (\n'
            '                neo["diameter_km"]\n'
            "            ),\n\n"
            '            "approach_date": (\n'
            '                neo["approach_date"]\n'
            "            ),\n\n"
            '            "miss_distance_km": (\n'
            '                neo["miss_distance_km"]\n'
            "            ),\n\n"
            '            "velocity_kph": (\n'
            '                neo["velocity_kph"]\n'
            "            ),\n"
            "        },\n\n"
            '        "assumptions": (\n'
            "            resolved.assumptions\n"
            "        ),\n\n"
            "        **extra,\n\n"
            '        "trajectory": (\n'
            "            simulation_response.trajectory\n"
            "        ),\n\n"
            '        "simulation": (\n'
            "            simulation_response.model_dump()\n"
            "        ),\n"
            "    }\n"
        )
        if old_return not in text:
            raise SystemExit("Could not find from-neo return block to patch")
        text = text.replace(old_return, new_return, 1)

    if "payload.update(extra)" not in text:
        old_entry = (
            "    return _build_simulation_response(\n"
            "        result,\n"
            "        scenario=scenario,\n"
            "        entry=entry,\n"
            "        asteroid=asteroid,\n"
            "    )\n\n\n"
            "# ============================================================\n"
            "# NASA -> SIMULATION\n"
            "# ============================================================"
        )
        new_entry = (
            "    simulation_response = _build_simulation_response(\n"
            "        result,\n"
            "        scenario=scenario,\n"
            "        entry=entry,\n"
            "        asteroid=asteroid,\n"
            "    )\n"
            "    extra = enrich_payload(\n"
            "        scenario=scenario,\n"
            "        simulation_response=simulation_response,\n"
            "    )\n"
            "    payload = simulation_response.model_dump()\n"
            "    payload.update(extra)\n"
            "    return payload\n\n\n"
            "# ============================================================\n"
            "# NASA -> SIMULATION\n"
            "# ============================================================"
        )
        if old_entry not in text:
            print("WARN: direct entry return not patched (pattern mismatch)")
        else:
            text = text.replace(old_entry, new_entry, 1)

    return text


def main() -> None:
    original = MAIN.read_text()
    updated = patch(original)
    compile(updated, str(MAIN), "exec")
    MAIN.write_text(updated)
    print(f"Patched {MAIN}")


if __name__ == "__main__":
    main()
