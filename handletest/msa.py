"""Type-1 gauge study of the rig: one master handle, measured 50 times.

Formulas as printed in the public supplier guide listed in docs/SOURCES.md (G1):
    Cg  = 0.2 T / (6 s)
    Cgk = (0.1 T - |mean - reference|) / (3 s)
with T the full tolerance width, s the standard deviation of the repeat measurements; both should be
1.33 or more, and the resolution should be 5 % of T or finer (G1, G2). Here the reference value of the
master is its value on an ideal rig (rigid, slow, no noise): that plays the role of the calibration value.
"""

from __future__ import annotations

import numpy as np

from handletest import mechanism as mech
from handletest.evaluate import features
from handletest.rig import IDEAL, Rig, measure

N_REPEATS = 50


def cg(T: float, s: float) -> float:
    return 0.2 * T / (6.0 * s)


def cgk(T: float, s: float, mean: float, ref: float) -> float:
    return (0.1 * T - abs(mean - ref)) / (3.0 * s)


def repeats(rig: Rig, rng: np.random.Generator, n: int = N_REPEATS) -> dict:
    """Features of the master handle from n pulls on `rig` (each pull: new sampling phase, new noise)."""
    master = mech.nominal()
    pop = {k: np.repeat(v, n) for k, v in master.items()}
    return features(measure(pop, rig, rng))


def reference() -> dict:
    f = features(measure(mech.nominal(), IDEAL, np.random.default_rng(0), grid=6000))
    return {k: float(v[0]) for k, v in f.items() if k != "touched"}


def type1(rig: Rig, rng: np.random.Generator, tol: dict, n: int = N_REPEATS) -> dict:
    """tol: {feature: full tolerance width T}. Returns per feature mean, s, bias, Cg, Cgk."""
    ref, rep = reference(), repeats(rig, rng, n)
    out = {}
    for name, T in tol.items():
        x = rep[name]
        m, s = float(np.mean(x)), float(np.std(x, ddof=1))
        out[name] = dict(ref=ref[name], mean=m, s=s, bias=m - ref[name], T=T, Cg=cg(T, s),
                         Cgk=cgk(T, s, m, ref[name]), values=[float(v) for v in x])
    return out
