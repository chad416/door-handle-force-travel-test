"""Figures. Everything is drawn from the dictionary returned by handletest.study.run()."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from handletest import evaluate as ev  # noqa: E402
from handletest import regulation  # noqa: E402

C = dict(peak="#8c8c8c", pull="#d98a00", pullret="#0b6fa4", envelope="#7a3e9d", good="#3c8d40", bad="#c0392b")
LABEL = dict(peak="peak force only", pull="pull-stroke windows", pullret="windows + return stroke",
             envelope="envelope")
NICE = dict(missing_spring="missing spring", wrong_variant_spring="wrong-variant spring",
            weak_spring="weak spring", binding_pivot="binding pivot", latch_lever_unhooked="latch lever unhooked",
            wrong_hand_spring="wrong-hand spring", particle_at_stop="particle at the end stop")
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130,
                     "axes.grid": True, "grid.alpha": 0.25})


def _save(fig, out: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(out / name)
    plt.close(fig)


def curves_windows(S: dict, out: Path) -> None:
    lim, R, cur = S["limits"]["pullret"], ev.RECIPE, S["example_curves"]
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    for i, c in enumerate(cur["good"]):
        ax.plot(c["xp"], c["fp"], color=C["good"], lw=0.6, alpha=0.5, label="good parts, pull" if i == 0 else None)
        ax.plot(c["xr"], c["fr"], color="#7fbf7f", lw=0.6, alpha=0.5, label="good parts, return" if i == 0 else None)
    env = S["envelope"]
    ax.fill_between(env["nodes"], env["lo"], env["hi"], color=C["envelope"], alpha=0.10, lw=0,
                    label="envelope (pull stroke)")
    g = R["GateX"]
    mlo, mhi = lim["FMean"]
    ax.plot([g, g], [mlo, mhi], color=C["pullret"], lw=4, solid_capstyle="butt", label="gate 1: mean of pull and return")
    ax.plot([R["Gate2X"]] * 2, lim["FpG2"], color=C["pull"], lw=4, solid_capstyle="butt", label="gate 2: pull force")
    (xa, xb), (fa, fb) = lim["XPeak"], lim["FPeak"]
    ax.add_patch(plt.Rectangle((xa, fa), xb - xa, fb - fa, fill=False, ec=C["bad"], lw=1.5, label="peak window"))
    ax.plot(lim["XStop"], [R["StopF"]] * 2, color="k", lw=4, solid_capstyle="butt", label="stop: travel at 30 N")
    ax.axhline(S["fixed_limits"]["F_reg"], color=C["bad"], ls=":", lw=1)
    ax.text(33.8, S["fixed_limits"]["F_reg"] + 0.4, "spring force of the\n30 g limit at gate 1", color=C["bad"],
            ha="right", fontsize=8)
    ax.set(xlabel="travel of the pull point (mm), rig deflection taken out", ylabel="force (N)", xlim=(0, 34),
           ylim=(0, 42), title="Good parts and the evaluation elements (simulated)")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    _save(fig, out, "curves_windows.png")


def defect_curves(S: dict, out: Path) -> None:
    cur = S["example_curves"]
    fig, axs = plt.subplots(2, 4, figsize=(12, 5.6), sharex=True, sharey=True)
    names = [k for k in cur if k != "good"]
    for ax, name in zip(axs.flat, names + [None]):
        if name is None:
            ax.axis("off")
            continue
        for c in cur["good"][:12]:
            ax.plot(c["xp"], c["fp"], color="#b5b5b5", lw=0.5)
            ax.plot(c["xr"], c["fr"], color="#d9d9d9", lw=0.5)
        for c in cur[name]:
            ax.plot(c["xp"], c["fp"], color=C["bad"], lw=0.9)
            ax.plot(c["xr"], c["fr"], color="#e08a7f", lw=0.9)
        ax.set_title(NICE[name], fontsize=9)
        ax.set(xlim=(0, 34), ylim=(0, 42))
    for ax in axs[1]:
        ax.set_xlabel("travel (mm)")
    for ax in axs[:, 0]:
        ax.set_ylabel("force (N)")
    fig.suptitle("Defective parts (red: pull, light red: return) against good parts (grey), simulated", fontsize=10)
    _save(fig, out, "defect_curves.png")


def spring_30g(S: dict, out: Path) -> None:
    r = S["regulation"]
    g = np.linspace(0, 45, 10)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(g, g * r["opening_torque_nm"] / r["a_g"], color="k", label="inertia torque, with counterweight")
    ax.plot(g, g * r["opening_torque_no_counterweight_nm"] / r["a_g"], color="k", ls="--",
            label="inertia torque, counterweight missing")
    avg = r["nominal_average_spring_torque_nm"]
    for val, lab, col in ((avg, "nominal spring (average torque)", C["good"]),
                          (r["opening_torque_nm"], "spring at the 30 g limit", C["pull"]),
                          (avg * r["wrong_variant_factor"], "wrong-variant spring", C["bad"])):
        ax.axhline(val, color=col, lw=1.3, label=lab)
    ax.axvline(30, color="#555", ls=":", lw=1)
    ax.text(30.4, 0.05, "30 g", color="#555")
    ax.set(xlabel="transverse acceleration (g)", ylabel="torque about the pivot (N m)", xlim=(0, 45), ylim=(0, 1.4),
           title="Why the spring has a lower limit: the handle must stay shut at 30 g")
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    _save(fig, out, "spring_30g_limit.png")


def detection(S: dict, out: Path) -> None:
    sw = S["sweeps"]
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.9), sharey=True)
    spec = (("weak_spring", "remaining spring wind-up (fraction of nominal)"),
            ("binding_pivot", "extra pivot friction (N m)"), ("particle_at_stop", "travel lost at the stop (mm)"))
    for ax, (d, xl) in zip(axs, spec):
        for m in ("peak", "pull", "envelope", "pullret"):
            ax.plot(sw[d]["levels"], 100 * np.array(sw[d]["reject"][m]), marker="o", ms=3, color=C[m], label=LABEL[m])
        ax.set(xlabel=xl, title=NICE[d], ylim=(-3, 103))
    lim = S["regulation"]["min_preload_fraction_of_nominal"]
    axs[0].axvline(lim, color=C["bad"], ls=":", lw=1)
    axs[0].text(lim - 0.01, 50, "30 g limit", color=C["bad"], rotation=90, ha="right", va="center", fontsize=8)
    axs[0].set_ylabel("parts rejected (%)")
    axs[2].legend(fontsize=8, frameon=False, loc="center right")
    fig.suptitle("Rejection against defect size, all methods set to the same false-reject target", fontsize=10)
    _save(fig, out, "detection_vs_defect_size.png")


def window_width(S: dict, out: Path) -> None:
    c = S["window_width_curve"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.9))
    a.semilogy(c["k"], 100 * np.maximum(np.array(c["false_reject"]), 1e-6), color=C["pullret"], marker="o", ms=3)
    a.axhline(100 * S["fr_target"], color=C["bad"], ls=":", lw=1)
    a.axvline(S["k_sigma"]["pullret"], color="#555", ls=":", lw=1)
    a.set(xlabel="window half-width (standard deviations of good parts)", ylabel="good parts rejected (%)",
          title="False rejects")
    for (name, y), col in zip(c["detection"].items(), (C["pullret"], C["pull"], "k")):
        b.plot(c["k"], 100 * np.array(y), marker="o", ms=3, color=col, label=name)
    b.axvline(S["k_sigma"]["pullret"], color="#555", ls=":", lw=1)
    b.set(xlabel="window half-width (standard deviations of good parts)", ylabel="parts rejected (%)",
          title="Marginal defects", ylim=(-3, 103))
    b.legend(fontsize=8, frameon=False)
    fig.suptitle("Windows with return stroke: false rejects and marginal defects against window width", fontsize=10)
    _save(fig, out, "false_reject_vs_window_width.png")


def gauge(S: dict, out: Path) -> None:
    t = S["type1"]
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.8))
    for ax, f, unit in ((axs[0], "FMean", "N"), (axs[1], "XStop", "mm")):
        for var, col in (("not_compensated", C["pull"]), ("compensated", C["pullret"])):
            d = t[var][f]
            ax.plot(range(1, len(d["values"]) + 1), d["values"], marker="o", ms=3, lw=0.6, color=col,
                    label=var.replace("_", " "))
        d = t["compensated"][f]
        ax.axhline(d["ref"], color="k", lw=1)
        for sgn in (-1, 1):
            ax.axhline(d["ref"] + sgn * 0.1 * d["T"], color=C["bad"], ls=":", lw=1)
        ax.set(xlabel="measurement of the master part", ylabel=f"{f} ({unit})",
               title=f"{f}: reference (black) and +/- 10 % of the window")
        ax.legend(fontsize=8, frameon=False)
    names = list(t["compensated"])
    x = np.arange(len(names))
    for i, (var, col) in enumerate((("not_compensated", C["pull"]), ("compensated", C["pullret"]))):
        axs[2].bar(x + (i - 0.5) * 0.38, [min(t[var][n]["Cgk"], 8) for n in names], 0.38, color=col,
                   label=var.replace("_", " "))
    axs[2].axhline(1.33, color=C["bad"], ls=":", lw=1)
    axs[2].set_xticks(x, names, rotation=30)
    axs[2].set(ylabel="Cgk (bars cut at 8)", title="Type-1 study, 50 pulls of one master")
    axs[2].legend(fontsize=8, frameon=False)
    _save(fig, out, "gauge_type1.png")


def sensitivity(S: dict, out: Path) -> None:
    s = S["sensitivity_false_reject"]
    names = [k for k in s if k != "baseline"]
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    y = np.arange(len(names))
    for i, m in enumerate(("pull", "pullret", "envelope")):
        ax.barh(y + (i - 1) * 0.27, [100 * s[n][m] for n in names], 0.27, color=C[m], label=LABEL[m])
    ax.axvline(100 * s["baseline"]["pullret"], color=C["pullret"], ls=":", lw=1)
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set(xlabel="good parts rejected (%), limits unchanged",
           title="What moves the false rejects (dotted: baseline of windows + return stroke)")
    ax.legend(fontsize=8, frameon=False)
    _save(fig, out, "sensitivity_false_reject.png")


def oee(S: dict, out: Path) -> None:
    w = S["week"]
    ms = ("peak", "pull", "pullret", "envelope")
    fig, (a, b) = plt.subplots(1, 2, figsize=(10.5, 3.9))
    d = w["pullret"]
    pbt = d["PBT"]
    lost_q = (d["PQ"] - d["GQ"]) * d["PRI"]
    parts = [("logged stops\n(availability)", d["logged_stop_s"]), ("micro-stops", d["micro_s"]),
             ("reject lock,\ntrue rejects", d["lock_true_s"]), ("reject lock,\nfalse rejects", d["lock_false_s"]),
             ("rejected parts\n(quality)", lost_q)]
    a.bar([p[0] for p in parts], [p[1] / 3600 for p in parts], color=["#555", "#999", C["pull"], C["bad"], C["envelope"]])
    a.set(ylabel="hours per week", title=f"Losses of the test station, windows + return stroke\n(planned busy time {pbt / 3600:.1f} h, OEE {100 * d['oee']:.1f} %)")
    a.tick_params(axis="x", labelsize=7)
    x = np.arange(len(ms))
    b.bar(x - 0.2, [w[m]["false_rejects"] for m in ms], 0.4, color=C["bad"], label="good parts rejected")
    b.bar(x + 0.2, [w[m]["escapes"] for m in ms], 0.4, color="k", label="defective parts passed")
    b.set_xticks(x, [LABEL[m].replace(" + ", "\n+ ") for m in ms], fontsize=7)
    b.set(ylabel="parts per week", title="Wrong verdicts per week by method")
    b.legend(fontsize=8, frameon=False)
    _save(fig, out, "oee_week.png")


def plc_trace(S: dict, out: Path) -> None:
    tr = S["trace"]
    fig, axs = plt.subplots(3, 1, figsize=(8.5, 5.4), sharex=True)
    axs[0].step(tr["t"], tr["state"], color="k", lw=1)
    axs[0].set(ylabel="State", yticks=range(0, 9))
    axs[1].plot(tr["t"], tr["pos"], color=C["pull"], label="axis position")
    axs[1].plot(tr["t"], tr["x"], color=C["pullret"], label="travel used for the evaluation")
    axs[1].set(ylabel="mm")
    axs[1].legend(fontsize=8, frameon=False)
    axs[2].plot(tr["t"], tr["force"], color=C["bad"])
    axs[2].set(ylabel="force (N)", xlabel="time (s)")
    fig.suptitle("One good part through FB_HandleStation (SCL run scan by scan against the plant model)", fontsize=10)
    _save(fig, out, "plc_cycle_trace.png")


def all_figures(S: dict, out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    for f in (curves_windows, defect_curves, spring_30g, detection, window_width, gauge, sensitivity, oee, plc_trace):
        f(S, out)
    return sorted(p.name for p in out.glob("*.png"))


__all__ = ["all_figures", "regulation"]
