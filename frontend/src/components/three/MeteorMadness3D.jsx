import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Canvas,
  useFrame,
  useThree,
} from "@react-three/fiber";

import {
  Html,
  Line,
  OrbitControls,
  Stars,
} from "@react-three/drei";

import * as THREE from "three";

import "./MeteorMadness3D.css";

const EARTH_RADIUS = 3;
const DEG = Math.PI / 180;

/* ========================================================================= */
/* HELPERS                                                                   */
/* ========================================================================= */

function finiteNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function firstFinite(...values) {
  for (const value of values) {
    const n = Number(value);

    if (Number.isFinite(n)) {
      return n;
    }
  }

  return null;
}

function formatNumber(value, digits = 2) {
  const n = Number(value);

  if (!Number.isFinite(n)) {
    return "—";
  }

  return n.toLocaleString("en-GB", {
    maximumFractionDigits: digits,
  });
}

function formatEnergy(value) {
  const n = Number(value);

  if (!Number.isFinite(n)) {
    return "—";
  }

  if (Math.abs(n) >= 1e15) {
    return `${(n / 1e15).toFixed(2)} PJ`;
  }

  if (Math.abs(n) >= 1e12) {
    return `${(n / 1e12).toFixed(2)} TJ`;
  }

  if (Math.abs(n) >= 1e9) {
    return `${(n / 1e9).toFixed(2)} GJ`;
  }

  if (Math.abs(n) >= 1e6) {
    return `${(n / 1e6).toFixed(2)} MJ`;
  }

  return `${n.toExponential(2)} J`;
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

function getEntryCoordinates(
  trajectory,
  impact
) {
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

/* ========================================================================= */
/* TRAJECTORY                                                                 */
/* ========================================================================= */

function createTrajectoryCurve(
  entryPosition,
  impactPosition
) {
  const start = entryPosition
    .clone()
    .normalize()
    .multiplyScalar(EARTH_RADIUS * 2.15);

  const end = impactPosition
    .clone()
    .normalize()
    .multiplyScalar(EARTH_RADIUS * 1.035);

  const midpoint = start
    .clone()
    .lerp(end, 0.48);

  midpoint.y += 2.35;

  return new THREE.CatmullRomCurve3([
    start,
    midpoint,
    end,
  ]);
}

/* ========================================================================= */
/* EARTH GRID                                                                 */
/* ========================================================================= */

function EarthGrid() {
  const lines = useMemo(() => {
    const result = [];

    // Latitude
    for (
      let latitude = -75;
      latitude <= 75;
      latitude += 15
    ) {
      const points = [];

      const lat = latitude * DEG;

      const radius =
        EARTH_RADIUS * Math.cos(lat);

      const y =
        EARTH_RADIUS * Math.sin(lat);

      for (
        let longitude = 0;
        longitude <= 360;
        longitude += 3
      ) {
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

    // Longitude
    for (
      let longitude = 0;
      longitude < 180;
      longitude += 15
    ) {
      const points = [];

      for (
        let latitude = -90;
        latitude <= 90;
        latitude += 3
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
        <Line
          key={index}
          points={points}
          color="#67b7e8"
          transparent
          opacity={0.1}
          lineWidth={0.5}
        />
      ))}
    </group>
  );
}

/* ========================================================================= */
/* ATMOSPHERE                                                                 */
/* ========================================================================= */

function Atmosphere() {
  const ref = useRef(null);

  useFrame((state) => {
    if (!ref.current) return;

    const pulse =
      1 +
      Math.sin(
        state.clock.elapsedTime * 0.8
      ) *
        0.003;

    ref.current.scale.setScalar(pulse);
  });

  return (
    <group ref={ref}>
      <mesh>
        <sphereGeometry
          args={[
            EARTH_RADIUS * 1.045,
            64,
            64,
          ]}
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
          args={[
            EARTH_RADIUS * 1.075,
            48,
            48,
          ]}
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

/* ========================================================================= */
/* EARTH                                                                      */
/* ========================================================================= */

function Earth({ spin }) {
  const ref = useRef(null);

  useFrame((_, delta) => {
    if (spin && ref.current) {
      ref.current.rotation.y += delta * 0.025;
    }
  });

  return (
    <group ref={ref}>
      <mesh>
        <sphereGeometry
          args={[
            EARTH_RADIUS,
            96,
            96,
          ]}
        />

        <meshStandardMaterial
          color="#075985"
          roughness={0.68}
          metalness={0.08}
        />
      </mesh>

      <mesh scale={1.003}>
        <sphereGeometry
          args={[
            EARTH_RADIUS,
            64,
            64,
          ]}
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
    </group>
  );
}

/* ========================================================================= */
/* ORBITAL RINGS                                                              */
/* ========================================================================= */

function OrbitalRings() {
  const rings = [
    {
      radius: 4.15,
      rotation: [
        Math.PI / 2.4,
        0.2,
        0,
      ],
      opacity: 0.17,
    },
    {
      radius: 4.65,
      rotation: [
        1.1,
        -0.4,
        0.7,
      ],
      opacity: 0.1,
    },
    {
      radius: 5.2,
      rotation: [
        0.5,
        0.8,
        -0.3,
      ],
      opacity: 0.075,
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

/* ========================================================================= */
/* TRAJECTORY VISUAL                                                          */
/* ========================================================================= */

function TrajectoryVisual({
  curve,
  active,
  deflected,
}) {
  const points = useMemo(
    () => curve.getPoints(120),
    [curve]
  );

  return (
    <>
      <Line
        points={points}
        color={
          deflected
            ? "#22c55e"
            : "#fbbf24"
        }
        transparent
        opacity={active ? 0.55 : 0.25}
        lineWidth={1.15}
        dashed
        dashSize={0.08}
        gapSize={0.05}
      />

      <Line
        points={points.slice(0, 70)}
        color="#f8fafc"
        transparent
        opacity={active ? 0.8 : 0.2}
        lineWidth={1.4}
      />
    </>
  );
}

/* ========================================================================= */
/* METEOR                                                                     */
/* ========================================================================= */

function Meteor({
  curve,
  playing,
  speed,
  deflected,
  onImpact,
}) {
  const groupRef = useRef(null);
  const progressRef = useRef(0);
  const impactTriggered = useRef(false);

  useEffect(() => {
    progressRef.current = playing ? 0 : 1;
    impactTriggered.current = false;
  }, [playing, curve]);

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    if (playing && !deflected) {
      const next = Math.min(
        1,
        progressRef.current +
          (speed * delta) / 4.2
      );

      progressRef.current = next;

      if (
        next >= 1 &&
        !impactTriggered.current
      ) {
        impactTriggered.current = true;
        onImpact?.();
      }
    }

    const progress =
      THREE.MathUtils.clamp(
        progressRef.current,
        0,
        1
      );

    const position =
      curve.getPointAt(progress);

    groupRef.current.position.copy(
      position
    );

    groupRef.current.rotation.x +=
      delta * 3;

    groupRef.current.rotation.y +=
      delta * 2;
  });

  const initialPosition =
    curve.getPointAt(1);

  return (
    <group
      ref={groupRef}
      position={initialPosition}
    >
      <mesh
        scale={0.17}
      >
        <icosahedronGeometry
          args={[1, 2]}
        />

        <meshStandardMaterial
          color="#7c2d12"
          roughness={0.92}
          metalness={0.04}
        />
      </mesh>

      <mesh scale={0.55}>
        <icosahedronGeometry
          args={[0.6, 1]}
        />

        <meshBasicMaterial
          color="#fff7ed"
        />
      </mesh>

      <mesh scale={0.9}>
        <sphereGeometry
          args={[0.5, 16, 16]}
        />

        <meshBasicMaterial
          color="#f97316"
          transparent
          opacity={0.12}
        />
      </mesh>

      <pointLight
        color="#f97316"
        intensity={2.2}
        distance={1.8}
      />
    </group>
  );
}

/* ========================================================================= */
/* METEOR TRAIL                                                               */
/* ========================================================================= */

function MeteorTrail({
  curve,
  playing,
}) {
  const points = useMemo(
    () => curve.getPoints(80),
    [curve]
  );

  if (!playing) {
    return null;
  }

  return (
    <Line
      points={points.slice(20, 80)}
      color="#fb923c"
      transparent
      opacity={0.25}
      lineWidth={2}
    />
  );
}

/* ========================================================================= */
/* IMPACT MARKER                                                              */
/* ========================================================================= */

function ImpactMarker({
  position,
  active,
}) {
  const ringRef = useRef(null);

  useFrame((state) => {
    if (!ringRef.current) return;

    ringRef.current.rotation.z =
      state.clock.elapsedTime * 0.4;

    const pulse =
      1 +
      Math.sin(
        state.clock.elapsedTime * 4
      ) *
        0.08;

    ringRef.current.scale.setScalar(
      pulse
    );
  });

  return (
    <group position={position}>
      <mesh
        ref={ringRef}
        rotation-x={Math.PI / 2}
      >
        <torusGeometry
          args={[
            0.24,
            0.028,
            12,
            96,
          ]}
        />

        <meshBasicMaterial
          color={
            active
              ? "#ef4444"
              : "#fb923c"
          }
        />
      </mesh>

      <mesh
        scale={
          active ? 0.15 : 0.08
        }
      >
        <sphereGeometry
          args={[
            1,
            20,
            20,
          ]}
        />

        <meshBasicMaterial
          color="#fff7ed"
        />
      </mesh>

      {active && (
        <pointLight
          color="#ef4444"
          intensity={3}
          distance={3}
        />
      )}
    </group>
  );
}

/* ========================================================================= */
/* IMPACT EXPLOSION                                                           */
/* ========================================================================= */

function ImpactExplosion({
  position,
  active,
  energy,
}) {
  const groupRef = useRef(null);
  const startRef = useRef(null);

  useEffect(() => {
    if (active) {
      startRef.current =
        performance.now();
    } else {
      startRef.current = null;
    }
  }, [active]);

  useFrame(() => {
    if (
      !active ||
      !groupRef.current ||
      startRef.current === null
    ) {
      return;
    }

    const elapsed =
      (performance.now() -
        startRef.current) /
      1000;

    const energyScale =
      THREE.MathUtils.clamp(
        Math.log10(
          Math.max(
            finiteNumber(energy, 1),
            1
          )
        ) / 10,
        0.8,
        2.8
      );

    const scale = Math.min(
      0.15 +
        elapsed *
          1.8 *
          energyScale,
      4
    );

    groupRef.current.scale.setScalar(
      scale
    );

    groupRef.current.rotation.z +=
      0.01;
  });

  if (!active) {
    return null;
  }

  return (
    <group
      ref={groupRef}
      position={position}
    >
      <mesh>
        <sphereGeometry
          args={[
            0.55,
            32,
            32,
          ]}
        />

        <meshBasicMaterial
          color="#fb923c"
          transparent
          opacity={0.42}
        />
      </mesh>

      {[0, 1, 2].map(
        (index) => (
          <mesh
            key={index}
            rotation-x={
              Math.PI / 2
            }
            scale={
              1 +
              index * 0.4
            }
          >
            <torusGeometry
              args={[
                0.3 +
                  index * 0.1,
                0.018,
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
                0.85 -
                index * 0.18
              }
            />
          </mesh>
        )
      )}

      <pointLight
        color="#fb923c"
        intensity={5}
        distance={6}
      />
    </group>
  );
}

/* ========================================================================= */
/* DEFENCE INTERCEPTOR                                                        */
/* ========================================================================= */

function DefenceInterceptor({
  active,
  progress,
  targetPosition,
  onIntercept,
}) {
  const groupRef = useRef(null);
  const triggeredRef = useRef(false);

  const startPosition = targetPosition
    .clone()
    .normalize()
    .multiplyScalar(8);

  const midPosition = startPosition
    .clone()
    .lerp(
      targetPosition
        .clone()
        .normalize()
        .multiplyScalar(4.5),
      0.5
    );

  midPosition.y += 1.5;

  const curve = useMemo(
    () =>
      new THREE.CatmullRomCurve3([
        startPosition,
        midPosition,
        targetPosition,
      ]),
    [targetPosition]
  );

  useEffect(() => {
    triggeredRef.current = false;
  }, [active]);

  useFrame((_, delta) => {
    if (!active || !groupRef.current) {
      return;
    }

    const p =
      THREE.MathUtils.clamp(
        progress,
        0,
        1
      );

    const position =
      curve.getPointAt(p);

    groupRef.current.position.copy(
      position
    );

    groupRef.current.rotation.x +=
      delta * 2;

    groupRef.current.rotation.y +=
      delta * 3;

    if (
      p >= 0.98 &&
      !triggeredRef.current
    ) {
      triggeredRef.current = true;
      onIntercept?.();
    }
  });

  if (!active) {
    return null;
  }

  return (
    <group
      ref={groupRef}
      position={startPosition}
    >
      {/* spacecraft body */}
      <mesh>
        <boxGeometry
          args={[
            0.18,
            0.11,
            0.34,
          ]}
        />

        <meshStandardMaterial
          color="#e2e8f0"
          metalness={0.85}
          roughness={0.22}
        />
      </mesh>

      {/* left panel */}
      <mesh
        position={[
          -0.25,
          0,
          0,
        ]}
      >
        <boxGeometry
          args={[
            0.32,
            0.012,
            0.14,
          ]}
        />

        <meshBasicMaterial
          color="#2563eb"
        />
      </mesh>

      {/* right panel */}
      <mesh
        position={[
          0.25,
          0,
          0,
        ]}
      >
        <boxGeometry
          args={[
            0.32,
            0.012,
            0.14,
          ]}
        />

        <meshBasicMaterial
          color="#2563eb"
        />
      </mesh>

      {/* engine */}
      <mesh
        position={[
          0,
          0,
          0.23,
        ]}
      >
        <sphereGeometry
          args={[
            0.045,
            12,
            12,
          ]}
        />

        <meshBasicMaterial
          color="#22d3ee"
        />
      </mesh>

      <pointLight
        color="#22d3ee"
        intensity={2}
        distance={1.5}
      />
    </group>
  );
}

/* ========================================================================= */
/* DEFENCE ORBIT                                                              */
/* ========================================================================= */

function DefenceTrajectory({
  targetPosition,
  active,
}) {
  const curve = useMemo(() => {
    if (!active) return null;

    const start =
      targetPosition
        .clone()
        .normalize()
        .multiplyScalar(8);

    const mid = start
      .clone()
      .lerp(
        targetPosition,
        0.5
      );

    mid.y += 1.5;

    return new THREE.CatmullRomCurve3([
      start,
      mid,
      targetPosition,
    ]);
  }, [
    targetPosition,
    active,
  ]);

  if (!curve) {
    return null;
  }

  return (
    <Line
      points={curve.getPoints(80)}
      color="#22d3ee"
      transparent
      opacity={0.65}
      lineWidth={1.3}
      dashed
      dashSize={0.08}
      gapSize={0.05}
    />
  );
}

/* ========================================================================= */
/* DEFLECTION                                                                  */
/* ========================================================================= */

function DeflectionPath({
  position,
  active,
}) {
  if (!active) {
    return null;
  }

  const normal =
    position
      .clone()
      .normalize();

  const tangent = new THREE.Vector3(
    -normal.z,
    0.5,
    normal.x
  ).normalize();

  const end = position
    .clone()
    .add(
      tangent.multiplyScalar(2.4)
    );

  return (
    <>
      <Line
        points={[
          position,
          end,
        ]}
        color="#22c55e"
        transparent
        opacity={0.9}
        lineWidth={2.2}
      />

      <Line
        points={[
          position,
          end.clone().add(
            new THREE.Vector3(
              0.4,
              0.15,
              -0.3
            )
          ),
        ]}
        color="#22c55e"
        transparent
        opacity={0.25}
        lineWidth={5}
      />

      <mesh position={end}>
        <sphereGeometry
          args={[
            0.07,
            16,
            16,
          ]}
        />

        <meshBasicMaterial
          color="#22c55e"
        />
      </mesh>
    </>
  );
}

/* ========================================================================= */
/* INTERCEPT FLASH                                                            */
/* ========================================================================= */

function InterceptFlash({
  position,
  active,
}) {
  const ref = useRef(null);
  const startRef = useRef(null);

  useEffect(() => {
    if (active) {
      startRef.current =
        performance.now();
    } else {
      startRef.current = null;
    }
  }, [active]);

  useFrame(() => {
    if (
      !active ||
      !ref.current ||
      startRef.current === null
    ) {
      return;
    }

    const elapsed =
      (performance.now() -
        startRef.current) /
      1000;

    ref.current.scale.setScalar(
      Math.min(
        0.15 + elapsed * 1.7,
        2.7
      )
    );

    ref.current.rotation.z +=
      0.02;
  });

  if (!active) {
    return null;
  }

  return (
    <group
      ref={ref}
      position={position}
    >
      <mesh>
        <sphereGeometry
          args={[
            0.4,
            32,
            32,
          ]}
        />

        <meshBasicMaterial
          color="#22d3ee"
          transparent
          opacity={0.35}
        />
      </mesh>

      <mesh
        rotation-x={
          Math.PI / 2
        }
      >
        <torusGeometry
          args={[
            0.45,
            0.025,
            12,
            96,
          ]}
        />

        <meshBasicMaterial
          color="#67e8f9"
        />
      </mesh>

      <pointLight
        color="#22d3ee"
        intensity={5}
        distance={5}
      />
    </group>
  );
}

/* ========================================================================= */
/* CAMERA                                                                     */
/* ========================================================================= */

function CameraRig({
  mode,
  impactPosition,
}) {
  const { camera } = useThree();
  const controlsRef = useRef(null);

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
      maxDistance={18}
    />
  );
}

/* ========================================================================= */
/* SCENE                                                                      */
/* ========================================================================= */

function Scene({
  trajectory,
  latitude,
  longitude,
  playing,
  speed,
  cameraMode,
  spinEarth,
  defenceActive,
  defenceProgress,
  deflected,
  defenceTarget,
  impactEnergy,
  onImpact,
  onIntercept,
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
    [
      trajectory,
      impact,
    ]
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

  const trajectoryCurve = useMemo(
    () =>
      createTrajectoryCurve(
        entryPosition,
        impactPosition
      ),
    [
      entryPosition,
      impactPosition,
    ]
  );

  const defenceTargetPosition =
    useMemo(() => {
      if (
        defenceTarget ===
        "early"
      ) {
        return latLonToVector3(
          impact.latitude + 12,
          impact.longitude + 25,
          EARTH_RADIUS * 1.35
        );
      }

      return impactPosition;
    }, [
      defenceTarget,
      impact,
      impactPosition,
    ]);

  const [
    impactDetected,
    setImpactDetected,
  ] = useState(false);

  const [
    interceptDetected,
    setInterceptDetected,
  ] = useState(false);

  useEffect(() => {
    setImpactDetected(false);
    setInterceptDetected(false);
  }, [
    impact.latitude,
    impact.longitude,
    playing,
  ]);

  function handleImpact() {
    setImpactDetected(true);
    onImpact?.();
  }

  function handleIntercept() {
    setInterceptDetected(true);
    onIntercept?.();
  }

  return (
    <>
      <color
        attach="background"
        args={[
          "#010611",
        ]}
      />

      <fog
        attach="fog"
        args={[
          "#010611",
          14,
          32,
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

      <Earth spin={spinEarth} />

      <TrajectoryVisual
        curve={trajectoryCurve}
        active={playing}
        deflected={deflected}
      />

      <MeteorTrail
        curve={trajectoryCurve}
        playing={playing}
      />

      <Meteor
        curve={trajectoryCurve}
        playing={playing}
        speed={speed}
        deflected={deflected}
        onImpact={handleImpact}
      />

      <ImpactMarker
        position={impactPosition}
        active={impactDetected}
      />

      <ImpactExplosion
        position={impactPosition}
        active={impactDetected}
        energy={impactEnergy}
      />

      <DefenceTrajectory
        targetPosition={
          defenceTargetPosition
        }
        active={defenceActive}
      />

      <DefenceInterceptor
        active={defenceActive}
        progress={defenceProgress}
        targetPosition={
          defenceTargetPosition
        }
        onIntercept={
          handleIntercept
        }
      />

      <InterceptFlash
        position={
          defenceTargetPosition
        }
        active={interceptDetected}
      />

      <DeflectionPath
        position={
          defenceTargetPosition
        }
        active={deflected}
      />

      <CameraRig
        mode={cameraMode}
        impactPosition={impactPosition}
      />

      {interceptDetected && (
        <Html
          position={[
            defenceTargetPosition.x,
            defenceTargetPosition.y + 0.5,
            defenceTargetPosition.z,
          ]}
          center
        >
          <div className="meteor-3d-intercept-label">
            <strong>
              INTERCEPT CONFIRMED
            </strong>

            <span>
              TRAJECTORY MODIFICATION
              DETECTED
            </span>
          </div>
        </Html>
      )}
    </>
  );
}

/* ========================================================================= */
/* MAIN COMPONENT                                                             */
/* ========================================================================= */

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

  const [speed, setSpeed] =
    useState(1);

  const [cameraMode, setCameraMode] =
    useState("globe");

  const [spinEarth, setSpinEarth] =
    useState(true);

  const [defenceActive, setDefenceActive] =
    useState(false);

  const [defenceProgress, setDefenceProgress] =
    useState(0);

  const [defenceTarget, setDefenceTarget] =
    useState("impact");

  const [defenceMode, setDefenceMode] =
    useState("kinetic");

  const [deflected, setDeflected] =
    useState(false);

  const [missionStatus, setMissionStatus] =
    useState("TRACKING");

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
      simulationData?.impact_energy_J,
      simulationData?.impact_energy,
      simulation?.impact_energy_J,
      consequences?.impact_energy_J,
      consequences?.impact_energy
    );

  const impactVelocity =
    firstFinite(
      simulationData?.impact_velocity_mps,
      simulationData?.velocity_mps,
      simulationData?.final_velocity_mps,

      selectedAsteroid?.velocity_kph != null
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

  /* ----------------------------------------------------------------------- */
  /* DEFENCE RESPONSE                                                         */
  /* ----------------------------------------------------------------------- */

  useEffect(() => {
    if (!defenceActive) {
      return;
    }

    let progress = 0;

    setDefenceProgress(0);
    setDeflected(false);
    setMissionStatus(
      defenceMode ===
        "kinetic"
        ? "INTERCEPTOR LAUNCH"
        : "TRACTOR DEPLOYMENT"
    );

    const timer = setInterval(() => {
      progress +=
        defenceMode ===
        "kinetic"
          ? 0.012
          : 0.006;

      const clamped =
        Math.min(
          progress,
          1
        );

      setDefenceProgress(
        clamped
      );

      if (
        clamped > 0.22
      ) {
        setMissionStatus(
          "MIDCOURSE TRACKING"
        );
      }

      if (
        clamped > 0.62
      ) {
        setMissionStatus(
          "TERMINAL GUIDANCE"
        );
      }

      if (
        clamped >= 1
      ) {
        clearInterval(timer);

        setDeflected(true);

        setMissionStatus(
          "TRAJECTORY DEFLECTED"
        );

        setCameraMode(
          "impact"
        );
      }
    }, 50);

    return () =>
      clearInterval(timer);
  }, [
    defenceActive,
    defenceMode,
    defenceTarget,
  ]);

  function runBaseline() {
    setDefenceActive(false);
    setDeflected(false);
    setMissionStatus(
      "IMPACT SEQUENCE"
    );

    setPlaying(false);

    requestAnimationFrame(() => {
      setPlaying(true);
    });
  }

  function launchDefence() {
    setPlaying(false);
    setDeflected(false);
    setDefenceProgress(0);

    setMissionStatus(
      "DEFENCE RESPONSE"
    );

    setDefenceActive(true);

    setCameraMode(
      "corridor"
    );
  }

  function resetMission() {
    setPlaying(false);
    setDefenceActive(false);
    setDefenceProgress(0);
    setDeflected(false);

    setMissionStatus(
      "TRACKING"
    );

    setCameraMode(
      "globe"
    );
  }

  return (
    <section className="meteor-3d-panel">

      {/* HEADER */}
      <header className="meteor-3d-header">
        <div>
          <p className="meteor-3d-kicker">
            PLANETARY DEFENCE MISSION
          </p>

          <h2>
            Earth Impact Mission Theatre
          </h2>

          <p>
            Explore the modelled threat,
            impact corridor and simulated
            planetary defence response.
          </p>
        </div>

        <div className="meteor-3d-status">
          <span className="meteor-3d-status-dot" />
          {missionStatus}
        </div>
      </header>

      {/* 3D WORLD */}
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
              trajectory={trajectory}
              latitude={latitude}
              longitude={longitude}
              playing={playing}
              speed={speed}
              cameraMode={cameraMode}
              spinEarth={spinEarth}
              defenceActive={
                defenceActive
              }
              defenceProgress={
                defenceProgress
              }
              deflected={deflected}
              defenceTarget={
                defenceTarget
              }
              impactEnergy={
                impactEnergy
              }
              onImpact={() =>
                setMissionStatus(
                  "IMPACT DETECTED"
                )
              }
              onIntercept={() =>
                setMissionStatus(
                  "INTERCEPT CONFIRMED"
                )
              }
            />
          </Suspense>
        </Canvas>

        {/* TELEMETRY */}
        <div className="meteor-3d-telemetry">
          <div className="telemetry-heading">
            <span>
              MISSION TELEMETRY
            </span>

            <b>
              {missionStatus}
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
              {impactVelocity != null
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
              {craterDiameter != null
                ? `${formatNumber(
                    craterDiameter / 1000,
                    2
                  )} km`
                : "—"}
            </strong>
          </div>
        </div>

        {/* TARGET LOCK */}
        <div className="meteor-3d-location">
          <span className="location-dot" />

          TARGET LOCK&nbsp;

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

        {/* DEFENCE PANEL */}
        <div className="meteor-3d-defence">

          <div className="defence-title">
            <div>
              <span>
                PLANETARY DEFENCE
              </span>

              <strong>
                RESPONSE SIMULATOR
              </strong>
            </div>

            <div
              className={
                deflected
                  ? "defence-safe"
                  : "defence-warning"
              }
            >
              {deflected
                ? "DEFLECTED"
                : "THREAT"}
            </div>
          </div>

          {/* STRATEGY */}
          <div className="defence-strategy">
            <button
              type="button"
              className={
                defenceMode ===
                "kinetic"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setDefenceMode(
                  "kinetic"
                )
              }
            >
              KINETIC
            </button>

            <button
              type="button"
              className={
                defenceMode ===
                "tractor"
                  ? "active"
                  : ""
              }
              onClick={() =>
                setDefenceMode(
                  "tractor"
                )
              }
            >
              GRAVITY TRACTOR
            </button>
          </div>

          {/* TARGET */}
          <div className="defence-target">
            <span>
              INTERCEPT POINT
            </span>

            <select
              value={
                defenceTarget
              }
              onChange={(event) =>
                setDefenceTarget(
                  event.target.value
                )
              }
            >
              <option value="impact">
                IMPACT CORRIDOR
              </option>

              <option value="early">
                EARLY INTERCEPT
              </option>
            </select>
          </div>

          {/* PROGRESS */}
          <div className="defence-progress">
            <div>
              <span>
                RESPONSE PROGRESS
              </span>

              <strong>
                {Math.round(
                  defenceProgress *
                    100
                )}
                %
              </strong>
            </div>

            <div className="defence-progress-track">
              <div
                style={{
                  width: `${defenceProgress * 100}%`,
                }}
              />
            </div>
          </div>

          {/* ACTIONS */}
          <div className="defence-actions">
            <button
              type="button"
              className="defence-launch"
              onClick={
                defenceActive
                  ? resetMission
                  : launchDefence
              }
            >
              {defenceActive
                ? "RESET MISSION"
                : "LAUNCH DEFENCE"}
            </button>

            <button
              type="button"
              onClick={
                runBaseline
              }
            >
              BASELINE
            </button>
          </div>
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
              runBaseline
            }
          >
            ▶ RUN IMPACT
          </button>

          <button
            type="button"
            onClick={() =>
              setSpinEarth(
                (value) => !value
              )
            }
          >
            {spinEarth
              ? "◉ ROTATION"
              : "○ ROTATION"}
          </button>
        </div>

        <div className="meteor-3d-help">
          <span>
            DRAG TO ORBIT
          </span>

          <span>
            SCROLL TO ZOOM
          </span>

          <span>
            DEFENCE RESPONSE IS
            SIMULATED
          </span>
        </div>

        <div className="meteor-3d-scanline" />
      </div>
    </section>
  );
}
