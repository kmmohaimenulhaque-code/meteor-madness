/**
 * Client-side Next Frontier enrichment fallback.
 * Mirrors backend environment schema + impact branch.
 */

function classifyEnvironment(lat, lon) {
  const absLat = Math.abs(lat);

  if (absLat >= 70) {
    return {
      coordinates: { latitude: lat, longitude: lon },
      surface: "ice",
      surface_confidence: 0.65,
      elevation_m: absLat >= 75 ? 100 : 20,
      bathymetry_m: null,
      terrain_source: "polar_heuristic_v1",
      material: { type: "ice", density_kg_m3: 917 },
      data_status: "heuristic",
      surface_type: "ice",
      confidence: 0.65,
      target_density_kg_m3: 917,
      terrain_label: "Likely ice (polar heuristic)",
      material_notes: "Client heuristic. Prefer backend Environment Engine.",
    };
  }

  const likelyOcean =
    (absLat < 60 && (lon < -80 || lon > 120) && absLat < 50) ||
    (absLat < 55 && lon > -60 && lon < -10) ||
    (absLat < 30 && lon > 40 && lon < 110);

  if (likelyOcean) {
    const depth = absLat < 40 ? 3500 : 2500;
    return {
      coordinates: { latitude: lat, longitude: lon },
      surface: "ocean",
      surface_confidence: 0.55,
      elevation_m: -depth,
      bathymetry_m: depth,
      terrain_source: "GEBCO_placeholder_heuristic",
      material: { type: "seawater", density_kg_m3: 1025 },
      data_status: "heuristic",
      surface_type: "ocean",
      confidence: 0.55,
      target_density_kg_m3: 1025,
      terrain_label: "Likely ocean (coarse heuristic)",
      material_notes: "Client heuristic. Prefer backend Environment Engine.",
    };
  }

  return {
    coordinates: { latitude: lat, longitude: lon },
    surface: "land",
    surface_confidence: 0.6,
    elevation_m: 150,
    bathymetry_m: null,
    terrain_source: "land_heuristic_v1",
    material: { type: "crystalline_crust", density_kg_m3: 2700 },
    data_status: "heuristic",
    surface_type: "land",
    confidence: 0.6,
    target_density_kg_m3: 2700,
    terrain_label: "Likely land (default heuristic)",
    material_notes: "Client heuristic. Prefer backend Environment Engine.",
  };
}

function resolveImpactBranch(environment, energyJ, consequences) {
  const mt = energyJ / 4.184e15;
  const surface = environment.surface || environment.surface_type;

  if (surface === "land") {
    const largest =
      (consequences && (consequences.largest_crater || consequences)) || {};
    return {
      branch: "land",
      models_run: ["crater", "blast", "thermal"],
      crater: {
        final_diameter_m:
          largest.final_crater_diameter_m ?? largest.transient_crater_diameter_m ?? null,
        status: "computed",
      },
      blast: {
        radius_m:
          largest.blast_radius_m ?? consequences?.maximum_blast_radius_m ?? null,
        status: "computed",
      },
      thermal: {
        radius_m:
          largest.thermal_radius_m ??
          consequences?.maximum_thermal_radius_m ??
          null,
        status: "computed",
      },
      impact_energy_J: energyJ,
      impact_energy_megatons_tnt: mt,
    };
  }

  if (surface === "ocean") {
    const depth = environment.bathymetry_m || 4000;
    const amp = Math.max(0.1, Math.pow(Math.max(mt, 1e-6), 1 / 3) * 0.8);
    return {
      branch: "ocean",
      models_run: ["water_displacement", "tsunami_screening", "seafloor_effects"],
      water_displacement: {
        estimated_volume_km3: Number((0.02 * Math.pow(Math.max(mt, 1e-9), 0.4)).toFixed(4)),
        status: "screening",
      },
      tsunami: {
        applicable: true,
        impact_energy_J: energyJ,
        impact_energy_megatons_tnt: mt,
        estimated_source_amplitude_m: amp,
        estimated_coastal_runup_indicator_m: amp * 2.5,
        notes: ["Client-side tsunami screening only."],
      },
      seafloor_effects: {
        water_depth_m: depth,
        estimated_crater_on_seafloor_m: Number(
          (80 * Math.pow(Math.max(mt, 1e-9), 0.25)).toFixed(1)
        ),
        status: "screening",
      },
      impact_energy_J: energyJ,
      impact_energy_megatons_tnt: mt,
    };
  }

  if (surface === "ice") {
    return {
      branch: "ice",
      models_run: ["ice_response"],
      ice_response: {
        estimated_excavation_diameter_m: Number(
          (60 * Math.pow(Math.max(mt, 1e-9), 0.28)).toFixed(1)
        ),
        estimated_melt_volume_m3: Number(
          (5e5 * Math.pow(Math.max(mt, 1e-9), 0.5)).toFixed(1)
        ),
        ice_density_kg_m3: environment.material?.density_kg_m3 ?? 917,
        status: "screening",
      },
      impact_energy_J: energyJ,
      impact_energy_megatons_tnt: mt,
    };
  }

  return {
    branch: "refused",
    models_run: [],
    reason: `Unknown surface: ${surface}`,
    impact_energy_J: energyJ,
    impact_energy_megatons_tnt: mt,
  };
}

function ruleAnalyst({
  outcome,
  surface_type,
  energyJ,
  fragmentation,
  terrainConfidence,
  tsunami,
  impactBranch,
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

  let summary = `Surface=${surface_type}, branch=${impactBranch?.branch ?? "n/a"}, energy ~${mt.toExponential(2)} Mt.`;
  if (surface_type === "ocean" && tsunami?.applicable) {
    summary = `Ocean branch: tsunami screening ~${Number(
      tsunami.estimated_source_amplitude_m
    ).toFixed(1)} m source amplitude (uncertain).`;
  } else if (surface_type === "ice") {
    summary = `Ice branch: excavation / melt screening for ~${mt.toExponential(2)} Mt.`;
  } else if (fragmentation) {
    summary = `Land/airburst context with fragmentation. Energy ~${mt.toExponential(2)} Mt.`;
  }

  return {
    confidence: Math.round(confidence * 1000) / 1000,
    confidence_label: label,
    risk_level: risk,
    summary,
    key_findings: [
      `Surface: ${surface_type}`,
      `Impact branch: ${impactBranch?.branch ?? "n/a"}`,
      `Models: ${(impactBranch?.models_run || []).join(", ") || "none"}`,
      `Energy: ${mt.toExponential(3)} Mt TNT`,
    ],
    limitations: [
      "Client-side enrichment fallback when backend patch is missing.",
      "Environment classification is heuristic until GEBCO is wired.",
    ],
    recommended_actions: [
      "python backend/apply_next_frontier_patch.py",
      "Restart uvicorn",
      "Set GEMINI_API_KEY in backend/.env for Gemini reports",
    ],
    source: "rule_based_client",
  };
}

export function ensureEnrichment(data, lat, lon) {
  if (!data || data.status === "error") return data;

  const sim = data.simulation || {};
  const energy =
    Number(sim.impact_energy_J) ||
    Number(sim.parent_final_energy_J) ||
    Number(sim.ground_impact_energy_J) ||
    0;

  const environment =
    data.environment ||
    data.terrain ||
    classifyEnvironment(Number(lat) || 0, Number(lon) || 0);

  const impact_branch =
    data.impact_branch ||
    resolveImpactBranch(environment, energy, sim.consequences || null);

  const tsunami =
    data.tsunami ||
    impact_branch.tsunami || {
      applicable: false,
      impact_energy_J: energy,
      impact_energy_megatons_tnt: energy / 4.184e15,
      estimated_source_amplitude_m: 0,
    };

  const analyst =
    data.analyst ||
    ruleAnalyst({
      outcome: sim.outcome || "completed",
      surface_type: environment.surface || environment.surface_type,
      energyJ: energy,
      fragmentation: Boolean(sim.fragmentation_detected),
      terrainConfidence: environment.surface_confidence ?? environment.confidence ?? 0.5,
      tsunami,
      impactBranch: impact_branch,
    });

  return {
    ...data,
    environment,
    impact_branch,
    terrain: environment,
    tsunami,
    analyst,
  };
}
