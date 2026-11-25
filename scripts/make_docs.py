"""Fill README.md and DOSSIER.md from results/summary.json.

The templates in docs/templates hold the text; every result number in them is a field
{{ expression :format }} that is evaluated against the summary (name `s`, attribute access).
No result number is typed by hand.

    python scripts/make_docs.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELD = re.compile(r"\{\{(.+?)(?::([^:{}]*))?\}\}")
METHODS = ("peak", "pull", "pullret", "envelope")


class A(dict):
    """Dictionary with attribute access."""

    def __getitem__(self, k):
        v = dict.__getitem__(self, k)
        return A(v) if isinstance(v, dict) else v

    def __getattr__(self, k):
        return self[k]

    def values(self):
        return [self[k] for k in self]

    def items(self):
        return [(k, self[k]) for k in self]


def detection_table(s: A) -> str:
    names = dict(missing_spring="Missing spring", wrong_variant_spring="Wrong-variant spring (1.6 mm wire)",
                 weak_spring="Weak spring, below the 30 g limit", binding_pivot="Binding pivot (+0.15 to +0.60 N m)",
                 latch_lever_unhooked="Latch lever missing or unhooked", wrong_hand_spring="Wrong-hand spring",
                 particle_at_stop="Particle at the end stop (0.5 to 3 mm)")
    rows = ["| Defect | Peak force only | Pull-stroke windows | Windows + return stroke | Envelope |", "|---|---|---|---|---|"]
    for k, n in names.items():
        rows.append(f"| {n} | " + " | ".join(f"{100 * s['detection'][k][m]:.1f} %" for m in METHODS) + " |")
    rows.append("| Weak spring (70 % wind-up) hidden by +0.10 N m pivot friction | "
                + " | ".join(f"{100 * s['masked_weak_spring'][m]:.1f} %" for m in METHODS) + " |")
    rows.append("| **Good parts rejected** (fresh sample) | "
                + " | ".join(f"**{100 * s['false_reject'][m]['rate']:.2f} %**" for m in METHODS) + " |")
    return "\n".join(rows)


def type1_table(s: A) -> str:
    rows = ["| Feature | Window width T | Part-to-part sd (ideal rig) | Repeatability s | Bias | Cg | Cgk | Cgk without compensation |",
            "|---|---|---|---|---|---|---|---|"]
    unit = dict(FMean="N", FHyst="N", FpG2="N", FPeak="N", XPeak="mm", XStop="mm")
    for f, d in s["type1"]["compensated"].items():
        u = unit[f]
        rows.append(f"| {f} | {d['T']:.2f} {u} | {d['sd_parts_ideal_rig']:.3f} {u} | {d['s']:.3f} {u} | {d['bias']:+.3f} {u} | "
                    f"{d['Cg']:.1f} | {d['Cgk']:.1f} | {s['type1']['not_compensated'][f]['Cgk']:.1f} |")
    return "\n".join(rows)


def limits_table(s: A) -> str:
    unit = dict(FMean="N", FHyst="N", FpG2="N", FPeak="N", XPeak="mm", XStop="mm", FrG1="N", FStep="N", FpG1="N")
    rows = ["| Element | Lower | Upper | Good parts: mean, sd |", "|---|---|---|---|"]
    for f, (lo, hi) in s["limits"]["pullret"].items():
        st = s["feature_stats"][f]
        up = "none" if hi is None else f"{hi:.2f} {unit[f]}"
        rows.append(f"| {f} | {lo:.2f} {unit[f]} | {up} | {st['mean']:.2f}, {st['sd']:.3f} {unit[f]} |")
    return "\n".join(rows)


def sensitivity_table(s: A) -> str:
    rows = ["| Change (limits unchanged) | Pull-stroke windows | Windows + return stroke | Envelope |", "|---|---|---|---|"]
    for k, d in s["sensitivity_false_reject"].items():
        rows.append(f"| {k} | {100 * d['pull']:.2f} % | {100 * d['pullret']:.2f} % | {100 * d['envelope']:.2f} % |")
    return "\n".join(rows)


def speed_table(s: A) -> str:
    rows = ["| Pull speed | Travel per sample | Test time (clamp to verdict) | Highest force at the stop | Good parts rejected | Weak spring 0.80 found | 1 mm particle found |",
            "|---|---|---|---|---|---|---|"]
    for v, d in s["speed"].items():
        rows.append(f"| {v} mm/s | {d['mm_per_sample']:.2f} mm | {d['t_test_s']:.2f} s | {d['f_peak_true_n']:.0f} N | "
                    f"{100 * d['false_reject_pullret']:.2f} % | {100 * d['detect_weak_080']:.0f} % | {100 * d['detect_particle_1mm']:.0f} % |")
    return "\n".join(rows)


def week_table(s: A) -> str:
    lab = dict(peak="Peak force only", pull="Pull-stroke windows", pullret="Windows + return stroke", envelope="Envelope",
               pullret_no_false_rejects="Windows + return stroke, if no good part were rejected")
    rows = ["| Method | Availability | Effectiveness | Quality rate | OEE | Parts tested | Good parts rejected | Defective parts passed |",
            "|---|---|---|---|---|---|---|---|"]
    for m, n in lab.items():
        w = s["week"][m]
        rows.append(f"| {n} | {100 * w['availability']:.2f} % | {100 * w['effectiveness']:.2f} % | {100 * w['quality']:.2f} % | "
                    f"{100 * w['oee']:.2f} % | {w['PQ']:.0f} | {w['false_rejects']:.1f} | {w['escapes']:.1f} |")
    return "\n".join(rows)


def sweep_at(s: A, defect: str, method: str, level: float) -> float:
    sw = s["sweeps"][defect]
    return sw["reject"][method][[round(x, 3) for x in sw["levels"]].index(round(level, 3))]


def fill(text: str, s: A) -> str:
    ns = dict(s=s, b=bench(), t=compile_records(), detection_table=detection_table, type1_table=type1_table,
              limits_table=limits_table, sensitivity_table=sensitivity_table, speed_table=speed_table,
              week_table=week_table, bench_case_table=bench_case_table, sweep_at=sweep_at, min=min, max=max, abs=abs,
              sum=sum, len=len, all=all)

    def sub(m: re.Match) -> str:
        val = eval(m.group(1).strip(), ns)  # templates are part of this repo
        return format(val, m.group(2) or "")

    return FIELD.sub(sub, text)


def bench() -> A:
    """Cases of the PLC test bench and its result in the translator (scripts/make_plcsim_bench.py)."""
    return A(json.loads((ROOT / "results" / "plcsim_bench_cases.json").read_text(encoding="utf-8")))


def compile_records() -> A:
    """The COMPILE and ARCHIVE lines of the TIA Portal records, as written by scripts/tia_build.ps1."""
    out = {}
    for key, name in (("blocks", "tia_compile.txt"), ("bench", "tia_compile_testbench.txt")):
        lines = (ROOT / "results" / name).read_text(encoding="utf-8-sig").splitlines()
        rec = dict(header=lines[0].strip(), compile="", archive_file="", archive_bytes=0, simulation="")
        for ln in lines:
            ln = ln.strip()
            if ln.startswith("COMPILE "):
                rec["compile"] = " ".join(ln.split())
            elif ln.startswith("ARCHIVE ") and ln.endswith(" bytes"):
                rec["archive_file"], size = ln[len("ARCHIVE "):-len(" bytes")].rsplit("  ", 1)
                rec["archive_bytes"] = int(size)
            elif ln.startswith("simulation support"):
                rec["simulation"] = ln
        out[key] = rec
    return A(out)


def bench_case_table(b: A) -> str:
    rows = ["| Case | What runs | Evaluation mode | Expected verdict | Expected NOK code (`CaseNok`) |", "|---|---|---|---|---|"]
    station_nok = b["translator"]["CaseNok"][b["replay_cases"]:]
    station_verdict = ("OK", "NOK", "stays locked, then opens", "NOK", "NOK, start blocked", "OK")
    for c in b["cases"]:
        if c["kind"] == "replay":
            rows.append(f"| {c['case']} | Replay: {c['part']} | {c['mode']} ({c['mode_name']}) | "
                        f"{'OK' if c['expected_ok'] else 'NOK'} | {c['expected_nok']} |")
        else:
            i = c["case"] - b["replay_cases"] - 1
            rows.append(f"| {c['case']} | {c['part']} | 3 | {station_verdict[i]} | {station_nok[i]} |")
    return "\n".join(rows)


def main() -> None:
    s = A(json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8")))
    for name, target in (("README", ROOT / "README.md"), ("DOSSIER", ROOT / "DOSSIER.md"),
                         ("PLCSIM_RUN", ROOT / "docs" / "PLCSIM_RUN.md")):
        tmpl = (ROOT / "docs" / "templates" / f"{name}.tmpl.md").read_text(encoding="utf-8")
        target.write_text(fill(tmpl, s), encoding="utf-8", newline="\n")
        print(f"wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
