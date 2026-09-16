import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { Canvas, useFrame } from "@react-three/fiber";

import {
  Html,
  OrbitControls,
  Stars,
} from "@react-three/drei";

import * as THREE from "three";

import "./MeteorMadness3D.css";

/* =========================================================
   CONSTANTS
========================================================= */

const EARTH_RADIUS = 3;

const DEG = Math.PI / 180;

/* =========================================================
   NUMBER HELPERS
========================================================= */

function finiteNumber(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number) ? number : fallback;
}

function firstFinite(...values) {
  for (const value of values) {
    const number = Number(value);

    if (Number.isFinite(number)) {
      return number;
    }
  }

  return null;
}

function formatNumber(value, digits = 2) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toLocaleString("en-GB", {
    maximumFractionDigits: digits,
  });
}

/* =========================================================
   COORDINATE EXTRACTION

   SAME priority as EarthImpactMap / GibsImpactView.
========================================================= */

function getImpactCoordinates(trajectory, latitude, longitude) {
  const impactLatitude = firstFinite(
    trajectory?.final_latitude_deg,
    trajectory?.impact_latitude_deg,
    trajectory?.latitude_deg,
    trajectory?.entry_latitude_deg,
    latitude
  );

  const impactLongitude = firstFinite(
    trajectory?.final_longitude_deg,
    trajectory?.impact_longitude_deg,
    trajectory?.longitude_deg,
    trajectory?.entry_longitude_deg,
    longitude
  );

  return {
    latitude: THREE.MathUtils.clamp(
      impactLatitude ?? 0,
      -89.5,
      89.5
    ),

    longitude: THREE.MathUtils.euclideanModulo(
      (impactLongitude ?? 0) + 180,
      360
    ) - 180,
  };
}

/* =========================================================
   ENTRY COORDINATES
========================================================= */

function getEntryCoordinates(trajectory, impact) {
  const latitude = firstFinite(
    trajectory?.entry_latitude_deg,
    trajectory?.initial_latitude_deg,
    impact.latitude
  );

  const longitude = firstFinite(
    trajectory?.entry_longitude_deg,
    trajectory?.initial_longitude_deg,
    impact.longitude
  );

  return {
    latitude,
    longitude,
  };
}

/* =========================================================
   LAT/LON → EARTH XYZ

   Coordinate convention:

   X = longitude
   Y = latitude
   Z = depth / facing direction
========================================================= */

function latLonToVector3(
  latitude,
  longitude,
  radius = EARTH_RADIUS
) {
  const lat = latitude * DEG;
  const lon = longitude * DEG;

  const cosLat = Math.cos(lat);

  return new THREE.Vector3(
    radius * cosLat * Math.sin(lon),
    radius * Math.sin(lat),
    radius * cosLat * Math.cos(lon)
  );
}

/* =========================================================
   EARTH GRID
========================================================= */

function EarthGrid() {
  const lines = useMemo(() => {
    const result = [];

    /* Latitude lines */
    for (let latitude = -75; latitude <= 75; latitude += 15) {
      const points = [];

      const radius =
        EARTH_RADIUS *
        Math.cos(latitude * DEG);

      const y =
        EARTH_RADIUS *
        Math.sin(latitude * DEG);

      for (let longitude = 0; longitude <= 360; longitude += 4) {
        const lon = longitude * DEG;

        points.push(
          new THREE.Vector3(
            radius * Math.sin(lon),
            y,
            radius * Math.cos(lon)
          )
        );
      }

      result.push(points);
    }

    /* Longitude lines */
    for (let longitude = 0; longitude < 180; longitude += 15) {
      const points = [];

      for (
        let latitude = -90;
        latitude <= 90;
        latitude += 4
      ) {
        points.push(
          latLonToVector3(
            latitude,
            longitude,
            EARTH_RADIUS * 1.002
          )
        );
      }

      result.push(points);

      result.push(
        points.map(
          (point) =>
            new THREE.Vector3(
              -point.x,
              point.y,
              -point.z
            )
        )
      );
    }

    return result;
  }, []);

  return (
    <group>
      {lines.map((points, index) => (
        <line key={index}>
          <bufferGeometry>
            <float32BufferAttribute
              attach="attributes-position"
              args={[
                new Float32Array(
                  points.flatMap((point) => [
                    point.x,
                    point.y,
                    point.z,
                  ])
                ),
                3,
              ]}
            />
          </bufferGeometry>

          <lineBasicMaterial
            color="#3978a9"
            transparent
            opacity={0.13}
          />
        </line>
      ))}
    </group>
  );
}

/* =========================================================
   EARTH
========================================================= */

function Earth() {
  return (
    <group>
      {/* Main Earth */}
      <mesh>
        <sphereGeometry
          args={[EARTH_RADIUS, 64, 64]}
        />

        <meshStandardMaterial
          color="#075985"
          roughness={0.72}
          metalness={0.05}
        />
      </mesh>

      {/* Atmospheric shell */}
      <mesh>
        <sphereGeometry
          args={[
            EARTH_RADIUS * 1.035,
            48,
            48,
          ]}
        />

        <meshBasicMaterial
          color="#38bdf8"
          transparent
          opacity={0.075}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Geographic grid */}
      <EarthGrid />

      {/* subtle polar glow */}
      <mesh>
        <sphereGeometry
          args={[
            EARTH_RADIUS * 1.012,
            48,
            48,
          ]}
        />

        <meshBasicMaterial
          color="#bae6fd"
          transparent
          opacity={0.035}
          wireframe
        />
      </mesh>
    </group>
  );
}

/* =========================================================
   IMPACT MARKER
========================================================= */

function ImpactMarker({
  position,
  craterDiameter,
  impactEnergy,
}) {
  const ringRef = useRef(null);
  const glowRef = useRef(null);

  const intensity = THREE.MathUtils.clamp(
    Math.log10(
      Math.max(
        finiteNumber(impactEnergy, 1),
        1
      )
    ) / 20,
    0.5,
    2
  );

  const craterScale = THREE.MathUtils.clamp(
    finiteNumber(craterDiameter, 100) /
      1000,
    0.6,
    2.4
  );

  useFrame((state) => {
    const time = state.clock.elapsedTime;

    const pulse =
      1 +
      Math.sin(time * 4) *
        0.08 *
        intensity;

    if (ringRef.current) {
      ringRef.current.scale.set(
        pulse * craterScale,
        pulse * craterScale,
        pulse * craterScale
      );

      ringRef.current.rotation.z =
        time * 0.25;
    }

    if (glowRef.current) {
      glowRef.current.scale.setScalar(
        1 +
          Math.sin(time * 5) *
            0.12 *
            intensity
      );
    }
  });

  return (
    <group position={position}>
      {/* crater ring */}
      <mesh
        ref={ringRef}
        rotation-x={Math.PI / 2}
      >
        <torusGeometry
          args={[
            0.16,
            0.025,
            16,
            64,
          ]}
        />

        <meshBasicMaterial
          color="#fb923c"
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* impact glow */}
      <mesh ref={glowRef}>
        <sphereGeometry
          args={[0.10, 20, 20]}
        />

        <meshBasicMaterial
          color="#f97316"
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* vertical locator */}
      <mesh
        position={[0, 0.18, 0]}
      >
        <cylinderGeometry
          args={[
            0.008,
            0.008,
            0.35,
            12,
          ]}
        />

        <meshBasicMaterial
          color="#fb923c"
        />
      </mesh>
    </group>
  );
}

/* =========================================================
   TRAJECTORY LINE
========================================================= */

function TrajectoryLine({
  entryPosition,
  impactPosition,
}) {
  const points = useMemo(() => {
    const start =
      entryPosition
        .clone()
        .normalize()
        .multiplyScalar(
          EARTH_RADIUS * 1.9
        );

    const end =
      impactPosition
        .clone()
        .normalize()
        .multiplyScalar(
          EARTH_RADIUS * 1.08
        );

    const midpoint = start
      .clone()
      .lerp(end, 0.45);

    midpoint.y += 2.3;

    const curve =
      new THREE.CatmullRomCurve3([
        start,
        midpoint,
        end,
      ]);

    return curve.getPoints(80);
  }, [
    entryPosition,
    impactPosition,
  ]);

  const positions = useMemo(
    () =>
      new Float32Array(
        points.flatMap((point) => [
          point.x,
          point.y,
          point.z,
        ])
      ),
    [points]
  );

  return (
    <line>
      <bufferGeometry>
        <float32BufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>

      <lineBasicMaterial
        color="#fbbf24"
        transparent
        opacity={0.72}
      />
    </line>
  );
}

/* =========================================================
   METEOR
========================================================= */

function Meteor({
  entryPosition,
  impactPosition,
  playing,
  onImpact,
}) {
  const meteorRef = useRef(null);

  const [progress, setProgress] =
    useState(0);

  const curve = useMemo(() => {
    const start =
      entryPosition
        .clone()
        .normalize()
        .multiplyScalar(
          EARTH_RADIUS * 1.9
        );

    const end =
      impactPosition
        .clone()
        .normalize()
        .multiplyScalar(
          EARTH_RADIUS * 1.06
        );

    const midpoint = start
      .clone()
      .lerp(end, 0.5);

    midpoint.y += 2.4;

    return new THREE.CatmullRomCurve3([
      start,
      midpoint,
      end,
    ]);
  }, [
    entryPosition,
    impactPosition,
  ]);

  useEffect(() => {
    if (!playing) {
      setProgress(0);
    }
  }, [playing]);

  useFrame((_, delta) => {
    if (!playing) {
      return;
    }

    setProgress((previous) => {
      const next = Math.min(
        previous + delta * 0.24,
        1
      );

      if (
        next >= 1 &&
        previous < 1
      ) {
        onImpact?.();
      }

      return next;
    });
  });

  const position = curve.getPointAt(
    THREE.MathUtils.clamp(
      progress,
      0,
      1
    )
  );

  const direction = curve
    .getTangentAt(
      THREE.MathUtils.clamp(
        progress,
        0,
        0.999
      )
    )
    .normalize();

  const meteorScale =
    THREE.MathUtils.lerp(
      0.11,
      0.22,
      progress
    );

  return (
    <group
      ref={meteorRef}
      position={position}
    >
      {/* meteor body */}
      <mesh scale={meteorScale}>
        <icosahedronGeometry
          args={[1, 2]}
        />

        <meshStandardMaterial
          color="#9a3412"
          roughness={0.9}
          metalness={0.05}
        />
      </mesh>

      {/* hot core */}
      <mesh scale={meteorScale * 0.58}>
        <icosahedronGeometry
          args={[1, 1]}
        />

        <meshBasicMaterial
          color="#fed7aa"
        />
      </mesh>

      {/* trail */}
      <Trail
        position={position}
        direction={direction}
        length={0.8 + progress * 1.4}
      />
    </group>
  );
}

/* =========================================================
   METEOR TRAIL
========================================================= */

function Trail({
  position,
  direction,
  length,
}) {
  const points = [
    position
      .clone()
      .add(
        direction
          .clone()
          .multiplyScalar(-length)
      ),

    position
      .clone()
      .add(
        direction
          .clone()
          .multiplyScalar(-length * 0.55)
      ),

    position.clone(),
  ];

  const positions = new Float32Array(
    points.flatMap((point) => [
      point.x,
      point.y,
      point.z,
    ])
  );

  return (
    <line>
      <bufferGeometry>
        <float32BufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>

      <lineBasicMaterial
        color="#fb923c"
        transparent
        opacity={0.8}
      />
    </line>
  );
}

/* =========================================================
   IMPACT EFFECT
========================================================= */

function ImpactExplosion({
  position,
  active,
  impactEnergy,
}) {
  const groupRef = useRef(null);

  const [life, setLife] =
    useState(0);

  useEffect(() => {
    if (!active) {
      setLife(0);
      return;
    }

    setLife(0);

    let animationFrame;

    const start = performance.now();

    const animate = (now) => {
      const elapsed =
        (now - start) / 1000;

      setLife(elapsed);

      if (elapsed < 3.2) {
        animationFrame =
          requestAnimationFrame(
            animate
          );
      }
    };

    animationFrame =
      requestAnimationFrame(
        animate
      );

    return () => {
      cancelAnimationFrame(
        animationFrame
      );
    };
  }, [active]);

  const energyScale =
    THREE.MathUtils.clamp(
      Math.log10(
        Math.max(
          finiteNumber(
            impactEnergy,
            1
          ),
          1
        )
      ) / 10,
      0.8,
      2.8
    );

  if (!active) {
    return null;
  }

  const expansion =
    Math.min(
      life * 2.5 * energyScale,
      3.5
    );

  const opacity =
    Math.max(
      0,
      1 - life / 3.2
    );

  return (
    <group
      ref={groupRef}
      position={position}
    >
      {/* fireball */}
      <mesh scale={0.18 + expansion * 0.22}>
        <sphereGeometry
          args={[1, 32, 32]}
        />

        <meshBasicMaterial
          color="#fb923c"
          transparent
          opacity={opacity * 0.75}
        />
      </mesh>

      {/* shockwave */}
      <mesh rotation-x={Math.PI / 2}>
        <torusGeometry
          args={[
            0.3 + expansion * 0.55,
            0.025,
            16,
            96,
          ]}
        />

        <meshBasicMaterial
          color="#fde68a"
          transparent
          opacity={opacity}
        />
      </mesh>

      {/* secondary shockwave */}
      <mesh rotation-x={Math.PI / 2}>
        <torusGeometry
          args={[
            0.55 + expansion * 0.9,
            0.012,
            12,
            96,
          ]}
        />

        <meshBasicMaterial
          color="#fb923c"
          transparent
          opacity={opacity * 0.6}
        />
      </mesh>
    </group>
  );
}

/* =========================================================
   CAMERA TARGET LABEL
========================================================= */

function ImpactLabel({
  position,
  latitude,
  longitude,
  surface,
}) {
  return (
    <group position={position}>
      <Html
        center
        distanceFactor={8}
        position={[0, 0.42, 0]}
      >
        <div className="meteor-3d-label">
          <strong>MODELLED IMPACT</strong>

          <span>
            {formatNumber(latitude, 4)}°
            {" "}
            {formatNumber(longitude, 4)}°
          </span>

          <small>
            {String(
              surface || "UNKNOWN"
            ).toUpperCase()}
          </small>
        </div>
      </Html>
    </group>
  );
}

/* =========================================================
   SCENE
========================================================= */

function Scene({
  trajectory,
  latitude,
  longitude,
  surface,
  craterDiameter,
  impactEnergy,
  impactVelocity,
  playing,
  setPlaying,
}) {
  const impact = useMemo(
    () =>
      getImpactCoordinates(
        trajectory,
        latitude,
        longitude
      ),
    [
      trajectory,
      latitude,
      longitude,
    ]
  );

  const entry = useMemo(
    () =>
      getEntryCoordinates(
        trajectory,
        impact
      ),
    [trajectory, impact]
  );

  const impactPosition = useMemo(
    () =>
      latLonToVector3(
        impact.latitude,
        impact.longitude,
        EARTH_RADIUS * 1.015
      ),
    [impact]
  );

  const entryPosition = useMemo(
    () =>
      latLonToVector3(
        entry.latitude,
        entry.longitude,
        EARTH_RADIUS
      ),
    [entry]
  );

  const [exploded, setExploded] =
    useState(false);

  useEffect(() => {
    setExploded(false);
    setPlaying(false);
  }, [
    impact.latitude,
    impact.longitude,
    setPlaying,
  ]);

  function handleImpact() {
    setExploded(true);
  }

  return (
    <>
      <color
        attach="background"
        args={["#020617"]}
      />

      <ambientLight intensity={0.45} />

      <directionalLight
        position={[5, 5, 5]}
        intensity={2}
      />

      <pointLight
        position={[-5, 2, -5]}
        intensity={1.1}
        color="#60a5fa"
      />

      <Stars
        radius={80}
        depth={50}
        count={1800}
        factor={2}
        saturation={0}
        fade
        speed={0.4}
      />

      <Earth />

      <TrajectoryLine
        entryPosition={entryPosition}
        impactPosition={impactPosition}
      />

      <ImpactMarker
        position={impactPosition}
        craterDiameter={craterDiameter}
        impactEnergy={impactEnergy}
      />

      <ImpactLabel
        position={impactPosition}
        latitude={impact.latitude}
        longitude={impact.longitude}
        surface={surface}
      />

      <Meteor
        entryPosition={entryPosition}
        impactPosition={impactPosition}
        playing={playing}
        onImpact={handleImpact}
      />

      <ImpactExplosion
        position={impactPosition}
        active={exploded}
        impactEnergy={impactEnergy}
      />

      <OrbitControls
        enablePan
        enableZoom
        minDistance={4.5}
        maxDistance={16}
        enableDamping
        dampingFactor={0.06}
      />

      <Html
        position={[
          0,
          -4.1,
          0,
        ]}
        center
      >
        <div className="meteor-3d-controls">
          <button
            type="button"
            onClick={() => {
              setExploded(false);
              setPlaying(true);
            }}
          >
            {playing
              ? "IMPACT SEQUENCE…"
              : "▶ RUN IMPACT"}
          </button>

          {exploded && (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setExploded(false);
                setPlaying(false);
              }}
            >
              RESET
            </button>
          )}
        </div>
      </Html>

      <Html
        position={[
          4.6,
          2.9,
          0,
        ]}
      >
        <div className="meteor-3d-data">
          <div>
            <span>LAT</span>
            <strong>
              {formatNumber(
                impact.latitude,
                4
              )}°
            </strong>
          </div>

          <div>
            <span>LON</span>
            <strong>
              {formatNumber(
                impact.longitude,
                4
              )}°
            </strong>
          </div>

          <div>
            <span>SURFACE</span>
            <strong>
              {String(
                surface || "UNKNOWN"
              ).toUpperCase()}
            </strong>
          </div>

          <div>
            <span>CRATER</span>
            <strong>
              {craterDiameter != null
                ? `${formatNumber(
                    craterDiameter / 1000,
                    2
                  )} km`
                : "—"}
            </strong>
          </div>

          <div>
            <span>VELOCITY</span>
            <strong>
              {impactVelocity != null
                ? `${formatNumber(
                    impactVelocity,
                    1
                  )}`
                : "—"}
            </strong>
          </div>
        </div>
      </Html>
    </>
  );
}

/* =========================================================
   PUBLIC COMPONENT
========================================================= */

export default function MeteorMadness3D({
  simulation,
  simulationData,
  environment,
  impactBranch,
  selectedAsteroid,
  latitude,
  longitude,
}) {
  const [playing, setPlaying] =
    useState(false);

  const trajectory =
    simulation?.trajectory ??
    simulationData?.trajectory ??
    simulation?.impact_trajectory ??
    simulationData?.impact_trajectory ??
    simulation?.modelled_trajectory ??
    simulationData?.modelled_trajectory ??
    simulationData ??
    {};

  const surface =
    environment?.surface ??
    environment?.surface_type ??
    impactBranch?.branch ??
    "UNKNOWN";

  const consequences =
    impactBranch?.consequences ??
    simulationData?.consequences ??
    simulation?.consequences ??
    null;

  const craterDiameter = firstFinite(
    impactBranch?.crater
      ?.final_diameter_m,

    impactBranch?.crater
      ?.diameter_m,

    consequences?.final_crater_diameter_m,

    consequences?.crater_diameter_m
  );

  const impactEnergy = firstFinite(
    simulationData?.impact_energy_J,

    simulationData?.impact_energy,

    consequences?.impact_energy_J,

    consequences?.impact_energy
  );

  const impactVelocity = firstFinite(
    simulationData?.impact_velocity_mps,

    simulationData?.velocity_mps,

    simulationData?.final_velocity_mps,

    selectedAsteroid?.velocity_kph != null
      ? Number(
          selectedAsteroid.velocity_kph
        ) / 3.6
      : null
  );

  return (
    <section className="meteor-3d-panel">
      <div className="meteor-3d-header">
        <div>
          <p className="meteor-3d-kicker">
            THREE-DIMENSIONAL IMPACT LAB
          </p>

          <h2>
            Interactive Earth Impact
          </h2>

          <p>
            Same modelled coordinates.
            Same simulation outputs.
            New spatial view.
          </p>
        </div>

        <div className="meteor-3d-status">
          <span className="meteor-3d-status-dot" />
          LIVE MODEL
        </div>
      </div>

      <div className="meteor-3d-stage">
        <Canvas
          camera={{
            position: [
              7,
              4.8,
              8,
            ],
            fov: 42,
          }}
          dpr={[1, 1.5]}
          gl={{
            antialias: true,
            powerPreference:
              "high-performance",
          }}
        >
          <Suspense fallback={null}>
            <Scene
              trajectory={trajectory}
              latitude={latitude}
              longitude={longitude}
              surface={surface}
              craterDiameter={
                craterDiameter
              }
              impactEnergy={
                impactEnergy
              }
              impactVelocity={
                impactVelocity
              }
              playing={playing}
              setPlaying={setPlaying}
            />
          </Suspense>
        </Canvas>

        <div className="meteor-3d-help">
          <span>🖱️ Drag</span>
          <span>🔍 Scroll</span>
          <span>☄️ Run impact</span>
        </div>
      </div>
    </section>
  );
}
