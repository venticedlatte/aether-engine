"""
Multi-domain material property database.

Every material carries electromagnetic, thermal, mechanical, and
quantum-relevant properties so that the coupling layer can translate
between physics domains without guesswork.

Sources cited inline (peer-reviewed or NIST).
"""

from __future__ import annotations

import dataclasses as _dc
from typing import Optional


@_dc.dataclass(frozen=True)
class Material:
    """Single material with cross-domain properties."""

    name: str

    # --- Electromagnetic ---
    n: float                          # refractive index @ 1550 nm
    dn_dT: float = 0.0               # thermo-optic coeff [K⁻¹]
    k_extinction: float = 0.0        # extinction coefficient @ 1550 nm
    loss_dB_cm: float = 0.0          # propagation loss [dB/cm]

    # --- Photoelastic (Biegelsen 1974 for Si) ---
    p11: float = 0.0                 # strain-optic tensor component
    p12: float = 0.0

    # --- Thermal ---
    k_thermal: float = 1.0           # thermal conductivity [W/(m·K)]
    alpha_CTE: float = 0.0           # coefficient of thermal expansion [K⁻¹]
    specific_heat: float = 700.0     # [J/(kg·K)]

    # --- Mechanical ---
    E_GPa: float = 70.0              # Young's modulus [GPa]
    nu_poisson: float = 0.28         # Poisson's ratio
    density_kg_m3: float = 2330.0    # [kg/m³]
    yield_MPa: float = 7000.0        # fracture / yield strength [MPa]

    # --- Quantum-relevant ---
    T_c_K: Optional[float] = None    # superconducting critical temp [K]
    bandgap_eV: Optional[float] = None

    def n_at_T(self, delta_T: float) -> float:
        """Refractive index shifted by thermo-optic effect."""
        return self.n + self.dn_dT * delta_T

    def delta_n_strain(self, eps_xx: float, eps_yy: float, eps_zz: float) -> float:
        """Photoelastic index change (isotropic approximation).

        Δn = -n³/2 · (p₁₁·ε₁ + p₁₂·(ε₂ + ε₃))
        Ref: Biegelsen, Phys. Rev. B 9, 5 (1974).
        """
        return -(self.n ** 3) / 2.0 * (
            self.p11 * eps_xx + self.p12 * (eps_yy + eps_zz)
        )

    def thermal_strain(self, delta_T: float) -> float:
        """Isotropic thermal strain ε = α·ΔT."""
        return self.alpha_CTE * delta_T


# ── Predefined materials (peer-reviewed values) ──────────────────────

Si = Material(
    name="Si",
    n=3.478,                       # Salzberg & Villa 1957
    dn_dT=1.86e-4,                 # Cocorullo et al. 1999
    loss_dB_cm=2.0,                # typical SOI 220 nm
    p11=-0.094,                    # Biegelsen 1974
    p12=0.017,
    k_thermal=148.0,               # NIST
    alpha_CTE=2.6e-6,              # Okada & Tokumaru 1984
    specific_heat=712.0,
    E_GPa=170.0,                   # [110] direction
    nu_poisson=0.28,
    density_kg_m3=2329.0,
    yield_MPa=7000.0,              # single-crystal fracture
    bandgap_eV=1.12,
)

SiO2 = Material(
    name="SiO2",
    n=1.444,                       # Malitson 1965
    dn_dT=1.0e-5,                  # Ghosh 1997
    k_thermal=1.38,
    alpha_CTE=0.55e-6,
    specific_heat=730.0,
    E_GPa=73.0,
    nu_poisson=0.17,
    density_kg_m3=2200.0,
    yield_MPa=8400.0,              # fused silica
)

SiN = Material(
    name="Si3N4",
    n=1.996,                       # Luke et al. 2015
    dn_dT=2.45e-5,                 # Arbabi et al. 2013
    loss_dB_cm=0.1,                # ultra-low-loss SiN
    k_thermal=20.0,
    alpha_CTE=3.3e-6,
    specific_heat=700.0,
    E_GPa=250.0,
    nu_poisson=0.23,
    density_kg_m3=3170.0,
    yield_MPa=14000.0,
)

NbN = Material(
    name="NbN",
    n=4.2,                         # approximate at 1550 nm (Semenov 2009)
    dn_dT=0.0,                     # superconductor — N/A above gap
    k_extinction=5.82,             # lossy below 2·Δ
    k_thermal=3.0,                 # thin film
    alpha_CTE=10.0e-6,
    E_GPa=300.0,
    nu_poisson=0.22,
    density_kg_m3=8470.0,
    T_c_K=16.0,                    # bulk NbN
)

LiNbO3 = Material(
    name="LiNbO3",
    n=2.138,                       # extraordinary @ 1550 nm
    dn_dT=3.34e-5,                 # Boyd et al.
    loss_dB_cm=0.03,               # TFLN
    p11=-0.026,
    p12=0.090,
    k_thermal=4.6,
    alpha_CTE=15.4e-6,             # c-axis
    E_GPa=200.0,
    nu_poisson=0.25,
    density_kg_m3=4640.0,
    yield_MPa=2000.0,
    bandgap_eV=3.78,
)

InP_mat = Material(
    name="InP",
    n=3.17,
    dn_dT=2.0e-4,
    loss_dB_cm=1.5,
    k_thermal=68.0,
    alpha_CTE=4.6e-6,
    E_GPa=61.0,
    nu_poisson=0.36,
    density_kg_m3=4810.0,
    bandgap_eV=1.35,
)

Al = Material(
    name="Al",
    n=1.44,                        # effective for thin metal
    dn_dT=0.0,
    k_thermal=237.0,
    alpha_CTE=23.1e-6,
    E_GPa=70.0,
    nu_poisson=0.35,
    density_kg_m3=2700.0,
    yield_MPa=40.0,
)

Au = Material(
    name="Au",
    n=0.55,
    dn_dT=0.0,
    k_thermal=317.0,
    alpha_CTE=14.2e-6,
    E_GPa=79.0,
    nu_poisson=0.44,
    density_kg_m3=19300.0,
    yield_MPa=120.0,
)


# ── Material stacks (predefined foundry processes) ───────────────────

@_dc.dataclass(frozen=True)
class MaterialStack:
    """Ordered layer stack for a photonic process."""

    name: str
    substrate: Material
    box: Material               # buried oxide / lower cladding
    core: Material              # waveguide core
    upper_clad: Material
    heater: Material
    detector: Optional[Material] = None
    metal_pad: Material = Al
    core_thickness_nm: float = 220.0
    box_thickness_um: float = 2.0
    clad_thickness_um: float = 1.0

    @property
    def CTE_mismatch(self) -> float:
        """Core–BOX CTE mismatch [K⁻¹] (dominant stress source)."""
        return abs(self.core.alpha_CTE - self.box.alpha_CTE)

    def bimorph_stress_MPa(self, delta_T: float) -> float:
        """Bimorph thermal stress from CTE mismatch.

        σ = E_core · (α_core − α_sub) · ΔT
        Ref: Timoshenko 1925, bimetallic strip.
        """
        return (
            self.core.E_GPa
            * 1e3  # GPa → MPa
            * (self.core.alpha_CTE - self.substrate.alpha_CTE)
            * delta_T
        )

    def waveguide_width_change_nm(self, w0_nm: float, delta_T: float) -> float:
        """Waveguide width change from thermal expansion [nm]."""
        return w0_nm * self.core.alpha_CTE * delta_T

    def resonance_shift_nm(
        self,
        lambda0_nm: float,
        delta_T: float,
        n_group: float = 4.2,
    ) -> float:
        """Ring resonator wavelength shift from thermo-optic effect.

        Δλ = λ₀ · (dn/dT · ΔT) / n_g
        Ref: Bogaerts et al., Laser & Photonics Reviews 6(1), 2012.
        """
        dn = self.core.dn_dT * delta_T
        return lambda0_nm * dn / n_group


# ── Pre-built stacks ─────────────────────────────────────────────────

SOI220 = MaterialStack(
    name="AIM 220 nm SOI",
    substrate=Si,
    box=SiO2,
    core=Si,
    upper_clad=SiO2,
    heater=Al,
    detector=NbN,
    core_thickness_nm=220.0,
    box_thickness_um=2.0,
    clad_thickness_um=1.0,
)

SiN_STACK = MaterialStack(
    name="SiN 400 nm",
    substrate=Si,
    box=SiO2,
    core=SiN,
    upper_clad=SiO2,
    heater=Al,
    core_thickness_nm=400.0,
    box_thickness_um=3.0,
    clad_thickness_um=2.0,
)

LNOI = MaterialStack(
    name="TFLN on Insulator",
    substrate=LiNbO3,
    box=SiO2,
    core=LiNbO3,
    upper_clad=SiO2,
    heater=Au,
    core_thickness_nm=600.0,
    box_thickness_um=2.0,
    clad_thickness_um=0.5,
)

InP = MaterialStack(
    name="InP Generic",
    substrate=InP_mat,
    box=InP_mat,
    core=InP_mat,
    upper_clad=InP_mat,
    heater=Au,
    core_thickness_nm=300.0,
)
