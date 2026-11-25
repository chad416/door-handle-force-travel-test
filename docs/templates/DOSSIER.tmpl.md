# Force-travel end-of-line test of an exterior door-handle unit

**Systems-engineering dossier, revision 1.0 (25 Nov 2026).** Simulation only: no hardware, no measured data. Every result number is filled in from `results/summary.json` by `scripts/make_docs.py`. Tags: **[S]** sourced (section 12 and `docs/SOURCES.md`), **[D]** derived here (file named), **[A]** assumed. The layout follows Wasson, *System Engineering Analysis, Design, and Development*, 2nd ed., Wiley 2016 (need, operations, modes, requirements, architecture, budgets, alternatives, models, reliability, verification); the book was not re-read for this project.

**Central question.** Which force-travel evaluation windows separate the real assembly defects of a painted exterior door-handle unit from good handles, given the rig's own measurement capability, and what do those windows cost in false rejects and cycle time on a three-shift line?

**Short answer.** Pull-stroke windows plus one return-stroke element. The return stroke is needed for one reason: the spring has a lower limit that comes from the 30 g inertial load rule, and on the pull stroke alone a stiff pivot hides a weak spring. The rig is good enough if its deflection is taken out of the travel. What decides the false rejects is the part-to-part spread of pivot friction, not the rig.

---

## 0. Findings

1. Minimum spring preload from the 30 g rule: {{s.regulation.min_preload_nm:.3f}} N m, {{100*s.regulation.min_preload_fraction_of_nominal:.0f}} % of nominal (section 5.1).
2. Windows with return stroke reject {{100*s.detection.weak_spring.pullret:.1f}} % of springs below that limit; pull-stroke windows {{100*s.detection.weak_spring.pull:.1f}} %, peak force only {{100*s.detection.weak_spring.peak:.1f}} %, envelope {{100*s.detection.weak_spring.envelope:.1f}} % (section 6).
3. A weak spring behind a stiff pivot: return-stroke method {{100*s.masked_weak_spring.pullret:.0f}} %, pull-stroke windows {{100*s.masked_weak_spring.pull:.1f}} % (section 6).
4. Peak force only rejects {{100*s.detection.particle_at_stop.peak:.1f}} % of particles at the stop. No method reliably finds a particle below about 1.25 mm (section 6).
5. Type-1 study: lowest Cgk {{min(d['Cgk'] for d in s.type1.compensated.values()):.1f}} with compliance compensation; stop travel Cgk {{s.type1.not_compensated.XStop.Cgk:.1f}} without (section 5.3).
6. Deciding parameter: spread of pivot friction. Times 1.5 takes false rejects from {{100*s.sensitivity_false_reject.baseline.pullret:.2f}} % to {{100*s.sensitivity_false_reject['pivot friction spread x1.5'].pullret:.2f}} % (section 7.3).
7. Test time {{s.plc_loop.t_test_ok_s:.2f}} s; pull speed limited to about 50 mm/s by the force at the stop (section 5.4). OEE of the simulated week {{100*s.week.pullret.oee:.1f}} % (section 5.5).

## 1. Need and operational concept

**System of interest.** The last station of a handle assembly line: fixture with clamp and latch simulator, servo axis with hook and load cell, part and variant sensors, reject chute with light barrier, PLC.

**Higher-order system.** Injection moulding, painting, assembly (lever, pivot pin, return spring, counterweight, latch lever), this test, packing.

| Who | Needs from the station |
|---|---|
| Vehicle safety | No handle leaves with a spring that cannot hold the handle shut at 30 g |
| Customer plant | No handle that binds, does not return, or does not pull the latch |
| Production (three shifts) | Test inside the takt; few good parts rejected; a reject cannot be put back on the line by mistake |
| Setter, maintenance | Limits that can be explained; a master part that shows whether the rig or the parts have moved |

**Operation.** The part is loaded, the sensors check presence and hand, the clamp closes, the load cell is tared, the axis approaches until it touches the grip, pulls to the end stop, returns, and the PLC judges. An OK part is unloaded. A rejected part locks the station until it has been taken out and the chute sensor has seen a part.

**Assumption [A].** That such lines test force against travel at the end of the line is assumed. The latch is not part of the unit; the fixture carries a spring-loaded latch simulator hooked to the latch lever.

## 2. Mission profile of one test

Approach 5 mm, touch, pull about 30 mm at 50 mm/s ({{s.type1_rig.travel_per_sample_mm:.1f}} mm per sample), reverse at 40 N, return at the same speed to travel 0, home at 150 mm/s. Sample time 2 ms. Figure: `docs/img/plc_cycle_trace.png`.

## 3. Modes and states

`FB_HandleStation`: 0 Idle, 1 Clamp, 2 Tare, 3 Approach, 4 Pull, 5 Return, 6 Evaluate, 7 UnloadOk, 8 RejectLock, 9 Fault, 10 Home.

Rules that matter:
- A unit of the wrong hand, or a sensor pattern that is not plausible, goes from Idle straight to a reject. The axis does not move.
- Touch outside its position window (3 to 7 mm) is a reject before the pull. This catches a missing spring: the hook finds no force until the cable is taut.
- Force above 60 N ends the pull.
- A fault (safety circuit, drive, clamp time-out, load cell does not tare) stops the drive. After the acknowledge the axis goes home and the part in test is a reject. A fault during RejectLock returns to RejectLock.
- Three rejects in a row block the start until the acknowledge key: run the master part.

## 4. Requirements

| ID | Requirement | Origin |
|---|---|---|
| R-01 | Reject every unit whose spring cannot hold the handle shut at 30 g (average of rest and release torque, friction not counted) | [S] UN R11 6.1.4, Annex 4 2.1.1; FMVSS 206 S4.1.1.4. Design rule of this study [A]: the handle holds itself |
| R-02 | Reject units with missing spring, wrong-hand spring, binding pivot, unhooked latch lever, obstructed stop | [A] defect list |
| R-03 | Reject at most {{100*s.fr_target:.1f}} % of good units | [A] |
| R-04 | Every element: Cg and Cgk at least 1.33 in a Type-1 study, resolution at most 5 % of the window | [S] G1, G2 |
| R-05 | Never pull a unit of the wrong hand | [A] poka-yoke |
| R-06 | A rejected unit cannot be followed by a new test until it has passed the reject chute | [A] poka-yoke |
| R-07 | At most 60 N on the painted grip | [A] |
| R-08 | Test inside a {{s.line_assumptions.takt_s:.0f}} s takt with margin for load and unload | [A] |

## 5. Design, budgets and margins

### 5.1 Spring and the 30 g rule (`handletest/regulation.py`) [D]

Moving masses [A]: grip 110 g at +40 mm, counterweight 60 g at -45 mm, latch lever 12 g at +10 mm. Static moment {{s.regulation.unbalance_kgm*1e3:.2f}} g m. Inertia torque at 30 g: {{s.regulation.opening_torque_nm:.3f}} N m. Without the counterweight: {{s.regulation.opening_torque_no_counterweight_nm:.3f}} N m.

Spring [A]: wire 1.8 mm, mean coil diameter 13 mm, 6 active turns, E = 206 GPa. Rate k = d^4 E / (64 D Na) = {{s.regulation.spring_rate_nm_per_rad:.3f}} N m/rad [S, D1]. Wind-up at rest 1.40 rad: preload {{s.regulation.nominal_preload_nm:.3f}} N m. Bending stress at the end stop {{s.regulation.spring_stress_at_stop_mpa:.0f}} MPa (not judged: no allowable was looked up).

Rule [S, R1]: spring torque = average of the torque at rest and at the release position ({{s.regulation.release_angle_rad:.2f}} rad). Nominal: {{s.regulation.nominal_average_spring_torque_nm:.3f}} N m, margin {{s.regulation.margin_nominal:.2f}}, holds {{s.regulation.g_held_nominal:.1f}} g. Minimum preload {{s.regulation.min_preload_nm:.3f}} N m. As a force at gate 1 (3 mm travel): {{s.fixed_limits.F_reg:.2f}} N; with two standard deviations of the gauge the lower limit of FMean is {{s.fixed_limits.MeanLo:.2f}} N.

The sample calculation of Annex 4, Figure 4-1 is recomputed as a check: {{s.regulation.figure_4_1.net_kgf_m:.4f}} kgf m against the printed 0,0347.

### 5.2 Mechanism model (`handletest/mechanism.py`) [D]

Pivot torque on the pull stroke = spring + latch cable load x lever arm + end stop + friction; on the return stroke the friction changes sign. Friction = Coulomb torque + viscous term. Latch load: free play, cable preload and rate, a detent load that builds up and drops at release (the step). Pull point 100 mm from the pivot: x = R sin(theta), F = M / (R cos(theta)).

Good parts as seen by the rig (mean, sd) and the limits of the chosen method:

{{limits_table(s)}}

### 5.3 Rig as a measurement system (`handletest/rig.py`, `handletest/msa.py`) [D]

Rig [A]: stiffness 40 N/mm between axis and handle, load cell noise 0.03 N, analog resolution {{s.type1_rig.force_resolution_n*1e3:.1f}} mN (100 N over 27648 counts), encoder resolution {{s.type1_rig.travel_resolution_mm*1e3:.0f}} µm, 50 mm/s, 2 ms. The PLC takes the rig deflection out of the travel: X = axis travel - (F - F_touch) x compliance.

Type-1 study [S, G1]: master = nominal part, {{s.type1_rig.repeats}} pulls, reference = the same part on an ideal rig. The study rig has a force gain error of {{100*s.type1_rig.gain:.1f}} %, a zero error of {{s.type1_rig.zero_n:.2f}} N and is compensated with {{s.type1_rig.k_comp:.0f}} N/mm instead of 40 [A].

{{type1_table(s)}}

FStep and FrG1 have one-sided limits; Cg is not defined for them. Resolution: the force resolution is {{100*s.type1_rig.force_resolution_n/s.type1.compensated.FMean['T']:.2f}} % of the narrowest force window. Figure: `docs/img/gauge_type1.png`.

### 5.4 Cycle time and pull speed [D]

{{speed_table(s)}}

Limits are set again for each speed, on {{s.sizes.sens}} good parts, and tried on another {{s.sizes.sens}}; the false-reject column therefore scatters by about 0.1 points around the target. The force at the stop is from the SCL block in the loop: the PLC reverses in the first sample at or above 40 N, the axis then needs time to stop (acceleration limit 3000 mm/s2 [A]). Sampling is not what limits the speed: at 0.2 mm per sample the detection is unchanged. R-07 limits it.

Station time for an OK part: load {{s.line_assumptions.t_load_s:.1f}} s + test {{s.plc_loop.t_test_ok_s:.2f}} s + unload 1.0 s = {{s.week.pullret.station_time_ok_s:.2f}} s of a {{s.line_assumptions.takt_s:.0f}} s takt.

### 5.5 One week on the line (`handletest/line.py`) [D]

OEE terms as in ISO 22400-2 [S, K1; the standard itself not read]: availability = APT / PBT, effectiveness = PRI x PQ / APT, quality rate = GQ / PQ. Classification [A]: logged stops (breakdowns, changeovers, master-part checks) leave APT; micro-stops and reject locks stay inside APT. No buffer in front of the station: a lock costs only what exceeds the slack of the takt. Mean of {{s.sizes.weeks}} simulated weeks:

{{week_table(s)}}

The week-to-week standard deviation of the OEE is {{100*s.week.pullret.oee_sd:.2f}} points, mostly from breakdowns. The rows differ reliably only in the last two columns. For the chosen method, per week: logged stops {{s.week.pullret.logged_stop_s/3600:.2f}} h, micro-stops {{s.week.pullret.micro_s/60:.0f}} min, lock after true rejects {{s.week.pullret.lock_true_s/60:.0f}} min, lock after false rejects {{s.week.pullret.lock_false_s/60:.1f}} min. Figure: `docs/img/oee_week.png`.

## 6. Trade study: four evaluation methods

Each method is set on {{s.sizes.cal}} good parts to reject {{100*s.fr_target:.1f}} % of them, then tried on {{s.sizes.val}} fresh good parts and {{s.sizes.defect}} parts per defect. Window half-widths: peak {{s.k_sigma.peak:.2f}}, pull {{s.k_sigma.pull:.2f}}, pull + return {{s.k_sigma.pullret:.2f}} standard deviations; envelope = lowest and highest of {{s.envelope.taught_from}} taught curves widened by {{s.envelope.margin_n:.2f}} N.

{{detection_table(s)}}

| Method | Cannot see | Why |
|---|---|---|
| Peak force only | Particle at the stop; a fifth of the weak springs | The peak lies before the stop; the spring is a small part of the peak |
| Pull-stroke windows | A weak spring behind a stiff pivot | Gate 1 reads spring + friction |
| Windows + return stroke | Particles below about 1.25 mm; extra friction below about 0.10 N m | Inside the spread of good parts |
| Envelope | More than half of the weak springs, a quarter of the binding pivots, small particles | The band must cover the take-up and the release step, whose travel varies |

Chosen: windows + return stroke. It is the only method that meets R-01 in the masked case. Its price: the friction window uses most of the false-reject budget, so its other windows are a little wider than those of the pull-only method (particles of 1.0 mm: {{100*sweep_at(s,'particle_at_stop','pullret',1.0):.0f}} % against {{100*sweep_at(s,'particle_at_stop','pull',1.0):.0f}} %). Figures: `docs/img/detection_vs_defect_size.png`, `docs/img/false_reject_vs_window_width.png`.

## 7. Models and what they are checked against

### 7.1 Two independent rig models
`handletest/rig.py` (vectorised, for the Monte Carlo) and the plant in `handletest/station.py` (stateful, for the PLC in the loop) were written separately. For good parts the largest difference between their elements is {{max(s.plc_loop.feature_max_abs_diff.values()):.2f}} (N or mm), with independent noise in each.

### 7.2 PLC in the loop
`FB_CurveEval` against the NumPy evaluation on the same samples: {{s.plc_loop.replay.agree}} of {{s.plc_loop.replay.of}} verdicts equal, largest element difference {{s.plc_loop.replay.feature_max_abs_diff:.1e}}. Whole station against the plant, {{s.plc_loop.n_each}} parts per group and method: no good part rejected; reject codes of the chosen method per defect are in `results/summary.json` (`plc_loop.nok_codes_pullret`).

Test bench inside the PLC (`plc/test/`, `docs/PLCSIM_RUN.md`): {{b.replay_cases}} replay cases and {{b.station_cases}} station cases with expected values from the NumPy evaluation, in a data block; a bench block compares and writes `DB_TestResult`. Through the translator: {{b.translator.CasesPassed}} of {{b.translator.CasesTotal}} cases pass. TIA Portal V18, whole test project: `{{t.bench.compile}}`. Not yet run in S7-PLCSIM.

### 7.3 Sensitivity: what moves the false rejects

{{sensitivity_table(s)}}

For the chosen method the friction spread moves the false rejects most. The envelope reacts most to the cable free play. Figure: `docs/img/sensitivity_false_reject.png`.

## 8. Assumed and sourced

Sourced: the 30 g value and the calculation rule (R1, R2), the Type-1 formulas and criteria (G1, G2), the OEE terms (K1), the kinds of evaluation element (M1), the spring formulas (D1).

Assumed: all masses, spring data, friction, latch load, tolerances and their distributions (`mechanism.py`, `NOM` and `SPREAD`); the wrong-variant spring (1.6 mm wire); defect sizes; rig stiffness, noise and calibration errors; axis acceleration; takt, defect rates, micro-stops, breakdowns, operator times (`line.py`).

## 9. FMEA of the test station

| Failure | Effect | What the design does |
|---|---|---|
| Rig deflection not compensated or stiffness changed | Travel elements biased (stop travel {{s.type1.not_compensated.XStop.bias:.2f}} mm) | Compensation in the PLC; master part shows the bias; 10 % softer rig changes false rejects from {{100*s.sensitivity_false_reject.baseline.pullret:.2f}} % to {{100*s.sensitivity_false_reject['rig 10 % softer than compensated'].pullret:.2f}} % |
| Load cell gain drifts by 1 % | Force elements shift | False rejects {{100*s.sensitivity_false_reject['force gain +1 %'].pullret:.2f}} %; master part at shift start |
| Load cell does not return to zero | Wrong forces | Tare check, fault 4 |
| Chute sensor stuck high | Lock could not be released | Edge, not level, releases the lock; station stays locked (safe side) |
| Chute sensor triggered by something else | Reject back on the line | Release needs the part to have left the fixture first; residual risk remains [not solved] |
| Variant sensor fails | Wrong hand pulled, or every part rejected | Pattern check: exactly one sensor must be on |
| Safety stop during the pull | Part with unknown result | Part becomes a reject (code 24) |
| Pull too fast | More than 60 N on the grip | Speed in the recipe, force limit in the PLC; the limit acts only after the sample |

## 10. Verification and validation

| Requirement | Evidence | Result |
|---|---|---|
| R-01 | `tests/test_model.py` (Annex 4 example, balance at 30 g); detection table | {{100*s.detection.weak_spring.pullret:.1f}} % of sub-limit springs rejected; masked case {{100*s.masked_weak_spring.pullret:.0f}} % |
| R-02 | Detection table, `tests/test_plc.py` | All but small particles and slight binding |
| R-03 | Fresh good parts | {{100*s.false_reject.pullret.rate:.2f}} % (95 % interval {{100*s.false_reject.pullret.ci95[0]:.2f}} to {{100*s.false_reject.pullret.ci95[1]:.2f}} %) |
| R-04 | Type-1 table | Met with compensation |
| R-05, R-06 | `tests/test_plc.py` | Pass in simulation |
| R-07 | Speed table | {{s.speed['50'].f_peak_true_n:.0f}} N at 50 mm/s: met with little margin |
| R-08 | Section 5.4 | {{s.week.pullret.station_time_ok_s:.2f}} s of {{s.line_assumptions.takt_s:.0f}} s |

Validation against a real handle and a real rig has not been done. First steps with hardware: measure friction and spring torque of 50 units, run the Type-1 study on the real rig, run the prepared test project in S7-PLCSIM (`docs/PLCSIM_RUN.md`), then load the SCL (it compiles in TIA Portal V18 with 0 errors and 0 warnings) on a CPU and check the cycle load of the 2 ms interrupt.

## 11. Limits of this work

Quasi-static model without inertia or stick-slip. One latch simulator instead of a real latch. Normal and log-normal spreads without correlation. One defect per part, except the masked case. Windows at mean plus or minus k sigma, although the friction element is skewed. The translator runs only the SCL subset used here.

## 12. References

See `docs/SOURCES.md`: R1 UN Regulation No. 11 (03 series, OJ L 120, 13.5.2010); R2 FMVSS 206 (49 CFR 571.206); G1, G2 Type-1 gauge study; K1 OPC 40501-1 Annex C for ISO 22400-2; M1 process-monitoring manual; D1 Shigley chapter 10 slides.
