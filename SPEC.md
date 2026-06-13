Below is how I’d spec this if the goal is a credible open-source package, not a “space data centers are inevitable” hype calculator.

The core design principle: **optimize delivered useful compute-years, not nominal watts or nominal GPUs**. Space only becomes interesting if it can beat Earth after launch mass, radiator mass, solar-array mass, batteries, utilization, failure rates, interconnect limits, ground-link limits, mission life, and replacement cadence. That framing matches the better current analyses: Google’s Project Suncatcher is explicitly studying TPUs, free-space optical links, orbital dynamics, and radiation effects; McCalip’s calculator reduces the economics to cost per usable compute watt; and a 2026 orbital-data-center paper frames feasibility around delivered IT power, kg/kW, communication intensity, utilization, and lifetime penalties. ([Google Research][1])

## Recommended package concept

Call it something like **`orbitdc`** or **`spacedc-mdao`**:

> An open-source Python package for multidisciplinary design analysis and optimization of orbital compute infrastructure, with comparable terrestrial data-center baselines.

It should support three user levels:

**Beginner mode:** YAML scenarios, built-in assumptions, calculator-style notebooks, Pareto plots, and “why did this design fail?” diagnostics.

**Power-user mode:** Python API with swappable models, uncertainty sweeps, Monte Carlo, sensitivity analysis, and custom optimizers.

**Advanced MDAO mode:** derivative-aware OpenMDAO components, coupled multidisciplinary solves, constrained optimization, surrogate models, and plugin hooks for high-fidelity thermal, orbital, RF, laser, and cost tools.

I would **not** build a custom optimizer framework from scratch. Use **OpenMDAO** as the main MDAO backbone because it is already an open-source framework for multidisciplinary optimization with analytic derivatives and integration of high-fidelity analyses. Use **GPkit** optionally for fast convex/geometric-programming trade studies where the physics can be expressed cleanly as monomial/posynomial constraints. Use **poliastro/Astropy** for orbital mechanics, units, coordinate transforms, and quick orbit visualization. ([OpenMDAO][2])

## The main comparison question

The package should answer:

> For a target workload, mission life, and service quality, what is the all-in cost, mass, energy, communication capacity, reliability, and environmental footprint of delivering one useful unit of compute from space versus Earth?

The most important output metrics should be:

| Metric                                                        | Why it matters                                                                                                                                                                                                                                          |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **$/delivered GPU-hour** or **$/accelerator-hour**            | Closest to how customers buy compute.                                                                                                                                                                                                                   |
| **$/useful PFLOP-day** or **$/useful TOPS-year**              | Better for hardware-neutral comparisons.                                                                                                                                                                                                                |
| **$/million tokens** or **joules/token**                      | More relevant for inference workloads than peak FLOPS.                                                                                                                                                                                                  |
| **Delivered IT power, MW**                                    | The denominator for almost every economic comparison.                                                                                                                                                                                                   |
| **Specific delivered power, W/kg**                            | Space economics are brutally mass-driven.                                                                                                                                                                                                               |
| **kg/kW delivered IT**                                        | Often clearer than W/kg for spacecraft sizing.                                                                                                                                                                                                          |
| **Radiator area per kW and radiator kg/kW**                   | Thermal rejection may be a first-order constraint, not a footnote.                                                                                                                                                                                      |
| **Solar-array W/kg and m²/kW**                                | Solar is the main advantage of orbit, but area, pointing, degradation, and structure matter. NASA notes that real spacecraft solar arrays cluster around roughly 30 W/kg, with an empirical upper bound near 200 W/kg in its cited dataset. ([NASA][3]) |
| **Sunlit fraction / eclipse duty cycle**                      | Drives battery mass, utilization, and thermal cycling.                                                                                                                                                                                                  |
| **Effective utilization**                                     | Nominal installed compute is irrelevant if thermal throttling, communication bottlenecks, or outages reduce usable compute.                                                                                                                             |
| **Annual accelerator failure rate**                           | Replacement is expensive in space; technicians cannot swap dead servers in five minutes.                                                                                                                                                                |
| **Communication intensity: bits moved per joule or per FLOP** | Determines whether the workload is space-native, edge-like, or hopelessly ground-dependent.                                                                                                                                                             |
| **Crosslink and downlink margin**                             | Distributed AI requires enormous inter-satellite bandwidth; Google’s Suncatcher work discusses links in the tens-of-terabits-per-second regime and very close satellite formations to close the link budget. ([Google Research][1])                     |
| **Latency and jitter**                                        | Matters for interactive inference, less for batch training or space-native processing.                                                                                                                                                                  |
| **PUE, WUE, CUE equivalent**                                  | Needed for Earth comparison. PUE and WUE are standard data-center efficiency metrics, and PUE is the ratio of total site power to IT power. ([Microsoft Datacenters][4])                                                                                |
| **Cost of avoided terrestrial constraints**                   | Grid interconnection, land, permitting, water, power contracts, and carbon intensity.                                                                                                                                                                   |

The package should avoid comparing “space solar power” to “bad Earth data center.” Terrestrial baselines should include best-in-class hyperscale cases. For example, Google reports fleet-wide PUE values around 1.08–1.10 in recent quarters, so a space design should not benchmark itself only against a mediocre PUE 1.5 facility. ([Google Data Centers][5])

## Critical model families to include

### 1. System-level mission model

This should define the mission architecture:

```yaml
scenario:
  name: "1 MW orbital inference cluster"
  mission_life_years: 5
  orbit:
    type: "dawn_dusk_sso"
    altitude_km: 650
    inclination_deg: auto
  workload:
    type: "llm_inference"
    target_tokens_per_second: 1.0e6
    communication_intensity_bits_per_token: 2000
  architecture:
    satellites: 64
    accelerators_per_satellite: 8
    crosslink: "optical"
    ground_link: ["optical", "rf_backup"]
```

It should produce a mission-level accounting table:

```text
Installed compute
→ thermally allowable compute
→ power-available compute
→ network-limited compute
→ reliability-adjusted compute
→ utilization-adjusted delivered compute
```

That waterfall is more useful than one headline cost number.

### 2. Compute model

Include GPUs, TPUs, ASICs, and future custom accelerators as data-driven objects:

```python
Accelerator(
    name="NVIDIA H100 SXM",
    tdp_w=700,
    fp16_tflops=1979,
    fp8_tflops=3958,
    memory_gb=80,
    memory_bandwidth_tb_s=3.35,
    mass_kg=None,
    radiation_model="user_defined"
)
```

NVIDIA lists H100 SXM at up to 700 W configurable TDP, 80 GB memory, 3.35 TB/s memory bandwidth, and high advertised tensor throughput; those values are useful as catalog defaults, but the package should distinguish **peak marketing throughput** from **sustained workload throughput**. ([NVIDIA][6])

Recommended compute submodels:

* Peak FLOPS/TOPS model.
* Sustained workload model: training, inference, embedding, Earth-observation preprocessing, batch simulation.
* Performance-per-watt curves.
* Thermal throttling curves.
* Memory-capacity and bandwidth limits.
* Interconnect overhead model.
* Radiation fault model: TID, single-event upsets, memory errors, reset rates, degraded nodes.
* Useful-output model: tokens/s, images/s, simulations/day, or custom user-defined units.

The package should support **space-native workloads** separately from **Earth-user workloads**. Space-native examples include Earth-observation preprocessing, satellite fleet autonomy, compression, event detection, and in-orbit inference. These are much more plausible early uses than “replace a Virginia hyperscale AI training cluster tomorrow.”

### 3. Power model

Include:

* Solar flux versus orbit and attitude.
* Solar-array area.
* Solar-array efficiency.
* Beginning-of-life and end-of-life degradation.
* Power electronics efficiency.
* Battery sizing for eclipse.
* Peak versus average IT load.
* Non-IT spacecraft loads: avionics, comms, pointing, pumps, heaters, station-keeping.
* Margin policy.

Key outputs:

```text
PV area
PV mass
battery mass
delivered bus power
delivered IT power
specific power W/kg
kg/kW delivered IT
```

The package should make **specific power** a first-class variable. NASA’s small-spacecraft power discussion explicitly says specific power fundamentally governs mission feasibility and flexibility, which is exactly the right framing for this problem. ([NASA][3])

### 4. Thermal model

This is where hype often breaks. Space is not “cold air cooling.” It is vacuum. Heat leaves mainly through radiation, so high-power compute needs large radiator area, good heat spreading, and careful view-factor/orientation design.

The package should include a low-order thermal balance:

```text
solar heating + albedo + planet IR + internal heat
=
stored heat + radiated heat
```

NASA’s spacecraft thermal-control overview frames spacecraft temperature exactly this way: absorbed solar, albedo, planet IR, internal generated heat, stored heat, and radiated heat must balance. ([NASA][7])

Recommended thermal model tiers:

**Tier 0: scalar radiator sizing**

```text
Q_rejected ≈ ε σ A_rad η_view (T_rad^4 − T_sink^4)
```

Use this for fast trade studies.

**Tier 1: lumped thermal network**

Nodes for GPU die, HBM, cold plate, heat pipe/fluid loop, radiator panel, spacecraft bus, solar array, and environment.

**Tier 2: orbit-transient thermal**

Time-dependent solar, albedo, Earth IR, eclipse, attitude, thermal capacitance, throttling, and survival heaters.

**Tier 3: plugin interface**

Allow coupling to external high-fidelity tools later without making them mandatory.

Important thermal metrics:

* Radiator m²/kW.
* Radiator kg/kW.
* Max chip junction temperature.
* HBM temperature margin.
* Thermal throttling fraction.
* Pump/heat-pipe power.
* Hot/cold survival margin.
* Radiator view-factor penalty.
* Thermal cycling fatigue proxy.

The package should also model compute architectures differently. A recent Space-CIM paper argues that thermally constrained space platforms may favor architectures with more uniform heat generation than conventional GPU/HBM layouts, so the package should not hard-code “GPU rack in orbit” as the only future architecture. ([arXiv][8])

### 5. Orbit, formation, and station-keeping model

Include:

* LEO, SSO, dawn-dusk SSO, MEO, GEO scenario presets.
* Sunlit fraction.
* Eclipse fraction.
* Atmospheric drag.
* J2 perturbation.
* Formation drift.
* Collision-avoidance margin.
* Station-keeping Δv.
* Propellant mass.
* End-of-life deorbit or disposal.
* Ground-station access windows.

For beginner mode, use simple orbit presets. For advanced mode, expose poliastro/Astropy integrations.

Google’s Suncatcher writeup is useful here because it explicitly treats close satellite formations, hundreds-of-meter separations, J2/non-sphericity, atmospheric drag, and station-keeping as part of the design problem. ([Google Research][1])

### 6. RF and antenna model

Even if the main compute fabric uses lasers, the package should include RF because RF remains important for telemetry, command, backup links, weather-resilient ground communications, emergency modes, and some user-service architectures.

RF model features:

* Uplink, downlink, and crosslink modes.
* Frequency band.
* Bandwidth.
* EIRP.
* Antenna gain.
* Aperture / phased-array size.
* Beamwidth.
* Pointing loss.
* Polarization loss.
* Free-space path loss.
* Atmospheric loss.
* Rain fade for higher bands.
* Link margin.
* Data rate.
* Spectrum/licensing notes as non-numeric metadata.

NASA’s communications overview divides spacecraft communications into uplink, downlink, and crosslink, and notes both RF and free-space optical systems. That maps cleanly into the package model. ([NASA][9])

Beginner output should look like:

```text
RF TT&C link margin: +9.4 dB
Ka-band downlink margin: +3.1 dB clear sky, -4.8 dB rain case
Required antenna aperture: 0.35 m
RF subsystem mass: 18 kg
RF subsystem power: 220 W
```

### 7. Laser / free-space optical model

Laser links should be first-class, not an afterthought.

Include:

* Inter-satellite optical crosslinks.
* Ground optical downlinks.
* Wavelength.
* Aperture diameter.
* Transmit optical power.
* Beam divergence.
* Pointing, acquisition, and tracking error.
* Receiver aperture.
* Detector sensitivity.
* Atmospheric attenuation.
* Cloud/weather availability for ground links.
* Modulation/coding.
* DWDM channel count.
* Spatial multiplexing.
* Link margin.
* Energy per bit.
* Terminal mass, power, cost.
* Thermal load from laser terminals.
* Formation-distance sensitivity.

This matters because orbital AI clusters need internal bandwidth. Google’s writeup says data-center-scale inter-satellite links may require tens of Tbps and that received power scales inversely with distance squared, motivating close formations. ([Google Research][1]) Free-space optical communication is also widely discussed as a way to reduce size, weight, and power while increasing bandwidth versus RF, though it adds pointing and weather constraints for ground links. ([arXiv][10])

### 8. Cost and business model

Separate costs into:

**Space capex**

* Accelerator cost.
* Server/compute payload cost.
* Satellite bus cost.
* Solar-array cost.
* Battery cost.
* Radiator cost.
* RF terminal cost.
* Optical terminal cost.
* Structure/deployment cost.
* Integration and test.
* Launch cost.
* Insurance.
* Ground segment.
* Replacement launches.
* Deorbit/disposal.

**Space opex**

* Mission operations.
* Ground stations.
* Cloud service operations.
* Failures and spares.
* Fleet management.
* Collision avoidance.
* Customer networking.
* Data egress.

**Earth baseline capex/opex**

* Land.
* Building shell.
* Electrical infrastructure.
* Cooling plant.
* Backup generation or storage.
* Grid interconnection.
* Power purchase agreement.
* Water.
* Staffing.
* Servers/accelerators.
* Network.
* Maintenance.
* Taxes, incentives, and depreciation.

Do **not** bake in one launch price. Treat launch cost as a scenario distribution: pessimistic, current public-ish, aggressive reusable, and speculative. Google’s Suncatcher post says its analysis suggests launch prices might fall below $200/kg by the mid-2030s, but that is a scenario, not a law of physics. ([Google Research][1])

### 9. Reliability, radiation, and maintainability

The package needs reliability modeling from day one.

Include:

* Component failure rates.
* Radiation environment by orbit.
* TID dose model.
* Single-event upset model.
* ECC/scrubbing mitigation.
* Reset/retry model.
* Graceful degradation.
* Spare capacity.
* Replacement cadence.
* Mission life.
* Accelerator survival curve.
* Availability and SLA.

Google reported proton-beam testing of Trillium TPU hardware and noted HBM as the more sensitive subsystem, with no hard failures attributable to total ionizing dose up to the tested dose on a single chip; that is promising, but it should be treated as hardware-specific evidence, not a universal “GPUs work fine in space” conclusion. ([Google Research][1])

## Package architecture

Recommended structure:

```text
orbitdc/
  core/
    units.py
    schema.py
    scenario.py
    registry.py
    assumptions.py
  data/
    accelerators/
    launch/
    solar_arrays/
    batteries/
    radiators/
    antennas/
    optical_terminals/
    earth_datacenters/
    cost_indices/
  models/
    compute.py
    power.py
    thermal.py
    orbit.py
    formation.py
    rf.py
    lasercom.py
    reliability.py
    cost.py
    earth_baseline.py
    environmental.py
  mdao/
    openmdao_components.py
    drivers.py
    constraints.py
    objectives.py
  optimize/
    doe.py
    pareto.py
    uncertainty.py
    sensitivity.py
    surrogate.py
  viz/
    dashboard.py
    pareto.py
    sankey.py
    thermal.py
    orbit3d.py
    constellation_graph.py
    link_budget.py
    cost_waterfall.py
  examples/
    notebooks/
    scenarios/
  cli.py
```

Use:

* `pydantic` for validated input schemas.
* `pint` or Astropy units for units.
* `numpy`, `scipy`, `pandas`, `polars` for analysis.
* `openmdao` for coupled MDAO.
* `gpkit` for optional convex trade studies.
* `poliastro` / `astropy` for orbital mechanics.
* `plotly`, `altair`, `pyvista`, `networkx`, and `panel` for visualization.
* `SALib` or equivalent for sensitivity analysis.
* `pytest` with regression tests against known examples.

## First-class visualization capabilities

This package should be as much an **engineering exploration environment** as an optimizer.

Minimum visualizations:

1. **Earth-vs-space cost waterfall**
   Launch, satellite hardware, solar, radiator, battery, comms, ground segment, replacement, operations, and accelerator cost.

2. **Delivered compute waterfall**
   Installed compute → power-limited → thermal-limited → network-limited → reliability-adjusted → utilization-adjusted.

3. **Mass treemap**
   Compute, radiator, solar, batteries, structure, comms, propulsion, shielding, margin.

4. **Power Sankey**
   Solar input → conversion losses → bus power → IT load → comms → pumps → thermal rejection.

5. **Thermal constraint plot**
   Radiator area versus allowable IT power, with chip temperature margin and throttling regions.

6. **Orbit timeline**
   Sunlight, eclipse, battery state of charge, temperature, compute throttling, ground access.

7. **Constellation graph**
   Satellites as nodes, RF/laser links as edges, bandwidth and margin encoded visually.

8. **RF/laser link-budget heatmap**
   Link margin versus range, aperture, pointing error, wavelength, and weather case.

9. **Pareto frontier**
   $/GPU-hour versus kg/kW versus availability versus latency.

10. **Tornado sensitivity chart**
    Launch $/kg, radiator kg/kW, solar W/kg, failure rate, utilization, satellite $/W, energy price, PUE, and ground power price.

11. **Uncertainty fan chart**
    Probability distribution for space beating Earth under user-defined assumptions.

12. **Assumption provenance panel**
    Every default number should show source, date, confidence, and whether it is empirical, vendor-stated, estimated, or speculative.

That last one is crucial. The package should make bad assumptions visible.

## Recommended model tiers

Use tiered models so beginners are not overwhelmed and advanced users are not boxed in.

| Tier       | Purpose                        | Example                                                       |
| ---------- | ------------------------------ | ------------------------------------------------------------- |
| **Tier 0** | Calculator-level sanity checks | Scalar W/kg, $/W, radiator m²/kW                              |
| **Tier 1** | Engineering trade studies      | Lumped thermal, link budgets, orbit presets                   |
| **Tier 2** | Coupled MDAO                   | OpenMDAO components with constraints and derivatives          |
| **Tier 3** | High-fidelity plugins          | External thermal, orbital, EM, or network simulators          |
| **Tier 4** | Empirical calibration          | Fit parameters from flight data, lab tests, or benchmark logs |

The default should be Tier 1. Tier 0 is too easy to misuse; Tier 3 is too slow for broad trade studies.

## MVP scope

The first credible MVP should include:

1. Terrestrial baseline model with PUE, WUE, energy price, capex $/MW, accelerator cost, and utilization.
2. Orbital scalar model with launch $/kg, satellite $/W, W/kg, mission life, failure rate, and utilization.
3. Solar-array sizing.
4. Radiator sizing.
5. Battery sizing for eclipse.
6. Simple RF link budget.
7. Simple optical crosslink budget.
8. Accelerator catalog with H100-like, TPU-like, and generic ASIC entries.
9. Monte Carlo and tornado sensitivity.
10. Pareto frontier dashboard.
11. Assumption provenance.

Do **not** start with formation-flying dynamics, detailed radiation transport, or full thermal finite-element modeling. Those are important, but they are not the MVP. The MVP wins by making first-order physics and economics impossible to hand-wave.

## Example beginner workflow

```python
import orbitdc as odc

space = odc.scenarios.load("orbital_1mw_inference.yaml")
earth = odc.scenarios.load("earth_hyperscale_baseline.yaml")

result = odc.compare(space, earth)

result.summary()
result.plot_cost_waterfall()
result.plot_delivered_compute_waterfall()
result.plot_pareto(["launch_cost_per_kg", "radiator_specific_mass", "solar_specific_power"])
result.explain_binding_constraints()
```

Expected output:

```text
Space case does not close.

Binding constraints:
1. Radiator area exceeds packaging limit by 38%.
2. Optical downlink limits useful utilization to 42%.
3. Replacement cadence dominates cost after year 4.
4. Space beats Earth only if launch < $240/kg, radiator < 6 kg/kW,
   annual accelerator failure < 4%, and utilization > 72%.
```

That kind of diagnostic is far more valuable than “space cost = $12.1B.”

## Optimization formulation

Example objective functions:

```text
minimize total_cost / delivered_compute_years
minimize launch_mass / delivered_IT_power
minimize radiator_area / delivered_IT_power
maximize useful_compute_per_kg
maximize availability
minimize carbon_per_compute_unit
minimize water_per_compute_unit
```

Core constraints:

```text
P_IT + P_comms + P_avionics + P_thermal <= P_solar_EOL * availability_factor
Q_generated <= Q_radiator_allowed
T_junction <= T_junction_max
battery_SOC_min >= reserve_margin
link_margin_rf >= required_margin
link_margin_optical >= required_margin
crosslink_bandwidth >= workload_required_bandwidth
downlink_bandwidth >= required_output_bandwidth
annual_failure_loss <= spare_capacity
launch_mass <= vehicle_capacity
deorbit_probability >= policy_threshold
```

The package should support multi-objective Pareto optimization, not just one “best” answer.

## Key tradeoffs to expose

**Solar power versus radiator area**
More compute requires more power, but nearly all IT power becomes heat. Solar is attractive in orbit; heat rejection is the bill.

**Higher radiator temperature versus chip reliability**
Hotter radiators reject more heat per m², but chips, HBM, batteries, and electronics have temperature limits.

**Close formations versus collision/station-keeping risk**
Close satellites help optical bandwidth but increase formation-control and safety requirements.

**Laser links versus RF links**
Lasers offer high bandwidth and lower SWaP for many cases, but require tight pointing and can suffer ground-weather availability issues. RF is lower-bandwidth but robust and essential for TT&C.

**Bigger satellites versus smaller modular satellites**
Bigger platforms may improve packaging and thermal integration. Smaller modules improve manufacturing, replacement, and graceful degradation.

**Space-native compute versus Earth-dependent compute**
If the workload requires huge Earth uplink/downlink, space loses quickly. If data is generated in space or output is compact, the case improves.

**Peak compute versus useful compute**
A satellite full of accelerators is not useful if it is power-limited, radiator-limited, link-limited, or constantly recovering from faults.

**Launch cost versus spacecraft cost**
Falling launch cost helps, but it does not eliminate radiator, solar, comms, reliability, manufacturing, and operations costs.

## My recommendation

Build this as a **transparent MDAO + visualization package**, not a single calculator. The best first release should be a rigorous assumption-exploration tool that lets users ask: “Under what assumptions does space beat Earth, and which assumptions are doing the work?”

The package should be skeptical by default. Its job is not to prove orbital data centers are viable. Its job is to make the feasibility boundary visible. The most important design choice is to report **binding constraints and sensitivity**, because the feasibility of space-based data centers is likely dominated by a small set of uncertain parameters: launch $/kg, satellite $/W, solar W/kg, radiator kg/kW, useful utilization, communication intensity, failure rate, and mission life.

[1]: https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/ "Exploring a space-based, scalable AI infrastructure system design"
[2]: https://openmdao.org/ "OpenMDAO.org | An open-source framework for efficient multidisciplinary optimization."
[3]: https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/ "3.0 Power - NASA"
[4]: https://datacenters.microsoft.com/sustainability/efficiency/ "Measuring energy and water efficiency for Microsoft datacenters - Microsoft Datacenters"
[5]: https://datacenters.google/efficiency "Power usage effectiveness – Google Data Centers"
[6]: https://www.nvidia.com/en-us/data-center/h100/ "H100 GPU | NVIDIA"
[7]: https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/ "7.0 Thermal Control - NASA"
[8]: https://arxiv.org/abs/2606.05741?utm_source=chatgpt.com "Space-CIM: Enabling Compute-In-Memory Accelerators for Thermally-Constrained Space Platforms"
[9]: https://www.nasa.gov/smallsat-institute/sst-soa/soa-communications/ "9.0 Communications - NASA"
[10]: https://arxiv.org/abs/2012.13166?utm_source=chatgpt.com "Free-space optical links for space communication networks"
