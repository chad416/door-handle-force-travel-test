"""The PLC test bench (plc/test) run through the translator: the same sources that go into the TIA Portal
test project, with their data blocks and OB1. What passes here is what DB_TestResult must show in PLCSIM."""

import json
from pathlib import Path

import numpy as np
import pytest

from handletest import evaluate as ev
from handletest import mechanism as mech
from handletest import scl
from handletest import station as stn
from handletest.rig import Rig, measure

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "plc" / n for n in ("FB_CurveEval.scl", "FB_HandleStation.scl", "test/DB_TestData.scl",
                                       "test/DB_TestResult.scl", "test/FB_TestPlant.scl", "test/FB_TestBench.scl",
                                       "test/OB_Main.scl")]
INFO = json.loads((ROOT / "results" / "plcsim_bench_cases.json").read_text(encoding="utf-8"))


def run(prog, max_calls: int = 2000) -> int:
    """Call OB1 until the bench reports Done. Returns the number of OB1 cycles."""
    for n in range(1, max_calls + 1):
        prog.ob["Main"]()
        if prog.db["DB_TestResult"].Done:
            return n
    raise AssertionError("bench did not finish")


def test_bench_passes_every_case():
    prog = scl.load_program(SOURCES)
    assert set(prog.ob) == {"Main"} and "InstTestBench" in prog.db
    calls = run(prog)
    r = prog.db["DB_TestResult"]
    total = INFO["cases_total"]
    assert total == 20 and INFO["replay_cases"] == prog.db["DB_TestData"].NCases == 14
    assert r.Done and r.AllPassed
    assert (r.CasesTotal, r.CasesRun, r.CasesPassed, r.CasesFailed) == (total, total, total, 0)
    assert (r.FirstFailedCase, r.FirstFailedCheck) == (0, 0)
    assert r.CasePass == [True] * total + [False] * (32 - total)
    assert r.CaseCheck == [0] * 32
    assert float(r.MaxFeatError) < float(prog.db["DB_TestData"].Tol) / 10
    assert int(r.BenchCalls) == calls == INFO["translator"]["BenchCalls"]       # the count docs/PLCSIM_RUN.md gives
    assert INFO["translator"]["AllPassed"] and INFO["translator"]["CaseNok"] == r.CaseNok[:total]
    # NOK codes the blocks gave: replay cases as listed by the generator, then the six station cases
    expected_nok = [c["expected_nok"] for c in INFO["cases"] if c["kind"] == "replay"] + [0, 20, 20, 5, 5, 0]
    assert r.CaseNok[:total] == expected_nok
    # the station really ran: five units judged, two passed, three rejects confirmed in the chute
    st = prog.db["InstTestBench"].Station
    assert (int(st.CntTotal), int(st.CntOk), int(st.CntNok), int(st.CntRejectConfirmed)) == (5, 2, 3, 3)
    assert int(st.CntByCode[20]) == 1 and int(st.CntByCode[5]) == 2 and int(st.State) == 0


def test_bench_holds_its_result_after_done():
    prog = scl.load_program(SOURCES)
    run(prog)
    r = prog.db["DB_TestResult"]
    before = dict(vars(r))
    before = {k: (list(v) if isinstance(v, list) else v) for k, v in before.items()}
    for _ in range(50):
        prog.ob["Main"]()
    assert {k: (list(v) if isinstance(v, list) else v) for k, v in vars(r).items()} == before


@pytest.mark.parametrize("case,elem", [(1, 0), (5, 8), (14, 5)])
def test_bench_reports_a_wrong_element(case, elem):
    prog = scl.load_program(SOURCES)
    d = prog.db["DB_TestData"]
    d.ExpFeat[(case - 1) * 9 + elem] += np.float32(0.01)
    run(prog)
    r = prog.db["DB_TestResult"]
    assert r.Done and not r.AllPassed
    assert (r.CasesFailed, r.FirstFailedCase, r.FirstFailedCheck) == (1, case, 3 + elem)
    assert not r.CasePass[case - 1] and r.CaseCheck[case - 1] == 3 + elem and r.CasesPassed == r.CasesTotal - 1


def test_bench_reports_a_wrong_verdict_and_a_wrong_code():
    prog = scl.load_program(SOURCES)
    d = prog.db["DB_TestData"]
    d.ExpOk[2] = True            # case 3 (missing spring) expected OK: verdict check must fail
    d.ExpNok[6] = 6              # case 7 (unhooked lever) expected code 6 instead of 5
    run(prog)
    r = prog.db["DB_TestResult"]
    assert (r.CasesFailed, r.FirstFailedCase, r.FirstFailedCheck) == (2, 3, 1)
    assert r.CaseCheck[2] == 1 and r.CaseCheck[6] == 2


def test_bench_reports_a_station_that_does_not_reject():
    prog = scl.load_program(SOURCES)
    d = prog.db["DB_TestData"]
    d.BadCurve = d.GoodCurve     # the "defective" unit of the station scenario is in fact good
    run(prog)
    r = prog.db["DB_TestResult"]
    n = d.NCases
    assert r.Done and not r.AllPassed and r.CasesRun == r.CasesTotal
    assert (r.FirstFailedCase, r.FirstFailedCheck) == (n + 4, 21)
    assert r.CasePass[: n + 3] == [True] * (n + 3)


def test_bench_reports_a_reject_lock_that_opens_too_early():
    """A station block without the lock (part gone is forced true) must fail case NCases+3."""
    src = [p.read_text(encoding="utf-8") for p in SOURCES]
    old = "IF #sPartGone AND #tChuteEdge THEN"
    assert old in src[1]
    src[1] = src[1].replace(old, "IF #tChuteEdge THEN")
    code, _ = scl.translate(src)
    ns = {"_FB": {}, "_DB": {}, "_OB": {}}
    exec(compile(code, "<scl>", "exec"), ns)
    for _ in range(2000):
        ns["_OB"]["Main"]()
        if ns["_DB"]["DB_TestResult"].Done:
            break
    r = ns["_DB"]["DB_TestResult"]
    assert r.Done and (r.FirstFailedCase, r.FirstFailedCheck) == (ns["_DB"]["DB_TestData"].NCases + 3, 26)


def test_translator_refuses_what_the_bench_must_not_do():
    fb = "\n".join(p.read_text(encoding="utf-8") for p in SOURCES[:2])
    bad_static = fb + '''
FUNCTION_BLOCK "FB_X"
   VAR
      St : "FB_HandleStation";
      a : Int;
   END_VAR
BEGIN
	#a := #St.sState;
END_FUNCTION_BLOCK
'''
    with pytest.raises(scl.SclError, match="not an input, an output or an instance"):
        scl.translate([bad_static])
    bad_write = bad_static.replace("#a := #St.sState;", "#St.State := 3;")
    with pytest.raises(scl.SclError, match="not allowed"):
        scl.translate([bad_write])
    with pytest.raises(scl.SclError, match="unknown data block"):
        scl.translate([bad_static.replace("#a := #St.sState;", '#a := "DB_None".x;')])


def test_numpy_nok_code_agrees_with_the_verdict_and_with_the_scl_block():
    """The expected NOK codes in DB_TestData come from evaluate.nok_code: check it on other parts too."""
    from handletest import regulation
    from handletest.study import Methods, fixed_limits

    rng = np.random.default_rng(31)
    rig = Rig()
    M = Methods(rig, 3000, rng, fixed_limits(regulation.summary(), 0.02, 0.03))
    base = mech.sample_good(5, rng)
    for pop in [base] + [mech.apply_defect(base, d, rng) for d in mech.DEFECTS]:
        c = measure(pop, rig, rng)
        feat, nodes, acc = ev.features(c), ev.at_nodes(c), M.accept(c)
        for i in range(5):
            for mode in (1, 2, 3, 4):
                code = ev.nok_code(feat, M.lim.get(mode, {}), mode, i, nodes, M.env)
                assert (code == 0) == bool(acc[mode][i])
                assert stn.replay(c, i, mode, M.lim.get(mode), M.env)["nok"] == code
