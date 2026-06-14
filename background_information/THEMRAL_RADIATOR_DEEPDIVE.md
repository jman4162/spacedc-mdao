# Thermal radiator deep dive

Your skepticism is exactly where the package should get more rigorous. For space-based data centers, **thermal rejection is not an auxiliary subsystem**. It is likely one of the dominant feasibility constraints, alongside launch cost, solar specific power, reliability, and communications.

The key framing:

> Space gives you abundant solar energy, but it does **not** give you easy cooling. In vacuum, you do not get atmospheric convection or evaporative cooling. You must conduct heat from chips into a thermal transport system and ultimately radiate it away through large surfaces.

NASA's SmallSat thermal guidance states the core issue plainly: in vacuum, heat transfer is by radiation and conduction, not convection, and external heat exchange is driven by thermal radiation. It also emphasizes radiator optical properties: high infrared emissivity and low solar absorptivity are the desired "radiator properties." ([NASA][1])

## 1. Core conclusion for the research packet

Make **thermal radiator feasibility** a first-class module in the package, not a secondary calculation.

The package should be able to answer questions like:

* How many square meters of radiator are needed per MW of IT load?
* How much radiator mass per delivered kW?
* What radiator temperature is required to make the design close?
* Can the chip/HBM junction temperatures stay within limits?
* How much does one-sided solar exposure hurt net heat rejection?
* How much thermal throttling occurs over an orbit?
* What happens if the radiator is degraded, contaminated, micrometeoroid-damaged, or partially shadowed?
* Does a GPU/HBM architecture close thermally, or do space-specific accelerator layouts perform better?

That last point matters. A recent Space-CIM paper argues that standard GPU/HBM layouts can create severe thermal hotspots under limited radiator capacity, while compute-in-memory accelerators can offer more uniform heat generation and better performance under radiator constraints. ([arXiv][2])

## 2. The physics wall: radiator area scales brutally

The first-order equation is Stefan-Boltzmann radiation:

$$
Q_{\mathrm{rad}} = \epsilon \sigma A \left(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4\right)
$$

For a flat radiator in space, the net heat rejection should be modeled as emitted radiation minus absorbed solar, albedo, and planet IR:

$$
Q_{\mathrm{net}} = N_{\mathrm{sides}}\,\epsilon \sigma A \left(T_{\mathrm{rad}}^4 - T_{\mathrm{sink}}^4\right)
- \alpha A S \cos\theta_{\odot}
- \alpha A F_{\oplus} A_{\mathrm{alb}} S
- \epsilon A F_{\oplus} \sigma T_{\oplus}^4
$$

Where:

* $N_{\mathrm{sides}}$: one-sided or two-sided radiation.
* $\epsilon$: infrared emissivity.
* $\alpha$: solar absorptivity.
* $S$: solar irradiance.
* $F_{\oplus}$: Earth view factor.
* $A_{\mathrm{alb}}$: Earth albedo.
* $T_{\mathrm{rad}}$: radiator temperature.
* $T_{\oplus}$: effective Earth IR temperature.
* $T_{\mathrm{sink}}$: deep-space sink temperature, often approximated near 3 K but not sufficient by itself because the radiator may see Sun/Earth.

A Lumen Orbit/Starcloud white paper uses this same accounting: emitted radiation from both sides, minus absorbed sunlight, Earth albedo, and Earth IR, yielding a claimed net radiator rejection of about 633 W/m² at a 20 °C radiator temperature under their assumptions. Treat that as an **optimistic design case**, not a universal constant. ([StarCloud][3])

## 3. Quick sanity-check numbers

Using a simplified ideal radiator with $\epsilon = 0.9$, perfect view to deep space, and no solar/Earth absorption, the one-sided gray-body heat rejection looks roughly like this:

| Radiator temperature | Heat rejected | Area for 1 MW |
| -------------------: | ------------: | ------------: |
|         300 K / 27 °C |     ~413 W/m² |     ~2,420 m² |
|         320 K / 47 °C |     ~535 W/m² |     ~1,870 m² |
|         350 K / 77 °C |     ~766 W/m² |     ~1,306 m² |
|        400 K / 127 °C |   ~1,306 W/m² |       ~765 m² |
|        500 K / 227 °C |   ~3,190 W/m² |       ~314 m² |
|        600 K / 327 °C |   ~6,614 W/m² |       ~151 m² |

This table explains the whole problem. If the radiator must run near electronics-friendly temperatures, the area is huge. If you can raise radiator temperature, the $T^4$ term helps dramatically — but now you need heat pumps, higher-temperature fluids, higher chip/cold-plate temperatures, or larger temperature lifts from chips to radiator. That may improve area but adds mass, complexity, parasitic power, reliability risk, and thermal-interface challenges.

For a data center, nearly all IT electrical power becomes waste heat. A 1 MW orbital compute module is therefore roughly a 1 MW thermal rejection problem before adding solar absorption, power electronics losses, pumps, comms, batteries, and margin.

## 4. Why ISS is a useful reality check

The ISS is not an orbital AI data center, but it is a good sanity check because it shows what real active space thermal control looks like: pumped loops, heat exchangers, ammonia, rotating radiators, redundancy, valves, accumulators, sensors, and freeze protection. NASA's ISS ATCS overview says the External Active Thermal Control System uses mechanically pumped ammonia loops to collect, transport, and reject heat through external radiators. It also states the EATCS is designed for 35 kW per loop, 70 kW total. ([NASA][4])

The ISS photovoltaic radiator example is also sobering: one deployable PVR rejects up to 14 kW, weighs 740.7 kg, and deploys to about 3.12 m by 13.6 m. That is not a state-of-the-art future data-center radiator, but it is a useful "heritage hardware" anchor for mass and complexity. ([NASA][4])

NASA also describes each EATCS radiator ORU as a deployable eight-panel system, with each ORU measuring 23.3 m by 3.4 m and weighing 1,122.64 kg; the full system uses rotating radiator wings and ammonia flow paths. ([NASA][4])

The implication: **future orbital data-center radiators must be much lighter, more deployable, more area-efficient, and more integrated than ISS-style hardware**. That is possible in principle, but it should be modeled as a major technology assumption.

## 5. Recommended fidelity ladder for the package

Implement thermal modeling in layers.

### Level 0 — scalar radiator sanity check

Purpose: beginner calculator and fast feasibility screening.

Inputs: IT power, radiator temperature, emissivity, absorptivity, one-sided/two-sided radiation, sun exposure, Earth view factor, albedo, Earth IR, area density (kg/m²), margin.

Outputs: radiator area, radiator mass, net W/m², kg/kW, "thermal closes?" flag.

Equations:

$$
A_{\mathrm{rad}} = \frac{Q_{\mathrm{waste}}}{q_{\mathrm{net}}}
\qquad
m_{\mathrm{rad}} = A_{\mathrm{rad}}\,\rho_{A,\mathrm{rad}}
\qquad
\frac{m}{P} = \frac{m_{\mathrm{rad}}}{P_{\mathrm{IT}}}
$$

This level should be intentionally conservative and should show "idealized / optimistic / heritage" presets.

### Level 1 — orbital environmental heat balance

Purpose: capture why radiator orientation and orbit matter.

NASA's thermal design training frames spacecraft thermal analysis from conservation of energy: stored heat equals heat in minus heat out plus generated heat, with conduction and radiation paths forming the basis of spacecraft thermal analysis. ([NASA Technical Reports Server][5])

$$
m C_p \frac{dT}{dt} = Q_{\mathrm{solar}}(t) + Q_{\mathrm{albedo}}(t) + Q_{\mathrm{planetIR}}(t)
+ Q_{\mathrm{internal}}(t) - Q_{\mathrm{radiated}}(t)
$$

Include: beta angle, eclipse, dawn-dusk SSO, Earth view factor, Sun incidence angle, radiator articulation, partial self-shadowing, transient thermal mass, hot case and cold case.

NASA's thermal design course emphasizes stacking worst-case hot and cold parameters, using margin, applying power-growth allowances, and tracking thermo-optical property degradation. ([NASA Technical Reports Server][5])

### Level 2 — lumped thermal network

Purpose: model chip-to-radiator paths rather than assuming a uniform radiator plate.

Represent the system as thermal nodes:

```text
GPU die / HBM / cold plate / coolant loop / manifold / heat pipe / radiator panel / space
```

For each node:

$$
C_i \frac{dT_i}{dt} = Q_i + \sum_j G_{ij}(T_j - T_i)
+ \sum_j \epsilon \sigma A_i F_{ij}\left(T_j^4 - T_i^4\right)
$$

Conductive paths and contact/interface paths:

$$
Q_{\mathrm{cond}} = k A \frac{\Delta T}{L}
\qquad
Q_{\mathrm{contact}} = h_c A\,\Delta T
$$

Thermal resistance stack:

$$
T_{\mathrm{junction}} = T_{\mathrm{rad}} + Q_{\mathrm{chip}}
\left(R_{\mathrm{jc}} + R_{\mathrm{TIM}} + R_{\mathrm{coldplate}} + R_{\mathrm{transport}} + R_{\mathrm{radiator}}\right)
$$

This is where you can see if the radiator is big enough but the die still overheats because the heat cannot spread or transport fast enough.

### Level 3 — active coolant-loop model

Purpose: model direct-to-chip liquid cooling, two-phase loops, pumped loops, and radiator headers.

For single-phase coolant, required mass flow, and pump power:

$$
Q = \dot{m} c_p (T_{\mathrm{out}} - T_{\mathrm{in}})
\qquad
\dot{m} = \frac{Q}{c_p \Delta T}
\qquad
P_{\mathrm{pump}} = \frac{\Delta p\,\dot{V}}{\eta_{\mathrm{pump}}}
$$

For two-phase cooling:

$$
Q \approx \dot{m} h_{fg} + \dot{m} c_p \Delta T
$$

Why include this: the Lumen/Starcloud white paper specifically discusses transferring heat from compute modules to radiators using several cooling loops, using two-phase systems where practical to reduce mass-flow requirements and pumping losses. It also discusses direct-to-chip liquid cooling or two-phase immersion cooling within compute modules. ([StarCloud][3])

### Level 4 — radiator geometry, view factors, and ray tracing

Purpose: capture real deployment geometry.

Include: one-sided vs two-sided radiation, blocked view to space, self-viewing radiator panels, panel-to-panel radiation, radiator-to-solar-array view, Earth and Sun view factors, articulated radiator pointing, thermal gradients across large flexible panels, finite conductance in deployable hinges, degradation of surface optical properties.

View factors matter because a radiator that "has area" but sees solar arrays, Earth, or itself does not behave like an ideal plate radiating into 3 K deep space.

This is where you would add optional Monte Carlo ray tracing or hemicube view-factor calculation.

### Level 5 — degradation, damage, and reliability

Purpose: model lifetime delivered heat rejection, not beginning-of-life heat rejection.

Include: emissivity degradation, absorptivity increase from contamination or UV exposure, micrometeoroid/orbital debris punctures, coolant leaks, stuck valves, pump failures, heat-pipe dryout or non-condensable gas, thermal cycling fatigue, radiator deployment failure, freeze/thaw risks, partial panel isolation.

NASA's ISS ATCS design uses independent loops, physical separation, flow isolation, and reduced-capacity operation after failures, which is a strong hint that reliability architecture matters as much as raw W/m². ([NASA][4])

## 6. Specific research questions to prioritize

### A. What is the realistic net W/m² for an orbital data-center radiator?

Not "blackbody to 3 K," but emitted minus absorbed:

$$
q_{\mathrm{net}} = q_{\mathrm{emit}} - q_{\mathrm{absorbed}}
$$

Compare scenarios:

| Case                      | Description                                                    |
| ------------------------- | -------------------------------------------------------------- |
| Ideal                     | two-sided, deep-space view, no Sun/Earth                       |
| Good engineering          | low-$\alpha$, high-$\epsilon$, articulated, low Earth view     |
| Starcloud-like optimistic | two-sided, one side sun-exposed, low absorptivity              |
| Conservative LEO          | Earth IR/albedo, sun exposure, self-view, degraded coating     |
| Failure/degraded          | partial deployment, increased absorptivity, reduced emissivity |

### B. What radiator temperature is actually allowable?

The package should not let users set $T_{\mathrm{rad}}$ independently from chip temperature.

$$
T_{\mathrm{chip}} = T_{\mathrm{rad}} + Q R_{\mathrm{total}}
$$

A high radiator temperature is great for area, but it may require either high chip temperature, excellent thermal transport, or active heat pumping. For GPUs/HBM, memory thermal limits and hotspots may bind before the radiator average temperature does.

### C. How much mass does the radiator really add?

Use a mass build-up:

$$
m_{\mathrm{thermal}} = m_{\mathrm{panels}} + m_{\mathrm{headers}} + m_{\mathrm{fluid}}
+ m_{\mathrm{pumps}} + m_{\mathrm{valves}} + m_{\mathrm{accumulators}} + m_{\mathrm{sensors}}
+ m_{\mathrm{deployment}} + m_{\mathrm{structure}} + m_{\mathrm{armor}} + m_{\mathrm{margin}}
$$

NASA has funded work on lightweight high-temperature heat-rejection radiators for space nuclear systems, including specific mass below 3 kg/m² for foldable heat-pipe radiator panels operating around 500–600 K. That technology is relevant, but note the catch: high-temperature nuclear-electric radiators are not automatically compatible with low-temperature GPU/HBM thermal limits. ([NASA][6])

### D. What architecture reduces thermal pain?

Research architecture alternatives: GPU/HBM direct-to-chip cold plates, GPU/HBM immersion modules, compute-in-memory accelerators, lower-power custom ASICs, distributed low-power accelerator tiles, high-temperature-tolerant electronics, radiator-integrated compute tiles, modular "compute leaf + radiator leaf" structures.

The Space-CIM paper is especially relevant because it argues that thermal uniformity can matter as much as peak TOPS/W in space. ([arXiv][2])

## 7. Recommended package modules for deeper radiator modeling

A dedicated namespace:

```text
orbitdc.thermal/
  radiation.py
  environment.py
  radiator.py
  coatings.py
  thermal_network.py
  coolant_loop.py
  heat_pipe.py
  cold_plate.py
  chip_package.py
  reliability.py
  degradation.py
  view_factors.py
  monte_carlo_raytrace.py
  validation_cases.py
```

Core data classes:

```python
RadiatorSurface(
    area_m2,
    sides=2,
    emissivity_ir=0.90,
    absorptivity_solar=0.08,
    areal_density_kg_m2=3.0,
    max_temp_K=350,
    view_factor_space=0.85,
    view_factor_earth=0.10,
    view_factor_self=0.05,
    degradation_model="coating_uv_atomic_oxygen"
)

CoolantLoop(
    fluid="ammonia",
    mode="single_phase",
    mass_flow_kg_s=...,
    cp_j_kg_k=...,
    delta_p_pa=...,
    pump_efficiency=...,
    freeze_temp_K=...
)

ChipThermalStack(
    chip_power_w=700,
    r_junction_to_case_K_W=...,
    r_tim_K_W=...,
    r_coldplate_K_W=...,
    t_junction_max_K=...
)
```

## 8. Validation anchors

| Validation case                         | Why useful                                                           |
| --------------------------------------- | -------------------------------------------------------------------- |
| Ideal blackbody plate                   | Checks Stefan-Boltzmann implementation.                              |
| Starcloud/Lumen white-paper example     | Good for reproducing an optimistic published orbital-DC calculation. |
| ISS PVR                                 | Real deployed radiator mass/area/heat-rejection sanity check.        |
| ISS EATCS                               | Real active pumped-loop architecture sanity check.                   |
| NASA thermal course single-node balance | Checks energy conservation and transient solver.                     |
| SmallSat deployable radiator examples   | Useful intermediate scale.                                           |
| High-temperature NASA radiator concepts | Bounds future lightweight radiator assumptions.                      |

For the Starcloud/Lumen example, explicitly mark it as "company white paper / optimistic scenario." Their assumptions include two-sided radiation, low absorptivity, and a 20 °C radiator producing a claimed net 633 W/m² after absorbed sunlight and Earth terms. ([StarCloud][3])

## 9. Thermal dashboard

The thermal dashboard should have these panels:

1. **Radiator area versus IT power**
2. **Radiator area versus radiator temperature**
3. **Net W/m² waterfall** — emitted radiation minus solar absorption, Earth IR, albedo, self-view penalty.
4. **Chip-to-radiator temperature ladder** — junction → package → cold plate → coolant → radiator.
5. **Thermal bottleneck diagnosis** — chip-limited, coolant-limited, transport-limited, radiator-limited, orientation-limited.
6. **Orbit timeline** — Sun exposure, Earth view, radiator temperature, chip temperature, throttling.
7. **Mass waterfall** — panels, fluid, pumps, valves, structure, deployment, armor, margin.
8. **Pareto frontier** — kg/kW versus radiator temperature versus chip temperature margin.
9. **Sensitivity tornado** — emissivity, absorptivity, radiator temperature, area density, view factor, pump power, coolant ΔT.
10. **Assumption provenance table** — source, confidence, empirical/theoretical/speculative, date.

## 10. The main gotchas to encode

These are the mistakes the package should prevent:

* Treating deep space as "cold air."
* Ignoring absorbed sunlight on sun-exposed radiators.
* Assuming all radiator area has perfect view to space.
* Treating radiator temperature as independent of chip temperature.
* Ignoring HBM hotspots.
* Counting two-sided radiation when one side faces a warm or sunlit structure.
* Ignoring coolant-loop mass and pump power.
* Ignoring degradation of $\alpha/\epsilon$ over mission life.
* Using beginning-of-life thermal closure instead of end-of-life thermal closure.
* Ignoring partial failure, leak isolation, or deployment failure.
* Comparing futuristic lightweight radiators against average terrestrial cooling rather than best-in-class Earth data centers.

## 11. Recommendation

Make the next major package milestone a **radiator-in-the-loop co-design module** before adding more economic complexity.

The minimum credible model should couple:

$$
\text{chip power} \rightarrow \text{junction temperature} \rightarrow \text{coolant loop}
\rightarrow \text{radiator temperature} \rightarrow \text{radiator area}
\rightarrow \text{radiator mass} \rightarrow \text{launch cost} \rightarrow \text{delivered compute cost}
$$

The best version should tell the user:

```text
This design fails thermally because radiator area closes only at 390 K,
but the chip/HBM thermal stack requires radiator inlet temperature below 325 K.

Binding constraints:
1. HBM junction temperature
2. radiator net W/m^2 after sun exposure
3. coolant-loop mass flow
4. deployable radiator areal density
5. end-of-life coating degradation
```

That is the level of diagnostic depth needed for this domain. Your skepticism is warranted because **thermal closure is where optimistic space-data-center economics can quietly fail**. The package should make that failure mode obvious, quantified, and traceable.

[1]: https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/ "7.0 Thermal Control - NASA"
[2]: https://arxiv.org/abs/2606.05741 "Space-CIM: Enabling Compute-In-Memory Accelerators for Thermally-Constrained Space Platforms"
[3]: https://starcloudinc.github.io/wp.pdf "Why we should train AI in space - White Paper"
[4]: https://www.nasa.gov/wp-content/uploads/2021/02/473486main_iss_atcs_overview.pdf "ATCS Team Overview"
[5]: https://ntrs.nasa.gov/api/citations/20230003714/downloads/Thermal%20Design%20for%20Spaceflight.pptx.pdf "Thermal Design for Spaceflight"
[6]: https://www.nasa.gov/directorates/stmd/space-tech-research-grants/advanced-lightweight-heat-rejection-radiators-for-space-nuclear-power-systems/ "Advanced Lightweight Heat Rejection Radiators for Space Nuclear Power Systems - NASA"
