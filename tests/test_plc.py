"""The SCL blocks: same samples as the NumPy evaluation, and the station sequence against the plant."""

import numpy as np
import pytest

from handletest import evaluate as ev
from handletest import mechanism as mech
from handletest import regulation
from handletest import station as stn
from handletest.rig import Rig, measure, with_
from handletest.study import Methods, fixed_limits

RIG = Rig()


@pytest.fixture(scope="module")
def methods():
    rng = np.random.default_rng(11)
    return Methods(RIG, 3000, rng, fixed_limits(regulation.summary(), 0.02, 0.03))


def test_scl_sources_translate():
    fb = stn.blocks()
    assert set(fb) == {"FB_CurveEval", "FB_HandleStation"}


def test_curve_eval_scl_equals_numpy_on_the_same_samples(methods):
    rng = np.random.default_rng(12)
    base = mech.sample_good(6, rng)
    pops = [base] + [mech.apply_defect(base, d, rng) for d in mech.DEFECTS]
    for pop in pops:
        c = measure(pop, RIG, rng)
        feat, acc = ev.features(c), methods.accept(c)
        for i in range(6):
            for mode in (1, 2, 3, 4):
                r = stn.replay(c, i, mode, methods.lim.get(mode), methods.env)
                assert r["ok"] == bool(acc[mode][i]), (mode, i, r)
            for k in ev.FEATURES:
                if np.isfinite(feat[k][i]):
                    assert r["feat"][k] == pytest.approx(float(feat[k][i]), abs=2e-4), k


def _cycle(methods, part, rng, mode=3, **kw):
    st = stn.new_station(RIG)
    stn.load_recipe(st.Eval, mode, methods.lim.get(mode), methods.env)
    pl = stn.Plant(part, RIG, rng, **kw)
    return st, pl, stn.run_cycle(st, pl, t_reject=1.0)


def test_good_part_passes_and_closed_loop_features_match_the_rig_model(methods):
    rng = np.random.default_rng(13)
    part = mech.nominal()
    st, pl, r = _cycle(methods, part, rng)
    assert r["verdict"] == 1 and r["nok"] == 0
    assert int(st.CntOk) == 1 and int(st.CntNok) == 0 and int(st.CntTotal) == 1
    ref = ev.features(measure(part, with_(RIG, sF=0.0), rng))
    for k, tol in (("FMean", 0.08), ("FHyst", 0.12), ("FpG2", 0.1), ("FPeak", 0.12), ("XPeak", 0.12),
                   ("FStep", 0.15), ("XStop", 0.05)):
        assert r["feat"][k] == pytest.approx(float(ref[k][0]), abs=tol), k
    assert 1.0 < r["t_test"] < 2.5
    assert r["f_peak_true"] < 60.0


@pytest.mark.parametrize("defect,codes", [("wrong_variant_spring", {2}), ("binding_pivot", {3}),
                                           ("latch_lever_unhooked", {5}), ("missing_spring", {21}),
                                           ("wrong_hand_spring", {21})])
def test_defects_are_rejected_with_the_expected_code(methods, defect, codes):
    rng = np.random.default_rng(14)
    part = mech.apply_defect(mech.nominal(), defect, rng)
    st, pl, r = _cycle(methods, part, rng)
    assert r["verdict"] == 2 and r["nok"] in codes


def test_particle_of_2_mm_is_rejected_on_the_stop_travel(methods):
    rng = np.random.default_rng(15)
    st, pl, r = _cycle(methods, mech.apply_defect(mech.nominal(), "particle_at_stop", rng, severity=2.0), rng)
    assert r["verdict"] == 2 and r["nok"] == 9


def test_wrong_hand_unit_is_never_pulled(methods):
    rng = np.random.default_rng(16)
    st = stn.new_station(RIG, variant_lh=True)
    stn.load_recipe(st.Eval, 3, methods.lim[3], methods.env)
    pl = stn.Plant(mech.nominal(), RIG, rng, hand_lh=False)
    for _ in range(400):
        stn.scan(st, pl)
    assert int(st.Verdict) == 2 and int(st.NokCode) == 20 and int(st.State) == 8
    assert pl.pos == 0.0 and pl.clamp == 0.0          # axis never moved, clamp never closed


def test_reject_locks_the_station_until_the_part_is_in_the_chute(methods):
    rng = np.random.default_rng(17)
    st = stn.new_station(RIG)
    stn.load_recipe(st.Eval, 3, methods.lim[3], methods.env)
    pl = stn.Plant(mech.apply_defect(mech.nominal(), "binding_pivot", rng, severity=0.4), RIG, rng)
    for _ in range(1500):
        stn.scan(st, pl)
    assert int(st.State) == 8 and bool(st.Locked) and int(st.Verdict) == 2
    # the rejected part is taken out and a NEW part is put in without using the chute: no start
    pl.present = False
    for _ in range(100):
        stn.scan(st, pl)
    pl2 = stn.Plant(mech.nominal(), RIG, rng)
    for _ in range(600):
        stn.scan(st, pl2)
    assert int(st.State) == 8 and pl2.pos == 0.0 and int(st.CntTotal) == 1
    # the chute sensor sees the rejected part: released
    pl2.present = False
    for _ in range(10):
        stn.scan(st, pl2)
    stn.scan(st, pl2, RejectChute=True)
    assert int(st.State) == 0 and not bool(st.Locked) and int(st.CntRejectConfirmed) == 1
    stn.scan(st, pl2, RejectChute=False)


def test_chute_signal_before_the_part_has_left_does_not_release(methods):
    rng = np.random.default_rng(18)
    st = stn.new_station(RIG)
    stn.load_recipe(st.Eval, 3, methods.lim[3], methods.env)
    pl = stn.Plant(mech.apply_defect(mech.nominal(), "latch_lever_unhooked", rng), RIG, rng)
    for _ in range(1500):
        stn.scan(st, pl)
    assert int(st.State) == 8
    stn.scan(st, pl, RejectChute=True)      # something passes the light barrier while the part is still clamped in
    stn.scan(st, pl, RejectChute=False)
    assert int(st.State) == 8 and bool(st.Locked)


def test_fault_during_the_pull_makes_the_part_a_reject_and_keeps_the_lock(methods):
    rng = np.random.default_rng(19)
    st = stn.new_station(RIG)
    stn.load_recipe(st.Eval, 3, methods.lim[3], methods.env)
    pl = stn.Plant(mech.nominal(), RIG, rng)
    while int(st.State) != 4:
        stn.scan(st, pl)
    for _ in range(50):
        stn.scan(st, pl)
    stn.scan(st, pl, SafetyOk=False)        # light curtain broken in the middle of the pull
    assert int(st.State) == 9 and int(st.FaultCode) == 1 and not bool(st.QDriveEnable)
    for _ in range(100):
        stn.scan(st, pl)
    assert pl.vel == 0.0
    stn.scan(st, pl, SafetyOk=True, AckFault=True)
    st.AckFault = False
    for _ in range(1500):
        stn.scan(st, pl)
    assert int(st.Verdict) == 2 and int(st.NokCode) == 24 and int(st.State) == 8
    # a second fault while locked: after the acknowledge the station is still locked
    stn.scan(st, pl, DriveOk=False)
    stn.scan(st, pl, DriveOk=True, AckFault=True)
    st.AckFault = False
    for _ in range(50):
        stn.scan(st, pl)
    assert int(st.State) == 8


def test_three_rejects_in_a_row_ask_for_the_master_part(methods):
    rng = np.random.default_rng(20)
    st = stn.new_station(RIG)
    stn.load_recipe(st.Eval, 3, methods.lim[3], methods.env)
    bad = mech.apply_defect(mech.nominal(), "latch_lever_unhooked", rng)
    for _ in range(3):
        stn.run_cycle(st, stn.Plant(bad, RIG, rng), t_reject=0.5)
    assert bool(st.RigCheckRequired) and int(st.CntConsecNok) == 3 and int(st.CntByCode[5]) == 3
    pl = stn.Plant(mech.nominal(), RIG, rng)
    for _ in range(500):
        stn.scan(st, pl)
    assert int(st.State) == 0 and pl.pos == 0.0        # start blocked
    stn.scan(st, pl, AckFault=True)
    st.AckFault = False
    r = stn.run_cycle(st, pl)
    assert r["verdict"] == 1 and int(st.CntConsecNok) == 0
