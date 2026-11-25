"""The SCL blocks in the loop: plc/*.scl translated by handletest/scl.py, run scan by scan against a
stateful model of the axis, the rig spring, the handle, the clamp and the sensors.

This plant model is written independently of handletest/rig.py (which is vectorised for the Monte Carlo):
here the handle travel is a state that moves forward when the rig spring force exceeds the pull resistance
and backward when it falls below the return resistance. The tests compare the two.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

from handletest import mechanism as mech
from handletest import scl
from handletest.evaluate import FEATURES, RECIPE
from handletest.rig import Rig

ROOT = Path(__file__).resolve().parents[1]
f32 = np.float32


@lru_cache(maxsize=1)
def blocks() -> dict:
    return scl.load(sorted((ROOT / "plc").glob("FB_*.scl")))


LIMIT_MAP = {"FpG1": ("G1Lo", "G1Hi"), "FMean": ("MeanLo", "MeanHi"), "FHyst": ("HystLo", "HystHi"),
             "FpG2": ("G2Lo", "G2Hi"), "FPeak": ("PeakFLo", "PeakFHi"), "XPeak": ("PeakXMin", "PeakXMax"),
             "XStop": ("StopXLo", "StopXHi")}


def load_recipe(ev, mode: int, lim: dict | None = None, env: tuple | None = None, recipe: dict = RECIPE) -> None:
    """Write the evaluation recipe into an FB_CurveEval instance (in TIA: a move from the recipe DB)."""
    ev.Mode = int(mode)
    for k in ("GateX", "Gate2X", "PeakXLo", "PeakXHi", "StepSpan", "StopF", "EnvX0", "EnvDx"):
        setattr(ev, k, f32(recipe[k]))
    ev.EnvN = int(recipe["EnvN"])
    for name, (lo, hi) in (lim or {}).items():
        if name in LIMIT_MAP:
            setattr(ev, LIMIT_MAP[name][0], f32(lo))
            setattr(ev, LIMIT_MAP[name][1], f32(hi))
        elif name == "FStep":
            ev.StepLo = f32(lo)
        elif name == "FrG1":
            ev.RetFMin = f32(lo)
    if env is not None:
        for i, (lo, hi) in enumerate(zip(*env)):
            ev.EnvLo[i], ev.EnvHi[i] = f32(lo), f32(hi)


def new_station(rig: Rig, variant_lh: bool = True):
    st = blocks()["FB_HandleStation"]()
    st.CycleTime, st.VPull = f32(rig.Ts), f32(rig.v)
    st.FTouch, st.FRev, st.XMax = f32(rig.F_touch), f32(rig.F_rev), f32(rig.x_max)
    st.Compliance = f32(1.0 / rig.k_comp if rig.k_comp > 0 else 0.0)
    st.VariantLH = bool(variant_lh)
    st.SafetyOk = st.DriveOk = st.StartEnable = st.ClampOpen = True
    return st


class Plant:
    """Axis, rig spring, one handle, clamp and part sensors."""

    ACC = 3000.0      # mm/s2, axis acceleration limit [A]
    T_CLAMP = 0.25    # s, clamp closing and opening time [A]

    def __init__(self, part: dict, rig: Rig, rng: np.random.Generator, hand_lh: bool = True,
                 seat: float = 5.0, grid: int = 1600):
        self.rig, self.rng = rig, rng
        th = np.linspace(0.0, 0.345, grid)
        mp, mr = mech.torques(part, th, rig.v * 1e-3 / mech.R_PULL)
        self.fp, self.fr = mech.force_n(mp[0], th), mech.force_n(mr[0], th)
        self.xh = mech.travel_mm(th)
        self.seat = seat                  # axis position at which the hook meets the grip
        self.hand_lh = hand_lh
        self.x, self.pos, self.vel = 0.0, 0.0, 0.0   # handle travel (mm), axis position, axis speed
        self.clamp = 0.0                  # 0 open .. 1 closed
        self.present = True
        self.f_true = 0.0
        self.f_peak = 0.0

    def step(self, qvel: float, enable: bool, qclamp: bool) -> None:
        dt = self.rig.Ts
        target = qvel if enable else 0.0
        self.vel += min(max(target - self.vel, -self.ACC * dt), self.ACC * dt)
        self.pos = max(0.0, self.pos + self.vel * dt)
        self.clamp = min(max(self.clamp + (dt if qclamp else -dt) / self.T_CLAMP, 0.0), 1.0)
        if not self.present:
            self.f_true = 0.0
            return
        a, k = self.pos - self.seat, self.rig.k_rig
        self._settle(a, k)
        self.f_true = max(0.0, k * (a - self.x))
        self.f_peak = max(self.f_peak, self.f_true)

    def _settle(self, a: float, k: float) -> None:
        """Move the handle to its new equilibrium. g = resistance - rig spring force is linear between
        grid points; the handle stops at the first zero of g in its direction of motion."""
        xh, x, n = self.xh, self.x, len(self.xh) - 1
        fs = k * (a - x)
        if fs > np.interp(x, xh, self.fp):                      # pulled forward
            g0, x0 = float(np.interp(x, xh, self.fp)) - fs, x
            j = int(np.searchsorted(xh, x, side="right"))
            while j <= n:
                g1 = self.fp[j] - k * (a - xh[j])
                if g1 >= 0.0:
                    self.x = x0 + (xh[j] - x0) * (-g0) / (g1 - g0)
                    return
                g0, x0, j = g1, xh[j], j + 1
            self.x = xh[n]
        elif x > 0.0 and fs < np.interp(x, xh, self.fr):        # pushed back by its spring
            h0, x0 = float(np.interp(x, xh, self.fr)) - fs, x
            j = int(np.searchsorted(xh, x, side="left")) - 1
            while j >= 0:
                h1 = self.fr[j] - k * (a - xh[j])
                if h1 <= 0.0:
                    self.x = x0 + (xh[j] - x0) * h0 / (h0 - h1)
                    return
                h0, x0, j = h1, xh[j], j - 1
            self.x = 0.0

    def force(self) -> float:
        r = self.rig
        f = self.f_true * (1 + r.gain) + r.zero + r.sF * self.rng.standard_normal()
        return round(f / r.qF) * r.qF if r.qF > 0 else f

    def position(self) -> float:
        r = self.rig
        x = self.pos + r.sx * self.rng.standard_normal()
        return round(x / r.qx) * r.qx if r.qx > 0 else x


def scan(st, plant: Plant, **inputs) -> None:
    """One PLC cycle: read inputs, run the FB, write outputs to the plant."""
    st.PartPresent = plant.present
    st.SensLH = plant.present and plant.hand_lh
    st.SensRH = plant.present and not plant.hand_lh
    st.ClampClosed, st.ClampOpen = plant.clamp >= 1.0, plant.clamp <= 0.0
    st.Pos, st.Force = f32(plant.position()), f32(plant.force())
    for k, v in inputs.items():
        setattr(st, k, v)
    st()
    plant.step(float(st.QVel), bool(st.QDriveEnable), bool(st.QClamp))


def run_cycle(st, plant: Plant, t_unload: float = 1.0, t_reject: float = 8.0, max_s: float = 60.0) -> dict:
    """One part through the station. An OK part is taken away t_unload after the verdict; a rejected part
    is taken out by the operator and dropped into the reject chute t_reject after the verdict."""
    dt = plant.rig.Ts
    t, t_verdict, chute_until = 0.0, None, -1.0
    while t < max_s:
        scan(st, plant, RejectChute=t < chute_until)
        t += dt
        if t_verdict is None and int(st.Verdict) != 0:
            t_verdict = t
        if t_verdict is not None and plant.present:
            if int(st.Verdict) == 1 and t >= t_verdict + t_unload:
                plant.present = False
            elif int(st.Verdict) == 2 and t >= t_verdict + t_reject:
                plant.present = False
                chute_until = t + 0.1
        if t_verdict is not None and not plant.present and int(st.State) == 0 and t > chute_until:
            break
    ev = st.Eval
    return dict(verdict=int(st.Verdict), nok=int(st.NokCode), t_test=float(st.TCycle), t_total=t,
                f_peak_true=plant.f_peak, samples=int(ev.NSamples),
                feat={k: float(getattr(ev, k)) for k in FEATURES},
                env_viol=int(ev.EnvViol), env_nodes=int(ev.EnvNodes))


def one(pop: dict, i: int) -> dict:
    return {k: v[i:i + 1] for k, v in pop.items()}


def replay(c: dict, i: int, mode: int, lim: dict | None, env: tuple | None) -> dict:
    """Feed the sampled curve of part i (from rig.measure) through FB_CurveEval, sample by sample.

    Same samples in, so features and verdict must equal handletest.evaluate (apart from Real = 32 bit)."""
    fb = blocks()["FB_CurveEval"]()
    load_recipe(fb, mode, lim, env)
    fb.Reset = True
    fb()
    fb.Reset = False
    n = int(c["n"][i])
    fb.Sample, fb.Stroke = True, 1
    for j in range(n):
        fb.X, fb.F = f32(c["Xp"][i, j]), f32(c["Fp"][i, j])
        fb()
    fb.Stroke = 2
    for j in range(n - 1, -1, -1):
        fb.X, fb.F = f32(c["Xr"][i, j]), f32(c["Fr"][i, j])
        fb()
    fb.Sample, fb.Finish = False, True
    fb()
    return dict(ok=bool(fb.Ok) and bool(c["touched"][i]), nok=int(fb.NokCode),
                feat={k: float(getattr(fb, k)) for k in FEATURES})
