"""Curve evaluation: features, windows, envelope. NumPy reference of what plc/FB_CurveEval.scl does.

The evaluation elements follow the way force-displacement monitoring units work (docs/SOURCES.md, M1):
a threshold line crossed at a set travel (force is read there), a window the curve must leave with its
peak inside, an envelope the curve must stay in. The return-stroke elements (mean and difference of the
pull and return force at one travel) are this study's addition.

Features (same names as the FB outputs):
  FpG1   pull force at gate 1 (GateX): spring + friction, before the cable is taut
  FrG1   return force at gate 1: spring - friction
  FMean  (FpG1 + FrG1) / 2: friction cancels, this is the spring
  FHyst  FpG1 - FrG1: twice the friction force
  FpG2   pull force at gate 2 (Gate2X): after cable take-up
  FPeak, XPeak   highest pull force inside [PeakXLo, PeakXHi] and its travel: latch release
  FStep  drop from the peak within StepSpan after it: the release step
  XStop  travel at which the pull force crosses StopF: end stop

Four evaluation methods (the alternatives of the trade study), `MODES`:
  1 peak      FPeak only
  2 pull      windows on the pull stroke: FpG1, FpG2, FPeak, XPeak, FStep, XStop
  3 pullret   as 2, but gate 1 is judged by FMean and FHyst, and FrG1 must stay above RetFMin
  4 envelope  the pull curve must stay inside an envelope at fixed travel nodes
"""

from __future__ import annotations

import numpy as np

RECIPE = dict(GateX=3.0, Gate2X=10.0, PeakXLo=13.0, PeakXHi=26.0, StepSpan=2.0, StopF=30.0,
              EnvX0=1.0, EnvDx=0.5, EnvN=55)
FEATURES = ("FpG1", "FrG1", "FMean", "FHyst", "FpG2", "FPeak", "XPeak", "FStep", "XStop")
MODES = {1: "peak", 2: "pull", 3: "pullret", 4: "envelope"}
# features with a two-sided statistical window, per mode
TWO_SIDED = {1: ("FPeak",), 2: ("FpG1", "FpG2", "FPeak", "XPeak", "XStop"),
             3: ("FMean", "FHyst", "FpG2", "FPeak", "XPeak", "XStop")}


def _cross_up(X: np.ndarray, F: np.ndarray, g: float) -> np.ndarray:
    """Force at travel g on the pull stroke: linear between the samples around the crossing."""
    ge = X >= g
    i = np.argmax(ge, axis=1)
    ok = ge.any(axis=1) & (i > 0)
    i0 = np.maximum(i - 1, 0)[:, None]
    x0, x1 = np.take_along_axis(X, i0, 1)[:, 0], np.take_along_axis(X, i[:, None], 1)[:, 0]
    f0, f1 = np.take_along_axis(F, i0, 1)[:, 0], np.take_along_axis(F, i[:, None], 1)[:, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        f = f0 + (f1 - f0) * (g - x0) / (x1 - x0)
    return np.where(ok & (x0 < g), f, np.nan)


def _cross_down(X: np.ndarray, F: np.ndarray, g: float, n: np.ndarray) -> np.ndarray:
    """Force at travel g on the return stroke (samples run from index n-1 down to 0)."""
    N, S = X.shape
    idx = np.arange(S)[None, :]
    valid = idx < n[:, None]
    le = (X <= g) & valid
    i = S - 1 - np.argmax(le[:, ::-1], axis=1)          # highest index at or below the gate: first in time
    ok = le.any(axis=1) & (i + 1 < n)
    i1 = np.minimum(i + 1, S - 1)[:, None]
    x0, x1 = np.take_along_axis(X, i1, 1)[:, 0], np.take_along_axis(X, i[:, None], 1)[:, 0]
    f0, f1 = np.take_along_axis(F, i1, 1)[:, 0], np.take_along_axis(F, i[:, None], 1)[:, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        f = f0 + (f1 - f0) * (g - x0) / (x1 - x0)
    return np.where(ok & (x0 > g), f, np.nan)


def features(c: dict, recipe: dict = RECIPE) -> dict:
    """Features of every measured part; NaN where the curve never gave the feature."""
    X, F, n = c["Xp"].astype(float), c["Fp"].astype(float), c["n"]
    Xr, Fr = c["Xr"].astype(float), c["Fr"].astype(float)
    N, S = X.shape
    idx = np.arange(S)[None, :]
    f = {}
    f["FpG1"] = _cross_up(X, F, recipe["GateX"])
    f["FpG2"] = _cross_up(X, F, recipe["Gate2X"])
    f["FrG1"] = _cross_down(Xr, Fr, recipe["GateX"], n)
    f["FMean"] = 0.5 * (f["FpG1"] + f["FrG1"])
    f["FHyst"] = f["FpG1"] - f["FrG1"]
    inwin = (X >= recipe["PeakXLo"]) & (X <= recipe["PeakXHi"])
    Fw = np.where(inwin, F, -np.inf)
    ip = np.argmax(Fw, axis=1)
    has = inwin.any(axis=1)
    f["FPeak"] = np.where(has, np.take_along_axis(F, ip[:, None], 1)[:, 0], np.nan)
    f["XPeak"] = np.where(has, np.take_along_axis(X, ip[:, None], 1)[:, 0], np.nan)
    after = (idx >= ip[:, None]) & (X <= (f["XPeak"] + recipe["StepSpan"])[:, None])
    fmin = np.min(np.where(after, F, np.inf), axis=1)
    f["FStep"] = np.where(has, f["FPeak"] - fmin, np.nan)
    Fs = np.where(X > recipe["Gate2X"], F, -np.inf)
    f["XStop"] = _cross_up_f(X, Fs, recipe["StopF"])
    f["touched"] = c["touched"]
    return f


def _cross_up_f(X: np.ndarray, F: np.ndarray, level: float) -> np.ndarray:
    """Travel at which the force first reaches `level` (beyond gate 2), linear between samples."""
    ge = F >= level
    i = np.argmax(ge, axis=1)
    ok = ge.any(axis=1) & (i > 0)
    i0 = np.maximum(i - 1, 0)[:, None]
    x0, x1 = np.take_along_axis(X, i0, 1)[:, 0], np.take_along_axis(X, i[:, None], 1)[:, 0]
    f0, f1 = np.take_along_axis(F, i0, 1)[:, 0], np.take_along_axis(F, i[:, None], 1)[:, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        x = x0 + (x1 - x0) * (level - f0) / (f1 - f0)
    return np.where(ok & np.isfinite(f0) & (f0 < level), x, np.nan)


def env_nodes(recipe: dict = RECIPE) -> np.ndarray:
    return recipe["EnvX0"] + recipe["EnvDx"] * np.arange(recipe["EnvN"])


def at_nodes(c: dict, recipe: dict = RECIPE) -> np.ndarray:
    """Pull force at every envelope node, shape (N, EnvN); NaN if the pull never reached the node."""
    X, F = c["Xp"].astype(float), c["Fp"].astype(float)
    return np.stack([_cross_up(X, F, g) for g in env_nodes(recipe)], axis=1)


# ---------------------------------------------------------------------------------------------------
# limits and verdicts
# ---------------------------------------------------------------------------------------------------

def stats(feat: dict) -> dict:
    return {k: (float(np.nanmean(feat[k])), float(np.nanstd(feat[k]))) for k in FEATURES}


def limits_for(mode: int, st: dict, k: float, fixed: dict) -> dict:
    """Window limits for one method: mean +/- k sigma of good parts, plus the fixed engineering limits.

    fixed: MeanLo (spring limit from the 30 g rule, as a force at gate 1), G1Lo (the same limit for the
    pull-only method, typical friction added), RetFMin (least return force at gate 1).
    """
    lim = {}
    for name in TWO_SIDED[mode]:
        m, s = st[name]
        lim[name] = [m - k * s, m + k * s]
    if mode == 3:
        lim["FMean"][0] = max(lim["FMean"][0], fixed["MeanLo"])
        lim["FrG1"] = [fixed["RetFMin"], np.inf]
    if mode == 2:
        lim["FpG1"][0] = max(lim["FpG1"][0], fixed["G1Lo"])
    if mode in (2, 3):
        m, s = st["FStep"]
        lim["FStep"] = [m - k * s, np.inf]
    return lim


def judge(feat: dict, lim: dict) -> np.ndarray:
    """True = part accepted. A feature that could not be measured (NaN) rejects the part."""
    ok = feat["touched"].copy()
    for name, (lo, hi) in lim.items():
        v = feat[name]
        with np.errstate(invalid="ignore"):
            ok &= (v >= lo) & (v <= hi)
    return ok


def judge_env(nodes_f: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return np.all((nodes_f >= lo[None, :]) & (nodes_f <= hi[None, :]), axis=1)


def envelope(nodes_f: np.ndarray, margin: float) -> tuple[np.ndarray, np.ndarray]:
    """Envelope that wraps a bundle of good curves: lowest and highest curve at every travel node,
    widened by a force margin (N)."""
    return np.nanmin(nodes_f, axis=0) - margin, np.nanmax(nodes_f, axis=0) + margin


def calibrate_k(mode: int, feat: dict, st: dict, fixed: dict, target: float) -> float:
    """Smallest k (window half-width in sigma) at which no more than `target` of good parts are rejected."""
    lo, hi = 1.0, 12.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        fr = 1.0 - judge(feat, limits_for(mode, st, mid, fixed)).mean()
        lo, hi = (mid, hi) if fr > target else (lo, mid)
    return hi
