"""
Example: Compare SOI vs LNOI under hypersonic thermal load.

LNOI has 30x larger CTE mismatch than SOI -- this analysis shows
why material selection matters for extreme-environment photonics.

Run:
    python examples/material_comparison.py
"""

import sys
sys.path.insert(0, ".")

import aether

env = aether.Hypersonic(mach=5, altitude_km=30)

for stack_name, stack in [("SOI 220nm", aether.SOI220), ("LNOI", aether.LNOI), ("SiN", aether.SiN_STACK)]:
    model = aether.CoupledModel(environment=env, material_stack=stack)
    result = model.solve()

    print(f"{'='*50}")
    print(f"  {stack_name} at Mach 5, 30 km")
    print(f"{'='*50}")
    print(f"  Thermal stress:    {result.peak_thermal_stress_MPa:>8.1f} MPa")
    print(f"  Resonance shift:   {result.resonance_shift_nm:>+8.3f} nm")
    print(f"  dn_eff (total):    {result.delta_n_eff_total:>+10.6f}")
    print(f"  Verdict:           {result.pass_fail}")
    print()
