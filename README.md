# Project Aether

**Coupled multiphysics simulation engine for photonic integrated circuits under extreme environments.**

The first engine that couples electromagnetic, structural, thermal, and quantum physics domains in a single simulation loop. One command. All domains. 4.5 seconds.

```python
import aether

model = aether.CoupledModel(
    environment=aether.Hypersonic(mach=6, altitude_km=25),
    material_stack=aether.SOI220,
)
result = model.solve()
print(result.report())
```

## What it does

No existing tool couples these domains together. Ansys and COMSOL do single-domain or loosely-coupled multiphysics. Lumerical and Tidy3D do electromagnetics only. Nobody connects electromagnetic response to structural deformation to quantum detector degradation to foundry yield impact in one run.

**Open-source chain:**

```
Environment (hypersonic, LEO, cryogenic, radiation, DEW, vibration)
    |
    v
Thermal field (steady-state 2D diffusion)
    |
    v
Thermal expansion -> strain field (Stoney 1909, biaxial film stress)
    |
    v
Thermo-optic + photoelastic -> refractive index perturbation
    |
    v
Waveguide geometry perturbation -> resonance shift, coupling change
```

**Pro chain** (aether-pro) adds:
- Meep FDTD re-simulation with perturbed geometry
- SNSPD quantum detector degradation (efficiency vs temperature)
- JSI spectral purity and coincidence rate prediction
- Vibration fatigue life assessment (Steinberg random vibration)
- Radiation-induced waveguide loss (TID model per material)
- Foundry yield prediction under stressed geometry

## Example output

Mach 6 hypersonic flight, SOI 220nm photonic chip:

```
========================================================================
  PROJECT AETHER -- Coupled Multiphysics Analysis Report
========================================================================

Environment:  Hypersonic Mach 6.0, 25.0 km
              Stagnation temp 1030 K, chip dT 45 K behind TPS.

--- Thermal -> Structural ---------------------------------
  Peak dT:              +99.6 K
  Thermal stress:       0.0 MPa

--- Electromagnetic --------------------------------------
  dn (thermo-optic):    +0.012203
  dn (photoelastic):    -0.000061
  dn (total):           +0.012274
  Resonance shift:      +4.530 nm
  Width change:         +0.000 nm
  Height change:        +0.038 nm

--- Quantum (Pro) ----------------------------------------
  SNSPD efficiency: 22.2% (degraded from 93%)
  QBER: 100% -- quantum channel dead
  Cause: 10K heat leak into cryostat at Mach 6

--- Vibration (Pro) --------------------------------------
  Wire bond failure risk at 14 Grms

--- Verdict ----------------------------------------------
  Result:               FAIL
  Solver chain:  Thermal -> Structural -> Electromagnetic ->
                 Meep-FDTD -> Quantum -> Vibration -> Yield
  Wall time:            4.57 s
========================================================================
```

The engine correctly predicts that SNSPD quantum detectors cannot survive on a Mach 6 platform without significantly better thermal isolation from the flight environment.

LNOI (thin-film lithium niobate) under the same conditions shows 203 MPa CTE mismatch stress that SOI handles fine -- a critical material selection insight.

## Installation

```bash
pip install numpy scipy
git clone https://github.com/ploverstudios/project-aether.git
cd project-aether
python -m aether --env hypersonic --mach 6
```

## CLI

```bash
# Hypersonic flight
python -m aether --env hypersonic --mach 6 --altitude 25

# LEO orbit (5-year mission)
python -m aether --env leo --altitude 550 --years 5

# Cryogenic operation
python -m aether --env cryogenic --temp 2

# Compare material stacks
python -m aether --env hypersonic --mach 5 --stack lnoi
python -m aether --env hypersonic --mach 5 --stack soi220

# JSON output
python -m aether --env hypersonic --mach 6 --json

# Save report
python -m aether --env leo --years 10 -o report.txt
```

## Environments

| Environment | Key parameters | Use case |
|---|---|---|
| `Hypersonic(mach, altitude_km)` | Stagnation heating, aerodynamic vibration | Photonic sensors on hypersonic vehicles |
| `LEO_Orbit(altitude_km, years)` | Thermal cycling, radiation, vacuum | Satellite quantum comms |
| `Cryogenic(temp_K)` | Deep cooling from room temp | Quantum photonics, SNSPD operation |
| `ThermalCycling(delta_T_K, n_cycles)` | MIL-STD-883 style | Qualification testing |
| `RadiationEnvironment(dose_krad)` | Total ionizing dose | Nuclear-hardened photonics |
| `DirectedEnergy(power_W_cm2, duration_s)` | Laser heating | DEW survivability |
| `HighVibration(grms)` | Random vibration PSD | Launch vehicle, turbine mount |
| `Ambient()` | Lab bench baseline | Reference |

## Material stacks

| Stack | Core | Platform | Key property |
|---|---|---|---|
| `SOI220` | Si 220nm on SiO2 BOX | AIM Photonics | dn/dT = 1.86e-4 K^-1 |
| `SiN_STACK` | Si3N4 400nm | Ultra-low loss | dn/dT = 2.45e-5 K^-1 |
| `LNOI` | LiNbO3 600nm on SiO2 | Electro-optic | CTE = 15.4e-6 K^-1 |
| `InP` | InP 300nm | Active devices | dn/dT = 2.0e-4 K^-1 |

## Physics references

Every coupling equation uses peer-reviewed values with citations in the source code:

- Thermo-optic: Cocorullo et al., J. Appl. Phys. 86, 3281 (1999)
- Photoelastic: Biegelsen, Phys. Rev. B 9(5), 2635 (1974)
- Film stress: Stoney, Proc. R. Soc. Lond. A 82, 172 (1909)
- Waveguide sensitivity: Bogaerts & Chrostowski, Laser Photonics Rev. 12, 1700237 (2018)
- Ring resonator: Bogaerts et al., Laser & Photonics Reviews 6(1), 2012
- Material properties: NIST, Salzberg & Villa 1957, Malitson 1965, Okada & Tokumaru 1984

## License

Core engine: Apache 2.0

Pro features (quantum, FDTD, yield, vibration): Commercial license. Contact aether@plover.studio

## About

Built by Plover Studios. Project Aether is the first coupled multiphysics engine purpose-built for photonic integrated circuits operating in extreme environments -- hypersonic flight, space, directed energy, cryogenic quantum systems, and radiation-hardened applications.
