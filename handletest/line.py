"""One simulated week of the test station on a paced three-shift line, and its OEE.

OEE as in ISO 22400-2 (not read; taken from the public description in docs/SOURCES.md, K1):
    Availability   = APT / PBT        actual production time / planned busy time
    Effectiveness  = PRI x PQ / APT   planned run time per item x produced quantity / actual production time
    Quality rate   = GQ / PQ          good quantity / produced quantity
    OEE            = Availability x Effectiveness x Quality rate

Classification used here [A]: stops that are logged (breakdowns, variant changeovers, master-part checks)
are taken out of APT. Micro-stops and the time the station is locked after a reject are not logged; they
stay inside APT and lower the effectiveness. PRI is the line takt. GQ counts parts that passed the test.

The line has no buffer in front of the station: the next part can enter when the takt has elapsed AND the
station is free. A station time shorter than the takt therefore costs nothing; a reject lock or a
micro-stop costs only what exceeds the slack.
"""

from __future__ import annotations

import numpy as np

# all values [A]
SHIFTS, SHIFT_S, BREAK_S = 15, 8 * 3600.0, 30 * 60.0        # 5 days x 3 shifts, 30 min break per shift
TAKT = 12.0                                                 # s, planned run time per item
T_LOAD = 1.5                                                # s, part into the fixture
MTBF_S, MTTR_MED, MTTR_GSD = 20 * 3600.0, 900.0, 1.6        # breakdowns of the station
CHANGEOVERS_PER_SHIFT, T_CHANGEOVER = 2, 180.0              # LH <-> RH
T_MASTER = 90.0                                             # master-part check at every shift start
P_MICRO, MICRO_MED, MICRO_GSD = 0.006, 20.0, 1.8            # micro-stop per part (part not seated, sensor)
REJECT_MED, REJECT_GSD = 15.0, 1.5                          # operator takes the part to the reject chute
# share of built units that carry each defect [A]
DEFECT_RATE = dict(missing_spring=300e-6, wrong_variant_spring=500e-6, weak_spring=800e-6,
                   binding_pivot=2000e-6, latch_lever_unhooked=600e-6, wrong_hand_spring=300e-6,
                   particle_at_stop=1500e-6, wrong_hand_unit=400e-6)


def simulate_week(rng: np.random.Generator, t_test_ok: float, t_unload: float, detection: dict,
                  p_false_reject: float) -> dict:
    """detection: P(reject | defect) per defect of DEFECT_RATE (wrong_hand_unit is found by the variant
    sensors before the pull). Returns times, counts and the OEE terms of one week."""
    pbt = SHIFTS * (SHIFT_S - BREAK_S)
    names = list(DEFECT_RATE)
    p_def = np.array([DEFECT_RATE[n] for n in names])
    p_det = np.array([1.0 if n == "wrong_hand_unit" else detection[n] for n in names])
    logged = SHIFTS * (CHANGEOVERS_PER_SHIFT * T_CHANGEOVER + T_MASTER)
    t = logged                       # logged planned stops are taken out first; the order does not matter
    next_break = rng.exponential(MTBF_S)
    run = 0.0                        # running time since the last breakdown
    pq = gq = 0
    n_def = n_true_rej = n_false_rej = n_escape = 0
    t_micro = t_lock_true = t_lock_false = 0.0
    start = t
    base = T_LOAD + t_test_ok + t_unload
    while True:
        occupied = base
        defect = rng.random() < p_def.sum()
        rejected = False
        if defect:
            n_def += 1
            k = rng.choice(len(names), p=p_def / p_def.sum())
            rejected = rng.random() < p_det[k]
            n_true_rej += rejected
            n_escape += not rejected
        elif rng.random() < p_false_reject:
            rejected = True
            n_false_rej += 1
        if rejected:
            lock = REJECT_MED * np.exp(np.log(REJECT_GSD) * rng.standard_normal())
            occupied += lock - t_unload
        micro = 0.0
        if rng.random() < P_MICRO:
            micro = min(120.0, MICRO_MED * np.exp(np.log(MICRO_GSD) * rng.standard_normal()))
            occupied += micro
        step = max(TAKT, occupied)
        over = step - TAKT
        if start + step > pbt:
            break
        # time beyond the takt is booked to its cause (micro-stop first, then the lock)
        m = min(over, micro)
        t_micro += m
        if rejected:
            if defect:
                t_lock_true += over - m
            else:
                t_lock_false += over - m
        start += step
        run += step
        pq += 1
        gq += not rejected
        if run >= next_break:
            down = MTTR_MED * np.exp(np.log(MTTR_GSD) * rng.standard_normal())
            start += down
            logged += down
            run, next_break = 0.0, rng.exponential(MTBF_S)
    apt = pbt - min(logged, pbt)
    return dict(PBT=pbt, APT=apt, PQ=pq, GQ=gq, PRI=TAKT,
                availability=apt / pbt, effectiveness=TAKT * pq / apt, quality=gq / pq,
                oee=(apt / pbt) * (TAKT * pq / apt) * (gq / pq),
                logged_stop_s=logged, micro_s=t_micro, lock_true_s=t_lock_true, lock_false_s=t_lock_false,
                defects=n_def, true_rejects=n_true_rej, false_rejects=n_false_rej, escapes=n_escape,
                station_time_ok_s=base)


def weeks(rng: np.random.Generator, n: int, **kw) -> dict:
    """Mean and standard deviation over n simulated weeks."""
    runs = [simulate_week(rng, **kw) for _ in range(n)]
    out = {}
    for k in runs[0]:
        v = np.array([r[k] for r in runs], dtype=float)
        out[k] = float(v.mean())
        out[k + "_sd"] = float(v.std(ddof=1)) if n > 1 else 0.0
    return out
