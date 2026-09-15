/**
 * Client-side enrichment fallback.
 * CRITICAL: No data = NO GUESS.
 * Without a backend environment payload we mark surface unknown
 * and refuse crater/tsunami manufacture.
 */

function unavailableEnvironment(lat, lon) {
  return {
    coordinates: { latitude: lat, longitude: lon },
    surface: "unknown",
    surface_confidence: 0.0,
    confidence: 0.0,
    elevation_m: null,
    bathymetry_m: null,
    terrain_source: "unavailable",
    source: "unavailable",
    material: null,
    data_status: "unavailable",
    physics_branch: "undetermined",
    surface_type: "unknown",
    target_density_kg_m3: null,
    terrain_label: "Environment data unavailable (client has no DEM access)",
    material_notes:
      "Frontend cannot invent land/ocean. Use backend GEBCO lookup or surface_hint.",
  };
}

function refusedBranch(energyJ) {
  return {
    branch: "undetermined",
    physics_branch: "undetermined",
    models_run: [],
    refused: true,
    reason:
      "No observed environment data. Crater and tsunami calculations are refused.",
    impact_energy_J: energyJ,
    impact_energy_megatons_tnt: energyJ / 4.184e15,
    crater: null,
    tsunami: null,
  };
}

function resolveImpactBranch(environment, energyJ, consequences) {
  const surface = environment.surface || environment.surface_type;
  const mt = energyJ / 4.184e15;

  if (surface === "unknown" || environment.physics_branch === "undetermined") {
    return refusedBranch(energyJ);
  }

  if (surface === "land") {
    const largest =
      (consequences && (consequences.largest_crater || consequences)) || {};
    return {
      branch: "land",
      models_run: ["crater", "blast", "thermal"],
      crater: {
        final_diameter_m:
          largest.final_crater_diameter_m ??
          largest.transient_crater_diameter_m ??
          null,
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
    const depth = environment.bathymetry_m;
    if (depth == null) {
      return refusedBranch(energyJ);
    }
    const amp = Math.max(0.1, Math.pow(Math.max(mt, 1e-6), 1 / 3) * 0.8);
    return {
      branch: "ocean",
      models_run: ["water_displacement", "tsunami_screening", "seafloor_effects"],
      water_displacement: {
        estimated_volume_km3: Number(
          (0.02 * Math.pow(Math.max(mt, 1e-9), 0.4)).toFixed(4)
        ),
        status: "screening",
      },
      tsunami: {
        applicable: true,
        impact_energy_J: energyJ,
        impact_energy_megatons_tnt: mt,
        estimated_source_amplitude_m: amp,
        estimated_coastal_runup_indicator_m: amp * 2.5,
        notes: ["Screening only; requires observed bathymetry."],
      },
      seafloor_effects: {
        water_depth_m: depth,
        depth_status: "observed",
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

  return refusedBranch(energyJ);
}

function ruleAnalyst({ surface_type, energyJ, impactBranch }) {
  const mt = energyJ / 4.184e15;
  const refused = impactBranch?.branch === "undetermined";

  return {
    confidence: refused ? 0.0 : 0.7,
    confidence_label: refused ? "Very low" : "Moderate",
    risk_level: refused ? "unknown" : mt >= 1 ? "high" : "moderate",
    summary: refused
      ? "Environment data unavailable. Impact-specific crater/tsunami physics was refused."
      : `Surface=${surface_type}, branch=${impactBranch?.branch}, energy ~${mt.toExponential(2)} Mt.`,
    key_findings: [
      `Surface: ${surface_type}`,
      `Physics branch: ${impactBranch?.branch ?? "undetermined"}`,
      refused
        ? "No crater/tsunami manufactured without Earth data"
        : `Models: ${(impactBranch?.models_run || []).join(", ")}`,
    ],
    limitations: [
      "Environment must come from observed DEM/bathymetry (GEBCO).",
      "Without data the simulator refuses environment-specific effects.",
    ],
    recommended_actions: [
      "Ensure backend can reach api.opentopodata.org (GEBCO 2020)",
      "Or pass surface_hint=land|ocean|ice as an explicit user override",
      "python backend/apply_next_frontier_patch.py && restart uvicorn",
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

  // Prefer backend environment. NEVER invent land/ocean on the client.
  const environment =
    data.environment ||
    data.terrain ||
    unavailableEnvironment(Number(lat) || 0, Number(lon) || 0);

  const impact_branch =
    data.impact_branch ||
    resolveImpactBranch(
      environment,
      energy,
      environment.surface === "land" ? sim.consequences || null : null
    );

  const tsunami =
    data.tsunami ||
    impact_branch.tsunami || {
      applicable: false,
      refused: impact_branch.branch === "undetermined",
      impact_energy_J: energy,
      impact_energy_megatons_tnt: energy / 4.184e15,
      estimated_source_amplitude_m: 0,
      notes: ["Tsunami not computed without observed ocean environment."],
    };

  const analyst =
    data.analyst ||
    ruleAnalyst({
      surface_type: environment.surface || environment.surface_type,
      energyJ: energy,
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
