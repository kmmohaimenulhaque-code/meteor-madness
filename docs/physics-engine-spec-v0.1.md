# Meteor Madness — Physics Engine Specification v0.1

**Project:** NASA Space Apps training project — Meteor Madness
**Engine:** Python
**Status:** Design specification
**Version:** 0.1
**Purpose:** Transparent educational/engineering model for asteroid atmospheric entry and impact-energy analysis.

---

## 1. Purpose and Scope

The physics engine models the atmospheric entry of an asteroid-like body from an initial altitude until one of the following occurs:

1. The object reaches the ground.
2. The object's mass falls below a defined minimum threshold.
3. The object reaches a fragmentation condition.
4. The simulation reaches its configured maximum time.

The engine estimates:

* Atmospheric density
* Aerodynamic drag
* Velocity evolution
* Mass loss through effective ablation
* Dynamic pressure
* Kinetic energy
* Drag energy dissipation
* Energy deposition as a function of altitude
* Fragmentation onset

The engine is **not intended to reproduce NASA-grade hydrocode, CFD, or full fragmentation modelling**.

It is a transparent, modular engineering model whose assumptions and limitations are explicitly documented.

---

# 2. Scientific Design Philosophy

The engine is divided conceptually into three layers:

```text
                    INPUT
                      │
                      ▼
              ┌───────────────┐
              │ Physics Model │
              │               │
              │ Drag          │
              │ Heating       │
              │ Ablation      │
              │ Fragmentation │
              └───────┬───────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Uncertainty     │
             │ / Monte Carlo   │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Consequences    │
             │ / Earth Model   │
             └────────┬────────┘
                      │
                      ▼
               Visualization
```

Version 0.1 implements only the first layer.

Uncertainty analysis and consequence modelling are separate future modules.

---

# 3. Units Convention

The physics engine uses SI units internally.

| Quantity     | Unit                 |
| ------------ | -------------------- |
| Distance     | metre (m)            |
| Time         | second (s)           |
| Mass         | kilogram (kg)        |
| Velocity     | metre/second (m/s)   |
| Acceleration | metre/second² (m/s²) |
| Density      | kg/m³                |
| Pressure     | pascal (Pa)          |
| Energy       | joule (J)            |
| Power        | watt (W)             |
| Area         | m²                   |
| Angle        | radian               |

API data may arrive in km, km/s, degrees, etc.

**Conversion must happen at the input boundary.**

The physics engine itself must never mix units.

---

# 4. Asteroid Parameter Model

The input object shall contain:

```text
AsteroidParameters
```

Required parameters:

```text
diameter_m
bulk_density_kg_m3
initial_velocity_m_s
entry_angle_rad

drag_coefficient
heat_transfer_coefficient
effective_heat_of_ablation_J_kg
material_strength_Pa

shape_factor
```

Optional future parameters:

```text
aspect_ratio
orientation
initial_altitude_m
```

---

# 5. Derived Geometric Properties

Assume an equivalent sphere for the object's volume.

Initial radius:

[
r_0 = \frac{D}{2}
]

Equivalent volume:

[
V = \frac{4}{3}\pi r_{eq}^3
]

Mass:

[
m = \rho_m V
]

Therefore:

[
m =
\rho_m\frac{4}{3}\pi r_{eq}^3
]

During ablation, density is held constant in V0.1 and equivalent radius is recalculated from remaining mass:

[
\boxed{
r_{eq} =
\left(
\frac{3m}{4\pi\rho_m}
\right)^{1/3}
}
]

---

# 6. Shape / Projected Area Model

Version 0.1 does not assume that every asteroid is perfectly spherical.

Instead, projected area is represented by an explicit shape factor:

[
\boxed{
A = C_A\pi r_{eq}^2
}
]

where:

* (A) = projected aerodynamic area
* (C_A) = shape/orientation factor
* (r_{eq}) = equivalent-sphere radius

For a perfect sphere:

[
C_A = 1
]

This architecture allows future versions to replace the constant (C_A) with a function of:

* aspect ratio
* orientation
* rotation
* aerodynamic shape

without rewriting the rest of the physics engine.

---

# 7. Atmosphere Model

Atmospheric density must vary with altitude.

The engine must **not use a single constant atmospheric density**.

[
\rho_a = \rho_a(h)
]

The atmosphere implementation shall use a recognised standard-atmosphere model rather than an arbitrary exponential approximation.

The implementation should be isolated behind an interface:

```python
atmosphere.density(altitude_m)
```

This allows the atmospheric model to be upgraded independently.

Required output:

```text
density_kg_m3
temperature_K
pressure_Pa
```

if available from the selected atmosphere model.

---

# 8. Gravity Model

Use altitude-dependent gravitational acceleration:

[
\boxed{
g(h)=g_0
\left(
\frac{R_E}{R_E+h}
\right)^2
}
]

where:

* (g_0) = standard gravitational acceleration at Earth's surface
* (R_E) = Earth radius
* (h) = altitude

This avoids treating gravity as perfectly constant throughout the simulation.

---

# 9. State Vector

Version 0.1 uses:

[
\boxed{
y =
\begin{bmatrix}
h\
v\
m
\end{bmatrix}
}
]

where:

* (h) = altitude
* (v) = velocity magnitude
* (m) = remaining mass

Entry angle (\gamma) is held constant in V0.1.

This is deliberately simplified.

A future trajectory model will evolve (\gamma) dynamically.

---

# 10. Initial Conditions

The simulation begins with:

```text
h = initial_altitude
v = initial_velocity
m = initial_mass
```

The initial mass is calculated from diameter and bulk density.

Default initial altitude should be selected consistently with the atmosphere model's valid range.

The engine must not silently extrapolate atmospheric density outside the model's validated range.

---

# 11. Aerodynamic Drag

Aerodynamic drag force:

[
\boxed{
F_D =
\frac12 C_D\rho_a v^2 A
}
]

where:

* (C_D) = drag coefficient
* (\rho_a) = atmospheric density
* (v) = velocity
* (A) = projected area

Drag acceleration:

[
\boxed{
a_D =
\frac{F_D}{m}
}
]

The drag coefficient is an explicit model parameter.

Version 0.1 treats it as constant.

Future versions may implement:

[
C_D =
f(M,Re,\text{shape},\text{flow regime})
]

---

# 12. Simplified Trajectory Equations

For V0.1:

-v\sin\gamma
}
]

Velocity evolution:

## -g(h)\sin\gamma

\frac{F_D}{m}
}
]

The constant-angle assumption is a deliberate simplification.

It means V0.1 is **not a full orbital/ballistic trajectory solver**.

Future versions should implement dynamic flight-path angle and Earth curvature.

---

# 13. Atmospheric Heating

Effective aerodynamic heating rate:

[
\boxed{
\dot Q =
\frac12 C_H\rho_a v^3 A
}
]

where:

* (C_H) = effective heat-transfer coefficient.

The coefficient must be treated as an explicit model parameter.

It must not be silently assumed to have a universal value.

---

# 14. Effective Ablation Model

Version 0.1 uses an effective heat-of-ablation model:

-\frac{\dot Q}{Q_*}
}
]

Therefore:

-\frac{
C_H\rho_a v^3 A
}{
2Q_*
}
}
]

where:

[
Q_* =
\text{effective heat of ablation}
]

This is an engineering approximation.

It does not attempt to model:

* detailed thermochemistry
* phase changes individually
* surface temperature distribution
* radiative transfer
* material-specific decomposition
* detailed melt/vapour physics

Future versions may replace this with a more sophisticated ablation model.

---

# 15. Dynamic Pressure

Dynamic pressure is:

[
\boxed{
q =
\frac12\rho_a v^2
}
]

It is recorded throughout the simulation.

Dynamic pressure is useful for identifying potentially important fragmentation conditions.

---

# 16. Fragmentation Criterion

Version 0.1 uses:

[
\boxed{
q > S
}
]

as a simplified fragmentation trigger.

where:

* (q) = dynamic pressure
* (S) = effective material strength

If:

[
q \geq S
]

the simulation records:

```text
fragmentation_detected = true
```

and stores:

```text
fragmentation_altitude
fragmentation_velocity
fragmentation_mass
fragmentation_dynamic_pressure
```

### Important limitation

This is **not a complete physical fragmentation model**.

Real asteroid failure depends on factors including:

* internal flaws
* porosity
* cracks
* material structure
* stress distribution
* strength variability
* aerodynamic loading
* rotation
* fragmentation history

V0.1 therefore treats (S) as an effective parameter.

V0.2 may introduce explicit fragment populations.

---

# 17. Kinetic Energy

Instantaneous translational kinetic energy:

[
\boxed{
E_k =
\frac12mv^2
}
]

Initial kinetic energy:

\frac12m_0v_0^2
]

Final kinetic energy:

\frac12m_fv_f^2
]

The engine shall report both.

---

# 18. Drag Energy Dissipation

Aerodynamic drag removes translational kinetic energy.

Drag power:

[
\boxed{
P_D =
F_Dv
}
]

Therefore:

[
\boxed{
P_D =
\frac12 C_D\rho_av^3A
}
]

This represents mechanical energy removed from the object's translational motion by aerodynamic drag.

The engine should integrate this quantity over time:

\int P_D,dt
]

and record its altitude distribution.

---

# 19. Energy Bookkeeping

Version 0.1 must **not** simply assume:

```text
impact energy = initial kinetic energy
```

because atmospheric interaction changes both velocity and mass.

The engine must separately report:

```text
initial kinetic energy
final kinetic energy
kinetic-energy change
integrated drag energy
mass lost
energy deposition profile
```

Ablation energy must not be arbitrarily added to drag energy.

The thermodynamic energy associated with ablation requires a consistent thermal/material model and is therefore outside V0.1's complete energy budget.

---

# 20. Energy Deposition Profile

At each timestep, record:

```text
altitude_m
velocity_m_s
mass_kg
density_kg_m3
drag_force_N
drag_power_W
kinetic_energy_J
dynamic_pressure_Pa
mass_loss_rate_kg_s
```

This produces an altitude-dependent atmospheric interaction profile.

The frontend can later visualize:

```text
Altitude
   │
100km ┤
      │
      │
      │       *
      │      ***
      │    ******
      │  *********
      │************
      └──────────────── Energy deposition
```

The visualisation must be generated from simulation output rather than fabricated values.

---

# 21. Numerical Integration

Version 0.1 uses fourth-order Runge-Kutta (RK4).

For:

[
\frac{dy}{dt}=f(t,y)
]

calculate:

[
k_1=f(t_n,y_n)
]

[
k_2=
f\left(
t_n+\frac{\Delta t}{2},
y_n+\frac{\Delta t}{2}k_1
\right)
]

[
k_3=
f\left(
t_n+\frac{\Delta t}{2},
y_n+\frac{\Delta t}{2}k_2
\right)
]

[
k_4=
f(t_n+\Delta t,y_n+\Delta tk_3)
]

Then:

y_n+
\frac{\Delta t}{6}
(k_1+2k_2+2k_3+k_4)
}
]

---

# 22. Event Detection

The solver must detect:

### Ground impact

[
h \leq 0
]

Record:

```text
impact_detected
impact_time
impact_velocity
impact_mass
impact_energy
```

### Complete ablation

[
m \leq m_{\min}
]

Record:

```text
airburst_or_ablation_end
altitude
remaining_mass
```

The exact interpretation must not automatically be called "airburst" unless the fragmentation/energy model supports that conclusion.

### Fragmentation

[
q \geq S
]

Record the fragmentation state.

---

# 23. Numerical Safety

The solver must prevent nonphysical states.

Examples:

```text
mass < 0
altitude < impossible model boundary
velocity < 0
NaN
Infinity
division by zero
```

Mass must be clamped to zero when numerical integration produces a tiny negative value.

The simulation must terminate safely when the physical model becomes invalid.

---

# 24. Timestep Configuration

Initial implementation:

```text
dt = configurable
```

The timestep must not be hidden inside the solver.

Example:

```python
SimulationConfig(
    timestep_s=0.01,
    max_time_s=1000
)
```

The exact production timestep must be determined through convergence testing.

---

# 25. Validation Tests

The engine must contain automated tests.

## Test 1 — Vacuum

Set:

```text
rho_atmosphere = 0
```

Expected:

```text
drag = 0
heating = 0
ablation = 0
mass = constant
```

---

## Test 2 — Zero Heating

Set:

```text
C_H = 0
```

Expected:

[
\frac{dm}{dt}=0
]

Mass remains constant.

---

## Test 3 — Zero Drag

Set:

```text
C_D = 0
```

Expected:

```text
drag force = 0
drag acceleration = 0
drag power = 0
```

---

## Test 4 — Zero Ablation

Use an effectively infinite (Q_*) or an explicit ablation-disabled configuration.

Expected:

```text
mass = constant
```

---

## Test 5 — Geometry Conservation

Verify:

[
m =
\rho_m
\frac43\pi r_{eq}^3
]

throughout the simulation.

---

## Test 6 — Energy Sanity

Verify that the object's translational kinetic energy does not increase due solely to drag.

---

## Test 7 — Timestep Convergence

Run the same scenario with:

```text
dt
dt / 2
dt / 4
```

Compare:

```text
impact velocity
impact mass
fragmentation altitude
energy deposition
```

The results should converge within an explicitly defined tolerance.

---

# 26. Sensitivity Analysis

Before claiming that a result is meaningful, vary uncertain parameters.

Important parameters:

```text
bulk density
C_D
C_H
Q_*
material strength
shape factor
entry velocity
entry angle
diameter
```

The engine should eventually support:

```text
parameter sweep
```

and later:

```text
Monte Carlo uncertainty propagation
```

This is preferable to presenting one highly precise-looking result based on uncertain asteroid properties.

---

# 27. Parameter Presets

Material presets may be introduced later.

For example:

```text
carbonaceous
stony
iron-rich
custom
```

However, presets must represent **ranges or clearly labelled representative assumptions**, not claim that every asteroid of that category has one exact density or strength.

The UI should make it obvious when a value is:

```text
measured
estimated
assumed
representative
uncertain
```

---

# 28. Data Provenance

Every scientifically meaningful parameter should eventually have metadata:

```text
parameter
value
unit
source
source_type
confidence
notes
```

Example:

```text
heat_transfer_coefficient:
    value: ...
    unit: dimensionless
    source: NASA research
    source_type: literature
    confidence: uncertain
    notes: model-dependent
```

No scientifically meaningful constant should be introduced merely because it "looks reasonable."

---

# 29. Separation of Concerns

The repository should eventually separate:

```text
physics/
    atmosphere.py
    geometry.py
    drag.py
    ablation.py
    fragmentation.py
    energy.py
    solver.py
    models.py
```

from:

```text
uncertainty/
```

and:

```text
consequences/
```

and:

```text
visualization/
```

The frontend must never contain the core physics equations.

---

# 30. Suggested Backend Architecture

```text
backend/
│
├── physics/
│   ├── __init__.py
│   ├── models.py
│   ├── atmosphere.py
│   ├── geometry.py
│   ├── drag.py
│   ├── ablation.py
│   ├── fragmentation.py
│   ├── energy.py
│   ├── solver.py
│   └── simulation.py
│
├── tests/
│   ├── test_geometry.py
│   ├── test_drag.py
│   ├── test_ablation.py
│   ├── test_energy.py
│   └── test_solver.py
│
├── nasa_client.py
├── main.py
└── requirements.txt
```

---

# 31. API Boundary

The FastAPI backend should expose a future endpoint similar to:

```text
POST /api/simulation/entry
```

Input:

```json
{
  "diameter_m": 50,
  "bulk_density_kg_m3": 3500,
  "initial_velocity_m_s": 20000,
  "entry_angle_rad": 0.785,
  "drag_coefficient": "...",
  "heat_transfer_coefficient": "...",
  "effective_heat_of_ablation_J_kg": "...",
  "material_strength_Pa": "...",
  "shape_factor": 1.0
}
```

Output:

```json
{
  "status": "completed",
  "outcome": "...",
  "initial_mass_kg": "...",
  "final_mass_kg": "...",
  "impact_velocity_m_s": "...",
  "impact_energy_J": "...",
  "fragmentation": {
    "detected": true,
    "altitude_m": "..."
  },
  "profile": []
}
```

The exact API schema may evolve.

---

# 32. Visualization Contract

The physics engine returns data.

It does **not** decide how that data is rendered.

Frontend visualizations may include:

### Velocity vs altitude

[
v(h)
]

### Mass vs altitude

[
m(h)
]

### Dynamic pressure vs altitude

[
q(h)
]

### Energy deposition vs altitude

[
E(h)
]

### Atmospheric density vs altitude

[
\rho(h)
]

### Simulation outcome

```text
GROUND IMPACT
AIRBORNE DISRUPTION
COMPLETE ABLATION
FRAGMENTATION
```

---

# 33. Future V0.2 — Fragmentation

V0.2 may replace:

```text
one body
```

with:

```text
parent body
     │
     ├── fragment 1
     ├── fragment 2
     ├── fragment 3
     └── debris cloud
```

Each fragment could have:

```text
mass
velocity
diameter
density
strength
shape
```

and independently interact with the atmosphere.

This is a major upgrade and should **not** be hacked into V0.1.

---

# 34. Future V0.3 — Dynamic Trajectory

Replace constant (\gamma) with a dynamically evolving flight-path angle.

Potential future state:

[
y =
[h,v,\gamma,m]
]

Earth curvature may also be introduced.

---

# 35. Future V0.4 — Consequences

Only after the atmospheric physics is sufficiently stable should the project model:

```text
airburst
ground impact
crater
blast
thermal radiation
seismic effects
tsunami
population exposure
```

These should be separate consequence models.

---

# 36. Future V0.5 — Uncertainty

Implement Monte Carlo sampling:

```text
                    asteroid parameters
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          scenario 1    scenario 2    scenario 3
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    outcome distribution
```

The system should report distributions rather than fake precision.

For example:

```text
impact altitude:
median = ...
5–95% range = ...
```

rather than:

```text
impact altitude = exactly 17,384.27 m
```

---

# 37. Scientific Limitations

V0.1 does not model:

* detailed atmospheric chemistry
* radiative heating
* detailed thermochemistry
* surface temperature
* fragmentation clouds
* rotating bodies
* tumbling
* irregular aerodynamic shapes
* dynamic flight-path angle
* Earth curvature
* winds
* detailed shock-wave propagation
* crater formation
* blast propagation
* thermal radiation
* seismic coupling
* tsunami generation
* population vulnerability

Therefore, V0.1 results must be described as:

> simplified engineering-model estimates

and never as NASA-grade predictions.

---

# 38. Scientific Sources

Primary sources should include official NASA and JPL material concerning:

* atmospheric entry
* asteroid properties
* atmospheric heating
* ablation
* fragmentation
* atmospheric energy deposition
* standard atmosphere modelling
* near-Earth objects

Relevant references include:

* NASA Asteroid Threat Assessment Project (ATAP)
* NASA Technical Reports Server (NTRS)
* NASA Glenn Research Center atmospheric modelling resources
* NASA Center for Near Earth Object Studies (CNEOS)
* NASA/JPL Small-Body Database
* NASA/JPL Mission Visualization resources

All equations and parameter assumptions used in the implementation must be traceable to an appropriate scientific source or explicitly labelled as engineering approximations.

---

# 39. Implementation Rule

**Cursor must implement this specification, not invent additional physics.**

If implementation requires a new assumption, Cursor must:

1. Stop and identify the assumption.
2. Explain why it is required.
3. Document it in the appropriate module.
4. Mark it as an approximation if necessary.
5. Avoid silently introducing arbitrary constants.

The implementation should favour:

```text
modularity
transparency
testability
scientific traceability
```

over unnecessary complexity.

---

# 40. Definition of Done for V0.1

V0.1 is complete when:

* [ ] SI units are enforced internally.
* [ ] Asteroid parameter model exists.
* [ ] Equivalent-sphere geometry exists.
* [ ] Shape factor exists.
* [ ] Standard atmosphere model exists.
* [ ] Altitude-dependent gravity exists.
* [ ] Drag model exists.
* [ ] Heating model exists.
* [ ] Effective ablation model exists.
* [ ] Dynamic-pressure calculation exists.
* [ ] Simplified fragmentation criterion exists.
* [ ] Kinetic-energy calculations exist.
* [ ] Drag-energy calculation exists.
* [ ] RK4 solver exists.
* [ ] Event detection exists.
* [ ] Automated physics tests exist.
* [ ] Timestep convergence test exists.
* [ ] API endpoint can run a simulation.
* [ ] Simulation results can be visualised by the existing frontend.
* [ ] All assumptions are documented.
* [ ] Scientific sources are documented.
* [ ] No undocumented physics constants are hidden in code.

---

# 41. Core Principle

The goal is not:

> "Make the asteroid animation look realistic."

The goal is:

> **Build a transparent computational model whose visualisation is driven by the physics.**

The visualisation comes last.

The equations, assumptions, validation, and uncertainty come first.
