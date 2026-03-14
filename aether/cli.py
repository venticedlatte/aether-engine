"""
aether -- Coupled Multiphysics CLI

Usage:
    python -m aether --env hypersonic --mach 6 --altitude 25
    python -m aether --env leo --altitude 550 --years 5
    python -m aether --env cryogenic --temp 4
    python -m aether --env ambient
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="aether",
        description="Project Aether -- Coupled Multiphysics Engine",
    )
    p.add_argument(
        "--env",
        choices=["ambient", "hypersonic", "leo", "thermal_cycling",
                 "radiation", "cryogenic", "dew", "vibration"],
        default="hypersonic",
    )
    p.add_argument("--mach", type=float, default=6.0)
    p.add_argument("--altitude", type=float, default=25.0)
    p.add_argument("--inclination", type=float, default=51.6)
    p.add_argument("--years", type=float, default=5.0)
    p.add_argument("--temp", type=float, default=4.0)
    p.add_argument("--dose", type=float, default=100.0)
    p.add_argument("--power", type=float, default=1e4)
    p.add_argument("--duration", type=float, default=5.0)
    p.add_argument("--grms", type=float, default=20.0)
    p.add_argument("--stack", choices=["soi220", "sin", "lnoi", "inp"], default="soi220")
    p.add_argument("--topology", type=str, default=None)
    p.add_argument("--output", "-o", type=str, default=None)
    p.add_argument("--json", action="store_true")

    args = p.parse_args(argv)

    from . import environment as envmod

    env_builders = {
        "ambient": lambda: envmod.Ambient(),
        "hypersonic": lambda: envmod.Hypersonic(mach=args.mach, altitude_km=args.altitude),
        "leo": lambda: envmod.LEO_Orbit(altitude_km=args.altitude, inclination_deg=args.inclination, mission_years=args.years),
        "thermal_cycling": lambda: envmod.ThermalCycling(),
        "radiation": lambda: envmod.RadiationEnvironment(total_dose_krad=args.dose),
        "cryogenic": lambda: envmod.Cryogenic(temp_K=args.temp),
        "dew": lambda: envmod.DirectedEnergy(power_W_cm2=args.power, duration_s=args.duration),
        "vibration": lambda: envmod.HighVibration(grms=args.grms),
    }
    env = env_builders[args.env]()

    from . import materials as matmod
    stacks = {"soi220": matmod.SOI220, "sin": matmod.SiN_STACK, "lnoi": matmod.LNOI, "inp": matmod.InP}
    stack = stacks[args.stack]

    topology = np.load(args.topology) if args.topology else None

    from .engine import CoupledModel
    model = CoupledModel(topology=topology, environment=env, material_stack=stack)
    result = model.solve()

    if args.json:
        import json
        text = json.dumps(result.to_dict(), indent=2, default=str)
    else:
        text = result.report()

    if args.output:
        Path(args.output).write_text(text)
        print(f"Report saved to {args.output}")
    else:
        print(text)

    codes = {"PASS": 0, "WARN": 1, "FAIL": 2}
    sys.exit(codes.get(result.pass_fail, 1))


if __name__ == "__main__":
    main()
