# door-handle-force-travel-test

End-of-line force-travel test of a painted exterior car door-handle unit: which evaluation windows separate assembly defects from good handles, what the rig must be able to measure, and what the test costs a three-shift line.

> **Simulated study, no hardware.** The handle, the test rig, the defects, the line and every "measurement" here are models. All part values and their spreads are illustrative. That handle lines run a force-travel test at the end of the line is an assumption of this study, not a published fact about any plant. The regulation and standards content comes from the public sources in [docs/SOURCES.md](docs/SOURCES.md); what was not read is listed there. The PLC code compiles in TIA Portal V18 with 0 errors and 0 warnings (record in `results/tia_compile.txt`); in the tests it runs through a translator in Python, and it was not run on a PLC.

## The question

The unit is a handle lever on a pivot with a torsion return spring, a counterweight and a lever that pulls the latch cable. The station pulls the grip once to the end stop and lets it return, and records force against travel.

Which force-travel evaluation windows separate the real assembly defects from good handles, given the rig's own measurement capability, and what do those windows cost in false rejects and cycle time on a three-shift line?

## The answer

1. **The spring has an engineering lower limit, and it comes from the 30 g rule.** UN Regulation No. 11 (6.1.4) and FMVSS 206 (S4.1.1.4) ask that the latch system, with its activation device, stays latched at 30 g. For the modelled handle (grip {{s.regulation.unbalance_kgm*1e3:.2f}} g m out of balance after the counterweight) the inertia torque at 30 g is {{s.regulation.opening_torque_nm:.3f}} N m. With spring torques averaged over rest and release position, as Annex 4 of the regulation prescribes, the nominal spring gives {{s.regulation.nominal_average_spring_torque_nm:.3f}} N m and holds {{s.regulation.g_held_nominal:.1f}} g. The preload may fall to {{s.regulation.min_preload_nm:.3f}} N m, {{100*s.regulation.min_preload_fraction_of_nominal:.0f}} % of nominal. The spring of the other handle variant (1.6 mm wire instead of 1.8 mm) gives {{100*s.regulation.wrong_variant_factor:.0f}} % and holds {{s.regulation.g_held_wrong_variant:.1f}} g: it fits, it returns the handle, and it is a safety defect. Without the counterweight the handle would need {{s.regulation.opening_torque_no_counterweight_nm:.2f}} N m.

2. **Windows on the pull stroke plus one element on the return stroke are the only method that finds every spring defect; each simpler method has a blind spot.** All four methods were set to the same false-reject target ({{100*s.fr_target:.1f}} % of good parts) and then tried on the same defective parts:

{{detection_table(s)}}

   Peak force only cannot see a particle at the end stop and passes {{100*(1-s.detection.weak_spring.peak):.0f}} % of the springs below the 30 g limit. Pull-stroke windows read spring plus friction at the start of the travel, so a stiff pivot hides a weak spring. The mean of pull and return force at the same travel cancels the friction and reads the spring alone; their difference reads the friction alone. The envelope is the weakest on weak springs and on binding pivots: its band must be wide enough for the cable take-up and the release step, whose travel varies from part to part. On the fresh sample it also rejected more good parts than its target.

3. **Small particles at the stop and slight binding lie inside the spread of good parts.** The stop travel of good parts already varies with a standard deviation of {{s.feature_stats.XStop.sd:.2f}} mm, so the window is {{s.limits.pullret.XStop[1]-s.limits.pullret.XStop[0]:.2f}} mm wide. A particle that takes 1.0 mm of travel is rejected in {{100*sweep_at(s,'particle_at_stop','pullret',1.0):.0f}} % of cases, 1.25 mm in {{100*sweep_at(s,'particle_at_stop','pullret',1.25):.0f}} %, 2.0 mm in {{100*sweep_at(s,'particle_at_stop','pullret',2.0):.0f}} %. In the same way extra pivot friction of 0.10 N m is rejected in {{100*sweep_at(s,'binding_pivot','pullret',0.10):.0f}} % of cases and 0.15 N m in {{100*sweep_at(s,'binding_pivot','pullret',0.15):.0f}} %.

4. **The rig is not the limit, as long as its own deflection is taken out of the travel. The deciding parameter is the part-to-part spread of pivot friction.** In a Type-1 study (one master part, 50 pulls) every element reaches Cg and Cgk above 1.33; the lowest Cgk is {{min(d['Cgk'] for d in s.type1.compensated.values()):.1f}}. The repeatability of the spring element is {{s.type1.compensated.FMean.s:.3f}} N against {{s.type1.compensated.FMean.sd_parts_ideal_rig:.3f}} N of part-to-part spread. Without compliance compensation the stop travel reads {{s.type1.not_compensated.XStop.bias:.2f}} mm long (rig stiffness 40 N/mm) and its Cgk is {{s.type1.not_compensated.XStop.Cgk:.1f}}. Almost all false rejects of the chosen method come from the friction element ({{100*s.false_reject_by_window_pullret.FHyst:.2f}} % of good parts; every other element {{100*max(v for k,v in s.false_reject_by_window_pullret.items() if k!='FHyst'):.2f}} % or less). If the friction spread grows by half, false rejects go from {{100*s.sensitivity_false_reject.baseline.pullret:.2f}} % to {{100*s.sensitivity_false_reject['pivot friction spread x1.5'].pullret:.2f}} % with unchanged limits; three times the load-cell noise gives {{100*s.sensitivity_false_reject['load cell noise x3'].pullret:.2f}} %.

5. **The test costs {{s.plc_loop.t_test_ok_s:.2f}} s of a {{s.line_assumptions.takt_s:.0f}} s takt, and its speed is limited by the force at the end stop, not by the sampling.** At 50 mm/s and a 2 ms sample the station needs {{s.speed['50'].t_test_s:.2f}} s from clamp to verdict and the stop sees {{s.speed['50'].f_peak_true_n:.0f}} N; at 100 mm/s it would be {{s.speed['100'].t_test_s:.2f}} s and {{s.speed['100'].f_peak_true_n:.0f}} N, above the 60 N allowed on the painted part. Over a simulated week (15 shifts, {{s.week.pullret.PQ:.0f}} parts) the station reaches an OEE of {{100*s.week.pullret.oee:.1f}} % (availability {{100*s.week.pullret.availability:.1f}} %, effectiveness {{100*s.week.pullret.effectiveness:.1f}} %, quality rate {{100*s.week.pullret.quality:.2f}} %). False rejects cost {{s.week.pullret.false_rejects:.0f}} good parts and {{s.week.pullret.lock_false_s/60:.1f}} minutes of locked station per week; micro-stops cost {{s.week.pullret.micro_s/60:.0f}} minutes. The chosen method lets {{s.week.pullret.escapes:.1f}} defective parts per week through (almost all small particles), peak force only {{s.week.peak.escapes:.1f}}.

![Good parts and the evaluation elements](docs/img/curves_windows.png)

*Key figure. Pull and return curves of good parts with the elements of the chosen method: gate 1 (mean and difference of pull and return force), gate 2, the peak window of the latch release, the stop travel at 30 N. The band is the envelope of the fourth method.*

Other figures:

- [defect_curves.png](docs/img/defect_curves.png): curves of each defect against good parts.
- [spring_30g_limit.png](docs/img/spring_30g_limit.png): inertia torque against acceleration and the spring torques.
- [detection_vs_defect_size.png](docs/img/detection_vs_defect_size.png): rejection against defect size for the four methods.
- [false_reject_vs_window_width.png](docs/img/false_reject_vs_window_width.png): false rejects and marginal defects against window width.
- [gauge_type1.png](docs/img/gauge_type1.png): Type-1 study with and without compliance compensation.
- [sensitivity_false_reject.png](docs/img/sensitivity_false_reject.png): what moves the false rejects.
- [oee_week.png](docs/img/oee_week.png): losses of the simulated week and wrong verdicts per method.
- [plc_cycle_trace.png](docs/img/plc_cycle_trace.png): one cycle of the SCL station block against the plant model.

The full report is [DOSSIER.md](DOSSIER.md): need, modes, requirements, architecture, budgets, trade study, models, FMEA, verification.

## PLC code

| Block | What it does |
|---|---|
| [`plc/FB_CurveEval.scl`](plc/FB_CurveEval.scl) | Curve evaluation on sampled data, one sample per call in the cyclic interrupt: forces at two travel gates on pull and return, peak window, release step, stop travel, envelope at fixed nodes. Four modes (the four methods above). No curve buffer. |
| [`plc/FB_HandleStation.scl`](plc/FB_HandleStation.scl) | Station sequence with poka-yoke: part presence, LH/RH sensor pattern before any motion, touch position window, force limit, a reject locks the station until the part has left and the reject-chute sensor has seen a part, an interrupted test counts as a reject, three rejects in a row ask for the master part. Counters per reject code. |

Both are Siemens SCL sources in TIA Portal V18 style. `handletest/scl.py` translates them to Python with 32-bit Real arithmetic, so the same source text runs in the tests: {{s.plc_loop.replay.of}} curves went through `FB_CurveEval` and through the NumPy evaluation with the same verdict in {{s.plc_loop.replay.agree}} cases (largest feature difference {{s.plc_loop.replay.feature_max_abs_diff:.1e}}), and {{s.plc_loop.parts}} parts went through the whole station against a plant model.

## How to run

```
pip install -r requirements.txt
python -m pytest -q
python scripts/run_all.py        # results/summary.json and docs/img (several minutes)
python scripts/make_docs.py      # README.md and DOSSIER.md from docs/templates and the summary
```

`--quick` runs a small study for CI. Every result number in this README and in the dossier is filled in from `results/summary.json` by `scripts/make_docs.py`.

## Assumptions and what was not verified

- All handle values (masses, spring, friction, latch load, tolerances) are illustrative. The findings are about the method; the numbers move with the part.
- The handle is asked to hold itself at 30 g with its own spring. The regulations allow the whole latch system to share the load, so this rule is stricter than they are. Their calculation paragraphs speak of the "activation device" and do not name the handle.
- The latch is replaced by a spring-loaded latch simulator on the fixture. Its release step stands for the real latch.
- Quasi-static model: no handle inertia, no stick-slip, no temperature, no paint damage. Drive dynamics are an acceleration limit only; the force at the stop depends on it.
- Defect rates, micro-stops, breakdowns and operator times of the line are assumed.
- UN R11 was read in the text of the 03 series of amendments; later revisions could not be opened. SAE J839, ISO 22400-2, the AIAG MSA manual and VDA Volume 5 were not read; public secondary sources were used and are named.
- The SCL compiles in TIA Portal V18 for an S7-1513 with 0 errors and 0 warnings (`scripts/tia_build.ps1`, record in `results/tia_compile.txt`). It was not run on a PLC or in PLCSIM. The translator supports only the subset used here.
- No real force-travel curve was available for comparison.

## Repo map

| Path | Content |
|---|---|
| `handletest/mechanism.py` | Lever, torsion spring, friction, latch load, end stop; good parts and seven defects |
| `handletest/regulation.py` | Inertia torque at 30 g, minimum preload, the regulation's sample calculation |
| `handletest/rig.py` | Rig as a measurement system: compliance, sampling, noise, touch, reversal |
| `handletest/evaluate.py` | Elements, limits, the four methods (NumPy reference of the PLC block) |
| `handletest/msa.py` | Type-1 gauge study |
| `handletest/station.py`, `handletest/scl.py` | SCL translator and the plant model for the blocks in the loop |
| `handletest/line.py` | One week on the line, OEE terms |
| `handletest/study.py`, `handletest/plots.py` | The whole study and the figures |
| `plc/` | The two SCL blocks |
| `tests/` | 28 tests: regulation example, closed forms, SCL against NumPy, station sequence, line model |
| `results/summary.json` | All numbers |
| `DOSSIER.md`, `docs/SOURCES.md` | Systems-engineering dossier; sources with what was taken from each |

MIT licence.
