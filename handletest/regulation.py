"""Inertial load on the handle and the minimum return-spring preload that follows from it.

Source read for this file (docs/SOURCES.md, R1): UN Regulation No. 11, text incorporating Supplement 2
to the 03 series of amendments (OJ L 120, 13.5.2010).

* 6.1.4.3: the combined resistance to unlatching "must assure that the door latch system ... will remain
  latched when subjected to an inertial load of 30 g".
* Annex 4, 2.1.1: "Spring forces are the average of the minimum spring output in the installed position
  and the minimum spring output in the release position. Friction effects and work to be done are not
  considered in the calculations."

Design rule of THIS study (stricter than the regulation, which allows the whole latch system to share the
load): the handle must hold itself closed at 30 g with its own spring, so that it puts no load into the
latch cable. Friction is not counted, as in Annex 4.

`figure_4_1()` recomputes the sample calculation printed in Annex 4, Figure 4-1 of the same text; the test
suite compares it with the printed results.
"""

from __future__ import annotations

from handletest.mechanism import G0, NOM, R_PULL, spring_rate

A_G = 30.0   # g, UN R11 6.1.4.1 / 6.1.4.3

# Moving masses of the handle about its pivot [A]. arm > 0: the inertia force of this mass tends to OPEN
# the handle when the door is accelerated in the vehicle transverse direction; arm < 0: tends to close it.
MASSES = (
    ("grip (painted lever)", 0.110, +0.040),
    ("counterweight", 0.060, -0.045),
    ("latch lever and cable end", 0.012, +0.010),
)


def unbalance(masses=MASSES) -> float:
    """Static moment of the moving parts about the pivot, kg m (positive = opens under transverse g)."""
    return sum(m * arm for _, m, arm in masses)


def opening_torque(a_g: float = A_G, masses=MASSES) -> float:
    """Torque about the pivot that tries to open the handle at a_g, N m."""
    return a_g * G0 * unbalance(masses)


def spring_average_torque(M0: float, ks: float, th_release: float) -> float:
    """Annex 4, 2.1.1: average of the spring output installed (rest) and at the release position."""
    return 0.5 * (M0 + (M0 + ks * th_release))


def min_preload(ks: float, th_release: float, a_g: float = A_G, masses=MASSES) -> float:
    """Smallest spring preload M0 (N m) at which the average spring torque equals the 30 g opening torque."""
    return opening_torque(a_g, masses) - 0.5 * ks * th_release


def summary() -> dict:
    ks = float(spring_rate(NOM["d"], NOM["D"], NOM["Na"], NOM["E"]))
    th_rel = NOM["play"] + NOM["rel"]
    m0 = ks * NOM["th0"]
    m_open = opening_torque()
    no_cw = tuple(m for m in MASSES if m[0] != "counterweight")
    m0_min = min_preload(ks, th_rel)
    return dict(
        a_g=A_G,
        unbalance_kgm=unbalance(),
        opening_torque_nm=m_open,
        opening_torque_no_counterweight_nm=opening_torque(masses=no_cw),
        spring_rate_nm_per_rad=ks,
        release_angle_rad=th_rel,
        nominal_preload_nm=m0,
        nominal_average_spring_torque_nm=spring_average_torque(m0, ks, th_rel),
        min_preload_nm=m0_min,
        min_preload_fraction_of_nominal=m0_min / m0,
        margin_nominal=spring_average_torque(m0, ks, th_rel) / m_open,
        g_held_nominal=spring_average_torque(m0, ks, th_rel) / (G0 * unbalance()),
        min_preload_force_at_pull_point_n=m0_min / R_PULL,
    )


def figure_4_1() -> dict:
    """UN R11 Annex 4, Figure 4-1 'Inertial loading - Sample calculation', recomputed (kgf, mm)."""
    a = 30.0                                   # g; with masses in kg the product is in kgf
    knob_spring, pawl_spring = 0.459, 0.0459   # kgf, kgf m
    M1, M2, M3, M4 = 0.0163, 0.0227, 0.0122, 0.0422
    d1, d2, d3, d4, d5, d6 = 31.50, 10.67, 4.83, 31.50, 37.59, 1.90
    F1 = M1 * a - knob_spring
    F2 = M2 * a
    F3 = M3 / 2 * a
    Mo = F1 * d1 + F2 * d2 - F3 * d3
    F5 = Mo / d4
    F6 = M4 * a
    net = pawl_spring - (F5 * d5 + F6 * d6) / 1000.0
    return dict(F1=F1, F2=F2, F3=F3, Mo=Mo, F5=F5, F6=F6, net_kgf_m=net)
