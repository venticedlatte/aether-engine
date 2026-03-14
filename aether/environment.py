"""
Extreme-environment models.

Each environment produces a physical loading profile:
    - ΔT distribution [K]
    - vibration PSD [g²/Hz]
    - radiation dose [rad]
    - pressure [Pa]
    - aerodynamic heat flux [W/m²]

These feed into the coupling layer, which maps loads to
photonic/structural/quantum domain perturbations.
"""

from __future__ import annotations

import dataclasses as _dc
import math
from typing import Optional


@_dc.dataclass
class ThermalProfile:
    """Thermal loading on the photonic chip."""
    delta_T_surface_K: float = 0.0       # surface temperature rise [K]
    delta_T_gradient_K_mm: float = 0.0   # through-thickness gradient [K/mm]
    cycling_amplitude_K: float = 0.0     # peak-to-peak thermal cycling
    cycling_period_s: float = 0.0        # cycle period [s]
    n_cycles: int = 0                    # total cycle count


@_dc.dataclass
class VibrationProfile:
    """Random vibration loading."""
    psd_g2_Hz: float = 0.0              # flat PSD level [g²/Hz]
    freq_lo_Hz: float = 20.0
    freq_hi_Hz: float = 2000.0
    grms: float = 0.0                   # overall Grms

    def __post_init__(self):
        if self.grms == 0.0 and self.psd_g2_Hz > 0:
            bw = self.freq_hi_Hz - self.freq_lo_Hz
            self.grms = math.sqrt(self.psd_g2_Hz * bw)


@_dc.dataclass
class RadiationProfile:
    """Ionizing / displacement damage."""
    total_dose_krad: float = 0.0         # total ionizing dose [krad(Si)]
    displacement_damage_MeV_g: float = 0 # DDD [MeV/g]
    see_flux_cm2_s: float = 0.0          # single-event rate


@_dc.dataclass
class Environment:
    """Base environment model."""
    name: str = "Ambient"
    thermal: ThermalProfile = _dc.field(default_factory=ThermalProfile)
    vibration: VibrationProfile = _dc.field(default_factory=VibrationProfile)
    radiation: RadiationProfile = _dc.field(default_factory=RadiationProfile)
    ambient_pressure_Pa: float = 101325.0
    description: str = ""


# ── Pre-built environments ───────────────────────────────────────────

def Ambient() -> Environment:
    """Lab bench at 25 °C, no external loads."""
    return Environment(
        name="Ambient (25 °C)",
        thermal=ThermalProfile(delta_T_surface_K=0.0),
        description="Standard laboratory conditions.",
    )


def Hypersonic(
    mach: float = 6.0,
    altitude_km: float = 25.0,
    duration_s: float = 300.0,
) -> Environment:
    """Hypersonic flight environment.

    Stagnation temperature: T_stag = T_∞ · (1 + (γ-1)/2 · M²)
    Ref: Anderson, *Hypersonic and High-Temperature Gas Dynamics*, 2006.

    At Mach 6, 25 km:  T_∞ ≈ 222 K → T_stag ≈ 1820 K → ΔT ≈ 1600 K
    Behind TPS, chip sees ~200–400 K rise depending on insulation.
    """
    gamma = 1.4  # air
    T_inf_K = 288.15 - 6.5 * altitude_km  # ISA lapse rate
    T_stag_K = T_inf_K * (1.0 + (gamma - 1.0) / 2.0 * mach ** 2)

    # Assume TPS + standoff reduces chip ΔT to 5% of stagnation rise
    tps_factor = 0.05
    delta_T_chip = (T_stag_K - T_inf_K) * tps_factor

    # Aerodynamic vibration: Grms scales roughly as M^1.5
    grms = 5.0 * (mach / 3.0) ** 1.5

    return Environment(
        name=f"Hypersonic Mach {mach}, {altitude_km} km",
        thermal=ThermalProfile(
            delta_T_surface_K=delta_T_chip,
            delta_T_gradient_K_mm=delta_T_chip * 0.3,  # 30% gradient
        ),
        vibration=VibrationProfile(
            psd_g2_Hz=0.04 * (mach / 3.0) ** 2,
            freq_lo_Hz=20.0,
            freq_hi_Hz=2000.0,
            grms=grms,
        ),
        ambient_pressure_Pa=_isa_pressure(altitude_km),
        description=(
            f"Hypersonic flight at Mach {mach}, {altitude_km} km altitude. "
            f"Stagnation temp {T_stag_K:.0f} K, chip ΔT {delta_T_chip:.0f} K "
            f"behind TPS. Duration {duration_s} s."
        ),
    )


def LEO_Orbit(
    altitude_km: float = 550.0,
    inclination_deg: float = 51.6,
    mission_years: float = 5.0,
) -> Environment:
    """Low-Earth orbit environment.

    Thermal cycling: eclipse ΔT ≈ 200 K every 90 min.
    Radiation: trapped protons + electrons + GCR.
    Ref: ECSS-E-ST-10-04C (ESA space environment standard).
    """
    orbital_period_s = 2.0 * math.pi * math.sqrt(
        ((6371.0 + altitude_km) * 1e3) ** 3 / 3.986e14
    )
    n_orbits = int(mission_years * 365.25 * 86400.0 / orbital_period_s)

    # Van Allen dose (simplified): higher inclination → more SAA passes
    dose_per_year_krad = 3.0 * (1.0 + 0.5 * math.sin(math.radians(inclination_deg)))

    return Environment(
        name=f"LEO {altitude_km:.0f} km, {inclination_deg}° inc",
        thermal=ThermalProfile(
            delta_T_surface_K=50.0,           # steady-state panel-mount rise
            cycling_amplitude_K=200.0,        # sun/eclipse swing
            cycling_period_s=orbital_period_s,
            n_cycles=n_orbits,
        ),
        vibration=VibrationProfile(grms=0.01),  # microgravity residual
        radiation=RadiationProfile(
            total_dose_krad=dose_per_year_krad * mission_years,
            see_flux_cm2_s=1e-8,
        ),
        ambient_pressure_Pa=0.0,
        description=(
            f"LEO at {altitude_km} km, {inclination_deg}° inclination, "
            f"{mission_years} yr mission. {n_orbits} thermal cycles, "
            f"TID {dose_per_year_krad * mission_years:.1f} krad(Si)."
        ),
    )


def ThermalCycling(
    delta_T_K: float = 200.0,
    period_s: float = 120.0,
    n_cycles: int = 10000,
) -> Environment:
    """Accelerated thermal cycling (MIL-STD-883 style)."""
    return Environment(
        name=f"Thermal Cycling ±{delta_T_K/2:.0f} K × {n_cycles}",
        thermal=ThermalProfile(
            cycling_amplitude_K=delta_T_K,
            cycling_period_s=period_s,
            n_cycles=n_cycles,
        ),
        description=f"MIL-STD-883-style cycling, {n_cycles} cycles of ±{delta_T_K/2:.0f} K.",
    )


def RadiationEnvironment(
    total_dose_krad: float = 100.0,
    displacement_MeV_g: float = 1e10,
) -> Environment:
    """Pure radiation environment (nuclear or deep space)."""
    return Environment(
        name=f"Radiation {total_dose_krad} krad",
        radiation=RadiationProfile(
            total_dose_krad=total_dose_krad,
            displacement_damage_MeV_g=displacement_MeV_g,
        ),
        description=f"Radiation: TID {total_dose_krad} krad(Si), DDD {displacement_MeV_g:.1e} MeV/g.",
    )


def Cryogenic(temp_K: float = 4.0) -> Environment:
    """Cryogenic operation (quantum photonics, SNSPD)."""
    return Environment(
        name=f"Cryogenic {temp_K} K",
        thermal=ThermalProfile(delta_T_surface_K=-(293.15 - temp_K)),
        description=f"Cryogenic at {temp_K} K (ΔT = {-(293.15 - temp_K):.0f} K from room temp).",
    )


def DirectedEnergy(
    power_W_cm2: float = 1e4,
    duration_s: float = 5.0,
    beam_diameter_mm: float = 10.0,
) -> Environment:
    """Directed-energy weapon thermal loading on optics.

    ΔT estimated via lumped-capacitance: ΔT = P·t / (ρ·c·V)
    for a Si slab of beam-spot area × 1 mm thickness.
    """
    from .materials import Si as _Si

    area_m2 = math.pi * (beam_diameter_mm * 0.5e-3) ** 2
    volume_m3 = area_m2 * 1e-3  # 1 mm thick
    energy_J = power_W_cm2 * 1e4 * area_m2 * duration_s
    mass_kg = _Si.density_kg_m3 * volume_m3
    delta_T = energy_J / (mass_kg * _Si.specific_heat)

    return Environment(
        name=f"DEW {power_W_cm2:.0e} W/cm², {duration_s}s",
        thermal=ThermalProfile(
            delta_T_surface_K=delta_T,
            delta_T_gradient_K_mm=delta_T * 0.5,
        ),
        description=(
            f"Directed energy: {power_W_cm2:.0e} W/cm² for {duration_s} s, "
            f"beam Ø{beam_diameter_mm} mm → ΔT ≈ {delta_T:.0f} K."
        ),
    )


def HighVibration(
    grms: float = 20.0,
    freq_lo: float = 20.0,
    freq_hi: float = 2000.0,
) -> Environment:
    """High-vibration environment (launch vehicle, turbine mount)."""
    psd = grms ** 2 / (freq_hi - freq_lo)
    return Environment(
        name=f"High Vibration {grms} Grms",
        vibration=VibrationProfile(
            psd_g2_Hz=psd,
            freq_lo_Hz=freq_lo,
            freq_hi_Hz=freq_hi,
            grms=grms,
        ),
        description=f"Random vibration {grms} Grms over {freq_lo}-{freq_hi} Hz.",
    )


# ── Helpers ──────────────────────────────────────────────────────────

def _isa_pressure(altitude_km: float) -> float:
    """ISA pressure [Pa] up to 32 km (troposphere + lower stratosphere)."""
    if altitude_km <= 11.0:
        T = 288.15 - 6.5 * altitude_km
        return 101325.0 * (T / 288.15) ** 5.2561
    elif altitude_km <= 20.0:
        p11 = 101325.0 * (216.65 / 288.15) ** 5.2561
        return p11 * math.exp(-0.0001577 * (altitude_km - 11.0) * 1000.0)
    else:
        p20 = 101325.0 * (216.65 / 288.15) ** 5.2561
        p20 *= math.exp(-0.0001577 * 9000.0)
        T = 216.65 + (altitude_km - 20.0)
        return p20 * (T / 216.65) ** (-34.1632)
