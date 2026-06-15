# spacedc-mdao

Multidisciplinary design analysis and optimization (MDAO) of orbital compute
infrastructure, with terrestrial data-center baselines for comparison.

The package optimizes **delivered useful compute**, not nominal watts or nominal
GPUs. It takes installed capacity and degrades it through power, thermal,
network, reliability, and utilization limits, then reports where a design fails
and which assumptions decide the outcome. Its job is to make the feasibility
boundary visible — not to argue that space wins.

```
C_delivered = C_peak · f_software · f_power · f_thermal · f_network · f_availability · f_utilization
```

Every default number is a provenance-tagged assumption (value, units, source,
date, confidence). For the bundled 1 MW text-inference scenario, Earth wins on
levelized cost — the orbital design is limited by optical-downlink availability
and the launch, radiator, and station-keeping mass it carries.

## Where to go next

- **[Quick start](quickstart.md)** — install and run the first comparison.
- **[User tiers](tiers.md)** — from a one-line CLI compare to custom catalogs.
- **[Model architecture](architecture.md)** — how the disciplines couple.
- **[Governing equations](equations.md)** — the physics behind each factor.
- **[Assumptions & provenance](provenance.md)** — every default, sourced.
- **[API reference](api.md)** — the public Python surface.
