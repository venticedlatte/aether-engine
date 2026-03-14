"""
Example: Ring resonator on a Mach 6 hypersonic vehicle.

Demonstrates the coupled simulation chain:
  Thermal -> Structural -> Electromagnetic

Run:
    python examples/hypersonic_ring.py
"""

import sys
sys.path.insert(0, ".")

import aether

# Define the problem
model = aether.CoupledModel(
    environment=aether.Hypersonic(mach=6, altitude_km=25),
    material_stack=aether.SOI220,
    waveguide_width_nm=500,
    ring_radius_um=10,
)

# Solve
result = model.solve()

# Print full report
print(result.report())

# Access specific values programmatically
print(f"\nResonance shift: {result.resonance_shift_nm:+.3f} nm")
print(f"Total dn_eff:    {result.delta_n_eff_total:+.6f}")
print(f"Thermal stress:  {result.peak_thermal_stress_MPa:.1f} MPa")
