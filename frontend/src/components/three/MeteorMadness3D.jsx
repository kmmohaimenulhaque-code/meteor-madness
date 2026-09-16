import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, OrbitControls, Stars, Line } from "@react-three/drei";
import * as THREE from "three";
import "./MeteorMadness3D.css";

const EARTH_RADIUS = 3;
const DEG = Math.PI / 180;

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function firstFinite(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) return number;
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

function formatEnergy(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  if (Math.abs(number) >= 1e15) {
    return `${(number / 1e15).toFixed(2)} PJ`;
  }

  if (Math.abs(number) >= 1e12) {
    return `${(number / 1e12).toFixed(2)} TJ`;
  }

  if (Math.abs(number) >= 1e9) {
    return `${(number / 1e9).toFixed(2)} GJ`;
  }

  if (Math.abs(number) >= 1e6) {
    return `${(number / 1e6).toFixed(2)} MJ`;
  }

  return `${number.toExponential(2)} J`;
}

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

function getImpactCoordinates(
  trajectory,
  latitude,
  longitude
) {
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

    longitude:
      THREE.MathUtils.euclideanModulo(
        (impactLongitude ?? 0) + 180,
        360
      ) - 180,
  };
}

function getEntryCoordinates(trajectory, impact) {
  return {
    latitude: firstFinite(
      trajectory?.entry_latitude_deg,
      trajectory?.initial_latitude_deg,
      impact.latitude
    ),

    longitude: firstFinite(
      trajectory?.entry_longitude_deg,
      trajectory?.initial_longitude_deg,
      impact.longitude
    ),
  };
}

function makeTrajectoryCurve(entryPosition, impactPosition) {
  const start = entryPosition
    .clone()
    .normalize()
    .multiplyScalar(EARTH_RADIUS * 2.15);

  const end = impactPosition
    .clone()
    .normalize()
    .multiplyScalar(EARTH_RADIUS * 1.035);

  const midpoint = start.clone().lerp(end, 0.48);

  midpoint.y += 2.35;

  return new THREE.CatmullRomCurve3([
    start,
    midpoint,
    end,
  ]);
}

/* -------------------------------------------------------------------------- */
/* EARTH GRID                                                                  */
/* -------------------------------------------------------------------------- */

function EarthGrid() {
  const lines = useMemo(() => {
    const result = [];

    // Latitude lines
    for (let latitude = -75; latitude <= 75; latitude += 15) {
      const points = [];

      const lat = latitude * DEG;
      const radius = EARTH_RADIUS * Math.cos(lat);
      const y = EARTH_RADIUS * Math.sin(lat);

      for (let longitude = 0; longitude <= 360; longitude += 3) {
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

    // Longitude lines
    for (let longitude = 0; longitude < 180; longitude += 15) {
      const points = [];

      for (let latitude = -90; latitude <= 90; latitude += 3) {
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
        <Line
          key={index}
          points={points}
          color="#67b7e8"
          transparent
          opacity={0.11}
          lineWidth={0.5}
        />
      ))}
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* ATMOSPHERE                                                                  */
/* -------------------------------------------------------------------------- */

function Atmosphere() {
  const atmosphereRef = useRef(null);

  useFrame((state) => {
    if (!atmosphereRef.current) {
      return;
    }

    const pulse =
      1 +
      Math.sin(state.clock.elapsedTime * 0.8) * 0.003;

    atmosphereRef.current.scale.setScalar(pulse);
  });

  return (
    <group ref={atmosphereRef}>
      <mesh>
        <sphereGeometry
          args={[EARTH_RADIUS * 1.045, 64, 64]}
        />

        <meshBasicMaterial
          color="#38bdf8"
          transparent
          opacity={0.055}
          side={THREE.BackSide}
        />
      </mesh>

      <mesh>
        <sphereGeometry
          args={[EARTH_RADIUS * 1.075, 48, 48]}
        />

        <meshBasicMaterial
          color="#60a5fa"
          transparent
          opacity={0.025}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* EARTH                                                                       */
/* -------------------------------------------------------------------------- */

function Earth({ spin }) {
  const earthRef = useRef(null);

  useFrame((_, delta) => {
    if (spin && earthRef.current) {
      earthRef.current.rotation.y += delta * 0.025;
    }
  });

  return (
    <group ref={earthRef}>
      <mesh>
        <sphereGeometry
          args={[EARTH_RADIUS, 96, 96]}
        />

        <meshStandardMaterial
          color="#075985"
          roughness={0.68}
          metalness={0.08}
        />
      </mesh>

      <mesh scale={1.003}>
        <sphereGeometry
          args={[EARTH_RADIUS, 64, 64]}
        />

        <meshBasicMaterial
          color="#0ea5e9"
          transparent
          opacity={0.07}
          wireframe
        />
      </mesh>

      <EarthGrid />

      <Atmosphere />

      <mesh
        rotation={[
          0.35,
          0.2,
          0.1,
        ]}
      >
        <sphereGeometry
          args={[EARTH_RADIUS * 1.008, 48, 48]}
        />

        <meshBasicMaterial
          color="#bae6fd"
          transparent
          opacity={0.025}
          wireframe
        />
      </mesh>
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* ORBITAL RINGS                                                               */
/* -------------------------------------------------------------------------- */

function OrbitalRings() {
  const rings = [
    {
      radius: 4.15,
      rotation: [
        Math.PI / 2.4,
        0.2,
        0,
      ],
      opacity: 0.18,
    },

    {
      radius: 4.65,
      rotation: [
        1.1,
        -0.4,
        0.7,
      ],
      opacity: 0.11,
    },

    {
      radius: 5.2,
      rotation: [
        0.5,
        0.8,
        -0.3,
      ],
      opacity: 0.08,
    },
  ];

  return (
    <group>
      {rings.map((ring, index) => (
        <mesh
          key={index}
          rotation={ring.rotation}
        >
          <torusGeometry
            args={[
              ring.radius,
              0.008,
              8,
              160,
            ]}
          />

          <meshBasicMaterial
            color="#38bdf8"
            transparent
            opacity={ring.opacity}
          />
        </mesh>
      ))}
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* TRAJECTORY                                                                  */
/* -------------------------------------------------------------------------- */

function TrajectoryLine({
  entryPosition,
  impactPosition,
  progress,
}) {
  const curve = useMemo(
    () =>
      makeTrajectoryCurve(
        entryPosition,
        impactPosition
      ),
    [entryPosition, impactPosition]
  );

  const points = useMemo(
    () => curve.getPoints(120),
    [curve]
  );

  const travelled = Math.max(
    2,
    Math.floor(
      points.length *
        Math.max(progress, 0.08)
    )
  );

  return (
    <group>
      {/* Full predicted corridor */}
      <Line
        points={points}
        color="#fbbf24"
        transparent
        opacity={0.22}
        lineWidth={1}
        dashed
        dashSize={0.08}
        gapSize={0.05}
      />

      {/* Active travelled path */}
      <Line
        points={points.slice(0, travelled)}
        color="#f8fafc"
        transparent
        opacity={0.92}
        lineWidth={1.8}
      />
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* METEOR                                                                      */
/* -------------------------------------------------------------------------- */

function Meteor({
  curve,
  playing,
  speed,
  onImpact,
}) {
  const meteorRef = useRef(null);
  const trailRef = useRef(null);
  const progressRef = useRef(0);
  const impactTriggered = useRef(false);

  useEffect(() => {
    progressRef.current = playing ? 0 : 1;
    impactTriggered.current = false;
  }, [playing, curve]);

  useFrame((_, delta) => {
    if (!playing) {
      return;
    }

    const progress = progressRef.current;

    const next = Math.min(
      1,
      progress + (speed * delta) / 4.2
    );

    progressRef.current = next;

    if (
      next >= 1 &&
      !impactTriggered.current
    ) {
      impactTriggered.current = true;
      onImpact?.();
    }

    if (meteorRef.current) {
      meteorRef.current.rotation.x +=
        delta * 3.2;

      meteorRef.current.rotation.y +=
        delta * 2.1;
    }

    if (trailRef.current) {
      trailRef.current.rotation.z +=
        delta * 0.9;
    }
  });

  const progress = THREE.MathUtils.clamp(
    progressRef.current,
    0,
    1
  );

  const position = curve.getPointAt(progress);

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
      0.09,
      0.22,
      progress
    );

  return (
    <group position={position}>
      <group ref={meteorRef}>
        {/* Main rock */}
        <mesh scale={meteorScale}>
          <icosahedronGeometry args={[1, 2]} />

          <meshStandardMaterial
            color="#7c2d12"
            roughness={0.92}
            metalness={0.04}
          />
        </mesh>

        {/* Hot core */}
        <mesh
          scale={meteorScale * 0.55}
        >
          <icosahedronGeometry args={[1, 1]} />

          <meshBasicMaterial
            color="#fff7ed"
          />
        </mesh>
      </group>

      {/* Fire trail */}
      <group ref={trailRef}>
        <Line
          points={[
            position
              .clone()
              .add(
                direction
                  .clone()
                  .multiplyScalar(
                    -0.45 -
                      progress * 0.8
                  )
              ),

            position
              .clone()
              .add(
                direction
                  .clone()
                  .multiplyScalar(-0.18)
              ),

            position.clone(),
          ]}
          color="#fb923c"
          transparent
          opacity={0.9}
          lineWidth={2.8}
        />

        <mesh
          position={direction
            .clone()
            .multiplyScalar(-0.3)}
          scale={
            0.18 +
            progress * 0.12
          }
        >
          <sphereGeometry
            args={[1, 16, 16]}
          />

          <meshBasicMaterial
            color="#f97316"
            transparent
            opacity={0.16}
          />
        </mesh>
      </group>
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* IMPACT MARKER                                                               */
/* -------------------------------------------------------------------------- */

function ImpactMarker({
  position,
  craterDiameter,
  exploded,
}) {
  const ringRef = useRef(null);
  const beamRef = useRef(null);

  const craterScale =
    THREE.MathUtils.clamp(
      finiteNumber(
        craterDiameter,
        500
      ) / 900,
      0.7,
      2.5
    );

  useFrame((state) => {
    const time =
      state.clock.elapsedTime;

    if (ringRef.current) {
      ringRef.current.rotation.z =
        time * 0.3;
    }

    if (beamRef.current) {
      beamRef.current.scale.y =
        0.85 +
        Math.sin(time * 3.5) *
          0.12;
    }
  });

  return (
    <group position={position}>
      {/* Target ring */}
      <mesh
        ref={ringRef}
        rotation-x={Math.PI / 2}
        scale={craterScale}
      >
        <torusGeometry
          args={[
            0.19,
            0.026,
            12,
            96,
          ]}
        />

        <meshBasicMaterial
          color="#fb923c"
          transparent
          opacity={
            exploded
              ? 0.98
              : 0.8
          }
        />
      </mesh>

      {/* Target centre */}
      <mesh
        scale={
          exploded
            ? 0.18
            : 0.09
        }
      >
        <sphereGeometry
          args={[1, 20, 20]}
        />

        <meshBasicMaterial
          color="#fff7ed"
        />
      </mesh>

      {/* Vertical target beam */}
      <mesh
        ref={beamRef}
        position={[0, 0.24, 0]}
      >
        <cylinderGeometry
          args={[
            0.006,
            0.018,
            0.5,
            12,
          ]}
        />

        <meshBasicMaterial
          color="#f97316"
          transparent
          opacity={0.75}
        />
      </mesh>

      {exploded && (
        <pointLight
          distance={3.5}
          intensity={3.5}
          color="#fb923c"
        />
      )}
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* IMPACT EXPLOSION                                                            */
/* -------------------------------------------------------------------------- */

function ImpactExplosion({
  position,
  active,
  impactEnergy,
}) {
  const groupRef = useRef(null);
  const startTime = useRef(null);

  useEffect(() => {
    if (!active) {
      startTime.current = null;
      return;
    }

    startTime.current =
      performance.now();
  }, [active]);

  useFrame(() => {
    if (
      !active ||
      startTime.current === null ||
      !groupRef.current
    ) {
      return;
    }

    const elapsed =
      (performance.now() -
        startTime.current) /
      1000;

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

    const expansion = Math.min(
      elapsed *
        2.4 *
        energyScale,
      4.2
    );

    const opacity = Math.max(
      0,
      1 - elapsed / 3.8
    );

    groupRef.current.scale.setScalar(
      0.14 + expansion * 0.18
    );

    groupRef.current.userData.opacity =
      opacity;
  });

  if (!active) {
    return null;
  }

  return (
    <group
      ref={groupRef}
      position={position}
    >
      {/* Fireball */}
      <mesh>
        <sphereGeometry
          args={[1, 32, 32]}
        />

        <meshBasicMaterial
          color="#fb923c"
          transparent
          opacity={0.38}
        />
      </mesh>

      {/* Shockwave rings */}
      {[0, 1, 2].map(
        (index) => (
          <mesh
            key={index}
            rotation-x={
              Math.PI / 2
            }
            scale={
              1 +
              index * 0.35
            }
          >
            <torusGeometry
              args={[
                0.28 +
                  index *
                    0.08,
                0.018 -
                  index *
                    0.004,
                10,
                96,
              ]}
            />

            <meshBasicMaterial
              color={
                index === 0
                  ? "#fff7ed"
                  : "#fb923c"
              }
              transparent
              opacity={
                0.8 -
                index * 0.16
              }
            />
          </mesh>
        )
      )}

      <pointLight
        intensity={4}
        distance={6}
        color="#fb923c"
      />
    </group>
  );
}

/* -------------------------------------------------------------------------- */
/* CAMERA                                                                      */
/* -------------------------------------------------------------------------- */

function CameraRig({
  mode,
  impactPosition,
}) {
  const { camera } = useThree();

  const controlsRef =
    useRef(null);

  useEffect(() => {
    const presets = {
      globe: {
        position: [
          7.4,
          4.8,
          8.5,
        ],
        target: [
          0,
          0,
          0,
        ],
      },

      corridor: {
        position: [
          5.5,
          7.2,
          7.8,
        ],
        target: [
          0,
          1.4,
          0,
        ],
      },

      impact: {
        position:
          impactPosition
            .clone()
            .normalize()
            .multiplyScalar(5.8)
            .toArray(),

        target:
          impactPosition.toArray(),
      },
    };

    const preset =
      presets[mode] ??
      presets.globe;

    camera.position.set(
      ...preset.position
    );

    camera.lookAt(
      ...preset.target
    );

    if (controlsRef.current) {
      controlsRef.current.target.set(
        ...preset.target
      );

      controlsRef.current.update();
    }
  }, [
    camera,
    mode,
    impactPosition,
  ]);

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan
      enableZoom
      enableDamping
      dampingFactor={0.06}
      rotateSpeed={0.55}
      minDistance={4.2}
      maxDistance={17}
    />
  );
}

/* -------------------------------------------------------------------------- */
/* IMPACT LABEL                                                                */
/* -------------------------------------------------------------------------- */

function ImpactLabel({
  position,
  latitude,
  longitude,
  surface,
  exploded,
}) {
  return (
    <group position={position}>
      <Html
        center
        distanceFactor={8}
        position={[0, 0.42, 0]}
      >
        <div
          className={`meteor-3d-label ${
            exploded
              ? "is-live"
              : ""
          }`}
        >
          <strong>
            {exploded
              ? "IMPACT DETECTED"
              : "MODELLED IMPACT"}
          </strong>

          <span>
            {formatNumber(
              latitude,
              4
            )}
            ° &nbsp;
            {formatNumber(
              longitude,
              4
            )}
            °
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

/* -------------------------------------------------------------------------- */
/* SCENE                                                                       */
/* -------------------------------------------------------------------------- */

function Scene({
  trajectory,
  latitude,
  longitude,
  surface,
  craterDiameter,
  impactEnergy,
  playing,
  speed,
  cameraMode,
  spinEarth,
  onImpact,
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
        EARTH_RADIUS *
          1.015
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

  const curve = useMemo(
    () =>
      makeTrajectoryCurve(
        entryPosition,
        impactPosition
      ),
    [
      entryPosition,
      impactPosition,
    ]
  );

  const [
    exploded,
    setExploded,
  ] = useState(false);

  useEffect(() => {
    setExploded(false);
  }, [
    impact.latitude,
    impact.longitude,
    playing,
  ]);

  function handleImpact() {
    setExploded(true);
    onImpact?.();
  }

  return (
    <>
      <color
        attach="background"
        args={["#010611"]}
      />

      <fog
        attach="fog"
        args={[
          "#010611",
          14,
          30,
        ]}
      />

      <ambientLight
        intensity={0.35}
      />

      <directionalLight
        position={[
          6,
          5,
          4,
        ]}
        intensity={2.1}
      />

      <directionalLight
        position={[
          -4,
          1,
          -5,
        ]}
        intensity={0.55}
        color="#60a5fa"
      />

      <Stars
        radius={90}
        depth={55}
        count={2600}
        factor={2.1}
        saturation={0}
        fade
        speed={0.22}
      />

      <OrbitalRings />

      <Earth
        spin={spinEarth}
      />

      <TrajectoryLine
        entryPosition={
          entryPosition
        }
        impactPosition={
          impactPosition
        }
        progress={
          playing ? 0.5 : 1
        }
      />

      <Meteor
        curve={curve}
        playing={playing}
        speed={speed}
        onImpact={
          handleImpact
        }
      />

      <ImpactMarker
        position={
          impactPosition
        }
        craterDiameter={
          craterDiameter
        }
        exploded={
          exploded
        }
      />

      <ImpactExplosion
        position={
          impactPosition
        }
        active={
          exploded
        }
        impactEnergy={
          impactEnergy
        }
      />

      <ImpactLabel
        position={
          impactPosition
        }
        latitude={
          impact.latitude
        }
        longitude={
          impact.longitude
        }
        surface={
          surface
        }
        exploded={
          exploded
        }
      />

      <CameraRig
        mode={cameraMode}
        impactPosition={
          impactPosition
        }
      />
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* MAIN COMPONENT                                                              */
/* -------------------------------------------------------------------------- */

export default function MeteorMadness3D({
  simulation,
  simulationData,
  environment,
  impactBranch,
  selectedAsteroid,
  latitude,
  longitude,
}) {
  const [
    playing,
    setPlaying,
  ] = useState(false);

  const [
    speed,
    setSpeed,
  ] = useState(1);

  const [
    cameraMode,
    setCameraMode,
  ] = useState("globe");

  const [
    impactPulse,
    setImpactPulse,
  ] = useState(false);

  const [
    spinEarth,
    setSpinEarth,
  ] = useState(true);

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

  const craterDiameter =
    firstFinite(
      impactBranch?.crater
        ?.final_diameter_m,

      impactBranch?.crater
        ?.diameter_m,

      consequences
        ?.final_crater_diameter_m,

      consequences
        ?.crater_diameter_m
    );

  const impactEnergy =
    firstFinite(
      simulationData
        ?.impact_energy_J,

      simulationData
        ?.impact_energy,

      simulation
        ?.impact_energy_J,

      consequences
        ?.impact_energy_J,

      consequences
        ?.impact_energy
    );

  const impactVelocity =
    firstFinite(
      simulationData
        ?.impact_velocity_mps,

      simulationData
        ?.velocity_mps,

      simulationData
        ?.final_velocity_mps,

      selectedAsteroid
        ?.velocity_kph != null
        ? Number(
            selectedAsteroid.velocity_kph
          ) / 3.6
        : null
    );

  const impact =
    getImpactCoordinates(
      trajectory,
      latitude,
      longitude
    );

  function runSequence() {
    setImpactPulse(false);
    setPlaying(false);

    requestAnimationFrame(
      () => {
        setPlaying(true);
      }
    );
  }

  function stopSequence() {
    setPlaying(false);
    setImpactPulse(false);
  }

  function handleImpact() {
    setImpactPulse(true);
    setCameraMode("impact");
  }

  return (
    <section className="meteor-3d-panel">
      <div className="meteor-3d-header">
        <div>
          <p className="meteor-3d-kicker">
            NASA-STYLE IMPACT VISUALISATION
          </p>

          <h2>
            Earth Impact Mission Theatre
          </h2>

          <p>
            Explore the modelled entry
            corridor, impact site and
            simulated consequences in
            three dimensions.
          </p>
        </div>

        <div className="meteor-3d-status">
          <span className="meteor-3d-status-dot" />
          LIVE SIMULATION
        </div>
      </div>

      <div className="meteor-3d-stage">
        <Canvas
          camera={{
            position: [
              7.4,
              4.8,
              8.5,
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
              trajectory={
                trajectory
              }
              latitude={
                latitude
              }
              longitude={
                longitude
              }
              surface={
                surface
              }
              craterDiameter={
                craterDiameter
              }
              impactEnergy={
                impactEnergy
              }
              playing={
                playing
              }
              speed={
                speed
              }
              cameraMode={
                cameraMode
              }
              spinEarth={
                spinEarth
              }
              onImpact={
                handleImpact
              }
            />
          </Suspense>
        </Canvas>

        {/* COMMAND BAR */}
        <div className="meteor-3d-commandbar">
          <div className="meteor-3d-segment">
            <button
              type="button"
              className={
                cameraMode ===
                "globe"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setCameraMode(
                  "globe"
                )
              }
            >
              GLOBE
            </button>

            <button
              type="button"
              className={
                cameraMode ===
                "corridor"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setCameraMode(
                  "corridor"
                )
              }
            >
              CORRIDOR
            </button>

            <button
              type="button"
              className={
                cameraMode ===
                "impact"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setCameraMode(
                  "impact"
                )
              }
            >
              IMPACT
            </button>
          </div>

          <button
            type="button"
            className="primary"
            onClick={
              playing
                ? stopSequence
                : runSequence
            }
          >
            {playing
              ? "■ ABORT"
              : "▶ RUN IMPACT"}
          </button>

          <button
            type="button"
            onClick={() =>
              setSpinEarth(
                (value) =>
                  !value
              )
            }
          >
            {spinEarth
              ? "◉ ROTATION"
              : "○ ROTATION"}
          </button>
        </div>

        {/* SPEED */}
        <div className="meteor-3d-speed">
          {[0.5, 1, 2, 4].map(
            (value) => (
              <button
                key={value}
                type="button"
                className={
                  speed === value
                    ? "active"
                    : ""
                }
                onClick={() =>
                  setSpeed(value)
                }
              >
                ×{value}
              </button>
            )
          )}
        </div>

        {/* TELEMETRY */}
        <div className="meteor-3d-telemetry">
          <div className="telemetry-heading">
            <span>
              MISSION TELEMETRY
            </span>

            <b>
              {impactPulse
                ? "IMPACT EVENT"
                : "TRACKING"}
            </b>
          </div>

          <div className="telemetry-row">
            <span>
              LAT / LON
            </span>

            <strong>
              {formatNumber(
                impact.latitude,
                3
              )}
              ° /
              {" "}
              {formatNumber(
                impact.longitude,
                3
              )}
              °
            </strong>
          </div>

          <div className="telemetry-row">
            <span>
              SURFACE
            </span>

            <strong>
              {String(
                surface
              ).toUpperCase()}
            </strong>
          </div>

          <div className="telemetry-row">
            <span>
              IMPACT ENERGY
            </span>

            <strong>
              {formatEnergy(
                impactEnergy
              )}
            </strong>
          </div>

          <div className="telemetry-row">
            <span>
              VELOCITY
            </span>

            <strong>
              {impactVelocity !=
              null
                ? `${formatNumber(
                    impactVelocity,
                    1
                  )} m/s`
                : "—"}
            </strong>
          </div>

          <div className="telemetry-row">
            <span>
              CRATER
            </span>

            <strong>
              {craterDiameter !=
              null
                ? `${formatNumber(
                    craterDiameter /
                      1000,
                    2
                  )} km`
                : "—"}
            </strong>
          </div>
        </div>

        {/* TARGET LOCK */}
        <div className="meteor-3d-location">
          <span className="location-dot" />

          TARGET LOCK

          {"  "}

          {formatNumber(
            impact.latitude,
            4
          )}
          ° /

          {" "}

          {formatNumber(
            impact.longitude,
            4
          )}
          °
        </div>

        {/* HELP */}
        <div className="meteor-3d-help">
          <span>
            DRAG TO ORBIT
          </span>

          <span>
            SCROLL TO ZOOM
          </span>

          <span>
            RUN IMPACT FOR
            CINEMATIC ENTRY
          </span>
        </div>

        <div className="meteor-3d-scanline" />
      </div>
    </section>
  );
}
