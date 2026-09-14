"""
Talks to NASA NeoWs (Near Earth Object Web Service) and returns a
small, frontend-friendly list of asteroids.

Why this file exists:
- Keeps all NASA-specific URL and JSON logic in one place
- The React app never has to understand NASA's nested JSON shape
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

NASA_FEED_URL = "https://api.nasa.gov/neo/rest/v1/feed"

# NeoWs feed allows at most 7 days between start and end.
MAX_RANGE_DAYS = 7


def default_date_range() -> tuple[str, str]:
    """Return (start_date, end_date) as YYYY-MM-DD for the next 7 days."""
    start = date.today()
    end = start + timedelta(days=MAX_RANGE_DAYS - 1)
    return start.isoformat(), end.isoformat()


def _estimated_diameter_km(neo: dict[str, Any]) -> float | None:
    """Pick a single diameter number (km) from NASA's min/max estimate."""
    try:
        km = neo["estimated_diameter"]["kilometers"]
        return round((km["estimated_diameter_min"] + km["estimated_diameter_max"]) / 2, 4)
    except (KeyError, TypeError):
        return None


def _first_approach(neo: dict[str, Any]) -> dict[str, Any]:
    """Each NEO can have several close-approach entries; we use the first."""
    approaches = neo.get("close_approach_data") or []
    return approaches[0] if approaches else {}


def flatten_neo(neo: dict[str, Any]) -> dict[str, Any]:
    """
    Convert one nested NASA NEO object into a flat dict for the UI.

    NASA shape (simplified):
      {
        "name": "(2024 AB)",
        "is_potentially_hazardous_asteroid": false,
        "estimated_diameter": { "kilometers": { "min": ..., "max": ... } },
        "close_approach_data": [
          {
            "close_approach_date": "2026-09-12",
            "miss_distance": { "kilometers": "1234567" },
            "relative_velocity": { "kilometers_per_hour": "50000" }
          }
        ]
      }

    Our shape:
      {
        "id", "name", "hazardous", "diameter_km",
        "approach_date", "miss_distance_km", "velocity_kph"
      }
    """
    approach = _first_approach(neo)
    miss = approach.get("miss_distance") or {}
    velocity = approach.get("relative_velocity") or {}

    miss_km = miss.get("kilometers")
    velocity_kph = velocity.get("kilometers_per_hour")

    return {
        "id": neo.get("id") or neo.get("neo_reference_id"),
        "name": neo.get("name", "Unknown"),
        "hazardous": bool(neo.get("is_potentially_hazardous_asteroid")),
        "diameter_km": _estimated_diameter_km(neo),
        "approach_date": approach.get("close_approach_date"),
        "miss_distance_km": round(float(miss_km), 0) if miss_km is not None else None,
        "velocity_kph": round(float(velocity_kph), 0) if velocity_kph is not None else None,
    }


def flatten_feed(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    NASA returns asteroids grouped by date:
      { "near_earth_objects": { "2026-09-11": [ {...}, ... ], ... } }

    We flatten that into one list so the chart/table are easy to build.
    """
    by_date = payload.get("near_earth_objects") or {}
    asteroids: list[dict[str, Any]] = []
    for _day, neos in by_date.items():
        for neo in neos:
            asteroids.append(flatten_neo(neo))
    # Stable, readable order for the table
    asteroids.sort(key=lambda a: (a.get("approach_date") or "", a.get("name") or ""))
    return asteroids


async def fetch_neos(
    api_key: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Call NASA NeoWs and return a compact payload for the dashboard.

    Returns:
      {
        "start_date": "...",
        "end_date": "...",
        "count": N,
        "hazardous_count": N,
        "asteroids": [ ... flattened objects ... ]
      }
    """
    if not start_date or not end_date:
        start_date, end_date = default_date_range()

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "api_key": api_key,
    }

    # Short timeout so a hung NASA request cannot freeze the app on a low-RAM machine.
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(NASA_FEED_URL, params=params)
        response.raise_for_status()
        raw = response.json()

    asteroids = flatten_feed(raw)
    hazardous_count = sum(1 for a in asteroids if a["hazardous"])

    return {
        "start_date": start_date,
        "end_date": end_date,
        "count": len(asteroids),
        "hazardous_count": hazardous_count,
        "asteroids": asteroids,
    }
