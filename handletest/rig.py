"""The test rig as a measurement system: what the PLC sees when the station pulls a handle once.

A servo axis pulls the grip through a hook and a load cell. The PLC samples force and axis position in a
cyclic interrupt. Modelled effects, all values [A]:

* rig compliance (hook, load cell, fixture): the axis travels further than the handle by F / k_rig
* sampling: one sample every v * Ts of travel; the phase against the handle is random
* touch detection: travel zero is the first sample with F > F_touch
* reversal: the first sample with F >= F_rev (the PLC cannot react between samples)
* load cell: gain and zero error of the rig, white noise, resolution of the analog input (27648 counts
  for the 100 N range, the S7 scaling of an analog channel)
* axis encoder: noise and resolution
* compliance compensation: X = axis travel - (F - F_touch) / k_comp, with k_comp the stiffness the PLC
  believes in (it can be wrong)

Quasi-static: handle inertia and drive dynamics are not modelled. The viscous pivot term uses the mean
angular speed of the stroke.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from handletest import mechanism as mech


@dataclass(frozen=True)
class Rig:
    v: float = 50.0            # mm/s pull and return speed
    Ts: float = 0.002          # s, cyclic interrupt
    k_rig: float = 40.0        # N/mm true stiffness between axis and handle
    k_comp: float = 40.0       # N/mm stiffness used for compensation; 0 = no compensation
    sF: float = 0.03           # N, load cell noise (1 sigma)
    qF: float = 100.0 / 27648  # N, analog resolution
    gain: float = 0.0          # relative gain error of the force channel
    zero: float = 0.0          # N, zero error after taring
    sx: float = 0.003          # mm, encoder noise
    qx: float = 0.001          # mm, encoder resolution
    F_touch: float = 1.5       # N
    F_rev: float = 40.0        # N, reverse when reached
    x_max: float = 38.0        # mm, reverse at the latest here (no end stop found)

    @property
    def dx(self) -> float:
        return self.v * self.Ts


IDEAL = Rig(k_rig=1e9, k_comp=0.0, sF=0.0, qF=0.0, sx=0.0, qx=0.0, v=10.0, Ts=0.001)  # reference: rigid, slow, 0.01 mm per sample


def _q(x: np.ndarray, q: float) -> np.ndarray:
    return np.round(x / q) * q if q > 0 else x


def measure(pop: dict, rig: Rig, rng: np.random.Generator, grid: int = 1600) -> dict:
    """Sampled pull and return curves for every part of `pop`.

    Returns arrays aligned at the touch sample (index 0), NaN after the reversal sample:
      Xp, Fp   travel (mm, compensated) and force (N) on the pull stroke, shape (N, S)
      Xr, Fr   the same on the return stroke; index i is the sample at the same axis position as Xp[i]
      n        number of pull samples (touch to reversal, inclusive)
      touched  False if no touch was found
    """
    n = len(pop["M0"])
    th = np.linspace(0.0, 0.345, grid)
    xh = mech.travel_mm(th)
    omega = rig.v * 1e-3 / mech.R_PULL
    S = int(np.ceil((rig.x_max + 3.0) / rig.dx)) + 2
    out = {k: np.full((n, S), np.nan, dtype=np.float32) for k in ("Xp", "Fp", "Xr", "Fr")}
    out["n"] = np.zeros(n, dtype=int)
    out["touched"] = np.zeros(n, dtype=bool)
    j = np.arange(S + 8)
    for a0 in range(0, n, 2000):
        sl = slice(a0, min(n, a0 + 2000))
        sub = {k: v[sl] for k, v in pop.items()}
        mp, mr = mech.torques(sub, th, omega)
        fp_all = mech.force_n(mp, th[None, :])
        fr_all = mech.force_n(mr, th[None, :])
        for i in range(fp_all.shape[0]):
            fp, fr = fp_all[i], fr_all[i]
            a = (j - 4) * rig.dx + rng.uniform(0.0, rig.dx)     # axis positions, handle contact at a = 0
            # pull: the handle advances whenever the rig spring force exceeds its resistance (snap allowed)
            xa = xh + fp / rig.k_rig
            keep = xa >= np.maximum.accumulate(xa)
            xa_k = np.concatenate(([0.0], xa[keep]))
            f_k = np.concatenate(([0.0], fp[keep]))
            xh_k = np.concatenate(([0.0], xh[keep]))
            f_true = np.interp(a, xa_k, f_k, left=0.0)
            f_meas = _q(f_true * (1 + rig.gain) + rig.zero + rig.sF * rng.standard_normal(a.size), rig.qF)
            hit = np.nonzero(f_meas > rig.F_touch)[0]
            if hit.size == 0:
                continue
            jt = int(hit[0])
            a_enc = _q(a + rig.sx * rng.standard_normal(a.size), rig.qx)
            end = np.nonzero((f_meas >= rig.F_rev) | (a_enc - a_enc[jt] >= rig.x_max))[0]
            end = end[end >= jt]
            jr = int(end[0]) if end.size else a.size - 1
            m = min(jr - jt + 1, S)
            jr = jt + m - 1
            comp = (lambda f: (f - f_meas[jt]) / rig.k_comp) if rig.k_comp > 0 else (lambda f: 0.0)
            # return: first the friction reversal with the handle at rest, then the handle follows the hook
            x_rev = np.interp(a[jr], xa_k, xh_k)
            xa_r = xh + np.maximum(fr, 0.0) / rig.k_rig
            below = np.nonzero((fr <= 0.0) & (xh <= x_rev))[0]
            lo = int(below[-1]) + 1 if below.size else 0
            if lo < grid - 1:
                f_curve = np.interp(a[jt:jr + 1], xa_r[lo:], fr[lo:], left=0.0)
            else:
                f_curve = np.zeros(m)
            f_line = f_true[jr] - rig.k_rig * (a[jr] - a[jt:jr + 1])
            fr_true = np.clip(np.maximum(f_line, f_curve), 0.0, None)
            fr_meas = _q(fr_true * (1 + rig.gain) + rig.zero + rig.sF * rng.standard_normal(m), rig.qF)
            a_enc_r = _q(a[jt:jr + 1] + rig.sx * rng.standard_normal(m), rig.qx)
            k = a0 + i
            out["Fp"][k, :m] = f_meas[jt:jr + 1]
            out["Xp"][k, :m] = a_enc[jt:jr + 1] - a_enc[jt] - comp(f_meas[jt:jr + 1])
            out["Fr"][k, :m] = fr_meas
            out["Xr"][k, :m] = a_enc_r - a_enc[jt] - comp(fr_meas)
            out["n"][k] = m
            out["touched"][k] = True
    return out


def with_(rig: Rig, **kw) -> Rig:
    return replace(rig, **kw)
