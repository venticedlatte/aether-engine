"""
Project Aether — Coupled Multiphysics Engine
=============================================

The first engine that couples electromagnetic, quantum, structural,
thermal, and fluidic physics domains in a single differentiable
simulation loop for extreme-environment photonic-electronic systems.

    import aether

    model = aether.CoupledModel(
        environment=aether.Hypersonic(mach=6, altitude_km=25),
        material_stack=aether.SOI220,
    )
    result = model.solve()
    print(result.report())

License: Apache 2.0 (core) / Commercial (aether-pro)
Copyright 2026 Plover Studios. All rights reserved.
"""

from .materials import (
    MaterialStack,
    Material,
    SOI220,
    SiN_STACK,
    LNOI,
    InP,
)
from .environment import (
    Environment,
    Ambient,
    Hypersonic,
    LEO_Orbit,
    ThermalCycling,
    RadiationEnvironment,
    Cryogenic,
    DirectedEnergy,
    HighVibration,
)
from .coupling import (
    ThermoOpticCoupler,
    PhotoelasticCoupler,
    ThermalExpansionCoupler,
    WaveguideGeometryCoupler,
)
from .engine import CoupledModel, CoupledResult

__version__ = "0.1.0"
