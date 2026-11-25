"""The whole study. Every number in README.md and DOSSIER.md comes from the dictionary this returns."""

from __future__ import annotations

import numpy as np

from handletest import evaluate as ev
from handletest import line, mechanism as mech, msa, regulation
from handletest import station as stn
from handletest.rig import IDEAL, Rig, measure, with_  # noqa: F401

FR_TARGET = 0.002          # design target: at most 0.2 % of good parts rejected [A]
RET_F_MIN = 1.0            # N, least return force at gate 1: the handle must come back by itself [A]
N_TEACH = 300              # good curves in the bundle that teaches the envelope
STUDY_RIG = with_(Rig(), gain=0.002, zero=0.02, k_comp=42.0)   # rig of the gauge study: small calibration errors [A]
SIZES = dict(full=dict(cal=20000, val=60000, defect=5000, sweep=2000, sens=15000, loop=20, weeks=10),
             quick=dict(cal=4000, val=6000, defect=1000, sweep=500, sens=3000, loop=4, weeks=2))


def _rate(ok: np.ndarray) -> float:
    return float(1.0 - np.mean(ok))


def _wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [float(max(0.0, c - h)), float(c + h)]


class Methods:
    """The four evaluation methods, calibrated on one set of good parts to the same false-reject target."""

    def __init__(self, rig: Rig, n_cal: int, rng: np.random.Generator, fixed: dict, target: float = FR_TARGET):
        self.rig, self.fixed = rig, fixed
        c = measure(mech.sample_good(n_cal, rng), rig, rng)
        feat, nodes = ev.features(c), ev.at_nodes(c)
        self.stats = ev.stats(feat)
        self.k = {m: ev.calibrate_k(m, feat, self.stats, fixed, target) for m in (1, 2, 3)}
        self.lim = {m: ev.limits_for(m, self.stats, self.k[m], fixed) for m in (1, 2, 3)}
        teach = nodes[:N_TEACH]
        lo, hi = 0.0, 20.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            fr = _rate(ev.judge_env(nodes, *ev.envelope(teach, mid)))
            lo, hi = (mid, hi) if fr > target else (lo, mid)
        self.env_margin = hi
        self.env = ev.envelope(teach, hi)

    def accept(self, c: dict) -> dict:
        feat = ev.features(c)
        out = {m: ev.judge(feat, self.lim[m]) for m in (1, 2, 3)}
        out[4] = ev.judge_env(ev.at_nodes(c), *self.env) & c["touched"]
        return out

    def reject_rate(self, pop: dict, rng: np.random.Generator, rig: Rig | None = None) -> dict:
        acc = self.accept(measure(pop, rig or self.rig, rng))
        return {ev.MODES[m]: _rate(a) for m, a in acc.items()}


def fixed_limits(reg: dict, s_mean: float, s_g1: float) -> dict:
    """Engineering limits that do not come from statistics.

    MeanLo: the force at gate 1 of a spring that just meets the 30 g rule, plus 2 s of the gauge.
    G1Lo:   the same spring seen on the pull stroke only: the friction force of a typical pivot is added.
    """
    th = mech.theta_of_travel(ev.RECIPE["GateX"])
    f_reg = (reg["min_preload_nm"] + reg["spring_rate_nm_per_rad"] * th) / (mech.R_PULL * np.cos(th))
    f_fric = mech.NOM["Mc"] / (mech.R_PULL * np.cos(th))
    return dict(F_reg=float(f_reg), MeanLo=float(f_reg + 2 * s_mean), G1Lo=float(f_reg + f_fric + 2 * s_g1),
                RetFMin=RET_F_MIN)


def run(quick: bool = False, seed: int = 20261125) -> dict:
    n = SIZES["quick" if quick else "full"]
    rng = np.random.default_rng(seed)
    rig = Rig()
    S: dict = dict(quick=quick, seed=seed, fr_target=FR_TARGET, sizes=n)

    # 1 -- spring and the 30 g rule -------------------------------------------------------------------
    reg = regulation.summary()
    reg["figure_4_1"] = regulation.figure_4_1()
    m_max = reg["nominal_preload_nm"] + reg["spring_rate_nm_per_rad"] * mech.NOM["th_e"]
    reg["spring_stress_at_stop_mpa"] = mech.spring_stress(m_max, mech.NOM["d"], mech.NOM["D"]) / 1e6
    reg["wrong_variant_factor"] = (mech.D_WRONG_VARIANT / mech.NOM["d"]) ** 4
    reg["g_held_wrong_variant"] = reg["g_held_nominal"] * reg["wrong_variant_factor"]
    S["regulation"] = reg

    # 2 -- repeatability of the rig (needed for the guard band of the spring limit) --------------------
    rep = msa.repeats(STUDY_RIG, rng)
    s_rep = {k: float(np.std(rep[k], ddof=1)) for k in ev.FEATURES}
    fixed = fixed_limits(reg, s_rep["FMean"], s_rep["FpG1"])
    S["fixed_limits"] = fixed

    # 3 -- calibrate the four methods to the same false-reject target, check on fresh good parts --------
    M = Methods(rig, n["cal"], rng, fixed)
    S["feature_stats"] = {k: dict(mean=m, sd=s) for k, (m, s) in M.stats.items()}
    S["k_sigma"] = {ev.MODES[m]: k for m, k in M.k.items()}
    S["limits"] = {ev.MODES[m]: {f: [float(a), float(b) if np.isfinite(b) else None] for f, (a, b) in lim.items()}
                   for m, lim in M.lim.items()}
    S["envelope"] = dict(margin_n=M.env_margin, taught_from=N_TEACH, nodes=[float(x) for x in ev.env_nodes()],
                         lo=[float(x) for x in M.env[0]], hi=[float(x) for x in M.env[1]])
    val = measure(mech.sample_good(n["val"], rng), rig, rng)
    acc_val = M.accept(val)
    S["false_reject"] = {ev.MODES[m]: dict(rate=_rate(a), ci95=_wilson(int((~a).sum()), a.size), n=int(a.size))
                         for m, a in acc_val.items()}
    fv = ev.features(val)
    why = {}
    for name, (lo, hi) in M.lim[3].items():
        with np.errstate(invalid="ignore"):
            why[name] = float(np.mean(~((fv[name] >= lo) & (fv[name] <= hi))))
    S["false_reject_by_window_pullret"] = why

    # 4 -- detection per defect ------------------------------------------------------------------------
    det = {}
    base = mech.sample_good(n["defect"], rng)
    for d in mech.DEFECTS:
        pop = mech.apply_defect(base, d, rng)
        acc = M.accept(measure(pop, rig, rng))
        if d == "weak_spring":       # judge only the springs that are below the 30 g limit
            below = pop["M0"] < regulation.min_preload(pop["ks"], reg["release_angle_rad"])
            det[d] = {ev.MODES[m]: _rate(a[below]) for m, a in acc.items()}
            det[d]["share_below_30g_limit"] = float(below.mean())
        else:
            det[d] = {ev.MODES[m]: _rate(a) for m, a in acc.items()}
    S["detection"] = det

    # 5 -- severity sweeps -----------------------------------------------------------------------------
    sw = mech.sample_good(n["sweep"], rng)
    sweeps = {}
    for d, levels in (("weak_spring", np.round(np.arange(0.50, 1.001, 0.05), 2)),
                      ("binding_pivot", np.array([0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30])),
                      ("particle_at_stop", np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]))):
        rows = {name: [] for name in ev.MODES.values()}
        for lv in levels:
            r = M.reject_rate(mech.apply_defect(sw, d, rng, severity=float(lv)), rng)
            for name in rows:
                rows[name].append(r[name])
        sweeps[d] = dict(levels=[float(x) for x in levels], reject=rows)
    S["sweeps"] = sweeps
    # a weak spring hidden by a stiff pivot: 70 % wind-up and +0.10 N m friction in the same part
    masked = mech.apply_defect(mech.apply_defect(sw, "weak_spring", rng, severity=0.70), "binding_pivot", rng, 0.10)
    S["masked_weak_spring"] = M.reject_rate(masked, rng)
    masked2 = mech.apply_defect(mech.apply_defect(sw, "weak_spring", rng, severity=0.70), "binding_pivot", rng, 0.15)
    S["masked_weak_spring_015"] = M.reject_rate(masked2, rng)

    # 6 -- false rejects against window width (pull + return method) -------------------------------------
    cal_f = ev.features(measure(mech.sample_good(n["cal"], rng), rig, rng))
    probes = {"weak_spring 0.80": mech.apply_defect(sw, "weak_spring", rng, 0.80),
              "binding_pivot +0.08 N m": mech.apply_defect(sw, "binding_pivot", rng, 0.08),
              "particle 1.0 mm": mech.apply_defect(sw, "particle_at_stop", rng, 1.0)}
    probes_f = {k: ev.features(measure(p, rig, rng)) for k, p in probes.items()}
    ks = [float(x) for x in np.arange(2.0, 6.01, 0.25)]
    curve = dict(k=ks, false_reject=[], detection={k: [] for k in probes})
    for k in ks:
        lim = ev.limits_for(3, M.stats, k, fixed)
        curve["false_reject"].append(_rate(ev.judge(cal_f, lim)))
        for name, pf in probes_f.items():
            curve["detection"][name].append(_rate(ev.judge(pf, lim)))
    S["window_width_curve"] = curve

    # 7 -- Type-1 gauge study --------------------------------------------------------------------------
    tol = {f: M.lim[3][f][1] - M.lim[3][f][0] for f in ev.TWO_SIDED[3]}
    t1 = {"compensated": msa.type1(STUDY_RIG, rng, tol),
          "not_compensated": msa.type1(with_(STUDY_RIG, k_comp=0.0), rng, tol)}
    ideal_f = ev.features(measure(mech.sample_good(min(n["cal"], 3000), rng), IDEAL, rng))
    for name in tol:
        t1["compensated"][name]["sd_parts_ideal_rig"] = float(np.nanstd(ideal_f[name]))
    S["type1"] = t1
    S["type1_rig"] = dict(gain=STUDY_RIG.gain, zero_n=STUDY_RIG.zero, k_rig=STUDY_RIG.k_rig, k_comp=STUDY_RIG.k_comp,
                          repeats=msa.N_REPEATS, force_resolution_n=rig.qF, travel_resolution_mm=rig.qx,
                          travel_per_sample_mm=rig.dx)

    # 8 -- what decides: false rejects with fixed limits when one spread or one rig property changes ----
    sens = {}
    cases = {"baseline": ({}, {}),
             "spring wind-up spread x1.5": ({"th0": 1.5}, {}),
             "pivot friction spread x1.5": ({"Mc_gsd": 1.5}, {}),
             "cable free-play spread x1.5": ({"play": 1.5}, {}),
             "release point spread x1.5": ({"rel": 1.5}, {}),
             "detent load spread x1.5": ({"Fd": 1.5}, {}),
             "end-stop spread x1.5": ({"th_e": 1.5}, {}),
             "load cell noise x3": ({}, {"sF": rig.sF * 3}),
             "rig 10 % softer than compensated": ({}, {"k_rig": rig.k_rig * 0.9}),
             "force gain +1 %": ({}, {"gain": 0.01})}
    for name, (scale, rigkw) in cases.items():
        pop = mech.sample_good(n["sens"], rng, scale=scale)
        sens[name] = M.reject_rate(pop, rng, with_(rig, **rigkw))
    S["sensitivity_false_reject"] = sens

    # 9 -- pull speed: samples per mm, force at reversal, test time ---------------------------------------
    speed = {}
    nominal = mech.nominal()
    for v in (25.0, 50.0, 100.0, 200.0):
        rv = with_(rig, v=v)
        Mv = Methods(rv, n["sens"], rng, fixed)
        fr = Mv.reject_rate(mech.sample_good(n["sens"], rng), rng)
        part = mech.apply_defect(sw, "particle_at_stop", rng, 1.0)
        weak = mech.apply_defect(sw, "weak_spring", rng, 0.80)
        st = stn.new_station(rv)
        stn.load_recipe(st.Eval, 3, Mv.lim[3], Mv.env)
        cyc = stn.run_cycle(st, stn.Plant(nominal, rv, rng))
        speed[str(int(v))] = dict(mm_per_sample=rv.dx, t_test_s=cyc["t_test"], f_peak_true_n=cyc["f_peak_true"],
                                  verdict=cyc["verdict"], false_reject_pullret=fr["pullret"],
                                  k_pullret=Mv.k[3], detect_particle_1mm=Mv.reject_rate(part, rng)["pullret"],
                                  detect_weak_080=Mv.reject_rate(weak, rng)["pullret"])
    S["speed"] = speed

    # 10 -- the SCL blocks in the loop -------------------------------------------------------------------
    S["plc_loop"] = plc_loop(M, rig, rng, n["loop"])

    # 11 -- one week on the line -------------------------------------------------------------------------
    wk = {}
    t_ok = S["plc_loop"]["t_test_ok_s"]
    for m, name in ev.MODES.items():
        d = {k: det[k][name] for k in mech.DEFECTS}
        wk[name] = line.weeks(np.random.default_rng(seed + 1), n["weeks"], t_test_ok=t_ok, t_unload=1.0, detection=d,
                              p_false_reject=S["false_reject"][name]["rate"])
    wk["pullret_no_false_rejects"] = line.weeks(np.random.default_rng(seed + 1), n["weeks"], t_test_ok=t_ok, t_unload=1.0,
                                                detection={k: det[k]["pullret"] for k in mech.DEFECTS},
                                                p_false_reject=0.0)
    S["week"] = wk
    S["line_assumptions"] = dict(takt_s=line.TAKT, shifts=line.SHIFTS, break_s=line.BREAK_S, t_load_s=line.T_LOAD,
                                 defect_rate=line.DEFECT_RATE, p_micro=line.P_MICRO, micro_median_s=line.MICRO_MED,
                                 reject_handling_median_s=line.REJECT_MED, mtbf_h=line.MTBF_S / 3600,
                                 mttr_median_s=line.MTTR_MED)
    # one traced cycle and example curves for the figures
    st = stn.new_station(rig)
    stn.load_recipe(st.Eval, 3, M.lim[3], M.env)
    pl = stn.Plant(mech.nominal(), rig, rng)
    tr = dict(t=[], state=[], pos=[], force=[], x=[])
    t = 0.0
    while t < 3.2:
        stn.scan(st, pl)
        t += rig.Ts
        if int(st.Verdict) == 1 and t > 2.6:
            pl.present = False
        for k, v in (("t", t), ("state", int(st.State)), ("pos", pl.pos), ("force", float(st.FNet)), ("x", float(st.XTravel))):
            tr[k].append(float(v))
    S["trace"] = tr
    ex = mech.sample_good(25, rng)
    exd = {"good": ex}
    for d in mech.DEFECTS:
        exd[d] = mech.apply_defect(mech.sample_good(4, rng), d, rng)
    curves = {}
    for name, pop in exd.items():
        c = measure(pop, rig, rng)
        curves[name] = [dict(xp=[round(float(v), 3) for v in c["Xp"][i, :c["n"][i]]],
                             fp=[round(float(v), 3) for v in c["Fp"][i, :c["n"][i]]],
                             xr=[round(float(v), 3) for v in c["Xr"][i, :c["n"][i]]],
                             fr=[round(float(v), 3) for v in c["Fr"][i, :c["n"][i]]]) for i in range(len(pop["M0"]))]
    S["example_curves"] = curves
    return S


def plc_loop(M: Methods, rig: Rig, rng: np.random.Generator, n_each: int) -> dict:
    """Run parts through the translated SCL station and compare with the NumPy evaluation."""
    out = dict(parts=0, verdict_agree={}, feature_max_abs_diff={})
    good = mech.sample_good(n_each, rng)
    groups = {"good": good}
    for d in mech.DEFECTS:
        groups[d] = mech.apply_defect(mech.sample_good(n_each, rng), d, rng)
    diffs = {k: [] for k in ev.FEATURES}
    t_ok, codes, per_group = [], {}, {}
    for mode in (2, 3, 4):
        agree = total = 0
        for gname, pop in groups.items():
            ref_acc = M.accept(measure(pop, rig, rng))[mode]
            rejected = 0
            for i in range(n_each):
                st = stn.new_station(rig)
                stn.load_recipe(st.Eval, mode, M.lim.get(mode), M.env)
                r = stn.run_cycle(st, stn.Plant(stn.one(pop, i), rig, rng), t_reject=1.0)
                total += 1
                agree += (r["verdict"] == 1) == bool(ref_acc[i])
                rejected += r["verdict"] == 2
                if mode == 3:
                    codes.setdefault(gname, {})
                    codes[gname][str(r["nok"])] = codes[gname].get(str(r["nok"]), 0) + 1
                    if gname == "good":
                        t_ok.append(r["t_test"])
                        f_ref = ev.features(measure(stn.one(pop, i), with_(rig, sF=0.0), rng))
                        for k in ev.FEATURES:
                            diffs[k].append(abs(r["feat"][k] - float(f_ref[k][0])))
            per_group.setdefault(gname, {})[ev.MODES[mode]] = rejected
        out["verdict_agree"][ev.MODES[mode]] = dict(agree=agree, of=total)
        out["parts"] += total
    # the same samples through FB_CurveEval and through the NumPy evaluation
    rp_agree = rp_total = 0
    rp_diff = 0.0
    for gname, pop in groups.items():
        c = measure(pop, rig, rng)
        acc, feat = M.accept(c), ev.features(c)
        for mode in (1, 2, 3, 4):
            for i in range(n_each):
                if not c["touched"][i]:
                    continue
                r = stn.replay(c, i, mode, M.lim.get(mode), M.env)
                rp_total += 1
                rp_agree += r["ok"] == bool(acc[mode][i])
                if mode == 3:
                    for k in ev.FEATURES:
                        if np.isfinite(feat[k][i]):
                            rp_diff = max(rp_diff, abs(r["feat"][k] - float(feat[k][i])))
    out["replay"] = dict(agree=rp_agree, of=rp_total, feature_max_abs_diff=rp_diff)
    out["rejected_of_n"] = per_group
    out["n_each"] = n_each
    out["nok_codes_pullret"] = codes
    out["feature_max_abs_diff"] = {k: float(np.max(v)) for k, v in diffs.items()}
    out["t_test_ok_s"] = float(np.mean(t_ok))
    out["t_test_ok_max_s"] = float(np.max(t_ok))
    return out
