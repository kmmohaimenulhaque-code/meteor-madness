/**
 * Client-side Next Frontier enrichment fallback.
 * Used when the API response lacks terrain/tsunami/analyst
 * (i.e. backend main.py not yet patched with enrich_payload).
 */

function classifySurface(lat, lon) {
  // Simple offline heuristic (mirrors backend location_engine)
  const absLat = Math.abs(lat);
  // Crude ocean bands — good enough for demo UI
  const likelyOcean =
    (absLat < 60 && Math.abs(lon) > 20 && Math.abs(lon) < 160 && absLat < 50) ||
    absLat > 70;

  // Prefer land near known continental sample points is hard offline;
  // use a conservative land default with moderate confidence.
  const surface_type = likelyOcean ? "ocean" : "land";
  return {
    surface_type,
    target_density_kg_m3: surface_type === "ocean" ? 1000 : 2500,
    terrain_label: surface_type === "ocean" ? "Ocean (heuristic)" : "Land (heuristic)",
    material_notes:
      surface_type === "ocean"
        ? "Client-side surface guess. Prefer backend Location Engine when available."
        : "Client-side surface guess. Prefer backend Location Engine when available.",
    confidence: 0.45,
  };
}

function estimateTsunami(energyJ, isOcean) {
  const mt = energyJ / 4.184e15;
  if (!isOcean || mt < 1e-6) {
    return {
      applicable: false,
      impact_energy_J: energyJ,
      impact_energy_megatons_tnt: mt,
      estimated_source_amplitude_m: 0,
    };
  }
  // Screening-scale amplitude ~ mt^0.25 (very approximate)
  const amp = Math.max(0.1, Math.pow(Math.max(mt, 1e-6), 0.25) * 2);
  return {
    applicable: true,
    impact_energy_J: energyJ,
    impact_energy_megatons_tnt: mt,
    estimated_source_amplitude_m: amp,
  };
}

function ruleAnalyst({
  outcome,
  surface_type,
  energyJ,
  fragmentation,
  terrainConfidence,
  tsunami,
}) {
  const mt = energyJ / 4.184e15;
  let confidence = 0.75 * (terrainConfidence || 0.5);
  if (mt > 1000) confidence *= 0.7;
  confidence = Math.max(0.15, Math.min(0.95, confidence));

  let risk = "low";
  if (mt >= 100) risk = "extreme";
  else if (mt >= 1) risk = "high";
  else if (mt >= 0.01) risk = "moderate";

  const label =
    confidence >= 0.85
      ? "High"
      : confidence >= 0.65
        ? "Moderate"
        : confidence >= 0.4
          ? "Low"
          : "Very low";

  let summary = `Simulation outcome '${outcome}'. Energy scale ~${mt.toExponential(2)} Mt TNT.`;
  if (surface_type === "ocean" && tsunami?.applicable) {
    summary = `Ocean impact ~${mt.toExponential(2)} Mt. Screening tsunami amplitude ~${Number(
      tsunami.estimated_source_amplitude_m
    ).toFixed(1)} m (uncertain).`;
  } else if (fragmentation) {
    summary = `Atmospheric fragmentation / airburst-like behaviour. Energy ~${mt.toExponential(2)} Mt.`;
  }

  return {
    confidence: Math.round(confidence * 1000) / 1000,
    confidence_label: label,
    risk_level: risk,
    summary,
    key_findings: [
      `Surface: ${surface_type} (client confidence ${terrainConfidence.toFixed(2)})`,
      `Energy: ${mt.toExponential(3)} Mt TNT`,
      `Fragmentation: ${fragmentation ? "yes" : "no"}`,
    ],
    limitations: [
      "Client-side enrichment fallback — run backend patch for full pipeline + Gemini.",
      "Surface classification is heuristic only.",
      "Tsunami amplitude is a screening estimate.",
    ],
    recommended_actions: [
      "Apply backend patch: python backend/apply_next_frontier_patch.py",
      "Restart uvicorn after patching",
      "Set GEMINI_API_KEY in backend/.env for Gemini reports",
    ],
    source: "rule_based_client",
  };
}

/**
 * Ensure simulation payload has terrain, tsunami, analyst.
 * Does not overwrite real backend fields.
 */
export function ensureEnrichment(data, lat, lon) {
  if (!data || data.status === "error") return data;

  const sim = data.simulation || {};
  const energy =
    Number(sim.impact_energy_J) ||
    Number(sim.parent_final_energy_J) ||
    Number(sim.ground_impact_energy_J) ||
    0;

  const terrain =
    data.terrain ||
    classifySurface(Number(lat) || 0, Number(lon) || 0);

  const tsunami =
    data.tsunami ||
    estimateTsunami(energy, terrain.surface_type === "ocean");

  const analyst =
    data.analyst ||
    ruleAnalyst({
      outcome: sim.outcome || "completed",
      surface_type: terrain.surface_type,
      energyJ: energy,
      fragmentation: Boolean(sim.fragmentation_detected),
      terrainConfidence: terrain.confidence,
      tsunami,
    });

  return {
    ...data,
    terrain,
    tsunami,
    analyst,
  };
}
