Below is the equation map I’d build into the package documentation. The key idea is that a space-based data-center model is not one equation. It is a set of **coupled conservation laws and bottleneck equations**:

> compute needs power; power creates heat; heat needs radiator area and mass; mass drives launch cost; orbit drives sunlight, eclipse, link geometry, and radiation; links determine whether the compute is useful.

## 1. The governing system equation

For the package, I’d make the top-level model compute **delivered useful compute**, not installed compute.

```text
installed accelerators
→ power-available accelerators
→ thermally allowable accelerators
→ network-usable accelerators
→ reliability-adjusted accelerators
→ utilization-adjusted delivered compute
```

A good master equation is:

[
C_{\mathrm{delivered}}
======================

C_{\mathrm{peak}}
\cdot f_{\mathrm{power}}
\cdot f_{\mathrm{thermal}}
\cdot f_{\mathrm{network}}
\cdot f_{\mathrm{availability}}
\cdot f_{\mathrm{utilization}}
\cdot f_{\mathrm{software}}
]

Where:

* (C_{\mathrm{peak}}): nominal peak compute, e.g. FLOP/s, token/s, inference/s.
* (f_{\mathrm{power}}): fraction of compute supportable by available power.
* (f_{\mathrm{thermal}}): fraction supportable without overheating.
* (f_{\mathrm{network}}): fraction supportable after interconnect/downlink bottlenecks.
* (f_{\mathrm{availability}}): uptime after failures, radiation events, resets, replacement limits.
* (f_{\mathrm{utilization}}): workload demand/utilization.
* (f_{\mathrm{software}}): real sustained performance versus theoretical peak.

This should be the package’s organizing principle. Otherwise users will compare “1 GW in orbit” to “1 GW on Earth” without asking whether the orbital system can actually reject heat, move data, survive faults, or stay utilized.

## 2. Compute and workload equations

Start with accelerators.

[
C_{\mathrm{peak}} = N_{\mathrm{accel}} \cdot C_{\mathrm{accel,peak}}
]

[
P_{\mathrm{IT}} = N_{\mathrm{accel}} P_{\mathrm{accel}} + P_{\mathrm{CPU}} + P_{\mathrm{memory}} + P_{\mathrm{network}} + P_{\mathrm{storage}}
]

For AI workloads, do not rely only on FLOPS. Add workload-level metrics:

[
E_{\mathrm{token}} = \frac{P_{\mathrm{IT}}}{R_{\mathrm{token}}}
]

[
$/\mathrm{Mtoken} =
\frac{C_{\mathrm{lifecycle}}}{N_{\mathrm{tokens,lifetime}}/10^6}
]

[
\eta_{\mathrm{compute}} =
\frac{C_{\mathrm{delivered}}}{P_{\mathrm{IT}}}
]

For GPUs, use catalog values as rough upper bounds. For example, NVIDIA lists H100 SXM at up to 700 W TDP, 80 GB memory, 3.35 TB/s memory bandwidth, and high tensor throughput depending on precision; the package should treat those as **hardware catalog values**, not as guaranteed sustained application performance. ([NVIDIA][1])

### What I recommend

Use three levels of compute modeling:

| Level                 |                                   Equation style | Use case                  |
| --------------------- | -----------------------------------------------: | ------------------------- |
| Peak FLOPS/TOPS       |                      (N \cdot C_{\mathrm{peak}}) | Quick sizing              |
| Sustained workload    | (C_{\mathrm{peak}} \cdot f_{\mathrm{sustained}}) | Realistic trade studies   |
| Application benchmark |            measured tokens/s, images/s, jobs/day | Best for package examples |

Do **not** make FLOPS the only unit. Space compute may make more sense for compact-output workloads than for huge Earth-dependent training jobs.

## 3. Power equations

The solar power model starts with incident solar energy.

[
P_{\mathrm{solar,BOL}}
======================

S \cdot A_{\mathrm{array}} \cdot \eta_{\mathrm{cell}}
\cdot \eta_{\mathrm{packing}}
\cdot \eta_{\mathrm{pointing}}
]

Where:

* (S): solar irradiance near Earth, roughly (1361 \ \mathrm{W/m^2}).
* (A_{\mathrm{array}}): solar-array area.
* (\eta_{\mathrm{cell}}): cell efficiency.
* (\eta_{\mathrm{packing}}): wiring, packing, coverglass, structural losses.
* (\eta_{\mathrm{pointing}}): cosine and pointing losses.

End-of-life power:

[
P_{\mathrm{solar,EOL}}
======================

P_{\mathrm{solar,BOL}}
\cdot (1-d_{\mathrm{annual}})^{t}
]

Available bus power:

[
P_{\mathrm{bus}}
================

P_{\mathrm{solar,EOL}}
\cdot f_{\mathrm{sun}}
\cdot \eta_{\mathrm{MPPT}}
\cdot \eta_{\mathrm{PDU}}
]

IT power constraint:

[
P_{\mathrm{IT}}
\le
P_{\mathrm{bus}}
----------------

## P_{\mathrm{avionics}}

## P_{\mathrm{comms}}

## P_{\mathrm{thermal}}

## P_{\mathrm{propulsion}}

P_{\mathrm{margin}}
]

Specific power is crucial:

[
SP_{\mathrm{array}} = \frac{P_{\mathrm{array}}}{m_{\mathrm{array}}}
]

[
m_{\mathrm{array}} = \frac{P_{\mathrm{array}}}{SP_{\mathrm{array}}}
]

NASA’s small-spacecraft power chapter notes that solar-array specific power strongly governs mission feasibility; its dataset clusters around roughly 30 W/kg with an empirical upper bound near 200 W/kg. That means package defaults should be conservative and provenance-tagged, not set to speculative best-case values by default. ([NASA][2])

### Battery equation for eclipse

If the orbit includes eclipse:

[
E_{\mathrm{batt,req}}
=====================

P_{\mathrm{load,eclipse}}
\cdot t_{\mathrm{eclipse}}
\cdot \frac{1}{\eta_{\mathrm{discharge}}}
\cdot \frac{1}{DOD_{\max}}
\cdot M_{\mathrm{reserve}}
]

[
m_{\mathrm{batt}}
=================

\frac{E_{\mathrm{batt,req}}}{e_{\mathrm{batt}}}
]

Where (e_{\mathrm{batt}}) is battery specific energy in Wh/kg.

### What I recommend

Make **power closure** a hard constraint:

[
P_{\mathrm{load,total}} \le P_{\mathrm{available,EOL}}
]

Beginner users should see a red/green “power closes?” diagnostic. Advanced users should be able to optimize solar area, battery mass, orbit, utilization, and duty cycle together.

## 4. Thermal equations

This is probably the most important physics section.

In space, high-power electronics do not dump heat into air or cooling towers. Almost all IT power becomes heat, and that heat must eventually leave through radiation.

NASA’s spacecraft thermal-control overview frames spacecraft temperature as a balance among absorbed solar heat, albedo, planet infrared, internally generated heat, stored heat, and radiated heat. ([NASA][3])

q_{\mathrm{solar}}+q_{\mathrm{albedo}}+q_{\mathrm{planetIR}}+Q_{\mathrm{gen}}=Q_{\mathrm{stored}}+Q_{\mathrm{rad}}

For steady-state radiator sizing:

[
Q_{\mathrm{rad}}
================

\epsilon \sigma A_{\mathrm{rad}} F_{\mathrm{view}}
\left(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4\right)
]

Solve for radiator area:

[
A_{\mathrm{rad}}
================

\frac{Q_{\mathrm{waste}}}
{\epsilon \sigma F_{\mathrm{view}}
\left(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4\right)}
]

Where:

* (\epsilon): infrared emissivity.
* (\sigma): Stefan-Boltzmann constant.
* (A_{\mathrm{rad}}): radiator area.
* (F_{\mathrm{view}}): view factor to cold space.
* (T_{\mathrm{rad}}): radiator temperature in Kelvin.
* (T_{\mathrm{sink}}): effective sink temperature in Kelvin.
* (Q_{\mathrm{waste}}): heat to reject, roughly IT power plus power-electronics losses.

This fourth-power relationship matters. Higher radiator temperature dramatically reduces required area, but chip reliability, HBM limits, coolant limits, batteries, and thermal cycling constrain how hot you can run.

### Chip-to-radiator thermal path

For electronics, use a thermal resistance chain:

[
T_{\mathrm{junction}}
=====================

T_{\mathrm{rad}}
+
Q_{\mathrm{chip}}
\left(
R_{\mathrm{jc}}
+
R_{\mathrm{interface}}
+
R_{\mathrm{coldplate}}
+
R_{\mathrm{transport}}
+
R_{\mathrm{radiator}}
\right)
]

Constraint:

[
T_{\mathrm{junction}} \le T_{\mathrm{junction,max}} - M_T
]

For transient thermal analysis:

[
C_{\mathrm{th}} \frac{dT}{dt}
=============================

Q_{\mathrm{in}}(t)
+
Q_{\mathrm{gen}}(t)
-------------------

Q_{\mathrm{out}}(t)
]

This lets the package model eclipse, sunlit periods, thermal soak, throttling, duty cycling, and radiator deployment.

### Heat transport limit

If using heat pipes, loop heat pipes, pumped fluid, or two-phase cooling:

[
Q_{\mathrm{transport}} \le Q_{\mathrm{transport,max}}
]

[
P_{\mathrm{pump}} =
\frac{\Delta p \cdot \dot{V}}{\eta_{\mathrm{pump}}}
]

For a first package version, I’d model this as an efficiency and max-heat-transfer constraint. Later versions can add fluid network models.

### What I recommend

Make thermal closure at least as visible as power closure:

```text
Thermal closes? yes/no
Radiator area required
Radiator mass required
Maximum junction temperature
Thermal throttling fraction
Radiator packaging ratio
```

Do **not** let the package silently assume all IT power can be rejected. That is where many optimistic space-data-center arguments get sloppy.

## 5. Mass equations

Mass is the economic coupling between physics and launch cost.

[
m_{\mathrm{dry}}
================

m_{\mathrm{compute}}
+
m_{\mathrm{solar}}
+
m_{\mathrm{battery}}
+
m_{\mathrm{radiator}}
+
m_{\mathrm{thermal\ transport}}
+
m_{\mathrm{RF}}
+
m_{\mathrm{optical}}
+
m_{\mathrm{structure}}
+
m_{\mathrm{avionics}}
+
m_{\mathrm{propulsion}}
+
m_{\mathrm{shielding}}
+
m_{\mathrm{margin}}
]

Useful mass-normalized metrics:

[
\frac{P_{\mathrm{IT,delivered}}}{m_{\mathrm{dry}}}
\quad [\mathrm{W/kg}]
]

[
\frac{m_{\mathrm{dry}}}{P_{\mathrm{IT,delivered}}}
\quad [\mathrm{kg/kW}]
]

[
\frac{C_{\mathrm{delivered}}}{m_{\mathrm{dry}}}
\quad [\mathrm{FLOP/s/kg}]
]

Subsystem mass models:

[
m_{\mathrm{solar}} = \frac{P_{\mathrm{solar,EOL}}}{SP_{\mathrm{solar,EOL}}}
]

[
m_{\mathrm{radiator}} = A_{\mathrm{rad}} \cdot \rho_{\mathrm{rad,areal}}
]

[
m_{\mathrm{battery}} = \frac{E_{\mathrm{batt,req}}}{e_{\mathrm{batt}}}
]

[
m_{\mathrm{structure}} = f_{\mathrm{structure}} \cdot m_{\mathrm{subsystems}}
]

### What I recommend

Use mass build-up plus margins, not one global (W/kg) assumption. A single “specific power” number hides whether the design is solar-limited, radiator-limited, battery-limited, or structure-limited.

## 6. Orbit and geometry equations

For circular orbit speed:

[
v = \sqrt{\frac{\mu}{r}}
]

Orbital period:

[
T = 2\pi \sqrt{\frac{a^3}{\mu}}
]

Where:

* (\mu): Earth gravitational parameter.
* (r) or (a): orbital radius / semi-major axis.

Approximate free-space path range depends on geometry. For ground links, slant range varies with elevation angle; low elevation increases path length, atmospheric loss, and pointing difficulty.

For eclipse modeling, the package can start with an orbit-propagation library rather than closed-form approximations. But the output should include:

[
f_{\mathrm{sun}} = \frac{t_{\mathrm{sunlit}}}{T_{\mathrm{orbit}}}
]

[
f_{\mathrm{eclipse}} = 1 - f_{\mathrm{sun}}
]

Average available solar power:

[
\bar{P}_{\mathrm{solar}}
========================

P_{\mathrm{solar,sunlit}}
\cdot f_{\mathrm{sun}}
]

For dawn-dusk sun-synchronous orbit, (f_{\mathrm{sun}}) can be very high, but the package should compute it rather than assume it.

### Drag and station-keeping

Atmospheric drag force:

[
F_D =
\frac{1}{2}
\rho v^2 C_D A
]

Acceleration:

[
a_D = \frac{F_D}{m}
]

Station-keeping propellant can use the rocket equation:

[
\Delta v = I_{sp} g_0 \ln\left(\frac{m_0}{m_f}\right)
]

or rearranged:

[
m_{\mathrm{prop}}
=================

m_0 \left(1 - e^{-\Delta v/(I_{sp} g_0)}\right)
]

### What I recommend

Use simple orbital equations for education, but use numerical propagation for actual package calculations. Google’s Project Suncatcher work explicitly treats close formations, J2/non-spherical gravity, drag, and station-keeping as real design constraints, so the package should not reduce orbit to “sunlight percentage only.” ([Google Research][4])

## 7. RF antenna and link-budget equations

RF matters even if optical links carry the main data. RF is still important for command, telemetry, backup, weather-resilient access, emergency modes, and some downlink cases. NASA describes spacecraft communications in terms of uplink, downlink, and crosslink, and notes that RF and optical systems are complementary because optical links can be blocked by clouds. ([NASA][5])

The basic RF link equation is Friis:

P_r=P_tG_tG_r\left(\frac{\lambda}{4\pi R}\right)^2

In decibels:

[
P_r \ [\mathrm{dBW}]
====================

P_t
+
G_t
+
G_r
---

## L_{\mathrm{FS}}

## L_{\mathrm{atm}}

## L_{\mathrm{rain}}

## L_{\mathrm{pointing}}

## L_{\mathrm{polarization}}

L_{\mathrm{implementation}}
]

Free-space path loss:

[
L_{\mathrm{FS}} \ [\mathrm{dB}]
===============================

20 \log_{10}\left(\frac{4\pi R}{\lambda}\right)
]

Antenna gain for aperture antenna:

[
G =
\eta_{\mathrm{ap}}
\left(\frac{\pi D}{\lambda}\right)^2
]

In dBi:

[
G_{\mathrm{dBi}}
================

10 \log_{10}(G)
]

Approximate beamwidth:

[
\theta_{\mathrm{HPBW}}
\approx
k \frac{\lambda}{D}
]

Noise density:

[
N_0 = k_B T_{\mathrm{sys}}
]

Carrier-to-noise-density ratio:

[
\frac{C}{N_0} =
\frac{P_r}{k_B T_{\mathrm{sys}}}
]

Energy per bit to noise density:

[
\frac{E_b}{N_0}
===============

\frac{C/N_0}{R_b}
]

Link margin:

[
M_{\mathrm{link}}
=================

## \left(\frac{E_b}{N_0}\right)_{\mathrm{available}}

\left(\frac{E_b}{N_0}\right)_{\mathrm{required}}
]

### What I recommend

The package should report RF links as pass/fail with margin:

```text
Ka downlink: +3.2 dB clear sky, -5.4 dB rain case
S-band TT&C: +12.1 dB
Crosslink RF backup: +1.8 dB
```

Do **not** treat RF bandwidth as free. Higher bandwidth usually pushes you toward higher frequencies, narrower beams, more pointing sensitivity, rain fade, and larger or more efficient apertures.

## 8. Laser / optical communication equations

For optical links, use a similar power-budget structure, but the physics is usually aperture diffraction, pointing, atmospheric loss, detector sensitivity, and acquisition/tracking.

Diffraction-limited beam divergence:

[
\theta
\approx
1.22 \frac{\lambda}{D_t}
]

Spot radius at range (R):

[
w \approx R \theta
]

Approximate geometric coupling:

[
\eta_{\mathrm{geo}}
\approx
\left(
\frac{D_r}{2 R \theta}
\right)^2
]

Received optical power:

[
P_r
===

P_t
\cdot \eta_t
\cdot \eta_r
\cdot \eta_{\mathrm{geo}}
\cdot \eta_{\mathrm{pointing}}
\cdot \eta_{\mathrm{atm}}
\cdot \eta_{\mathrm{coding}}
]

Photon energy:

[
E_{\gamma} =
\frac{hc}{\lambda}
]

Photons per bit:

[
N_{\gamma/bit}
==============

\frac{P_r}{R_b}
\cdot
\frac{\lambda}{hc}
]

Optical link margin:

[
M_{\mathrm{optical}}
====================

## P_{r,\mathrm{dB}}

## P_{\mathrm{sens,dB}}

L_{\mathrm{margin,dB}}
]

Pointing loss can be approximated with a Gaussian beam model:

[
\eta_{\mathrm{pointing}}
\approx
\exp\left(
-2 \frac{\theta_{\mathrm{err}}^2}{\theta_{\mathrm{beam}}^2}
\right)
]

For inter-satellite AI clusters, optical crosslinks are central because required internal bandwidth may be enormous. Google’s Suncatcher work explicitly highlights free-space optical links, close satellite formations, and communication rates in the tens of terabits per second as a core system challenge. ([Google Research][4])

### What I recommend

Model two optical regimes separately:

| Link type                         | Main constraint                                               |
| --------------------------------- | ------------------------------------------------------------- |
| Inter-satellite optical crosslink | range, pointing, aperture, terminal power, formation geometry |
| Satellite-ground optical downlink | clouds, atmosphere, site diversity, access windows            |

Do **not** let users assume one optical ground station gives continuous availability. Optical ground links need weather/site-diversity modeling.

## 9. Network and distributed-compute equations

A data center is not just many GPUs. The network has to support the workload.

For a workload with communication intensity:

[
B_{\mathrm{req}}
================

C_{\mathrm{delivered}}
\cdot I_{\mathrm{comm}}
]

Where:

* (B_{\mathrm{req}}): required bandwidth.
* (I_{\mathrm{comm}}): bits transferred per unit compute, e.g. bits/FLOP or bits/token.

Network constraint:

[
B_{\mathrm{req}} \le B_{\mathrm{available}}
]

Latency:

[
t_{\mathrm{prop}} = \frac{R}{c}
]

Total communication time:

[
t_{\mathrm{comm}}
=================

t_{\mathrm{prop}}
+
t_{\mathrm{serialization}}
+
t_{\mathrm{queue}}
+
t_{\mathrm{protocol}}
]

Serialization delay:

[
t_{\mathrm{serialization}} =
\frac{N_{\mathrm{bits}}}{R_b}
]

For distributed training, useful scaling can be approximated:

[
S(N)
====

\frac{N}
{1 + \alpha (N-1) + \beta \frac{B_{\mathrm{model}}}{B_{\mathrm{network}}}}
]

Where:

* (S(N)): speedup from (N) accelerators.
* (\alpha): parallel overhead.
* (\beta): communication penalty.
* (B_{\mathrm{model}}): model/gradient communication burden.
* (B_{\mathrm{network}}): available interconnect bandwidth.

### What I recommend

Make network bottlenecks explicit:

```text
Compute-limited: no
Power-limited: yes
Thermal-limited: yes
Crosslink-limited: maybe
Downlink-limited: yes for Earth-user inference
```

The package should distinguish **space-native workloads** from **Earth-dependent workloads**. Space-native workloads can produce compact outputs. Earth-dependent training or inference may require huge input/output movement.

## 10. Reliability, radiation, and availability equations

A simple exponential reliability model:

[
R(t) = e^{-\lambda t}
]

Failure probability by time (t):

[
P_{\mathrm{fail}}(t) = 1 - e^{-\lambda t}
]

For (N) independent accelerators:

[
N_{\mathrm{surviving}}(t)
=========================

N_0 e^{-\lambda t}
]

Availability:

[
A =
\frac{MTBF}{MTBF + MTTR}
]

In space, (MTTR) is not “send a technician.” It may be reset time, graceful degradation, spare activation, or replacement launch cadence.

Radiation total dose approximation:

[
D_{\mathrm{TID}} =
\int_0^T \dot{D}(t) , dt
]

Single-event upset rate:

[
R_{\mathrm{SEU}}
================

\int \Phi(E) \sigma_{\mathrm{SEU}}(E) , dE
]

Where:

* (\Phi(E)): particle flux spectrum.
* (\sigma_{\mathrm{SEU}}(E)): device upset cross-section.

Expected soft errors:

[
N_{\mathrm{SEU}} = R_{\mathrm{SEU}} \cdot t \cdot N_{\mathrm{devices}}
]

Effective useful compute after failures:

[
C_{\mathrm{reliable}}
=====================

C_{\mathrm{delivered}}
\cdot A
\cdot (1 - f_{\mathrm{degraded}})
]

### What I recommend

Start with empirical failure-rate parameters and uncertainty ranges. Do not pretend the package can accurately predict modern GPU/HBM radiation behavior from first principles without data. Radiation should be modeled as a **scenario and sensitivity driver** until calibrated with real test or flight data.

Google has reported radiation testing for TPUs under Project Suncatcher, but that evidence is hardware-specific; it should not be generalized to every GPU, HBM stack, memory controller, optical terminal, or power converter. ([Google Research][4])

## 11. Cost equations

Lifecycle cost:

[
C_{\mathrm{life}}
=================

C_{\mathrm{capex}}
+
C_{\mathrm{launch}}
+
C_{\mathrm{ops}}
+
C_{\mathrm{replacement}}
+
C_{\mathrm{ground}}
+
C_{\mathrm{deorbit}}
--------------------

C_{\mathrm{residual}}
]

Launch cost:

[
C_{\mathrm{launch}} =
m_{\mathrm{launch}} \cdot c_{$/kg}
]

Satellite hardware cost:

[
C_{\mathrm{sat}}
================

c_{\mathrm{bus}}
+
c_{\mathrm{solar}}P_{\mathrm{solar}}
+
c_{\mathrm{radiator}}A_{\mathrm{rad}}
+
c_{\mathrm{battery}}E_{\mathrm{batt}}
+
c_{\mathrm{comms}}
+
c_{\mathrm{integration}}
]

Accelerator cost:

[
C_{\mathrm{accel}} =
N_{\mathrm{accel}} \cdot c_{\mathrm{accel}}
]

Cost per delivered compute:

[
$/\mathrm{GPU\text{-}hr}
========================

\frac{C_{\mathrm{life}}}
{N_{\mathrm{GPU,equiv}} \cdot 8760 \cdot T_{\mathrm{years}} \cdot A \cdot U}
]

[
$/\mathrm{useful\ PFLOP\text{-}day}
===================================

\frac{C_{\mathrm{life}}}
{C_{\mathrm{delivered}} \cdot T_{\mathrm{mission}}}
]

Levelized cost of compute:

[
LCOC =
\frac{
\sum_t \frac{C_t}{(1+r)^t}
}{
\sum_t \frac{C_{\mathrm{delivered},t}}{(1+r)^t}
}
]

### What I recommend

Use levelized cost, not just capex. Space systems can look better or worse depending on mission life, degradation, failure rate, replacement cadence, and utilization.

Also separate accelerator cost from spacecraft/platform cost. The same GPU or TPU may be required on Earth and in space, so whether to include or exclude accelerator cost depends on the comparison being made.

## 12. Earth data-center baseline equations

For Earth comparison:

[
P_{\mathrm{facility}} =
P_{\mathrm{IT}} \cdot PUE
]

PUE is conventionally defined as total facility energy or power divided by IT equipment energy or power. ([Vertiv][6])

Energy cost:

[
C_{\mathrm{energy}}
===================

P_{\mathrm{facility}}
\cdot 8760
\cdot T_{\mathrm{years}}
\cdot c_{$/kWh}
\cdot U
]

Water usage:

[
W_{\mathrm{water}}
==================

E_{\mathrm{facility}} \cdot WUE
]

Carbon emissions:

[
CO_2e =
E_{\mathrm{grid}} \cdot CI_{\mathrm{grid}}
+
CO_{2e,\mathrm{embodied}}
]

Earth delivered compute:

[
C_{\mathrm{earth,delivered}}
============================

C_{\mathrm{peak}}
\cdot f_{\mathrm{sustained}}
\cdot A_{\mathrm{earth}}
\cdot U_{\mathrm{earth}}
]

### What I recommend

Use multiple Earth baselines:

1. **Average leased colocation**
2. **Modern hyperscale data center**
3. **Renewable-heavy solar/wind + storage site**
4. **Gas-backed high-availability site**
5. **Constrained-grid expensive-power site**

Do **not** compare space against a straw-man Earth data center. Best-in-class terrestrial facilities have very good PUE, mature maintenance, supply chains, redundancy, and cheap repair access.

## 13. Environmental equations

Space is not automatically “green.” It shifts the burdens.

Operational carbon:

[
CO_{2e,\mathrm{op}}
===================

E_{\mathrm{source}} \cdot CI
]

Embodied carbon:

[
CO_{2e,\mathrm{embodied}}
=========================

\sum_i m_i \cdot EF_i
]

Launch emissions:

[
CO_{2e,\mathrm{launch}}
=======================

m_{\mathrm{propellant}} \cdot EF_{\mathrm{propellant}}
+
CO_{2e,\mathrm{manufacturing}}
]

Compute-normalized carbon:

[
\frac{CO_{2e}}{\mathrm{useful\ compute}}
========================================

\frac{
CO_{2e,\mathrm{embodied}}
+
CO_{2e,\mathrm{launch}}
+
CO_{2e,\mathrm{ops}}
}
{C_{\mathrm{delivered,lifetime}}}
]

Water-normalized compute:

[
\frac{L_{\mathrm{water}}}{\mathrm{Mtoken}}
\quad \text{or} \quad
\frac{L_{\mathrm{water}}}{\mathrm{GPU\text{-}hr}}
]

### What I recommend

Include environmental accounting, but label it lower-confidence unless good embodied-carbon and launch-emissions datasets are available. The package should not imply that “powered by sunlight” equals low total environmental impact.

## 14. Optimization formulation

A clean MDAO formulation:

[
\min_x \quad J(x)
]

Possible objectives:

[
J_1 = \frac{C_{\mathrm{life}}}{C_{\mathrm{delivered,lifetime}}}
]

[
J_2 = \frac{m_{\mathrm{launch}}}{P_{\mathrm{IT,delivered}}}
]

[
J_3 = \frac{CO_{2e}}{C_{\mathrm{delivered,lifetime}}}
]

[
J_4 = -A_{\mathrm{system}}
]

Subject to:

[
P_{\mathrm{load}} \le P_{\mathrm{available,EOL}}
]

[
Q_{\mathrm{generated}} \le Q_{\mathrm{rejected}}
]

[
T_{\mathrm{junction}} \le T_{\max}
]

[
B_{\mathrm{required}} \le B_{\mathrm{available}}
]

[
M_{\mathrm{RF}} \ge M_{\mathrm{RF,min}}
]

[
M_{\mathrm{optical}} \ge M_{\mathrm{optical,min}}
]

[
m_{\mathrm{launch}} \le m_{\mathrm{vehicle,max}}
]

[
A_{\mathrm{availability}} \ge A_{\min}
]

[
P_{\mathrm{collision}} \le P_{\mathrm{collision,max}}
]

OpenMDAO is a good backbone because it is designed for multidisciplinary optimization, analytic derivatives, coupled systems, and integration of high-fidelity analyses. ([OpenMDAO][7])

### What I recommend

Support:

* Design of experiments for beginners.
* Pareto frontiers for trade studies.
* Gradient-based optimization for smooth problems.
* Evolutionary or Bayesian optimization for mixed discrete/continuous architecture choices.
* Monte Carlo and sensitivity analysis for uncertain assumptions.

Do **not** force everything into one optimizer. Early-stage architecture work needs exploration more than false precision.

## 15. The minimum equation set I would ship in v0.1

For a first credible version, implement these as tested components:

| Discipline     | Minimum equations                                          |
| -------------- | ---------------------------------------------------------- |
| Compute        | peak, sustained, tokens/s, joules/token                    |
| Power          | solar area, EOL power, battery energy, bus efficiency      |
| Thermal        | heat balance, radiator area, thermal resistance chain      |
| Mass           | subsystem mass buildup, kg/kW, W/kg                        |
| Orbit          | period, sunlight fraction, eclipse duration, ground access |
| RF             | Friis, FSPL, antenna gain, link margin                     |
| Optical        | divergence, geometric coupling, pointing loss, photons/bit |
| Network        | required bandwidth, latency, serialization delay           |
| Reliability    | exponential survival, availability, spare capacity         |
| Cost           | launch cost, lifecycle cost, levelized cost of compute     |
| Earth baseline | PUE, energy cost, water, carbon, utilization               |

This is enough to expose most first-order feasibility boundaries.

## 16. What I would explicitly avoid in early versions

I would avoid:

* Full CFD or finite-element thermal modeling as a core dependency.
* Detailed radiation transport as a core dependency.
* High-fidelity orbital conjunction analysis as a core dependency.
* Vendor-specific GPU performance claims as default sustained performance.
* One “space beats Earth” calculator result.
* Assuming optical links have continuous ground availability.
* Assuming launch cost falls to speculative values without uncertainty ranges.
* Assuming all IT power is useful compute.
* Assuming power closure implies thermal closure.

Those can all become plugins or advanced modules later.

## Bottom line

The package should teach users that the space-data-center problem is governed by a brutal chain:

[
\text{useful compute}
\rightarrow
\text{power}
\rightarrow
\text{heat}
\rightarrow
\text{radiator area}
\rightarrow
\text{mass}
\rightarrow
\text{launch cost}
\rightarrow
\text{lifetime delivered compute}
]

The most important equations are not exotic. They are conservation of energy, Stefan-Boltzmann radiation, link budgets, orbital geometry, reliability, and levelized cost. The hard part is coupling them honestly. My strongest recommendation is to make the package’s default output not “the answer,” but a **constraint diagnosis**:

```text
This design is power-feasible.
This design is not thermally feasible.
The binding constraint is radiator mass.
Space beats Earth only below $X/kg launch cost,
above Y W/kg solar specific power,
below Z kg/kW radiator mass,
and above U% utilization.
```

That is the kind of tool beginners can learn from and advanced users can trust.

[1]: https://www.nvidia.com/en-us/data-center/h100/?utm_source=chatgpt.com "H100 GPU"
[2]: https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/?utm_source=chatgpt.com "3.0 Power - NASA"
[3]: https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/?utm_source=chatgpt.com "7.0 Thermal Control"
[4]: https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/?utm_source=chatgpt.com "Exploring a space-based, scalable AI infrastructure system ..."
[5]: https://www.nasa.gov/smallsat-institute/sst-soa/soa-communications/?utm_source=chatgpt.com "9.0 Communications - NASA"
[6]: https://www.vertiv.com/en-us/about/news-and-events/articles/educational-articles/what-is-pue-power-usage-effectiveness-and-what-does-it-measure/?utm_source=chatgpt.com "What Is PUE (Power Usage Effectiveness) and What Does ..."
[7]: https://openmdao.org/?utm_source=chatgpt.com "OpenMDAO.org | An open-source framework for efficient ..."
