"""
AI Analyst — confidence scoring and plain-language report.

Uses Gemini when GEMINI_API_KEY is set; otherwise falls back to a
transparent rule-based offline report (demo-safe / judge-auditable).

Gemini model:
  gemini-3.8-flash

Never hard-code API keys. Set:
  export GEMINI_API_KEY=...

Optional:
  export GEMINI_MODEL=gemini-3.8-flash
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# Gemini configuration
# ---------------------------------------------------------------------------

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


# ---------------------------------------------------------------------------
# Analyst report model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AnalystReport:
    """Structured output of the AI Analyst layer."""

    confidence: float  # 0.0 – 1.0
    confidence_label: str
    risk_level: str  # "low" | "moderate" | "high" | "extreme"
    summary: str
    key_findings: tuple[str, ...]
    limitations: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    source: str = "rule_based"  # "gemini" | "rule_based"

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "risk_level": self.risk_level,
            "summary": self.summary,
            "key_findings": list(self.key_findings),
            "limitations": list(self.limitations),
            "recommended_actions": list(self.recommended_actions),
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# Confidence helpers
# ---------------------------------------------------------------------------

def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.65:
        return "Moderate"
    if score >= 0.40:
        return "Low"
    return "Very low"


# ---------------------------------------------------------------------------
# Offline / deterministic fallback
# ---------------------------------------------------------------------------

def _rule_based_report(
    *,
    outcome: str,
    surface_type: str,
    impact_energy_J: float,
    impact_energy_mt: float,
    fragmentation_detected: bool,
    terrain_confidence: float,
    has_tsunami: bool,
    tsunami_amplitude_m: float | None = None,
    crater_diameter_m: float | None = None,
    atmospheric_fraction: float | None = None,
) -> AnalystReport:

    confidence = 0.75 * terrain_confidence

    if impact_energy_mt > 1000:
        confidence *= 0.7
    elif impact_energy_mt < 1e-4:
        confidence *= 0.85

    if surface_type == "ocean" and has_tsunami:
        confidence *= 0.9

    confidence = max(0.15, min(0.95, confidence))

    if impact_energy_mt >= 100:
        risk = "extreme"
    elif impact_energy_mt >= 1:
        risk = "high"
    elif impact_energy_mt >= 0.01:
        risk = "moderate"
    else:
        risk = "low"

    # ---------------------------------------------------------------
    # Land
    # ---------------------------------------------------------------

    if outcome == "ground_impact" and surface_type == "land":

        crater_txt = (
            f" Estimated final crater diameter "
            f"~{crater_diameter_m / 1000:.2f} km."
            if crater_diameter_m and crater_diameter_m > 0
            else ""
        )

        summary = (
            f"Ground impact on land releasing approximately "
            f"{impact_energy_mt:.3g} Mt TNT equivalent."
            f"{crater_txt}"
        )

    # ---------------------------------------------------------------
    # Ocean
    # ---------------------------------------------------------------

    elif surface_type == "ocean" and has_tsunami:

        amp = tsunami_amplitude_m or 0.0

        summary = (
            f"Ocean impact releasing ~{impact_energy_mt:.3g} Mt. "
            f"Screening tsunami source amplitude on the order of "
            f"{amp:.1f} m "
            f"(highly uncertain; bathymetry required for real assessment)."
        )

    # ---------------------------------------------------------------
    # Atmospheric fragmentation / airburst
    # ---------------------------------------------------------------

    elif fragmentation_detected:

        summary = (
            f"Atmospheric fragmentation / airburst-like behaviour. "
            f"Total energy ~{impact_energy_mt:.3g} Mt with significant "
            f"deposition at altitude."
        )

    # ---------------------------------------------------------------
    # Generic result
    # ---------------------------------------------------------------

    else:

        summary = (
            f"Simulation completed with outcome '{outcome}'. "
            f"Energy scale ~{impact_energy_mt:.3g} Mt TNT equivalent."
        )

    findings = [
        f"Surface classification: {surface_type} "
        f"(terrain confidence {terrain_confidence:.2f}).",
        f"Impact / event energy: {impact_energy_mt:.4g} Mt TNT.",
        f"Fragmentation detected: "
        f"{'yes' if fragmentation_detected else 'no'}.",
    ]

    if atmospheric_fraction is not None:
        findings.append(
            f"Approximate atmospheric energy fraction: "
            f"{atmospheric_fraction * 100:.1f} %."
        )

    if has_tsunami and tsunami_amplitude_m is not None:
        findings.append(
            f"Tsunami screening source amplitude: "
            f"~{tsunami_amplitude_m:.1f} m."
        )

    # IMPORTANT:
    # A terrestrial crater is only reported for the land branch.
    if (
        surface_type == "land"
        and crater_diameter_m
        and crater_diameter_m > 0
    ):
        findings.append(
            f"Final crater diameter (land scaling): "
            f"~{crater_diameter_m / 1000:.3f} km."
        )

    limitations = (
        "Atmospheric entry model is an engineering approximation "
        "(not full hydrocode).",
        "Material strength, density and ablation parameters carry "
        "large uncertainty.",
        "Terrain classification confidence depends on the "
        "environment data source.",
        "Tsunami, blast and thermal effects are screening estimates only.",
        "Results are for educational and relative-risk illustration.",
    )

    actions = (
        "Treat numbers as order-of-magnitude guidance, not precise forecasts.",
        "For any real threat assessment, escalate to specialised "
        "planetary-defence models and agencies.",
        "Improve surface classification with GEBCO / land-cover data "
        "for higher confidence.",
        "Run sensitivity sweeps on density, strength and entry angle.",
    )

    return AnalystReport(
        confidence=round(confidence, 3),
        confidence_label=_confidence_label(confidence),
        risk_level=risk,
        summary=summary,
        key_findings=tuple(findings),
        limitations=limitations,
        recommended_actions=actions,
        source="rule_based",
    )


# ---------------------------------------------------------------------------
# Gemini JSON parsing
# ---------------------------------------------------------------------------

def _parse_gemini_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from Gemini text."""

    cleaned = text.strip()

    # Handle optional markdown JSON fences.
    fence = re.search(
        r"```(?:json)?\s*([\s\S]*?)```",
        cleaned,
    )

    if fence:
        cleaned = fence.group(1).strip()

    try:
        data = json.loads(cleaned)

        if isinstance(data, dict):
            return data

    except json.JSONDecodeError:
        pass

    # Fallback: locate the first JSON object.
    match = re.search(r"\{[\s\S]*\}", cleaned)

    if match:

        try:
            data = json.loads(match.group(0))

            if isinstance(data, dict):
                return data

        except json.JSONDecodeError:
            return None

    return None


# ---------------------------------------------------------------------------
# Gemini 3.8 Flash analyst
# ---------------------------------------------------------------------------

def _gemini_report(
    *,
    outcome: str,
    surface_type: str,
    impact_energy_J: float,
    impact_energy_mt: float,
    fragmentation_detected: bool,
    terrain_confidence: float,
    has_tsunami: bool,
    tsunami_amplitude_m: float | None = None,
    crater_diameter_m: float | None = None,
    atmospheric_fraction: float | None = None,
    api_key: str,
) -> AnalystReport | None:
    """
    Call Gemini 3.8 Flash generateContent.

    Returns None on API failure so the caller can safely use
    the deterministic rule-based fallback.
    """

    payload_context = {
        "outcome": outcome,
        "surface_type": surface_type,
        "impact_energy_J": impact_energy_J,
        "impact_energy_mt": impact_energy_mt,
        "fragmentation_detected": fragmentation_detected,
        "terrain_confidence": terrain_confidence,
        "has_tsunami": has_tsunami,
        "tsunami_amplitude_m": tsunami_amplitude_m,
        "crater_diameter_m": crater_diameter_m,
        "atmospheric_fraction": atmospheric_fraction,
    }

    prompt = f"""You are Mitigation+, the planetary-defence screening analyst
for the NASA Space Apps project "Meteor Madness".

Your job is to explain the supplied simulation results clearly and cautiously.

IMPORTANT AUTHORITY RULES:

1. The simulation is authoritative for numerical results.
2. Never invent or modify a simulation value.
3. Never apply a physics model to the wrong environment branch.
4. Land, ocean, ice and unknown are different branches.
5. A terrestrial crater result is valid only for the land branch.
6. Ocean impacts may have water-displacement, tsunami-screening and
   seafloor-effect results, but these are not coastal inundation forecasts.
7. Unknown terrain must remain unknown. Do not invent environmental effects.
8. Clearly distinguish screening estimates from observations and forecasts.
9. Do not invent casualty numbers.
10. Do not present this demo as an operational emergency-warning system.
11. Explain uncertainty whenever it materially affects interpretation.

Respond with ONLY valid JSON. Do not use markdown.

Schema:
{{
  "confidence": <float 0-1>,
  "risk_level": "<low|moderate|high|extreme>",
  "summary": "<one or two plain-English sentences>",
  "key_findings": ["<short finding>", "..."],
  "limitations": ["<short limitation>", "..."],
  "recommended_actions": ["<short action>", "..."]
}}

Simulation data:
{json.dumps(payload_context, indent=2)}
"""

    # Gemini 3.8 Flash migration:
    #
    # Removed:
    #   temperature
    #   top_p
    #   top_k
    #   thinking_budget
    #   candidate_count
    #
    # Gemini 3.x uses thinkingLevel instead of thinkingBudget.
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "thinkingLevel": "medium",
            "maxOutputTokens": 1024,
            "responseMimeType": "application/json",
        },
    }

    try:

        with httpx.Client(timeout=20.0) as client:

            response = client.post(
                GEMINI_API_URL,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=body,
            )

            response.raise_for_status()

            data = response.json()

    except Exception:
        return None

    try:

        candidates = data.get("candidates", [])

        if not candidates:
            return None

        parts = (
            candidates[0]
            .get("content", {})
            .get("parts", [])
        )

        raw_text = "".join(
            str(part.get("text", ""))
            for part in parts
            if isinstance(part, dict)
        )

    except (IndexError, AttributeError, TypeError):

        return None

    parsed = _parse_gemini_json(raw_text)

    if not parsed:
        return None

    # ---------------------------------------------------------------
    # Confidence
    # ---------------------------------------------------------------

    try:
        confidence = float(
            parsed.get("confidence", 0.6)
        )

    except (TypeError, ValueError):

        confidence = 0.6

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    # ---------------------------------------------------------------
    # Risk
    # ---------------------------------------------------------------

    risk = str(
        parsed.get("risk_level", "moderate")
    ).lower()

    if risk not in (
        "low",
        "moderate",
        "high",
        "extreme",
    ):
        risk = "moderate"

    # ---------------------------------------------------------------
    # List helper
    # ---------------------------------------------------------------

    def _as_tuple(
        value: Any,
        fallback: tuple[str, ...],
    ) -> tuple[str, ...]:

        if isinstance(value, list) and value:

            return tuple(
                str(item)
                for item in value
            )

        return fallback

    # ---------------------------------------------------------------
    # Final report
    # ---------------------------------------------------------------

    return AnalystReport(
        confidence=round(confidence, 3),
        confidence_label=_confidence_label(confidence),
        risk_level=risk,
        summary=str(
            parsed.get("summary")
            or "Gemini analysis completed."
        ),
        key_findings=_as_tuple(
            parsed.get("key_findings"),
            ("No findings returned.",),
        ),
        limitations=_as_tuple(
            parsed.get("limitations"),
            ("Gemini response did not list limitations.",),
        ),
        recommended_actions=_as_tuple(
            parsed.get("recommended_actions"),
            (
                "Review physics outputs and escalate if needed.",
            ),
        ),
        source="gemini",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_analyst_report(
    *,
    outcome: str,
    surface_type: str,
    impact_energy_J: float,
    impact_energy_mt: float,
    fragmentation_detected: bool,
    terrain_confidence: float,
    has_tsunami: bool,
    tsunami_amplitude_m: float | None = None,
    crater_diameter_m: float | None = None,
    atmospheric_fraction: float | None = None,
) -> AnalystReport:
    """
    Produce an analyst report.

    Prefer Gemini 3.8 Flash when GEMINI_API_KEY is set.

    If Gemini is unavailable, return the transparent deterministic
    rule-based report so the application never hard-fails.
    """

    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if api_key:

        gemini = _gemini_report(
            outcome=outcome,
            surface_type=surface_type,
            impact_energy_J=impact_energy_J,
            impact_energy_mt=impact_energy_mt,
            fragmentation_detected=fragmentation_detected,
            terrain_confidence=terrain_confidence,
            has_tsunami=has_tsunami,
            tsunami_amplitude_m=tsunami_amplitude_m,
            crater_diameter_m=crater_diameter_m,
            atmospheric_fraction=atmospheric_fraction,
            api_key=api_key,
        )

        if gemini is not None:
            return gemini

    return _rule_based_report(
        outcome=outcome,
        surface_type=surface_type,
        impact_energy_J=impact_energy_J,
        impact_energy_mt=impact_energy_mt,
        fragmentation_detected=fragmentation_detected,
        terrain_confidence=terrain_confidence,
        has_tsunami=has_tsunami,
        tsunami_amplitude_m=tsunami_amplitude_m,
        crater_diameter_m=crater_diameter_m,
        atmospheric_fraction=atmospheric_fraction,
    )
