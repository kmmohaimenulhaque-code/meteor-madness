"""Reverse geocode lat/lon to a human place label (OpenStreetMap Nominatim)."""
from __future__ import annotations

from typing import Any

import httpx


def reverse_geocode(latitude: float, longitude: float) -> dict[str, Any]:
    """
    Best-effort place recognition in English.

    Uses Nominatim with accept-language=en so city/region/country labels
    are returned in English rather than the local language.
    On failure returns unavailable without inventing a location.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "zoom": 8,
                    "addressdetails": 1,
                    # Prefer English names (e.g. "Rajshahi, Bangladesh" not local script)
                    "accept-language": "en",
                },
                headers={
                    "User-Agent": "MeteorMadness-SpaceApps/1.0 (educational demo)",
                    "Accept-Language": "en",
                },
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        return {
            "status": "unavailable",
            "display_name": None,
            "language": "en",
            "error": type(exc).__name__,
        }

    if not isinstance(data, dict):
        return {
            "status": "unavailable",
            "display_name": None,
            "language": "en",
        }

    address = data.get("address") or {}
    parts = [
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet"),
        address.get("state") or address.get("region"),
        address.get("country"),
    ]
    short = ", ".join(p for p in parts if p)

    return {
        "status": "ok",
        "display_name": data.get("display_name") or short or None,
        "short_name": short or data.get("display_name"),
        "country": address.get("country"),
        "state": address.get("state") or address.get("region"),
        "city": address.get("city")
        or address.get("town")
        or address.get("village"),
        "source": "nominatim",
        "language": "en",
    }
