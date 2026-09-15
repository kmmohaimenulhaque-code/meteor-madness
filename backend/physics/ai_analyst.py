"""
AI Analyst — confidence scoring and plain-language report.

Rule-based, fully transparent, offline.
No external LLM required for the baseline.
This keeps the 48-hour demo reproducible and judge-auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": self.confidence,
            "confidence_label": self.confidence_label,
            "risk_level": self.risk_level,
            "summary": self.summary,
            "key_findings": list(self.key_findings),
            "limitations": list(self.limitations),
            "recommended_actions": list(self.recommended_actions),
        }


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "High"
    if score >= 0.65:
        return "Moderate"
    if score >= 0.40:
        return "Low"
    return "Very low"


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
    Produce a transparent, rule-based analysis report.

    Confidence is reduced by:
    - low terrain classification confidence
    - extreme energy regimes outside the screening model validity
    - missing or highly uncertain secondary effects
    """

    # Base confidence from terrain classification and model regime
    confidence = 0.75 * terrain_confidence

    if impact_energy_mt > 1000:
        # Model is outside comfortable screening range
        confidence *= 0.7
    elif impact_energy_mt < 1e-4:
        confidence *= 0.85

    if surface_type == "ocean" and has_tsunami:
        confidence *= 0.9  # extra uncertainty from tsunami scaling

    confidence = max(0.15, min(0.95, confidence))

    # Risk level
    if impact_energy_mt >= 100:
        risk = "extreme"
    elif impact_energy_mt >= 1:
        risk = "high"
    elif impact_energy_mt >= 0.01:
        risk = "moderate"
    else:
        risk = "low"

    # Summary sentence
    if outcome == "ground_impact" and surface_type == "land":
        crater_txt = (
            f" Estimated final crater diameter ~{crater_diameter_m/1000:.2f} km."
            if crater_diameter_m and crater_diameter_m > 0
            else ""
        )
        summary = (
            f"Ground impact on land releasing approximately {impact_energy_mt:.3g} Mt TNT equivalent."
            f"{crater_txt}"
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
            f"Total energy ~{impact_energy_mt:.3g} Mt with significant deposition at altitude."
        )
    else:
        summary = (
            f"Simulation completed with outcome '{outcome}'. "
            f"Energy scale ~{impact_energy_mt:.3g} Mt TNT equivalent."
        )

    findings = [
        f"Surface classification: {surface_type} (terrain confidence {terrain_confidence:.2f}).",
        f"Impact / event energy: {impact_energy_mt:.4g} Mt TNT.",
        f"Fragmentation detected: {'yes' if fragmentation_detected else 'no'}.",
    ]

    if atmospheric_fraction is not None:
        findings.append(
            f"Approximate atmospheric energy fraction: {atmospheric_fraction*100:.1f} %."
        )

    if has_tsunami and tsunami_amplitude_m is not None:
        findings.append(
            f"Tsunami screening source amplitude: ~{tsunami_amplitude_m:.1f} m."
        )

    if crater_diameter_m and crater_diameter_m > 0:
        findings.append(
            f"Final crater diameter (land scaling): ~{crater_diameter_m/1000:.3f} km."
        )

    limitations = [
        "Atmospheric entry model is an engineering approximation (not full hydrocode).",
        "Material strength, density and ablation parameters carry large uncertainty.",
        "Terrain classification is currently heuristic or user-provided.",
        "Tsunami and blast radii are screening estimates only.",
        "Results are for educational and relative-risk illustration.",
    ]

    actions = [
        "Treat numbers as order-of-magnitude guidance, not precise forecasts.",
        "For any real threat assessment, escalate to specialised planetary-defence models and agencies.",
        "Improve surface classification with GEBCO / land-cover data for higher confidence.",
        "Run sensitivity sweeps on density, strength and entry angle.",
    ]

    return AnalystReport(
        confidence=round(confidence, 3),
        confidence_label=_confidence_label(confidence),
        risk_level=risk,
        summary=summary,
        key_findings=tuple(findings),
        limitations=tuple(limitations),
        recommended_actions=tuple(actions),
    )
