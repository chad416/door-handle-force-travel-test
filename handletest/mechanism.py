"""Exterior door-handle mechanism: lever, torsion return spring, pivot friction, latch load, end stop.

All parameter VALUES are illustrative (tag [A] in DOSSIER.md section 8). The relations are textbook ones:

* helical torsion spring rate per radian  k = d^4 E / (64 D Na)           Shigley eq. (10-49)
* bending stress at the inner fibre       sigma = Ki 32 M / (pi d^3)       Shigley eq. (10-44)
  with                                    Ki = (4C^2 - C - 1) / (4C (C - 1))   eq. (10-43), C = D/d
* pivot friction: Coulomb torque (sign of the velocity) plus a viscous term proportional to speed.

Geometry: the test rig pulls the grip in a straight line, perpendicular to the lever at rest, at radius
R_PULL from the pivot. With the handle at angle th the travel of the pull point is x = R sin(th) and the
force that balances a pivot torque M is F = M / (R cos(th)).

Units: SI inside this module (N m, rad); helper functions give mm and N at the pull point.
"""

from __future__ import annotations

import numpy as np

R_PULL = 0.100      # m, pivot to pull point [A]
R_LATCH = 0.025     # m, pivot to the cable pin on the latch lever [A]
G0 = 9.80665        # m/s2

# nominal part [A]
NOM = dict(
    d=1.8e-3, D=13.0e-3, Na=6.0, E=206e9,   # spring wire, mean coil diameter, active turns, modulus
    th0=1.40,                               # rad, wind-up of the spring at handle rest (gives the preload)
    Mc=0.080,                               # N m, Coulomb friction torque of the pivot
    cv=0.004,                               # N m s/rad, viscous friction (grease)
    play=0.060,                             # rad, free travel before the cable is taut
    Fl0=12.0,                               # N, cable load at take-up (latch simulator preload)
    kl=2000.0,                              # N/m, rate of the latch simulator along the cable
    Fd=16.0,                                # N, extra cable load of the release detent just before release
    rel=0.140,                              # rad after take-up at which the detent releases
    th_e=0.300,                             # rad, end stop
)
RAMP = 0.050        # rad, detent load builds up over this angle before release
DROP = 0.006        # rad, detent load falls over this angle at release (the "step")
TAKEUP = 0.004      # rad, cable take-up is not perfectly sharp
K_STOP = 600.0      # N m/rad, end-stop stiffness (60 N/mm at the pull point)

# part-to-part spread of good parts [A]
SPREAD = dict(d=0.006e-3, th0=0.050, Mc_gsd=1.35, cv_rel=0.20, play=0.006, Fl0=0.6, kl_rel=0.05,
              Fd=1.0, rel=0.004, th_e=0.003)

D_WRONG_VARIANT = 1.6e-3   # m, wire of the spring that belongs to another handle variant [A]

DEFECTS = ("missing_spring", "wrong_variant_spring", "weak_spring", "binding_pivot", "latch_lever_unhooked",
           "wrong_hand_spring", "particle_at_stop")


def spring_rate(d: float | np.ndarray, D: float, Na: float, E: float) -> float | np.ndarray:
    """Torque per radian of a helical torsion spring, Shigley eq. (10-49)."""
    return d ** 4 * E / (64.0 * D * Na)


def spring_stress(M: float, d: float, D: float) -> float:
    """Bending stress at the inner fibre of the coil, Shigley eqs. (10-43), (10-44). Pa."""
    C = D / d
    Ki = (4 * C * C - C - 1) / (4 * C * (C - 1))
    return Ki * 32.0 * M / (np.pi * d ** 3)


def nominal() -> dict[str, np.ndarray]:
    """One nominal part as a population of size 1."""
    return sample_good(1, np.random.default_rng(0), spread=0.0)


def sample_good(n: int, rng: np.random.Generator, spread: float = 1.0, scale: dict | None = None) -> dict:
    """n correctly assembled parts. `scale` multiplies single spreads (sensitivity study)."""
    sc = {k: spread * (scale or {}).get(k, 1.0) for k in SPREAD}
    z = lambda: rng.standard_normal(n)
    d = NOM["d"] + sc["d"] * SPREAD["d"] * z()
    th0 = NOM["th0"] + sc["th0"] * SPREAD["th0"] * z()
    ks = spring_rate(d, NOM["D"], NOM["Na"], NOM["E"])
    gsd = 1.0 + sc["Mc_gsd"] * (SPREAD["Mc_gsd"] - 1.0)
    pop = dict(
        ks=ks, M0=ks * th0, th_free=np.zeros(n),
        Mc=NOM["Mc"] * np.exp(np.log(gsd) * z()),
        cv=NOM["cv"] * (1 + sc["cv_rel"] * SPREAD["cv_rel"] * z()),
        play=NOM["play"] + sc["play"] * SPREAD["play"] * z(),
        Fl0=NOM["Fl0"] + sc["Fl0"] * SPREAD["Fl0"] * z(),
        kl=NOM["kl"] * (1 + sc["kl_rel"] * SPREAD["kl_rel"] * z()),
        Fd=NOM["Fd"] + sc["Fd"] * SPREAD["Fd"] * z(),
        rel=NOM["rel"] + sc["rel"] * SPREAD["rel"] * z(),
        th_e=NOM["th_e"] + sc["th_e"] * SPREAD["th_e"] * z(),
        latch=np.ones(n),
    )
    return pop


def apply_defect(pop: dict, name: str, rng: np.random.Generator, severity: float | None = None) -> dict:
    """Return a copy of `pop` in which every part carries the defect.

    severity (optional) fixes the defect size instead of drawing it:
      weak_spring       remaining fraction of the preload wind-up (default: uniform 0.50 to 0.80)
      binding_pivot     added Coulomb torque in N m (default: uniform 0.15 to 0.60)
      particle_at_stop  travel lost at the pull point in mm (default: uniform 0.5 to 3.0)
    """
    p = {k: v.copy() for k, v in pop.items()}
    n = len(p["M0"])
    if name == "missing_spring":            # spring not fitted: no preload, no rate
        p["M0"][:] = 0.0
        p["ks"][:] = 0.0
    elif name == "wrong_variant_spring":    # thinner wire, same coil and legs: rate and preload scale with d^4
        f = (D_WRONG_VARIANT / NOM["d"]) ** 4
        p["M0"] *= f
        p["ks"] *= f
    elif name == "weak_spring":             # leg not in its seat / spring has taken a set: wind-up lost
        f = np.full(n, severity) if severity is not None else rng.uniform(0.50, 0.80, n)
        p["M0"] *= f
    elif name == "binding_pivot":           # paint overspray in the pivot bore
        add = np.full(n, severity) if severity is not None else rng.uniform(0.15, 0.60, n)
        p["Mc"] += add
    elif name == "latch_lever_unhooked":    # lever missing or cable not hooked: no latch load at all
        p["latch"][:] = 0.0
    elif name == "wrong_hand_spring":       # mirror-image spring: legs meet their seats only after a free angle
        p["th_free"] = rng.uniform(0.10, 0.20, n)
        p["M0"][:] = 0.0
    elif name == "particle_at_stop":        # chip between handle and bumper: the stop comes early
        mm = np.full(n, severity) if severity is not None else rng.uniform(0.5, 3.0, n)
        p["th_e"] -= mm * 1e-3 / R_PULL
    else:
        raise KeyError(name)
    return p


def torques(pop: dict, th: np.ndarray, omega: float) -> tuple[np.ndarray, np.ndarray]:
    """Pivot torque needed to move the handle on the pull stroke and held on the return stroke.

    pop arrays have shape (N,), th has shape (G,). Returns (M_pull, M_return), shape (N, G), N m.
    omega is the angular speed magnitude (rad/s) for the viscous term.
    """
    c = lambda k: pop[k][:, None]
    t = th[None, :]
    spring = np.where(t >= c("th_free"), c("M0") + c("ks") * (t - c("th_free")), 0.0)
    past = t - c("play")
    cable = np.clip(past / TAKEUP, 0.0, 1.0) * (c("Fl0") + c("kl") * R_LATCH * np.maximum(past, 0.0))
    up = np.clip((past - (c("rel") - RAMP)) / RAMP, 0.0, 1.0)
    down = np.clip(1.0 - (past - c("rel")) / DROP, 0.0, 1.0)
    detent = c("Fd") * np.where(past < c("rel"), up, down)
    stop = K_STOP * np.maximum(t - c("th_e"), 0.0)
    fric = c("Mc") + c("cv") * omega
    m_pull = spring + c("latch") * (cable + detent) * R_LATCH + stop + fric
    m_ret = spring + c("latch") * cable * R_LATCH + stop - fric
    return m_pull, m_ret


def travel_mm(th: np.ndarray) -> np.ndarray:
    return 1e3 * R_PULL * np.sin(th)


def force_n(M: np.ndarray, th: np.ndarray) -> np.ndarray:
    return M / (R_PULL * np.cos(th))


def theta_of_travel(x_mm: float) -> float:
    return float(np.arcsin(x_mm * 1e-3 / R_PULL))
