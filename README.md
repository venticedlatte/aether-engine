# Aether Engine

**Coupled multiphysics simulation engine for photonic integrated circuits under extreme environments.**

Thermal. Structural. Electromagnetic. One solver chain. Sub-second wall time.

Aether, couples three physics domains for photonic ICs in a single run.

---

## Why this matters

Photonic chips are being deployed in hypersonic vehicles, LEO satellites, cryogenic quantum systems, and radiation-hardened defense platforms. Every one of these environments changes how the chip behaves:

- **Heat** shifts refractive index (thermo-optic effect)
- **Thermal stress** warps waveguide geometry and induces birefringence (photoelastic effect)
- **CTE mismatch** between thin-film layers generates hundreds of MPa of mechanical stress

These effects interact. You cannot simulate them separately and add the results, the coupling is nonlinear. A resonance shift from thermal expansion changes the stress field, which changes the index, which changes the resonance.

Aether solves the coupled system.

---

## Results

### Material comparison: Mach 5 hypersonic flight (30 km altitude)

| Material Stack | Thermal Stress | Index Change | Resonance Shift | Verdict |
|---|---|---|---|---|
| **SOI 220nm** | 24.8 MPa | +0.006461 | +2.384 nm | PASS |
| **SiN** | 45.8 MPa | +0.000976 | +0.360 nm | PASS |
| **LNOI** | 203.0 MPa | +0.001656 | +0.611 nm | PASS |
| **InP** | 0.0 MPa | +0.006919 | +2.553 nm | PASS |

**Key finding:** LNOI (thin-film lithium niobate) develops **8x more thermal stress** than SOI under identical flight conditions. This is driven by LiNbO₃'s CTE of 15.4×10⁻⁶ /K vs SiO₂'s 0.55×10⁻⁶ /K - a 28x mismatch that becomes critical in defense thermal environments.

This is directly relevant to programs developing domestic TFLN photonic capability for defense applications.

### LNOI stress vs Mach number

```
  Mach 2  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   43.8 MPa
  Mach 3  █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   98.6 MPa
  Mach 4  █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  175.2 MPa
  Mach 5  ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░  273.8 MPa
  Mach 6  ████████████████████░░░░░░░░░░░░░░░░░░░░░  394.3 MPa
  Mach 7  ███████████████████████████░░░░░░░░░░░░░░  536.7 MPa
  Mach 8  ███████████████████████████████████░░░░░░░  701.0 MPa
```

LNOI CTE mismatch stress scales quadratically with Mach number. At Mach 8, film stress reaches **701 MPa**, approaching the fracture strength of lithium niobate thin films (~1 GPa). This predicts delamination risk for TFLN photonics on high-Mach platforms without stress mitigation.

### Environment sweep: SOI 220nm across operating conditions

| Environment | Peak ΔT | Thermal Stress | Resonance Shift | Verdict |
|---|---|---|---|---|
| Ambient (lab bench) | +0.0 K | 0.0 MPa | +0.000 nm | PASS |
| Hypersonic Mach 3 | +31.3 K | 15.2 MPa | +1.457 nm | PASS |
| Hypersonic Mach 5 | +51.3 K | 24.8 MPa | +2.384 nm | PASS |
| Hypersonic Mach 6 | +99.6 K | 48.2 MPa | +4.631 nm | PASS |
| LEO orbit (550 km, 5 yr) | +100.0 K | 48.4 MPa | +3.885 nm | PASS |
| Cryogenic (4 K) | +289.1 K | 140.0 MPa | −11.235 nm | PASS |

### Cryogenic comparison: all stacks at 4 K

| Material Stack | Thermal Stress | Resonance Shift | Verdict |
|---|---|---|---|
| **SOI 220nm** | 140.0 MPa | −11.235 nm | PASS |
| **SiN** | 258.2 MPa | −1.696 nm | PASS |
| **LNOI** | 1145.0 MPa | −2.880 nm | **WARN** |
| **InP** | 0.0 MPa | −12.031 nm | PASS |

**Key finding:** LNOI at cryogenic temperatures develops **1.15 GPa** of thermal stress from cooldown. This exceeds typical thin-film adhesion limits and predicts delamination for standard TFLN-on-insulator stacks cooled to liquid helium temperatures without compensating buffer layers.

### LNOI vs SOI: coupled domain breakdown (Mach 5)

```
                        SOI 220nm          LNOI
                        ─────────          ────
  Peak ΔT              +51.3 K            +51.3 K        (same environment)
  CTE mismatch         2.05×10⁻⁶ /K      14.85×10⁻⁶ /K  (7.2x larger)
  Thermal stress       24.8 MPa           203.0 MPa       (8.2x larger)
  dn (thermo-optic)    +0.006282          +0.001128       (Si has higher dn/dT)
  dn (photoelastic)    +0.000100          −0.000239       (opposite sign - compressive)
  dn (total)           +0.006461          +0.001656
  Resonance shift      +2.384 nm          +0.611 nm
  Insertion loss       1.00 dB            0.02 dB
```

The photoelastic effect in LNOI is **compressive** (negative dn) while SOI is tensile (positive dn) - they push the effective index in opposite directions. This is not captured by single-domain thermal or structural simulation alone.

---

## Full solver output

```
========================================================================
  AETHER ENGINE Coupled Multiphysics Analysis Report
========================================================================

Environment:  Hypersonic Mach 6.0, 25.0 km
              Stagnation temp 1030 K, chip ΔT 45 K behind TPS.

--- Thermal → Structural ---------------------------------
  Peak dT:              +99.6 K
  Thermal stress:       48.2 MPa

--- Electromagnetic --------------------------------------
  dn (thermo-optic):    +0.012203
  dn (photoelastic):    +0.000194
  dn (total):           +0.012549
  Resonance shift:      +4.631 nm
  Width change:         +0.067 nm
  Height change:        +0.015 nm
  Insertion loss (est): 1.00 dB

--- Verdict ----------------------------------------------
  Result:               PASS

  Solver chain:   Thermal → Structural → Electromagnetic
  Wall time:      <1 ms
========================================================================
```

---

## Solver chain

```
Environment model
  │  Atmospheric heating, orbital thermal cycling, cryogenic cooldown,
  │  radiation dose, vibration PSD, directed energy flux
  ▼
Thermal field solver
  │  Steady-state 2D diffusion → peak ΔT at waveguide core
  ▼
Structural mechanics
  │  CTE mismatch → biaxial film stress (Stoney 1909)
  │  Thermal expansion → waveguide geometry change
  ▼
Electromagnetic coupling
  │  Thermo-optic:   Δn = dn/dT × ΔT
  │  Photoelastic:   Δn = −n³/2 · (p₁₁ε₁ + p₁₂(ε₂+ε₃))
  │  Geometry:       Δn_eff from width/height perturbation
  ▼
Device-level prediction
     Resonance shift, insertion loss, coupling change, pass/fail
```

---

## Physics references

Every equation uses peer-reviewed coefficients cited inline in the source:

| Domain | Equation | Reference |
|---|---|---|
| Thermo-optic | Δn = dn/dT × ΔT | Cocorullo et al., J. Appl. Phys. 86, 3281 (1999) |
| Photoelastic | Δn = −n³/2·(p₁₁ε₁ + p₁₂(ε₂+ε₃)) | Biegelsen, Phys. Rev. B 9(5), 2635 (1974) |
| Film stress | σ = E·Δα·ΔT/(1−ν) | Stoney, Proc. R. Soc. Lond. A 82, 172 (1909) |
| Waveguide sensitivity | ∂n_eff/∂w | Bogaerts & Chrostowski, Laser Photonics Rev. 12 (2018) |
| Material properties | Si, SiO₂, Si₃N₄, LiNbO₃, InP | NIST, Salzberg & Villa 1957, Malitson 1965, Okada & Tokumaru 1984 |

---

## Supported environments

| Environment | Key physics | Use case |
|---|---|---|
| Hypersonic | Stagnation heating, aerodynamic vibration | Photonic sensors on Mach 3–8 vehicles |
| LEO Orbit | Thermal cycling, radiation, vacuum | Satellite quantum key distribution |
| Cryogenic | Deep cooldown from 300 K | SNSPD operation, quantum photonics |
| Thermal Cycling | MIL-STD-883 qualification profiles | Reliability screening |
| Radiation | Total ionizing dose (TID) | Nuclear-hardened photonics |
| Directed Energy | Laser/RF heating | DEW survivability analysis |
| High Vibration | Random vibration PSD | Launch vehicle, turbine mount |
| Ambient | Lab bench baseline | Reference measurement |

## Supported material stacks

| Stack | Core layer | Platform | CTE mismatch | dn/dT |
|---|---|---|---|---|
| SOI 220nm | Si on SiO₂ | AIM Photonics | 2.05×10⁻⁶ /K | 1.86×10⁻⁴ /K |
| SiN | Si₃N₄ on SiO₂ | Ultra-low loss | 2.65×10⁻⁶ /K | 2.45×10⁻⁵ /K |
| LNOI | LiNbO₃ on SiO₂ | Electro-optic | 14.85×10⁻⁶ /K | 4.0×10⁻⁵ /K |
| InP | InP on InP | Active devices | 0 /K | 2.0×10⁻⁴ /K |

---

## Status

**Core engine:** Complete. Validated against literature.

**Code release:** Coming soon. Star or watch this repo for updates.

---

## License

Apache 2.0

---

Built by [Project Aether]. Contact: contact@aeroza.dev
