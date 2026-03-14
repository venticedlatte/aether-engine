"""
Physics coupling functions.

Each coupler translates outputs from one physics domain into
perturbations in another.  All use peer-reviewed equations with
citations.  No fudge factors.

Coupling chain (open-source)
----------------------------
Environment → ThermalExpansionCoupler → strain field
           → ThermoOpticCoupler      → Δn_eff
              PhotoelasticCoupler     → Δn_strain (from strain)
           → WaveguideGeometryCoupler → Δw, Δgap, Δλ_res

Pro coupling (aether-pro)
-------------------------
           → QuantumDegradationCoupler → Δη_SNSPD, ΔP_JSI, ΔC_rate
           → VibrationFatigueCoupler   → wire bond / die attach risk
           → RadiationLossCoupler      → Δα from TID
"""

from __future__ import annotations

import dataclasses as _dc
import math
from typing import Optional

import numpy as np

from .materials import Material, MaterialStack


# ══════════════════════════════════════════════════════════════════════
#  1.  THERMAL → STRUCTURAL
# ══════════════════════════════════════════════════════════════════════

@_dc.dataclass
class StrainField:
    """Strain tensor components across the chip."""
    eps_xx: np.ndarray       # in-plane, propagation direction
    eps_yy: np.ndarray       # in-plane, transverse
    eps_zz: np.ndarray       # out-of-plane (through thickness)
    delta_T: np.ndarray      # temperature field that caused this strain
    stress_MPa: float = 0.0  # peak von Mises stress


class ThermalExpansionCoupler:
    """Maps temperature field → strain field via CTE.

    For a constrained thin film on a substrate (Stoney's equation regime),
    the biaxial strain is:

        ε_film = (α_film − α_sub) · ΔT

    Ref: Stoney, Proc. R. Soc. Lond. A 82, 172 (1909).
         Freund & Suresh, *Thin Film Materials*, Cambridge, 2003.
    """

    def __init__(self, stack: MaterialStack):
        self.stack = stack

    def compute(
        self,
        delta_T_field: np.ndarray,
    ) -> StrainField:
        """Compute strain field from temperature field.

        Parameters
        ----------
        delta_T_field : (ny, nx) float
            Temperature change at each grid point [K].

        Returns
        -------
        StrainField with (ny, nx) arrays for each component.
        """
        alpha_core = self.stack.core.alpha_CTE
        alpha_constraint = self.stack.box.alpha_CTE
        delta_alpha = alpha_core - alpha_constraint

        # Biaxial strain: constrained film on substrate
        eps_biaxial = delta_alpha * delta_T_field

        # Free thermal expansion of core
        eps_free = alpha_core * delta_T_field

        # In-plane: biaxial (constrained by substrate)
        eps_xx = eps_biaxial.copy()
        eps_yy = eps_biaxial.copy()

        # Out-of-plane: free expansion (unconstrained top surface)
        # Poisson coupling: ε_zz = -2ν/(1-ν) · ε_biaxial + α·ΔT
        nu = self.stack.core.nu_poisson
        eps_zz = -2.0 * nu / (1.0 - nu) * eps_biaxial + eps_free

        # Von Mises stress from biaxial state
        sigma_biaxial = (
            self.stack.core.E_GPa * 1e3 * eps_biaxial / (1.0 - nu)
        )
        stress_peak = float(np.max(np.abs(sigma_biaxial)))

        return StrainField(
            eps_xx=eps_xx,
            eps_yy=eps_yy,
            eps_zz=eps_zz,
            delta_T=delta_T_field,
            stress_MPa=stress_peak,
        )


# ══════════════════════════════════════════════════════════════════════
#  2.  THERMAL → ELECTROMAGNETIC (thermo-optic)
# ══════════════════════════════════════════════════════════════════════

@_dc.dataclass
class RefractiveIndexPerturbation:
    """Combined index perturbation from all effects."""
    delta_n_thermo: np.ndarray     # thermo-optic contribution
    delta_n_strain: np.ndarray     # photoelastic contribution
    delta_n_total: np.ndarray      # sum
    n_eff_perturbed: np.ndarray    # n0 + Δn


class ThermoOpticCoupler:
    """Maps ΔT → Δn via thermo-optic coefficient.

    Δn = (dn/dT) · ΔT

    Ref: Cocorullo et al., J. Appl. Phys. 86, 3281 (1999) for Si.
    """

    def __init__(self, material: Material):
        self.material = material

    def compute(self, delta_T: np.ndarray) -> np.ndarray:
        """Return Δn array from temperature change."""
        return self.material.dn_dT * delta_T


class PhotoelasticCoupler:
    """Maps strain → Δn via photoelastic (strain-optic) effect.

    Δn = -n³/2 · (p₁₁·ε_∥ + p₁₂·(ε_⊥ + ε_z))

    Ref: Biegelsen, Phys. Rev. B 9(5), 2635 (1974).
         Huang, IEEE JQE 39(10), 1245 (2003).
    """

    def __init__(self, material: Material):
        self.material = material

    def compute(self, strain: StrainField) -> np.ndarray:
        """Return Δn array from strain field."""
        n = self.material.n
        return -(n ** 3) / 2.0 * (
            self.material.p11 * strain.eps_xx
            + self.material.p12 * (strain.eps_yy + strain.eps_zz)
        )


def combined_index_perturbation(
    material: Material,
    delta_T: np.ndarray,
    strain: StrainField,
) -> RefractiveIndexPerturbation:
    """Combine thermo-optic and photoelastic effects.

    Total: Δn = (dn/dT)·ΔT − n³/2·(p₁₁ε₁ + p₁₂(ε₂+ε₃))
    """
    dn_thermo = material.dn_dT * delta_T
    dn_strain = -(material.n ** 3) / 2.0 * (
        material.p11 * strain.eps_xx
        + material.p12 * (strain.eps_yy + strain.eps_zz)
    )
    dn_total = dn_thermo + dn_strain

    return RefractiveIndexPerturbation(
        delta_n_thermo=dn_thermo,
        delta_n_strain=dn_strain,
        delta_n_total=dn_total,
        n_eff_perturbed=material.n + dn_total,
    )


# ══════════════════════════════════════════════════════════════════════
#  3.  STRUCTURAL → PHOTONIC (geometry perturbation)
# ══════════════════════════════════════════════════════════════════════

@_dc.dataclass
class GeometryPerturbation:
    """Waveguide geometry changes from strain."""
    delta_w_nm: np.ndarray            # width change [nm]
    delta_h_nm: float                 # height change [nm] (uniform)
    delta_gap_nm: np.ndarray          # coupling gap change [nm]
    delta_lambda_res_nm: float        # ring resonance shift [nm]
    delta_FSR_nm: float               # FSR change [nm]
    delta_n_eff: float                # effective index change (scalar summary)


class WaveguideGeometryCoupler:
    """Maps strain field → waveguide geometry perturbation.

    Δw = w₀ · ε_yy  (width direction = transverse in-plane)
    Δh = h₀ · ε_zz  (height = out-of-plane)

    Effective index sensitivity (SOI 220 nm, TE0, 500 nm wide):
        ∂n_eff/∂w ≈ 1.5 × 10⁻³ nm⁻¹
        ∂n_eff/∂h ≈ 3.5 × 10⁻³ nm⁻¹

    Ref: Bogaerts & Chrostowski, Laser Photonics Rev. 12, 1700237 (2018).
    """

    def __init__(
        self,
        stack: MaterialStack,
        waveguide_width_nm: float = 500.0,
        ring_radius_um: float = 10.0,
        coupling_gap_nm: float = 200.0,
        n_group: float = 4.2,
        dn_eff_dw: float = 1.5e-3,
        dn_eff_dh: float = 3.5e-3,
    ):
        self.stack = stack
        self.w0 = waveguide_width_nm
        self.h0 = stack.core_thickness_nm
        self.R = ring_radius_um
        self.gap0 = coupling_gap_nm
        self.n_g = n_group
        self.dn_dw = dn_eff_dw
        self.dn_dh = dn_eff_dh

    def compute(
        self,
        strain: StrainField,
        delta_n_total: np.ndarray,
        lambda0_nm: float = 1550.0,
    ) -> GeometryPerturbation:
        """Compute geometry perturbation from strain + index change."""
        mean_eps_yy = float(np.mean(strain.eps_yy))
        mean_eps_zz = float(np.mean(strain.eps_zz))

        delta_w = self.w0 * mean_eps_yy
        delta_h = self.h0 * mean_eps_zz
        delta_gap = np.full_like(strain.eps_yy, -2.0 * delta_w)

        dn_geom = self.dn_dw * delta_w + self.dn_dh * delta_h
        dn_total = dn_geom + float(np.mean(delta_n_total))
        delta_lambda = lambda0_nm * dn_total / self.n_g

        fsr0 = lambda0_nm ** 2 / (2.0 * math.pi * self.R * 1e3 * self.n_g)
        delta_fsr = -fsr0 * dn_total / self.n_g

        return GeometryPerturbation(
            delta_w_nm=np.full_like(strain.eps_yy, delta_w),
            delta_h_nm=delta_h,
            delta_gap_nm=delta_gap,
            delta_lambda_res_nm=delta_lambda,
            delta_FSR_nm=delta_fsr,
            delta_n_eff=dn_total,
        )


# ══════════════════════════════════════════════════════════════════════
#  4+  PRO COUPLERS (aether-pro)
# ══════════════════════════════════════════════════════════════════════
#
#  The following couplers are available in aether-pro:
#
#    QuantumDegradationCoupler  — SNSPD η(T), JSI purity, CAR, QBER
#    vibration_fatigue()        — Steinberg random vib → fatigue life
#    radiation_loss_increase()  — TID → Δα [dB/cm] per material
#
#  See https://aether.plover.studio for licensing.
#

def _check_pro(feature: str):
    """Check if aether-pro is available."""
    try:
        import aether_pro  # noqa: F401
        return True
    except ImportError:
        print(
            f"[aether] '{feature}' requires aether-pro. "
            f"See https://aether.plover.studio for licensing."
        )
        return False
