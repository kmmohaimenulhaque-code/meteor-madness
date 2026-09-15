#!/usr/bin/env python3
"""One-shot patch: wire Next Frontier enrichment into main.py (idempotent)."""
from __future__ import annotations

from pathlib import Path

MAIN = Path(__file__).resolve().parent / "main.py"


def main() -> None:
    text = MAIN.read_text()
    if "from physics.enrichment import enrich_payload" in text:
        print("Already patched")
        return

    text = text.replace(
        "from physics.consequences import (\n    calculate_impact_consequences,\n    consequences_to_dict,\n)",
        "from physics.consequences import (\n    calculate_impact_consequences,\n    consequences_to_dict,\n)\nfrom physics.enrichment import enrich_payload",
        1,
    )

    text = text.replace('API_VERSION = "0.4.0"', 'API_VERSION = "0.5.0"', 1)

    if "surface_hint" not in text:
        text = text.replace(
            """    entry_azimuth_deg: float = Field(\n        default=90.0,\n        ge=0.0,\n        lt=360.0,\n    )\n\n\nclass SimulationResponse""",
            """    entry_azimuth_deg: float = Field(\n        default=90.0,\n        ge=0.0,\n        lt=360.0,\n    )\n\n    surface_hint: str | None = Field(\n        default=None,\n        description=\"Optional land or ocean. None = auto-classify.\",\n    )\n\n\nclass SimulationResponse""",
            1,
        )

    # from-neo: add surface_hint param if missing
    if "surface_hint: str | None = None" not in text:
        text = text.replace(
            """async def simulate_from_neo(\n    asteroid_id: str,\n    latitude_deg: float = 0.0,\n    longitude_deg: float = 0.0,\n    entry_azimuth_deg: float = 90.0,\n):\n\n    scenario = ImpactScenario(\n        latitude_deg=latitude_deg,\n        longitude_deg=longitude_deg,\n        entry_azimuth_deg=entry_azimuth_deg,\n    )""",
            """async def simulate_from_neo(\n    asteroid_id: str,\n    latitude_deg: float = 0.0,\n    longitude_deg: float = 0.0,\n    entry_azimuth_deg: float = 90.0,\n    surface_hint: str | None = None,\n):\n\n    scenario = ImpactScenario(\n        latitude_deg=latitude_deg,\n        longitude_deg=longitude_deg,\n        entry_azimuth_deg=entry_azimuth_deg,\n        surface_hint=surface_hint,\n    )""",
            1,
        )

    # Enrich from-neo return
    marker = '"simulation": (\n            simulation_response.model_dump()\n        ),\n    }'
    if "enrich_payload" not in text.split("simulate_from_neo")[-1]:
        enrichment_block = '''    extra = enrich_payload(\n        scenario=scenario,\n        simulation_response=simulation_response,\n    )\n\n    return {\n\n        "status": "completed",\n\n        "asteroid": {\n            "id": (\n                resolved.asteroid_id\n            ),\n\n            "name": (\n                resolved.name\n            ),\n\n            "hazardous": (\n                resolved.hazardous\n            ),\n\n            "diameter_km": (\n                neo["diameter_km"]\n            ),\n\n            "approach_date": (\n                neo["approach_date"]\n            ),\n\n            "miss_distance_km": (\n                neo["miss_distance_km"]\n            ),\n\n            "velocity_kph": (\n                neo["velocity_kph"]\n            ),\n        },\n\n        "assumptions": (\n            resolved.assumptions\n        ),\n\n        **extra,\n\n        "trajectory": (\n            simulation_response.trajectory\n        ),\n\n        "simulation": (\n            simulation_response.model_dump()\n        ),\n    }'''
        # Replace only the final return of from-neo (last occurrence of the pattern)
        idx = text.rfind('    return {\n\n        "status": "completed",')
        if idx < 0:
            raise SystemExit("could not find from-neo return")
        end = text.find("    }\n", idx)
        if end < 0:
            raise SystemExit("could not find end of return")
        end = end + len("    }\n")
        text = text[:idx] + enrichment_block + "\n" + text[end:]

    MAIN = Path(__file__).resolve().parent / "main.py"
    # When run as script, write to main.py
    MAIN.write_text(text) if False else None

    # Always write when executed properly:
    Path(__file__).resolve().parent.joinpath("main.py").write_text(text)
    compile(text, "main.py", "exec")
    print("Patched main.py successfully")


if __name__ == "__main__":
    main()
