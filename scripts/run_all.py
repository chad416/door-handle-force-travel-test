"""Run the whole study: results/summary.json, results/example_curves.json and the figures in docs/img.

    python scripts/run_all.py            full study (several minutes)
    python scripts/run_all.py --quick    small study for CI: results/summary_quick.json, no figures
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from handletest import plots, study  # noqa: E402


def main() -> None:
    quick = "--quick" in sys.argv
    t0 = time.time()
    S = study.run(quick=quick)
    res = ROOT / "results"
    res.mkdir(exist_ok=True)
    if not quick:
        figs = plots.all_figures(S, ROOT / "docs" / "img")
        (res / "example_curves.json").write_text(json.dumps(S["example_curves"]), encoding="utf-8")
        print("figures:", ", ".join(figs))
    S.pop("example_curves")
    S.pop("trace")
    for var in S["type1"].values():
        for d in var.values():
            d.pop("values")
    name = "summary_quick.json" if quick else "summary.json"
    (res / name).write_text(json.dumps(S, indent=1, default=float), encoding="utf-8")
    print(f"wrote results/{name} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
