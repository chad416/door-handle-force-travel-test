"""Generate the data of the PLC test bench: plc/test/DB_TestData.scl and results/plcsim_bench_cases.json.

The data block holds force-travel curves recorded from the Python model (rig.measure), the evaluation
recipe of the study (limits and envelope from results/summary.json) and, for every replay case, the
verdict, the NOK code and the element values that the NumPy evaluation gives for the same samples.
plc/test/FB_TestBench.scl replays the curves into FB_CurveEval inside the PLC and compares.

    python scripts/make_plcsim_bench.py

Nothing in the data block is typed by hand. Rerun this script after a new study (new limits).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from handletest import evaluate as ev  # noqa: E402
from handletest import mechanism as mech  # noqa: E402
from handletest import regulation  # noqa: E402
from handletest.rig import Rig, measure  # noqa: E402

SEED = 20261126
TOL = 0.001            # N or mm: allowed difference between the PLC and the NumPy value of an element
MARGIN = 0.02          # N or mm: every case must be at least this far from each limit it is judged by
MAX_CASES = 32
LIM_ORDER = ("G1Lo", "G1Hi", "MeanLo", "MeanHi", "HystLo", "HystHi", "RetFMin", "G2Lo", "G2Hi", "PeakFLo", "PeakFHi",
             "PeakXMin", "PeakXMax", "StepLo", "StopXLo", "StopXHi")
LIM_OF = {"FpG1": (0, 1), "FMean": (2, 3), "FHyst": (4, 5), "FrG1": (6, None), "FpG2": (7, 8), "FPeak": (9, 10),
          "XPeak": (11, 12), "FStep": (13, None), "XStop": (14, 15)}
MODE_NAME = {1: "peak force only", 2: "pull-stroke windows", 3: "windows + return stroke", 4: "envelope"}
# station scenario of FB_TestBench (fixed in the SCL source); listed here for the documentation
STATION_CASES = (
    "Station: good LH unit is clamped, pulled and passed",
    "Station: RH unit on an LH recipe is rejected with code 20 and never pulled",
    "Station: the reject lock ignores a chute signal while the part is in the fixture, refuses a new part, "
    "and opens when the chute sensor sees a part after the fixture is empty",
    "Station: unit with unhooked latch lever is pulled and rejected with code 5",
    "Station: third reject in a row asks for the master part and blocks the start",
    "Station: after the acknowledge a good unit is pulled and passed",
)


def f32(v) -> np.float32:
    return np.float32(v)


def lit(v) -> str:
    """Shortest decimal text that gives back the same 32-bit Real."""
    return np.format_float_positional(np.float32(v), unique=True, trim="0")


def build() -> dict:
    summary = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(SEED)
    rig = Rig()
    nom = mech.nominal()
    reg = regulation.summary()

    def defect(name, sev=None, base=nom):
        return mech.apply_defect(base, name, rng, severity=sev)

    parts = [
        ("good, nominal part", nom),
        ("good, random part", mech.sample_good(1, rng)),
        ("missing spring", defect("missing_spring")),
        ("weak spring, 70 % wind-up (below the 30 g limit)", defect("weak_spring", 0.70)),
        ("wrong-variant spring (1.6 mm wire)", defect("wrong_variant_spring")),
        ("binding pivot, +0.35 N m", defect("binding_pivot", 0.35)),
        ("latch lever unhooked", defect("latch_lever_unhooked")),
        ("wrong-hand spring", defect("wrong_hand_spring")),
        ("particle at the end stop, 2.0 mm", defect("particle_at_stop", 2.0)),
        ("weak spring (70 %) hidden by +0.10 N m pivot friction", defect("binding_pivot", 0.10, defect("weak_spring", 0.70))),
    ]
    weak = parts[3][1]
    assert weak["M0"][0] < regulation.min_preload(weak["ks"][0], reg["release_angle_rad"])
    pop = {k: np.concatenate([p[k] for _, p in parts]) for k in nom}
    c = measure(pop, rig, rng)
    assert c["touched"].all()
    feat, nodes = ev.features(c), ev.at_nodes(c)

    # recipe: the limits of the study, rounded to 32-bit Real so that PLC and NumPy judge with the same numbers
    lim_arr = np.zeros((4, 16), dtype=np.float32)
    lims: dict[int, dict] = {}
    for mode, key in ((1, "peak"), (2, "pull"), (3, "pullret")):
        lims[mode] = {}
        for name, (lo, hi) in summary["limits"][key].items():
            a, b = LIM_OF[name]
            lim_arr[mode - 1, a] = f32(lo)
            if b is not None:
                lim_arr[mode - 1, b] = f32(hi)
            lims[mode][name] = [float(f32(lo)), float(f32(hi)) if b is not None else np.inf]
    n_env = ev.RECIPE["EnvN"]
    env = (np.array(summary["envelope"]["lo"], dtype=np.float32), np.array(summary["envelope"]["hi"], dtype=np.float32))
    assert len(env[0]) == n_env

    # replay cases: every curve in mode 3, a few in the other modes
    replay = [(i, 3) for i in range(len(parts))] + [(9, 2), (8, 1), (0, 4), (3, 4)]
    cases = []
    for curve, mode in replay:
        code = ev.nok_code(feat, lims.get(mode, {}), mode, curve, nodes, env, n_env)
        viol, done = ev.env_counts(nodes[curve], env)
        vals = [float(feat[k][curve]) for k in ev.FEATURES]
        # no case may sit close to a limit it is judged by: a last-bit difference must not flip a verdict
        for name, (lo, hi) in lims.get(mode, {}).items():
            v = feat[name][curve]
            if np.isfinite(v):
                assert min(abs(v - lo), abs(v - hi)) > MARGIN, (parts[curve][0], mode, name, v, lo, hi)
        cases.append(dict(curve=curve, mode=mode, part=parts[curve][0], ok=code == 0, nok=code, feat=vals,
                          env_viol=viol, env_nodes=done))
    for i in range(len(parts)):      # envelope counts are compared in every case
        d = np.minimum(np.abs(nodes[i] - env[0]), np.abs(nodes[i] - env[1]))
        assert np.nanmin(d) > 2 * TOL, (parts[i][0], float(np.nanmin(d)))
    by = {(k["curve"], k["mode"]): k for k in cases}
    assert by[(0, 3)]["ok"] and by[(1, 3)]["ok"] and by[(0, 4)]["ok"]
    assert not any(by[(i, 3)]["ok"] for i in range(2, 10))
    assert by[(6, 3)]["nok"] == 5          # the station scenario expects this code for the unhooked lever

    starts, npull, xs, fs = [], [], [], []
    for i in range(len(parts)):
        n = int(c["n"][i])
        starts.append(len(xs))
        npull.append(n)
        xs += list(c["Xp"][i, :n]) + list(c["Xr"][i, :n][::-1])      # pull, then return in time order
        fs += list(c["Fp"][i, :n]) + list(c["Fr"][i, :n][::-1])
    return dict(parts=[p for p, _ in parts], cases=cases, starts=starts, npull=npull, x=xs, f=fs, lim=lim_arr,
                env=env, n_env=n_env, good_curve=0, bad_curve=6)


def scl(b: dict) -> str:
    ns, nc, ncurves = len(b["x"]), len(b["cases"]), len(b["parts"])
    R = ev.RECIPE
    out = [
        "// Generated by scripts/make_plcsim_bench.py. Do not edit: rerun the script.",
        "// Recorded force-travel curves from the Python model, the evaluation recipe of the study and the",
        "// values the NumPy evaluation gives for the same samples. Read by FB_TestBench and FB_TestPlant.",
        "//   X, F            samples of all curves, one after the other. A curve is CurveNPull pull samples",
        "//                   followed by the same number of return samples, in the order they were taken.",
        "//   Case..., Exp... replay cases 1..NCases: curve, evaluation mode, expected verdict, NOK code,",
        "//                   elements (9 per case: FpG1 FrG1 FMean FHyst FpG2 FPeak XPeak FStep XStop) and",
        "//                   envelope counts",
        "//   Lim             16 limits per mode, index (mode - 1) * 16 + n, n in the order",
        "//                   " + " ".join(LIM_ORDER),
        'DATA_BLOCK "DB_TestData"',
        "{ S7_Optimized_Access := 'TRUE' }",
        "VERSION : 0.1",
        "NON_RETAIN",
        "   VAR",
        "      NCurves : Int;",
        "      NCases : Int;",
        "      NSamples : Int;",
        "      Tol : Real;   // N or mm, allowed difference of an element",
        "      GoodCurve : Int;   // curve of the good unit in the station scenario",
        "      BadCurve : Int;   // curve of the rejected unit in the station scenario",
        "      GateX : Real;",
        "      Gate2X : Real;",
        "      PeakXLo : Real;",
        "      PeakXHi : Real;",
        "      StepSpan : Real;",
        "      StopF : Real;",
        "      EnvX0 : Real;",
        "      EnvDx : Real;",
        "      EnvN : Int;",
        "      CurveStart : Array[0..15] of Int;",
        "      CurveNPull : Array[0..15] of Int;",
        f"      CaseCurve : Array[1..{MAX_CASES}] of Int;",
        f"      CaseMode : Array[1..{MAX_CASES}] of Int;",
        f"      ExpOk : Array[1..{MAX_CASES}] of Bool;",
        f"      ExpNok : Array[1..{MAX_CASES}] of Int;",
        f"      ExpEnvViol : Array[1..{MAX_CASES}] of Int;",
        f"      ExpEnvNodes : Array[1..{MAX_CASES}] of Int;",
        f"      ExpFeat : Array[0..{MAX_CASES * 9 - 1}] of Real;",
        f"      ExpFeatValid : Array[0..{MAX_CASES * 9 - 1}] of Bool;",
        "      Lim : Array[0..63] of Real;",
        "      EnvLo : Array[0..63] of Real;",
        "      EnvHi : Array[0..63] of Real;",
        f"      X : Array[0..{ns - 1}] of Real;   // mm",
        f"      F : Array[0..{ns - 1}] of Real;   // N",
        "   END_VAR",
        "",
        "BEGIN",
        f"   NCurves := {ncurves};",
        f"   NCases := {nc};",
        f"   NSamples := {ns};",
        f"   Tol := {lit(TOL)};",
        f"   GoodCurve := {b['good_curve']};",
        f"   BadCurve := {b['bad_curve']};",
    ]
    for k in ("GateX", "Gate2X", "PeakXLo", "PeakXHi", "StepSpan", "StopF", "EnvX0", "EnvDx"):
        out.append(f"   {k} := {lit(R[k])};")
    out.append(f"   EnvN := {b['n_env']};")
    for i, (s, n) in enumerate(zip(b["starts"], b["npull"])):
        out.append(f"   CurveStart[{i}] := {s};")
        out.append(f"   CurveNPull[{i}] := {n};")
    for k, cs in enumerate(b["cases"], start=1):
        out.append(f"   CaseCurve[{k}] := {cs['curve']};")
        out.append(f"   CaseMode[{k}] := {cs['mode']};")
        if cs["ok"]:
            out.append(f"   ExpOk[{k}] := TRUE;")
        out.append(f"   ExpNok[{k}] := {cs['nok']};")
        out.append(f"   ExpEnvViol[{k}] := {cs['env_viol']};")
        out.append(f"   ExpEnvNodes[{k}] := {cs['env_nodes']};")
        for j, v in enumerate(cs["feat"]):
            if np.isfinite(v):
                out.append(f"   ExpFeat[{(k - 1) * 9 + j}] := {lit(v)};")
                out.append(f"   ExpFeatValid[{(k - 1) * 9 + j}] := TRUE;")
    for m in range(4):
        for j in range(16):
            if b["lim"][m, j] != 0:
                out.append(f"   Lim[{m * 16 + j}] := {lit(b['lim'][m, j])};")
    for i in range(b["n_env"]):
        out.append(f"   EnvLo[{i}] := {lit(b['env'][0][i])};")
        out.append(f"   EnvHi[{i}] := {lit(b['env'][1][i])};")
    for i, v in enumerate(b["x"]):
        if v != 0:
            out.append(f"   X[{i}] := {lit(v)};")
    for i, v in enumerate(b["f"]):
        if v != 0:
            out.append(f"   F[{i}] := {lit(v)};")
    out += ["", "END_DATA_BLOCK", ""]
    return "\n".join(out)


BENCH_SOURCES = ("FB_CurveEval.scl", "FB_HandleStation.scl", "test/DB_TestData.scl", "test/DB_TestResult.scl",
                 "test/FB_TestPlant.scl", "test/FB_TestBench.scl", "test/OB_Main.scl")


def translator_run() -> dict:
    """Run the bench sources (with the data block just written) through the SCL translator. The values
    of DB_TestResult found here are the ones the PLC must show."""
    from handletest import scl

    prog = scl.load_program([ROOT / "plc" / n for n in BENCH_SOURCES])
    r = prog.db["DB_TestResult"]
    for _ in range(5000):
        prog.ob["Main"]()
        if r.Done:
            break
    st = prog.db["InstTestBench"].Station
    n = int(r.CasesTotal)
    return dict(Done=bool(r.Done), AllPassed=bool(r.AllPassed), CasesTotal=n, CasesRun=int(r.CasesRun),
                CasesPassed=int(r.CasesPassed), CasesFailed=int(r.CasesFailed), FirstFailedCase=int(r.FirstFailedCase),
                FirstFailedCheck=int(r.FirstFailedCheck), MaxFeatError=float(r.MaxFeatError), BenchCalls=int(r.BenchCalls),
                CasePass=[bool(v) for v in r.CasePass[:n]], CaseCheck=[int(v) for v in r.CaseCheck[:n]],
                CaseNok=[int(v) for v in r.CaseNok[:n]],
                station=dict(CntTotal=int(st.CntTotal), CntOk=int(st.CntOk), CntNok=int(st.CntNok),
                             CntRejectConfirmed=int(st.CntRejectConfirmed)))


def main() -> None:
    b = build()
    assert len(b["cases"]) + len(STATION_CASES) <= MAX_CASES and len(b["parts"]) <= 16 and len(b["x"]) < 32000
    (ROOT / "plc" / "test").mkdir(parents=True, exist_ok=True)
    (ROOT / "plc" / "test" / "DB_TestData.scl").write_text(scl(b), encoding="utf-8", newline="\n")
    rows = [dict(case=k, kind="replay", part=cs["part"], mode=cs["mode"], mode_name=MODE_NAME[cs["mode"]],
                 expected_ok=cs["ok"], expected_nok=cs["nok"]) for k, cs in enumerate(b["cases"], start=1)]
    rows += [dict(case=len(b["cases"]) + i, kind="station", part=text) for i, text in enumerate(STATION_CASES, start=1)]
    info = dict(seed=SEED, tolerance=TOL, margin=MARGIN, curves=len(b["parts"]), samples=len(b["x"]),
                replay_cases=len(b["cases"]), station_cases=len(STATION_CASES), cases_total=len(rows),
                data_bytes=8 * len(b["x"]), cases=rows)
    info["translator"] = translator_run()
    (ROOT / "results" / "plcsim_bench_cases.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    t = info["translator"]
    print(f"translator: {t['CasesPassed']} of {t['CasesTotal']} cases pass in {t['BenchCalls']} OB1 cycles, "
          f"largest element difference {t['MaxFeatError']:.1e}")
    print(f"{len(b['parts'])} curves, {len(b['x'])} samples, {len(b['cases'])} replay cases + "
          f"{len(STATION_CASES)} station cases = {len(rows)}")
    for r in rows[: len(b["cases"])]:
        print(f"  {r['case']:2d}  mode {r['mode']}  {'OK ' if r['expected_ok'] else 'NOK'} {r['expected_nok']:2d}  {r['part']}")


if __name__ == "__main__":
    main()
