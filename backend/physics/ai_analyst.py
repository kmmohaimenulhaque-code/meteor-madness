"""
AI Analyst — confidence scoring and plain-language report.

Uses Gemini when GEMINI_API_KEY is set; otherwise falls back to a
transparent rule-based offline report (demo-safe / judge-auditable).

Never hard-code API keys. Set:
  export GEMINI_API_KEY=...
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


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


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.65:
        return "Moderate"
    if score >= 0.40:
        return "Low"
    return "Very low"


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

    if outcome == "ground_impact" and surface_type == "land":
        crater_txt = (
            f" Estimated final crater diameter ~{crater_diameter_m / 1000:.2f} km."
            if crater_diameter_m and crater_diameter_m > 0
            else ""
        )
        summary = (
            f"Ground impact on land releasing approximately "
            f"{impact_energy_mt:.3g} Mt TNT equivalent.{crater_txt}"
        )
    elif surface_type == "ocean" and has_tsunami:
        amp = tsunami_amplitude_m or 0.0
        summary = (
            f"Ocean impact releasing ~{impact_energy_mt:.3g} Mt. "
            f"Screening tsunami source amplitude on the order of {amp:.1f} m "
            f"(highly uncertain; bathymetry required for real assessment)."
        )
    elif fragmentation_detected:
        summary = (
            f"Atmospheric fragmentation / airburst-like behaviour. "
            f"Total energy ~{impact_energy_mt:.3g} Mt with significant "
            f"deposition at altitude."
        )
    else:
        summary = (
            f"Simulation completed with outcome '{outcome}'. "
            f"Energy scale ~{impact_energy_mt:.3g} Mt TNT equivalent."
        )

    findings = [
        f"Surface classification: {surface_type} "
        f"(terrain confidence {terrain_confidence:.2f}).",
        f"Impact / event energy: {impact_energy_mt:.4g} Mt TNT.",
        f"Fragmentation detected: {'yes' if fragmentation_detected else 'no'}.",
    ]

    if atmospheric_fraction is not None:
        findings.append(
            f"Approximate atmospheric energy fraction: "
            f"{atmospheric_fraction * 100:.1f} %."
        )

    if has_tsunami and tsunami_amplitude_m is not None:
        findings.append(
            f"Tsunami screening source amplitude: ~{tsunami_amplitude_m:.1f} m."
        )

    if crater_diameter_m and crater_diameter_m > 0:
        findings.append(
            f"Final crater diameter (land scaling): "
            f"~{crater_diameter_m / 1000:.3f} km."
        )

    limitations = (
        "Atmospheric entry model is an engineering approximation (not full hydrocode).",
        "Material strength, density and ablation parameters carry large uncertainty.",
        "Terrain classification is currently heuristic or user-provided.",
        "Tsunami and blast radii are screening estimates only.",
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


def _parse_gemini_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from Gemini text (handles optional markdown fences)."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return None
    return None


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
    """Call Gemini generateContent; return None on any failure."""

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

    prompt = f"""You are a planetary-defense screening analyst for a NASA Space Apps demo.
Given this asteroid atmospheric-entry simulation result, respond with ONLY valid JSON
(no markdown) matching this schema:
{{
  "confidence": <float 0-1>,
  "risk_level": "<low|moderate|high|extreme>",
  "summary": "<one or two plain-English sentences>",
  "key_findings": ["<short bullet>", "..."],
  "limitations": ["<short bullet>", "..."],
  "recommended_actions": ["<short bullet>", "..."]
}}

Be scientifically cautious. Emphasize screening-level uncertainty.
Do not invent precise casualty numbers.

Simulation data:
{json.dumps(payload_context, indent=2)}
"""

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
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
        parts = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        raw_text = "".join(
            str(part.get("text", "")) for part in parts
        )
    except (IndexError, AttributeError, TypeError):
        return None

    parsed = _parse_gemini_json(raw_text)
    if not parsed:
        return None

    confidence = float(parsed.get("confidence", 0.6))
    confidence = max(0.0, min(1.0, confidence))
    risk = str(parsed.get("risk_level", "moderate")).lower()
    if risk not in ("low", "moderate", "high", "extreme"):
        risk = "moderate"

    def _as_tuple(value: Any, fallback: tuple[str, ...]) -> tuple[str, ...]:
        if isinstance(value, list) and value:
            return tuple(str(item) for item in value)
        return fallback

    return AnalystReport(
        confidence=round(confidence, 3),
        confidence_label=_confidence_label(confidence),
        risk_level=risk,
        summary=str(parsed.get("summary") or "Gemini analysis completed."),
        key_findings=_as_tuple(parsed.get("key_findings"), ("No findings returned.",)),
        limitations=_as_tuple(
            parsed.get("limitations"),
            ("Gemini response did not list limitations.",),
        ),
        recommended_actions=_as_tuple(
            parsed.get("recommended_actions"),
            ("Review physics outputs and escalate if needed.",),
        ),
        source="gemini",
    )


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

    Prefer Gemini when GEMINI_API_KEY is set; otherwise use the
    transparent rule-based fallback so demos never hard-fail.
    """

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
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
