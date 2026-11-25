"""Line model and OEE terms."""

import numpy as np
import pytest

from handletest import line
from handletest import mechanism as mech


def _week(**kw):
    det = {d: 1.0 for d in mech.DEFECTS}
    args = dict(t_test_ok=1.75, t_unload=1.0, detection=det, p_false_reject=0.002)
    args.update(kw)
    return line.simulate_week(np.random.default_rng(5), **args)


def test_oee_is_the_product_of_its_three_terms_and_equals_good_time_over_planned_time():
    w = _week()
    assert w["oee"] == pytest.approx(w["availability"] * w["effectiveness"] * w["quality"])
    assert w["oee"] == pytest.approx(w["PRI"] * w["GQ"] / w["PBT"])
    assert w["PBT"] == 15 * 7.5 * 3600
    assert 0 < w["effectiveness"] <= 1 and 0 < w["availability"] < 1


def test_time_is_accounted_for():
    w = _week()
    used = w["PQ"] * w["PRI"] + w["micro_s"] + w["lock_true_s"] + w["lock_false_s"] + w["logged_stop_s"]
    assert w["PBT"] - 200 < used <= w["PBT"] + 1e-6      # at most one unfinished part is left over


def test_false_rejects_cost_parts_and_time():
    a, b = _week(p_false_reject=0.0), _week(p_false_reject=0.02)
    assert a["false_rejects"] == 0 and b["false_rejects"] > 400
    assert b["GQ"] < a["GQ"] and b["lock_false_s"] > 0 and a["lock_false_s"] == 0


def test_escapes_follow_detection():
    none = _week(detection={d: 0.0 for d in mech.DEFECTS})
    full = _week()
    assert full["escapes"] == 0
    assert none["escapes"] > 0
    assert none["true_rejects"] > 0          # wrong-hand units are still stopped by the variant sensors
