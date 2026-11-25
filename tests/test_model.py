"""Mechanism, spring, the 30 g rule and the rig model."""

import numpy as np
import pytest

from handletest import mechanism as mech
from handletest import msa, regulation
from handletest.evaluate import RECIPE, features
from handletest.rig import IDEAL, Rig, measure


def test_un_r11_figure_4_1_sample_calculation():
    # results printed in UN R11 Annex 4, Figure 4-1 (docs/SOURCES.md, R1)
    f = regulation.figure_4_1()
    assert f["F1"] == pytest.approx(0.03, abs=0.001)
    assert f["F2"] == pytest.approx(0.681, abs=0.001)
    assert f["F3"] == pytest.approx(0.183, abs=0.001)
    assert f["Mo"] == pytest.approx(7.33, abs=0.01)
    assert f["F5"] == pytest.approx(0.2328, abs=0.0005)
    assert f["F6"] == pytest.approx(1.266, abs=0.001)
    assert f["net_kgf_m"] == pytest.approx(0.0347, abs=0.0001)


def test_spring_rate_and_stress_formulas():
    # rate per radian = rate per turn / (2 pi), Shigley eq. (10-50): k' = d^4 E / (10.2 D Na)
    d, D, Na, E = 1.8e-3, 13e-3, 6.0, 206e9
    assert 2 * np.pi * mech.spring_rate(d, D, Na, E) == pytest.approx(d ** 4 * E / (10.2 * D * Na), rel=0.002)
    # Ki tends to 1 for a large spring index: stress tends to that of a straight round bar, 32 M / (pi d^3)
    assert mech.spring_stress(1.0, 1e-3, 1.0) == pytest.approx(32 / (np.pi * 1e-9), rel=0.002)
    assert mech.spring_stress(1.0, d, D) > 32 / (np.pi * d ** 3)


def test_min_preload_balances_30_g():
    r = regulation.summary()
    avg = regulation.spring_average_torque(r["min_preload_nm"], r["spring_rate_nm_per_rad"], r["release_angle_rad"])
    assert avg == pytest.approx(r["opening_torque_nm"], rel=1e-12)
    assert r["opening_torque_nm"] == pytest.approx(30 * mech.G0 * regulation.unbalance())
    assert 1.0 < r["margin_nominal"] < 1.5
    assert r["opening_torque_no_counterweight_nm"] > r["nominal_average_spring_torque_nm"]


def test_torque_balance_of_the_nominal_part():
    p = mech.nominal()
    th = np.array([mech.theta_of_travel(RECIPE["GateX"])])
    mp, mr = mech.torques(p, th, omega=0.0)
    spring = p["M0"][0] + p["ks"][0] * th[0]            # gate 1 lies before the cable take-up
    assert mp[0, 0] == pytest.approx(spring + p["Mc"][0])
    assert mr[0, 0] == pytest.approx(spring - p["Mc"][0])
    assert th[0] < p["play"][0]


def test_ideal_rig_reads_spring_and_friction_at_gate_1():
    p = mech.nominal()
    f = features(measure(p, IDEAL, np.random.default_rng(0), grid=6000))
    th = mech.theta_of_travel(RECIPE["GateX"])
    lever = mech.R_PULL * np.cos(th)
    cv = p["cv"][0] * IDEAL.v * 1e-3 / mech.R_PULL
    assert f["FMean"][0] == pytest.approx((p["M0"][0] + p["ks"][0] * th) / lever, abs=0.01)
    assert f["FHyst"][0] == pytest.approx(2 * (p["Mc"][0] + cv) / lever, abs=0.01)
    assert f["XStop"][0] == pytest.approx(1e3 * mech.R_PULL * np.sin(p["th_e"][0]), abs=0.6)
    assert f["FStep"][0] == pytest.approx(p["Fd"][0] * mech.R_LATCH / mech.R_PULL, rel=0.08)


def test_each_defect_moves_the_feature_it_should():
    rng = np.random.default_rng(3)
    good = mech.sample_good(200, rng)
    rig = Rig()
    f0 = features(measure(good, rig, rng))

    def med(f, k):
        return float(np.nanmedian(f[k]))

    f = {d: features(measure(mech.apply_defect(good, d, rng), rig, rng)) for d in mech.DEFECTS}
    assert med(f["wrong_variant_spring"], "FMean") < 0.7 * med(f0, "FMean")
    assert med(f["weak_spring"], "FMean") < 0.85 * med(f0, "FMean")
    assert med(f["binding_pivot"], "FHyst") > 3 * med(f0, "FHyst")
    assert med(f["binding_pivot"], "FMean") == pytest.approx(med(f0, "FMean"), abs=0.1)   # friction cancels
    assert med(f["latch_lever_unhooked"], "FStep") < 0.3
    assert med(f["particle_at_stop"], "XStop") < med(f0, "XStop") - 1.0
    assert med(f["particle_at_stop"], "FPeak") == pytest.approx(med(f0, "FPeak"), abs=0.15)


def test_compliance_shifts_travel_unless_compensated():
    rng = np.random.default_rng(4)
    ref = msa.reference()
    on = msa.repeats(Rig(), rng, 20)
    off = msa.repeats(Rig(k_comp=0.0), rng, 20)
    assert abs(np.mean(on["XStop"]) - ref["XStop"]) < 0.1
    # uncompensated: deflection (30 N - touch force) / k_rig
    assert np.mean(off["XStop"]) - ref["XStop"] == pytest.approx((30 - 1.5) / 40, abs=0.15)


def test_type1_formulas():
    # Cg = 0.2 T / (6 s); with no bias Cgk = Cg; a bias of 0.1 T gives Cgk = 0
    assert msa.cg(6.0, 0.1) == pytest.approx(2.0)
    assert msa.cgk(6.0, 0.1, 5.0, 5.0) == pytest.approx(msa.cg(6.0, 0.1))
    assert msa.cgk(6.0, 0.1, 5.6, 5.0) == pytest.approx(0.0, abs=1e-12)
