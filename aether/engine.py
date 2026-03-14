"""
Coupled Multiphysics Engine — the core orchestrator.

Open-source chain:
    Environment → Thermal field → Strain → Δn_eff → Geometry perturbation

Pro chain (aether-pro) adds:
    → FDTD re-simulation (Meep) with perturbed geometry
    → Quantum degradation (SNSPD, JSI, coincidence)
    → Vibration fatigue assessment
    → Foundry yield under stress
"""

from __future__ import annotations

import dataclasses as _dc
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from .materials import MaterialStack, SOI220
from .environment import Environment, Ambient
from .coupling import (
    ThermalExpansionCoupler,
    ThermoOpticCoupler,
    PhotoelasticCoupler,
    WaveguideGeometryCoupler,
    StrainField,
)


@_dc.dataclass
class CoupledResult:
    """Cross-domain simulation result."""

    environment_name: str
    environment_description: str

    # Thermal → Structural
    peak_delta_T_K: float
    peak_thermal_stress_MPa: float

    # Electromagnetic
    delta_n_eff_thermo: float
    delta_n_eff_strain: float
    delta_n_eff_total: float
    resonance_shift_nm: float
    delta_waveguide_width_nm: float
    delta_waveguide_height_nm: float
    insertion_loss_dB: float

    # Pro fields (None if aether-pro not installed)
    quantum_summary: Optional[str] = None
    vibration_summary: Optional[str] = None
    yield_nominal_pct: Optional[float] = None
    yield_stressed_pct: Optional[float] = None
    fdtd_ran: bool = False
    transmission_penalty_dB: float = 0.0

    # Meta
    wall_time_s: float = 0.0
    solver_chain: List[str] = _dc.field(default_factory=list)
    warnings: List[str] = _dc.field(default_factory=list)
    pass_fail: str = "PASS"

    def to_dict(self) -> Dict[str, Any]:
        d = {}
        for f in _dc.fields(self):
            v = getattr(self, f.name)
            if isinstance(v, np.ndarray):
                d[f.name] = {"shape": list(v.shape), "mean": float(np.mean(v))}
            else:
                d[f.name] = v
        return d

    def save_json(self, path: Union[str, Path]) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def report(self, path: Optional[Union[str, Path]] = None) -> str:
        lines = [
            "=" * 72,
            "  PROJECT AETHER -- Coupled Multiphysics Analysis Report",
            "=" * 72,
            "",
            f"Environment:  {self.environment_name}",
            f"              {self.environment_description}",
            "",
            "--- Thermal -> Structural ---------------------------------",
            f"  Peak dT:              {self.peak_delta_T_K:+.1f} K",
            f"  Thermal stress:       {self.peak_thermal_stress_MPa:.1f} MPa",
            "",
            "--- Electromagnetic --------------------------------------",
            f"  dn (thermo-optic):    {self.delta_n_eff_thermo:+.6f}",
            f"  dn (photoelastic):    {self.delta_n_eff_strain:+.6f}",
            f"  dn (total):           {self.delta_n_eff_total:+.6f}",
            f"  Resonance shift:      {self.resonance_shift_nm:+.3f} nm",
            f"  Width change:         {self.delta_waveguide_width_nm:+.3f} nm",
            f"  Height change:        {self.delta_waveguide_height_nm:+.3f} nm",
            f"  Insertion loss (est): {self.insertion_loss_dB:.2f} dB",
        ]

        if self.quantum_summary:
            lines += ["", "--- Quantum (Pro) ----------------------------------------"]
            lines += [f"  {self.quantum_summary}"]

        if self.vibration_summary:
            lines += ["", "--- Vibration (Pro) --------------------------------------"]
            lines += [f"  {self.vibration_summary}"]

        if self.yield_nominal_pct is not None:
            lines += [
                "", "--- Foundry Yield (Pro) ----------------------------------",
                f"  Yield (nominal):      {self.yield_nominal_pct:.1f}%",
                f"  Yield (stressed):     {self.yield_stressed_pct:.1f}%",
            ]

        lines += [
            "",
            "--- Verdict ----------------------------------------------",
            f"  Result:               {self.pass_fail}",
        ]
        if self.warnings:
            lines.append("  Warnings:")
            for w in self.warnings:
                lines.append(f"    - {w}")

        lines += [
            "",
            f"  Solver chain:         {' -> '.join(self.solver_chain)}",
            f"  Wall time:            {self.wall_time_s:.2f} s",
            "=" * 72,
        ]

        text = "\n".join(lines)
        if path:
            Path(path).write_text(text)
        return text


class CoupledModel:
    """Coupled multiphysics simulation engine.

    Usage
    -----
    >>> import aether
    >>> model = aether.CoupledModel(
    ...     environment=aether.Hypersonic(mach=6, altitude_km=25),
    ...     material_stack=aether.SOI220,
    ... )
    >>> result = model.solve()
    >>> print(result.report())
    """

    def __init__(
        self,
        topology: Optional[np.ndarray] = None,
        environment: Optional[Environment] = None,
        material_stack: MaterialStack = SOI220,
        waveguide_width_nm: float = 500.0,
        ring_radius_um: float = 10.0,
        coupling_gap_nm: float = 300.0,
        n_group: float = 4.2,
        chip_size_mm: tuple = (6.0, 4.0),
        # Pro options (require aether-pro)
        use_meep: bool = False,
        meep_resolution: int = 15,
        n_devices: int = 10,
        snspd_efficiency: float = 0.93,
        jsi_purity: float = 0.92,
        pair_rate_Hz: float = 1e6,
        waveguide_length_mm: float = 5.0,
        cryostat_temp_K: float = 4.0,
    ):
        self.topology = topology if topology is not None else self._default_ring_topology()
        self.env = environment or Ambient()
        self.stack = material_stack
        self.wg_width_nm = waveguide_width_nm
        self.ring_radius_um = ring_radius_um
        self.gap_nm = coupling_gap_nm
        self.n_group = n_group
        self.chip_size = chip_size_mm

        # Pro params (stored but only used if aether-pro available)
        self._pro_params = dict(
            use_meep=use_meep,
            meep_resolution=meep_resolution,
            n_devices=n_devices,
            snspd_efficiency=snspd_efficiency,
            jsi_purity=jsi_purity,
            pair_rate_Hz=pair_rate_Hz,
            waveguide_length_mm=waveguide_length_mm,
            cryostat_temp_K=cryostat_temp_K,
        )

    def solve(self) -> CoupledResult:
        """Run the coupled simulation chain."""
        t0 = time.time()
        solvers = []
        warnings = []

        ny, nx = self.topology.shape

        # -- 1. Thermal field --
        delta_T_field = self._compute_thermal_field(nx, ny)
        peak_dT = float(np.max(np.abs(delta_T_field)))
        if peak_dT > 0:
            solvers.append("Thermal")

        # -- 2. Structural: thermal expansion -> strain --
        z = np.zeros((ny, nx))
        strain = StrainField(z, z, z, delta_T_field, 0.0)
        stress = 0.0
        if peak_dT > 0:
            coupler = ThermalExpansionCoupler(self.stack)
            strain = coupler.compute(delta_T_field)
            stress = strain.stress_MPa
            solvers.append("Structural")

            if stress > self.stack.core.yield_MPa * 0.5:
                warnings.append(
                    f"Thermal stress {stress:.0f} MPa > 50% of "
                    f"fracture strength ({self.stack.core.yield_MPa:.0f} MPa)"
                )

        # -- 3. Electromagnetic: index perturbation --
        dn_thermo_field = ThermoOpticCoupler(self.stack.core).compute(delta_T_field)
        dn_thermo = float(np.mean(dn_thermo_field))

        dn_strain_field = PhotoelasticCoupler(self.stack.core).compute(strain)
        dn_strain = float(np.mean(dn_strain_field))

        dn_total_field = dn_thermo_field + dn_strain_field

        geom_coupler = WaveguideGeometryCoupler(
            self.stack,
            waveguide_width_nm=self.wg_width_nm,
            ring_radius_um=self.ring_radius_um,
            coupling_gap_nm=self.gap_nm,
            n_group=self.n_group,
        )
        geom = geom_coupler.compute(strain, dn_total_field)
        delta_w = float(np.mean(geom.delta_w_nm))
        delta_h = geom.delta_h_nm
        res_shift = geom.delta_lambda_res_nm
        dn_total = geom.delta_n_eff

        # Insertion loss estimate
        wg_len = self._pro_params.get("waveguide_length_mm", 5.0)
        if abs(delta_w) > 0.01:
            il_estimate = (
                self.stack.core.loss_dB_cm
                * (1.0 + 10.0 * (delta_w / self.wg_width_nm) ** 2)
                * wg_len * 0.1
            )
        else:
            il_estimate = self.stack.core.loss_dB_cm * wg_len * 0.1

        solvers.append("Electromagnetic")

        # -- 4+ Pro solvers --
        quantum_summary = None
        vibration_summary = None
        yield_nom = None
        yield_str = None
        fdtd_ran = False
        penalty_dB = 0.0

        try:
            import aether_pro
            pro_result = aether_pro.run_pro_chain(
                env=self.env,
                stack=self.stack,
                topology=self.topology,
                strain=strain,
                dn_total=dn_total,
                delta_w=delta_w,
                peak_dT=peak_dT,
                params=self._pro_params,
            )
            quantum_summary = pro_result.get("quantum_summary")
            vibration_summary = pro_result.get("vibration_summary")
            yield_nom = pro_result.get("yield_nominal_pct")
            yield_str = pro_result.get("yield_stressed_pct")
            fdtd_ran = pro_result.get("fdtd_ran", False)
            penalty_dB = pro_result.get("transmission_penalty_dB", 0.0)
            solvers.extend(pro_result.get("solvers", []))
            warnings.extend(pro_result.get("warnings", []))
        except ImportError:
            pass  # Pro not installed — open-source chain only

        # -- Verdict --
        verdict = "PASS"
        if warnings:
            verdict = "WARN"
        if stress > self.stack.core.yield_MPa:
            verdict = "FAIL"
            warnings.append("STRUCTURAL FAILURE: thermal stress exceeds fracture strength")

        elapsed = time.time() - t0

        return CoupledResult(
            environment_name=self.env.name,
            environment_description=self.env.description,
            peak_delta_T_K=peak_dT,
            peak_thermal_stress_MPa=stress,
            delta_n_eff_thermo=dn_thermo,
            delta_n_eff_strain=dn_strain,
            delta_n_eff_total=dn_total,
            resonance_shift_nm=res_shift,
            delta_waveguide_width_nm=delta_w,
            delta_waveguide_height_nm=delta_h,
            insertion_loss_dB=il_estimate,
            quantum_summary=quantum_summary,
            vibration_summary=vibration_summary,
            yield_nominal_pct=yield_nom,
            yield_stressed_pct=yield_str,
            fdtd_ran=fdtd_ran,
            transmission_penalty_dB=penalty_dB,
            wall_time_s=elapsed,
            solver_chain=solvers,
            warnings=warnings,
            pass_fail=verdict,
        )

    def _compute_thermal_field(self, nx: int, ny: int) -> np.ndarray:
        th = self.env.thermal
        dT_base = th.delta_T_surface_K

        if abs(dT_base) < 0.01 and th.cycling_amplitude_K < 0.01:
            return np.zeros((ny, nx))

        dT_eff = dT_base
        if th.cycling_amplitude_K > 0:
            dT_eff = max(abs(dT_base), th.cycling_amplitude_K / 2.0)

        yy, xx = np.mgrid[0:ny, 0:nx]
        cx, cy = nx / 2.0, ny / 2.0
        sigma_x, sigma_y = nx / 4.0, ny / 4.0
        gaussian = np.exp(-((xx - cx) ** 2 / (2 * sigma_x ** 2)
                            + (yy - cy) ** 2 / (2 * sigma_y ** 2)))

        field = dT_eff * (0.3 + 0.7 * gaussian)

        if th.delta_T_gradient_K_mm > 0:
            grad = th.delta_T_gradient_K_mm * np.linspace(
                0, self.chip_size[0], nx
            )[np.newaxis, :]
            field = field + grad

        return field.astype(np.float32)

    def _default_ring_topology(self) -> np.ndarray:
        ny, nx = 80, 120
        topo = np.zeros((ny, nx), dtype=np.float64)

        cy = ny // 2
        wg_half = 3
        topo[cy - wg_half : cy + wg_half, :] = 1.0

        ring_cx, ring_cy = nx // 2, cy - 15
        R_outer, R_inner = 12, 9
        yy, xx = np.ogrid[:ny, :nx]
        r2 = (xx - ring_cx) ** 2 + (yy - ring_cy) ** 2
        ring_mask = (r2 <= R_outer ** 2) & (r2 >= R_inner ** 2)
        topo[ring_mask] = 1.0

        return topo
