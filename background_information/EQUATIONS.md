# Equation map

A space-based data-center model is not one equation. It is a set of **coupled conservation laws and bottleneck equations**:

> compute needs power; power creates heat; heat needs radiator area and mass; mass drives launch cost; orbit drives sunlight, eclipse, link geometry, and radiation; links determine whether the compute is useful.

Math here is written in GitHub-renderable LaTeX (`$$ … $$`). The disciplines map 1:1 onto `models/` modules. Section 15 lists the minimum set to ship in v0.1; section 16 lists what to leave out of early versions.

## 1. The governing system equation

The top-level model computes **delivered useful compute**, not installed compute:

```text
installed accelerators
→ power-available accelerators
→ thermally allowable accelerators
→ network-usable accelerators
→ reliability-adjusted accelerators
→ utilization-adjusted delivered compute
```

The master equation:

$$
C_{\mathrm{delivered}}
= C_{\mathrm{peak}}
\cdot f_{\mathrm{power}}
\cdot f_{\mathrm{thermal}}
\cdot f_{\mathrm{network}}
\cdot f_{\mathrm{availability}}
\cdot f_{\mathrm{utilization}}
\cdot f_{\mathrm{software}}
$$

Where:

* $C_{\mathrm{peak}}$: nominal peak compute, e.g. FLOP/s, token/s, inference/s.
* $f_{\mathrm{power}}$: fraction of compute supportable by available power.
* $f_{\mathrm{thermal}}$: fraction supportable without overheating.
* $f_{\mathrm{network}}$: fraction supportable after interconnect/downlink bottlenecks.
* $f_{\mathrm{availability}}$: uptime after failures, radiation events, resets, replacement limits.
* $f_{\mathrm{utilization}}$: workload demand / utilization.
* $f_{\mathrm{software}}$: real sustained performance versus theoretical peak.

This is the organizing principle. Without it, users compare "1 GW in orbit" to "1 GW on Earth" without asking whether the orbital system can reject heat, move data, survive faults, or stay utilized.

## 2. Compute and workload equations

Start with accelerators:

$$
C_{\mathrm{peak}} = N_{\mathrm{accel}} \cdot C_{\mathrm{accel,peak}}
$$

$$
P_{\mathrm{IT}} = N_{\mathrm{accel}} P_{\mathrm{accel}} + P_{\mathrm{CPU}} + P_{\mathrm{memory}} + P_{\mathrm{network}} + P_{\mathrm{storage}}
$$

For AI workloads, do not rely only on FLOPS. Add workload-level metrics:

$$
E_{\mathrm{token}} = \frac{P_{\mathrm{IT}}}{R_{\mathrm{token}}}
$$

$$
\text{\\$/Mtoken} = \frac{C_{\mathrm{lifecycle}}}{N_{\mathrm{tokens,lifetime}} / 10^6}
$$

$$
\eta_{\mathrm{compute}} = \frac{C_{\mathrm{delivered}}}{P_{\mathrm{IT}}}
$$

Treat vendor catalog numbers as rough upper bounds, not sustained application performance. NVIDIA lists the H100 SXM at up to 700 W TDP, 80 GB memory, and 3.35 TB/s memory bandwidth. **Its headline tensor-throughput figures assume 2:4 structured sparsity**: the often-quoted 1,979 FP16 TFLOPS and 3,958 FP8 TFLOPS are the sparsity-enabled numbers, and **dense throughput is half** (≈ 989 FP16 TFLOPS, ≈ 1,979 FP8 TFLOPS). The accelerator catalog must record precision and a dense-vs-sparse flag explicitly, default to dense, and separate peak from sustained. ([NVIDIA][1])

Use three levels of compute modeling:

| Level                 | Equation style                                  | Use case                  |
| --------------------- | ----------------------------------------------- | ------------------------- |
| Peak FLOPS/TOPS       | $N \cdot C_{\mathrm{peak}}$                      | Quick sizing              |
| Sustained workload    | $C_{\mathrm{peak}} \cdot f_{\mathrm{sustained}}$ | Realistic trade studies  |
| Application benchmark | measured tokens/s, images/s, jobs/day           | Best for package examples |

Do not make FLOPS the only unit. Space compute may suit compact-output workloads more than huge Earth-dependent training jobs.

## 3. Power equations

The solar power model starts with incident solar energy:

$$
P_{\mathrm{solar,BOL}}
= S \cdot A_{\mathrm{array}} \cdot \eta_{\mathrm{cell}}
\cdot \eta_{\mathrm{packing}}
\cdot \eta_{\mathrm{pointing}}
$$

Where:

* $S$: solar irradiance near Earth, ≈ $1361\ \mathrm{W/m^2}$.
* $A_{\mathrm{array}}$: solar-array area.
* $\eta_{\mathrm{cell}}$: cell efficiency.
* $\eta_{\mathrm{packing}}$: wiring, packing, coverglass, structural losses.
* $\eta_{\mathrm{pointing}}$: cosine and pointing losses.

End-of-life power:

$$
P_{\mathrm{solar,EOL}} = P_{\mathrm{solar,BOL}} \cdot (1 - d_{\mathrm{annual}})^{t}
$$

Available bus power:

$$
P_{\mathrm{bus}} = P_{\mathrm{solar,EOL}} \cdot f_{\mathrm{sun}} \cdot \eta_{\mathrm{MPPT}} \cdot \eta_{\mathrm{PDU}}
$$

IT power constraint:

$$
P_{\mathrm{IT}} \le P_{\mathrm{bus}} - P_{\mathrm{avionics}} - P_{\mathrm{comms}} - P_{\mathrm{thermal}} - P_{\mathrm{propulsion}} - P_{\mathrm{margin}}
$$

Specific power:

$$
SP_{\mathrm{array}} = \frac{P_{\mathrm{array}}}{m_{\mathrm{array}}}
\qquad
m_{\mathrm{array}} = \frac{P_{\mathrm{array}}}{SP_{\mathrm{array}}}
$$

NASA's small-spacecraft power chapter notes that solar-array specific power strongly governs mission feasibility; its dataset clusters around ≈ 30 W/kg with an empirical upper bound near 200 W/kg. Package defaults should be conservative and provenance-tagged, not set to speculative best-case values. ([NASA][2])

### Battery sizing for eclipse

$$
E_{\mathrm{batt,req}}
= P_{\mathrm{load,eclipse}}
\cdot t_{\mathrm{eclipse}}
\cdot \frac{1}{\eta_{\mathrm{discharge}}}
\cdot \frac{1}{DOD_{\max}}
\cdot M_{\mathrm{reserve}}
$$

$$
m_{\mathrm{batt}} = \frac{E_{\mathrm{batt,req}}}{e_{\mathrm{batt}}}
$$

Where $e_{\mathrm{batt}}$ is battery specific energy in Wh/kg.

Make **power closure** a hard constraint:

$$
P_{\mathrm{load,total}} \le P_{\mathrm{available,EOL}}
$$

Beginner users should see a red/green "power closes?" diagnostic. Advanced users should be able to optimize solar area, battery mass, orbit, utilization, and duty cycle together.

## 4. Thermal equations

This is the most important physics section. In space, high-power electronics do not dump heat into air or cooling towers. Nearly all IT power becomes heat, and that heat must leave through radiation.

NASA's spacecraft thermal-control overview frames spacecraft temperature as a balance among absorbed solar heat, albedo, planet infrared, internally generated heat, stored heat, and radiated heat. ([NASA][3])

$$
q_{\mathrm{solar}} + q_{\mathrm{albedo}} + q_{\mathrm{planetIR}} + Q_{\mathrm{gen}}
= Q_{\mathrm{stored}} + Q_{\mathrm{rad}}
$$

Steady-state radiator heat rejection:

$$
Q_{\mathrm{rad}} = \epsilon \sigma A_{\mathrm{rad}} F_{\mathrm{view}}
\left(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4\right)
$$

But the usable **net** rejection subtracts the absorbed environment — direct
solar, Earth albedo, and Earth IR — which is what the `orbitdc.thermal` module
implements (Phase 2A). Per unit panel area, with `N_sides` radiating sides:

$$
q_{\mathrm{net}} = N_{\mathrm{sides}}\,\epsilon \sigma \left(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4\right)
- \left[\alpha\,S\cos\theta_\odot + \alpha\,A_{\mathrm{alb}} F_\oplus S + \epsilon\,F_\oplus\,Q_{\mathrm{IR}}\right]
$$

with solar absorptance $\alpha$, IR emissivity $\epsilon$, solar irradiance
$S\approx 1361\ \mathrm{W/m^2}$, albedo $A_{\mathrm{alb}}\approx 0.30$, Earth IR
$Q_{\mathrm{IR}}\approx 238\ \mathrm{W/m^2}$, and Earth view factor $F_\oplus$.
Low $\alpha$ / high $\epsilon$ is the design goal; net flux can go to zero. Closure
must be checked at **end of life** ($\alpha$ rises, $\epsilon$ falls). Radiator area:

$$
A_{\mathrm{rad}} = \frac{Q_{\mathrm{waste}}}{q_{\mathrm{net}}}
$$

The radiator temperature is **not free**: the chip stack sets a ceiling
$T_{\mathrm{rad,max}} = T_{j,\max} - Q_{\mathrm{chip}} R_{\mathrm{total}}$ (the
resistance chain below), and running hotter cuts area as $T^4$ but risks the
junction. Where the older form
$Q_{\mathrm{rad}} = \epsilon \sigma A_{\mathrm{rad}} F_{\mathrm{view}}(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4)$
appears with a constant $T_{\mathrm{sink}}$, treat it as a Tier-0 sanity check only.

Where:

* $\epsilon$: infrared emissivity.
* $\sigma$: Stefan-Boltzmann constant.
* $A_{\mathrm{rad}}$: radiator area.
* $F_{\mathrm{view}}$: view factor to cold space.
* $T_{\mathrm{rad}}$, $T_{\mathrm{sink}}$: radiator and effective sink temperatures (K).
* $Q_{\mathrm{waste}}$: heat to reject, ≈ IT power plus power-electronics losses.

The fourth-power relationship matters: higher radiator temperature sharply reduces required area, but chip reliability, HBM limits, coolant limits, batteries, and thermal cycling constrain how hot you can run.

### Chip-to-radiator thermal path

$$
T_{\mathrm{junction}} = T_{\mathrm{rad}} + Q_{\mathrm{chip}}
\left(R_{\mathrm{jc}} + R_{\mathrm{interface}} + R_{\mathrm{coldplate}} + R_{\mathrm{transport}} + R_{\mathrm{radiator}}\right)
$$

Constraint:

$$
T_{\mathrm{junction}} \le T_{\mathrm{junction,max}} - M_T
$$

Transient thermal analysis:

$$
C_{\mathrm{th}} \frac{dT}{dt} = Q_{\mathrm{in}}(t) + Q_{\mathrm{gen}}(t) - Q_{\mathrm{out}}(t)
$$

This captures eclipse, sunlit periods, thermal soak, throttling, duty cycling, and radiator deployment.

### Heat transport limit

For heat pipes, loop heat pipes, pumped fluid, or two-phase cooling:

$$
Q_{\mathrm{transport}} \le Q_{\mathrm{transport,max}}
\qquad
P_{\mathrm{pump}} = \frac{\Delta p \cdot \dot{V}}{\eta_{\mathrm{pump}}}
$$

For a first version, model this as an efficiency and max-heat-transfer constraint; add fluid-network models later.

Make thermal closure at least as visible as power closure: thermal closes (yes/no), radiator area required, radiator mass required, maximum junction temperature, thermal throttling fraction, radiator packaging ratio. Do not let the package silently assume all IT power can be rejected — that is where optimistic space-data-center arguments get sloppy.

## 5. Mass equations

Mass is the economic coupling between physics and launch cost.

$$
m_{\mathrm{dry}} = m_{\mathrm{compute}} + m_{\mathrm{solar}} + m_{\mathrm{battery}} + m_{\mathrm{radiator}}
+ m_{\mathrm{thermal\ transport}} + m_{\mathrm{RF}} + m_{\mathrm{optical}} + m_{\mathrm{structure}}
+ m_{\mathrm{avionics}} + m_{\mathrm{propulsion}} + m_{\mathrm{shielding}} + m_{\mathrm{margin}}
$$

Mass-normalized metrics:

$$
\frac{P_{\mathrm{IT,delivered}}}{m_{\mathrm{dry}}}\ [\mathrm{W/kg}]
\qquad
\frac{m_{\mathrm{dry}}}{P_{\mathrm{IT,delivered}}}\ [\mathrm{kg/kW}]
\qquad
\frac{C_{\mathrm{delivered}}}{m_{\mathrm{dry}}}\ [\mathrm{FLOP/s/kg}]
$$

Subsystem mass models:

$$
m_{\mathrm{solar}} = \frac{P_{\mathrm{solar,EOL}}}{SP_{\mathrm{solar,EOL}}}
\qquad
m_{\mathrm{radiator}} = A_{\mathrm{rad}} \cdot \rho_{\mathrm{rad,areal}}
$$

$$
m_{\mathrm{battery}} = \frac{E_{\mathrm{batt,req}}}{e_{\mathrm{batt}}}
\qquad
m_{\mathrm{structure}} = f_{\mathrm{structure}} \cdot m_{\mathrm{subsystems}}
$$

Use mass build-up plus margins, not one global W/kg assumption. A single specific-power number hides whether the design is solar-limited, radiator-limited, battery-limited, or structure-limited.

## 6. Orbit and geometry equations

Circular orbit speed and period:

$$
v = \sqrt{\frac{\mu}{r}}
\qquad
T = 2\pi \sqrt{\frac{a^3}{\mu}}
$$

Where $\mu$ is Earth's gravitational parameter and $r$ (or $a$) is the orbital radius / semi-major axis.

For ground links, slant range varies with elevation angle; low elevation increases path length, atmospheric loss, and pointing difficulty.

Sunlit and eclipse fractions:

$$
f_{\mathrm{sun}} = \frac{t_{\mathrm{sunlit}}}{T_{\mathrm{orbit}}}
\qquad
f_{\mathrm{eclipse}} = 1 - f_{\mathrm{sun}}
$$

Average available solar power:

$$
\bar{P}_{\mathrm{solar}} = P_{\mathrm{solar,sunlit}} \cdot f_{\mathrm{sun}}
$$

For dawn-dusk sun-synchronous orbit, $f_{\mathrm{sun}}$ can be very high, but compute it rather than assume it.

### Drag and station-keeping

$$
F_D = \tfrac{1}{2} \rho v^2 C_D A
\qquad
a_D = \frac{F_D}{m}
$$

Station-keeping propellant via the rocket equation:

$$
\Delta v = I_{sp} g_0 \ln\!\left(\frac{m_0}{m_f}\right)
\qquad
m_{\mathrm{prop}} = m_0 \left(1 - e^{-\Delta v / (I_{sp} g_0)}\right)
$$

Use closed-form orbital equations for education and for the v0.1 sunlit/eclipse estimate; use numerical propagation for higher-fidelity work. Google's Project Suncatcher treats close formations, J2/non-spherical gravity, drag, and station-keeping as real design constraints, so do not reduce orbit to "sunlight percentage only." ([Google Research][4])

## 7. RF antenna and link-budget equations

RF matters even when optical links carry the main data: it remains important for command, telemetry, backup, weather-resilient access, and emergency modes. NASA describes spacecraft communications in terms of uplink, downlink, and crosslink, and notes that RF and optical systems are complementary because optical links can be blocked by clouds. ([NASA][5])

Friis transmission:

$$
P_r = P_t G_t G_r \left(\frac{\lambda}{4\pi R}\right)^2
$$

In decibels:

$$
P_r\,[\mathrm{dBW}] = P_t + G_t + G_r
- L_{\mathrm{FS}} - L_{\mathrm{atm}} - L_{\mathrm{rain}}
- L_{\mathrm{pointing}} - L_{\mathrm{polarization}} - L_{\mathrm{implementation}}
$$

Free-space path loss:

$$
L_{\mathrm{FS}}\,[\mathrm{dB}] = 20 \log_{10}\!\left(\frac{4\pi R}{\lambda}\right)
$$

Aperture-antenna gain:

$$
G = \eta_{\mathrm{ap}} \left(\frac{\pi D}{\lambda}\right)^2
\qquad
G_{\mathrm{dBi}} = 10 \log_{10}(G)
$$

Approximate beamwidth:

$$
\theta_{\mathrm{HPBW}} \approx k\,\frac{\lambda}{D}
$$

Noise and link margin:

$$
N_0 = k_B T_{\mathrm{sys}}
\qquad
\frac{C}{N_0} = \frac{P_r}{k_B T_{\mathrm{sys}}}
\qquad
\frac{E_b}{N_0} = \frac{C/N_0}{R_b}
$$

$$
M_{\mathrm{link}} = \left(\frac{E_b}{N_0}\right)_{\mathrm{available}} - \left(\frac{E_b}{N_0}\right)_{\mathrm{required}}
$$

Report RF links as pass/fail with margin (e.g. "Ka downlink: +3.2 dB clear sky, −5.4 dB rain case"). Do not treat RF bandwidth as free: higher bandwidth pushes toward higher frequencies, narrower beams, more pointing sensitivity, rain fade, and larger or more efficient apertures.

## 8. Laser / optical communication equations

Optical links use a similar power-budget structure, but the physics is aperture diffraction, pointing, atmospheric loss, detector sensitivity, and acquisition/tracking.

Diffraction-limited divergence and spot radius at range $R$:

$$
\theta \approx 1.22\,\frac{\lambda}{D_t}
\qquad
w \approx R \theta
$$

Approximate geometric coupling:

$$
\eta_{\mathrm{geo}} \approx \left(\frac{D_r}{2 R \theta}\right)^2
$$

Received optical power:

$$
P_r = P_t \cdot \eta_t \cdot \eta_r \cdot \eta_{\mathrm{geo}}
\cdot \eta_{\mathrm{pointing}} \cdot \eta_{\mathrm{atm}} \cdot \eta_{\mathrm{coding}}
$$

Photon energy and photons per bit:

$$
E_{\gamma} = \frac{hc}{\lambda}
\qquad
N_{\gamma/\mathrm{bit}} = \frac{P_r}{R_b} \cdot \frac{\lambda}{hc}
$$

Optical link margin and pointing loss (Gaussian-beam model):

$$
M_{\mathrm{optical}} = P_{r,\mathrm{dB}} - P_{\mathrm{sens,dB}} - L_{\mathrm{margin,dB}}
$$

$$
\eta_{\mathrm{pointing}} \approx \exp\!\left(-2\,\frac{\theta_{\mathrm{err}}^2}{\theta_{\mathrm{beam}}^2}\right)
$$

Orbital AI clusters need large internal bandwidth. Google's Suncatcher work highlights free-space optical links, close satellite formations, and crosslink rates in the tens of terabits per second as a core system challenge. ([Google Research][4])

Model two optical regimes separately:

| Link type                         | Main constraint                                               |
| --------------------------------- | ------------------------------------------------------------- |
| Inter-satellite optical crosslink | range, pointing, aperture, terminal power, formation geometry |
| Satellite-ground optical downlink | clouds, atmosphere, site diversity, access windows            |

Do not let users assume one optical ground station gives continuous availability; ground links need weather and site-diversity modeling.

## 9. Network and distributed-compute equations

A data center is not just many GPUs; the network has to support the workload.

$$
B_{\mathrm{req}} = C_{\mathrm{delivered}} \cdot I_{\mathrm{comm}}
\qquad
B_{\mathrm{req}} \le B_{\mathrm{available}}
$$

Where $I_{\mathrm{comm}}$ is bits transferred per unit compute (bits/FLOP or bits/token).

Latency:

$$
t_{\mathrm{prop}} = \frac{R}{c}
\qquad
t_{\mathrm{comm}} = t_{\mathrm{prop}} + t_{\mathrm{serialization}} + t_{\mathrm{queue}} + t_{\mathrm{protocol}}
\qquad
t_{\mathrm{serialization}} = \frac{N_{\mathrm{bits}}}{R_b}
$$

Distributed-training speedup (approximate):

$$
S(N) = \frac{N}{1 + \alpha (N-1) + \beta\,\dfrac{B_{\mathrm{model}}}{B_{\mathrm{network}}}}
$$

Where $\alpha$ is parallel overhead, $\beta$ is the communication penalty, $B_{\mathrm{model}}$ is the model/gradient communication burden, and $B_{\mathrm{network}}$ is available interconnect bandwidth.

Make network bottlenecks explicit, and distinguish **space-native workloads** (compact outputs) from **Earth-dependent workloads** (large input/output movement).

## 10. Reliability, radiation, and availability equations

Exponential reliability:

$$
R(t) = e^{-\lambda t}
\qquad
P_{\mathrm{fail}}(t) = 1 - e^{-\lambda t}
\qquad
N_{\mathrm{surviving}}(t) = N_0\, e^{-\lambda t}
$$

Availability:

$$
A = \frac{MTBF}{MTBF + MTTR}
$$

In space, $MTTR$ is not "send a technician" — it may be reset time, graceful degradation, spare activation, or replacement-launch cadence.

Radiation total ionizing dose and single-event upsets:

$$
D_{\mathrm{TID}} = \int_0^T \dot{D}(t)\,dt
\qquad
R_{\mathrm{SEU}} = \int \Phi(E)\,\sigma_{\mathrm{SEU}}(E)\,dE
\qquad
N_{\mathrm{SEU}} = R_{\mathrm{SEU}} \cdot t \cdot N_{\mathrm{devices}}
$$

Where $\Phi(E)$ is the particle flux spectrum and $\sigma_{\mathrm{SEU}}(E)$ is the device upset cross-section.

Useful compute after failures:

$$
C_{\mathrm{reliable}} = C_{\mathrm{delivered}} \cdot A \cdot (1 - f_{\mathrm{degraded}})
$$

Start with empirical failure-rate parameters and uncertainty ranges. Do not predict modern GPU/HBM radiation behavior from first principles without data; model radiation as a scenario and sensitivity driver until calibrated. Google has reported TPU radiation testing under Project Suncatcher, but that evidence is hardware-specific and should not be generalized to every GPU, HBM stack, memory controller, optical terminal, or power converter. ([Google Research][4])

## 11. Cost equations

Lifecycle cost:

$$
C_{\mathrm{life}} = C_{\mathrm{capex}} + C_{\mathrm{launch}} + C_{\mathrm{ops}}
+ C_{\mathrm{replacement}} + C_{\mathrm{ground}} + C_{\mathrm{deorbit}} - C_{\mathrm{residual}}
$$

Launch and hardware:

$$
C_{\mathrm{launch}} = m_{\mathrm{launch}} \cdot c_{\$/\mathrm{kg}}
$$

$$
C_{\mathrm{sat}} = c_{\mathrm{bus}} + c_{\mathrm{solar}} P_{\mathrm{solar}}
+ c_{\mathrm{radiator}} A_{\mathrm{rad}} + c_{\mathrm{battery}} E_{\mathrm{batt}}
+ c_{\mathrm{comms}} + c_{\mathrm{integration}}
$$

$$
C_{\mathrm{accel}} = N_{\mathrm{accel}} \cdot c_{\mathrm{accel}}
$$

Cost per delivered compute:

$$
\text{\\$/GPU-hr} = \frac{C_{\mathrm{life}}}
{N_{\mathrm{GPU,equiv}} \cdot 8760 \cdot T_{\mathrm{years}} \cdot A \cdot U}
$$

$$
\text{\\$/useful PFLOP-day} = \frac{C_{\mathrm{life}}}{C_{\mathrm{delivered}} \cdot T_{\mathrm{mission}}}
$$

Levelized cost of compute:

$$
LCOC = \frac{\sum_t \dfrac{C_t}{(1+r)^t}}{\sum_t \dfrac{C_{\mathrm{delivered},t}}{(1+r)^t}}
$$

Use levelized cost, not just capex: space systems look better or worse depending on mission life, degradation, failure rate, replacement cadence, and utilization. Separate accelerator cost from spacecraft/platform cost — the same GPU or TPU may be required on Earth and in space, so whether to include it depends on the comparison.

## 12. Earth data-center baseline equations

$$
P_{\mathrm{facility}} = P_{\mathrm{IT}} \cdot PUE
$$

PUE is total facility power (or energy) divided by IT equipment power (or energy). ([Vertiv][6])

$$
C_{\mathrm{energy}} = P_{\mathrm{facility}} \cdot 8760 \cdot T_{\mathrm{years}} \cdot c_{\$/\mathrm{kWh}} \cdot U
$$

$$
W_{\mathrm{water}} = E_{\mathrm{facility}} \cdot WUE
$$

$$
CO_2e = E_{\mathrm{grid}} \cdot CI_{\mathrm{grid}} + CO_{2e,\mathrm{embodied}}
$$

Earth delivered compute:

$$
C_{\mathrm{earth,delivered}} = C_{\mathrm{peak}} \cdot f_{\mathrm{sustained}} \cdot A_{\mathrm{earth}} \cdot U_{\mathrm{earth}}
$$

Use multiple Earth baselines: average leased colocation; modern hyperscale; renewable-heavy solar/wind + storage; gas-backed high-availability; constrained-grid expensive-power. Do not compare space against a straw-man Earth data center — best-in-class terrestrial facilities have very good PUE, mature maintenance, supply chains, redundancy, and cheap repair access.

## 13. Environmental equations

Space is not automatically "green"; it shifts the burdens.

$$
CO_{2e,\mathrm{op}} = E_{\mathrm{source}} \cdot CI
\qquad
CO_{2e,\mathrm{embodied}} = \sum_i m_i \cdot EF_i
$$

$$
CO_{2e,\mathrm{launch}} = m_{\mathrm{propellant}} \cdot EF_{\mathrm{propellant}} + CO_{2e,\mathrm{manufacturing}}
$$

Compute- and water-normalized:

$$
\frac{CO_{2e}}{\text{useful compute}}
= \frac{CO_{2e,\mathrm{embodied}} + CO_{2e,\mathrm{launch}} + CO_{2e,\mathrm{ops}}}
{C_{\mathrm{delivered,lifetime}}}
\qquad
\frac{L_{\mathrm{water}}}{\mathrm{Mtoken}}\ \text{or}\ \frac{L_{\mathrm{water}}}{\mathrm{GPU\text{-}hr}}
$$

Include environmental accounting, but label it lower-confidence unless good embodied-carbon and launch-emissions datasets are available. "Powered by sunlight" does not equal low total environmental impact.

## 14. Optimization formulation

$$
\min_x\ J(x)
$$

Candidate objectives:

$$
J_1 = \frac{C_{\mathrm{life}}}{C_{\mathrm{delivered,lifetime}}}
\qquad
J_2 = \frac{m_{\mathrm{launch}}}{P_{\mathrm{IT,delivered}}}
\qquad
J_3 = \frac{CO_{2e}}{C_{\mathrm{delivered,lifetime}}}
\qquad
J_4 = -A_{\mathrm{system}}
$$

Subject to:

$$
\begin{aligned}
P_{\mathrm{load}} &\le P_{\mathrm{available,EOL}} \\
Q_{\mathrm{generated}} &\le Q_{\mathrm{rejected}} \\
T_{\mathrm{junction}} &\le T_{\max} \\
B_{\mathrm{required}} &\le B_{\mathrm{available}} \\
M_{\mathrm{RF}} &\ge M_{\mathrm{RF,min}} \\
M_{\mathrm{optical}} &\ge M_{\mathrm{optical,min}} \\
m_{\mathrm{launch}} &\le m_{\mathrm{vehicle,max}} \\
A_{\mathrm{availability}} &\ge A_{\min} \\
P_{\mathrm{collision}} &\le P_{\mathrm{collision,max}}
\end{aligned}
$$

OpenMDAO is a good backbone for multidisciplinary optimization with analytic derivatives, coupled systems, and integration of high-fidelity analyses. ([OpenMDAO][7])

Support design of experiments for beginners, Pareto frontiers for trade studies, gradient-based optimization for smooth problems, evolutionary or Bayesian optimization for mixed discrete/continuous architecture choices, and Monte Carlo plus sensitivity analysis for uncertain assumptions. Do not force everything into one optimizer; early-stage architecture work needs exploration more than false precision.

## 15. Minimum equation set for v0.1

Implement these as tested components first:

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

## 16. What to avoid in early versions

* Full CFD or finite-element thermal modeling as a core dependency.
* Detailed radiation transport as a core dependency.
* High-fidelity orbital conjunction analysis as a core dependency.
* Vendor-specific GPU performance claims as default sustained performance.
* One "space beats Earth" calculator result.
* Assuming optical links have continuous ground availability.
* Assuming launch cost falls to speculative values without uncertainty ranges.
* Assuming all IT power is useful compute.
* Assuming power closure implies thermal closure.

These can become plugins or advanced modules later.

## Bottom line

The space-data-center problem is governed by a chain:

$$
\text{useful compute}
\rightarrow \text{power}
\rightarrow \text{heat}
\rightarrow \text{radiator area}
\rightarrow \text{mass}
\rightarrow \text{launch cost}
\rightarrow \text{lifetime delivered compute}
$$

The key equations are not exotic: conservation of energy, Stefan-Boltzmann radiation, link budgets, orbital geometry, reliability, and levelized cost. The hard part is coupling them honestly. Make the default output not "the answer" but a constraint diagnosis:

```text
This design is power-feasible.
This design is not thermally feasible.
The binding constraint is radiator mass.
Space beats Earth only below $X/kg launch cost,
above Y W/kg solar specific power,
below Z kg/kW radiator mass,
and above U% utilization.
```

[1]: https://www.nvidia.com/en-us/data-center/h100/ "H100 GPU | NVIDIA"
[2]: https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/ "3.0 Power - NASA"
[3]: https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/ "7.0 Thermal Control - NASA"
[4]: https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/ "Exploring a space-based, scalable AI infrastructure system design"
[5]: https://www.nasa.gov/smallsat-institute/sst-soa/soa-communications/ "9.0 Communications - NASA"
[6]: https://www.vertiv.com/en-us/about/news-and-events/articles/educational-articles/what-is-pue-power-usage-effectiveness-and-what-does-it-measure/ "What Is PUE (Power Usage Effectiveness)?"
[7]: https://openmdao.org/ "OpenMDAO | An open-source framework for efficient multidisciplinary optimization"
