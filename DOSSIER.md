# Force-travel end-of-line test of an exterior door-handle unit

**Systems-engineering dossier, revision 1.0 (25 Nov 2026).** Simulation only: no hardware, no measured data. Every result number is filled in from `results/summary.json` by `scripts/make_docs.py`. Tags: **[S]** sourced (section 12 and `docs/SOURCES.md`), **[D]** derived here (file named), **[A]** assumed. The layout follows Wasson, *System Engineering Analysis, Design, and Development*, 2nd ed., Wiley 2016 (need, operations, modes, requirements, architecture, budgets, alternatives, models, reliability, verification); the book was not re-read for this project.

**Central question.** Which force-travel evaluation windows separate the real assembly defects of a painted exterior door-handle unit from good handles, given the rig's own measurement capability, and what do those windows cost in false rejects and cycle time on a three-shift line?

**Short answer.** Pull-stroke windows plus one return-stroke element. The return stroke is needed for one reason: the spring has a lower limit that comes from the 30 g inertial load rule, and on the pull stroke alone a stiff pivot hides a weak spring. The rig is good enough if its deflection is taken out of the travel. What decides the false rejects is the part-to-part spread of pivot friction, not the rig.

---

## 0. Findings

1. Minimum spring preload from the 30 g rule: 0.492 N m, 81 % of nominal (section 5.1).
2. Windows with return stroke reject 100.0 % of springs below that limit; pull-stroke windows 96.5 %, peak force only 79.6 %, envelope 42.1 % (section 6).
3. A weak spring behind a stiff pivot: return-stroke method 100 %, pull-stroke windows 12.6 % (section 6).
4. Peak force only rejects 0.1 % of particles at the stop. No method reliably finds a particle below about 1.25 mm (section 6).
5. Type-1 study: lowest Cgk 3.7 with compliance compensation; stop travel Cgk -5.2 without (section 5.3).
6. Deciding parameter: spread of pivot friction. Times 1.5 takes false rejects from 0.14 % to 1.71 % (section 7.3).
7. Test time 1.74 s; pull speed limited to about 50 mm/s by the force at the stop (section 5.4). OEE of the simulated week 95.4 % (section 5.5).

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

Approach 5 mm, touch, pull about 30 mm at 50 mm/s (0.1 mm per sample), reverse at 40 N, return at the same speed to travel 0, home at 150 mm/s. Sample time 2 ms. Figure: `docs/img/plc_cycle_trace.png`.

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
| R-03 | Reject at most 0.2 % of good units | [A] |
| R-04 | Every element: Cg and Cgk at least 1.33 in a Type-1 study, resolution at most 5 % of the window | [S] G1, G2 |
| R-05 | Never pull a unit of the wrong hand | [A] poka-yoke |
| R-06 | A rejected unit cannot be followed by a new test until it has passed the reject chute | [A] poka-yoke |
| R-07 | At most 60 N on the painted grip | [A] |
| R-08 | Test inside a 12 s takt with margin for load and unload | [A] |

## 5. Design, budgets and margins

### 5.1 Spring and the 30 g rule (`handletest/regulation.py`) [D]

Moving masses [A]: grip 110 g at +40 mm, counterweight 60 g at -45 mm, latch lever 12 g at +10 mm. Static moment 1.82 g m. Inertia torque at 30 g: 0.535 N m. Without the counterweight: 1.330 N m.

Spring [A]: wire 1.8 mm, mean coil diameter 13 mm, 6 active turns, E = 206 GPa. Rate k = d^4 E / (64 D Na) = 0.433 N m/rad [S, D1]. Wind-up at rest 1.40 rad: preload 0.606 N m. Bending stress at the end stop 1434 MPa (not judged: no allowable was looked up).

Rule [S, R1]: spring torque = average of the torque at rest and at the release position (0.20 rad). Nominal: 0.650 N m, margin 1.21, holds 36.4 g. Minimum preload 0.492 N m. As a force at gate 1 (3 mm travel): 5.05 N; with two standard deviations of the gauge the lower limit of FMean is 5.09 N.

The sample calculation of Annex 4, Figure 4-1 is recomputed as a check: 0.0348 kgf m against the printed 0,0347.

### 5.2 Mechanism model (`handletest/mechanism.py`) [D]

Pivot torque on the pull stroke = spring + latch cable load x lever arm + end stop + friction; on the return stroke the friction changes sign. Friction = Coulomb torque + viscous term. Latch load: free play, cable preload and rate, a detent load that builds up and drops at release (the step). Pull point 100 mm from the pivot: x = R sin(theta), F = M / (R cos(theta)).

Good parts as seen by the rig (mean, sd) and the limits of the chosen method:

| Element | Lower | Upper | Good parts: mean, sd |
|---|---|---|---|
| FMean | 5.19 N | 7.21 N | 6.20, 0.232 N |
| FHyst | -0.55 N | 3.98 N | 1.71, 0.518 N |
| FpG2 | 9.21 N | 12.61 N | 10.91, 0.389 N |
| FPeak | 14.73 N | 18.93 N | 16.83, 0.481 N |
| XPeak | 16.77 mm | 22.89 mm | 19.83, 0.701 mm |
| XStop | 28.54 mm | 31.02 mm | 29.78, 0.284 mm |
| FrG1 | 1.00 N | none | 5.34, 0.349 N |
| FStep | 2.81 N | none | 3.92, 0.254 N |

### 5.3 Rig as a measurement system (`handletest/rig.py`, `handletest/msa.py`) [D]

Rig [A]: stiffness 40 N/mm between axis and handle, load cell noise 0.03 N, analog resolution 3.6 mN (100 N over 27648 counts), encoder resolution 1 µm, 50 mm/s, 2 ms. The PLC takes the rig deflection out of the travel: X = axis travel - (F - F_touch) x compliance.

Type-1 study [S, G1]: master = nominal part, 50 pulls, reference = the same part on an ideal rig. The study rig has a force gain error of 0.2 %, a zero error of 0.02 N and is compensated with 42 N/mm instead of 40 [A].

| Feature | Window width T | Part-to-part sd (ideal rig) | Repeatability s | Bias | Cg | Cgk | Cgk without compensation |
|---|---|---|---|---|---|---|---|
| FMean | 2.02 N | 0.229 N | 0.015 N | +0.033 N | 4.5 | 3.7 | 2.6 |
| FHyst | 4.52 N | 0.530 N | 0.036 N | +0.047 N | 4.2 | 3.8 | 3.9 |
| FpG2 | 3.40 N | 0.389 N | 0.020 N | +0.055 N | 5.8 | 4.8 | 3.6 |
| FPeak | 4.20 N | 0.475 N | 0.033 N | +0.024 N | 4.2 | 4.0 | 3.2 |
| XPeak | 6.12 mm | 0.702 mm | 0.035 mm | -0.016 mm | 5.8 | 5.6 | 2.1 |
| XStop | 2.48 mm | 0.285 mm | 0.004 mm | +0.036 mm | 22.4 | 19.2 | -5.2 |

FStep and FrG1 have one-sided limits; Cg is not defined for them. Resolution: the force resolution is 0.18 % of the narrowest force window. Figure: `docs/img/gauge_type1.png`.

### 5.4 Cycle time and pull speed [D]

| Pull speed | Travel per sample | Test time (clamp to verdict) | Highest force at the stop | Good parts rejected | Weak spring 0.80 found | 1 mm particle found |
|---|---|---|---|---|---|---|
| 25 mm/s | 0.05 mm | 3.07 s | 44 N | 0.29 % | 94 % | 23 % |
| 50 mm/s | 0.10 mm | 1.74 s | 54 N | 0.26 % | 94 % | 21 % |
| 100 mm/s | 0.20 mm | 1.10 s | 87 N | 0.31 % | 94 % | 24 % |
| 200 mm/s | 0.40 mm | 0.84 s | 212 N | 0.19 % | 90 % | 14 % |

Limits are set again for each speed, on 15000 good parts, and tried on another 15000; the false-reject column therefore scatters by about 0.1 points around the target. The force at the stop is from the SCL block in the loop: the PLC reverses in the first sample at or above 40 N, the axis then needs time to stop (acceleration limit 3000 mm/s2 [A]). Sampling is not what limits the speed: at 0.2 mm per sample the detection is unchanged. R-07 limits it.

Station time for an OK part: load 1.5 s + test 1.74 s + unload 1.0 s = 4.24 s of a 12 s takt.

### 5.5 One week on the line (`handletest/line.py`) [D]

OEE terms as in ISO 22400-2 [S, K1; the standard itself not read]: availability = APT / PBT, effectiveness = PRI x PQ / APT, quality rate = GQ / PQ. Classification [A]: logged stops (breakdowns, changeovers, master-part checks) leave APT; micro-stops and reject locks stay inside APT. No buffer in front of the station: a lock costs only what exceeds the slack of the takt. Mean of 10 simulated weeks:

| Method | Availability | Effectiveness | Quality rate | OEE | Parts tested | Good parts rejected | Defective parts passed |
|---|---|---|---|---|---|---|---|
| Peak force only | 96.69 % | 98.79 % | 99.36 % | 94.92 % | 32240 | 50.6 | 59.0 |
| Pull-stroke windows | 97.34 % | 98.69 % | 99.22 % | 95.32 % | 32421 | 52.6 | 14.7 |
| Windows + return stroke | 97.41 % | 98.70 % | 99.24 % | 95.42 % | 32450 | 48.3 | 16.5 |
| Envelope | 96.91 % | 98.72 % | 99.25 % | 94.95 % | 32288 | 87.9 | 61.9 |
| Windows + return stroke, if no good part were rejected | 97.02 % | 98.80 % | 99.39 % | 95.26 % | 32350 | 0.0 | 16.4 |

The week-to-week standard deviation of the OEE is 0.59 points, mostly from breakdowns. The rows differ reliably only in the last two columns. For the chosen method, per week: logged stops 2.91 h, micro-stops 53 min, lock after true rejects 26 min, lock after false rejects 6.2 min. Figure: `docs/img/oee_week.png`.

## 6. Trade study: four evaluation methods

Each method is set on 20000 good parts to reject 0.2 % of them, then tried on 60000 fresh good parts and 5000 parts per defect. Window half-widths: peak 3.30, pull 3.84, pull + return 4.37 standard deviations; envelope = lowest and highest of 300 taught curves widened by 1.58 N.

| Defect | Peak force only | Pull-stroke windows | Windows + return stroke | Envelope |
|---|---|---|---|---|
| Missing spring | 100.0 % | 100.0 % | 100.0 % | 100.0 % |
| Wrong-variant spring (1.6 mm wire) | 98.8 % | 99.9 % | 100.0 % | 74.8 % |
| Weak spring, below the 30 g limit | 79.6 % | 96.5 % | 100.0 % | 42.1 % |
| Binding pivot (+0.15 to +0.60 N m) | 95.4 % | 98.6 % | 100.0 % | 77.0 % |
| Latch lever missing or unhooked | 100.0 % | 100.0 % | 100.0 % | 100.0 % |
| Wrong-hand spring | 100.0 % | 100.0 % | 100.0 % | 100.0 % |
| Particle at the end stop (0.5 to 3 mm) | 0.1 % | 73.8 % | 67.7 % | 52.4 % |
| Weak spring (70 % wind-up) hidden by +0.10 N m pivot friction | 4.9 % | 12.6 % | 100.0 % | 0.2 % |
| **Good parts rejected** (fresh sample) | **0.18 %** | **0.18 %** | **0.17 %** | **0.30 %** |

| Method | Cannot see | Why |
|---|---|---|
| Peak force only | Particle at the stop; a fifth of the weak springs | The peak lies before the stop; the spring is a small part of the peak |
| Pull-stroke windows | A weak spring behind a stiff pivot | Gate 1 reads spring + friction |
| Windows + return stroke | Particles below about 1.25 mm; extra friction below about 0.10 N m | Inside the spread of good parts |
| Envelope | More than half of the weak springs, a quarter of the binding pivots, small particles | The band must cover the take-up and the release step, whose travel varies |

Chosen: windows + return stroke. It is the only method that meets R-01 in the masked case. Its price: the friction window uses most of the false-reject budget, so its other windows are a little wider than those of the pull-only method (particles of 1.0 mm: 14 % against 30 %). Figures: `docs/img/detection_vs_defect_size.png`, `docs/img/false_reject_vs_window_width.png`.

## 7. Models and what they are checked against

### 7.1 Two independent rig models
`handletest/rig.py` (vectorised, for the Monte Carlo) and the plant in `handletest/station.py` (stateful, for the PLC in the loop) were written separately. For good parts the largest difference between their elements is 0.14 (N or mm), with independent noise in each.

### 7.2 PLC in the loop
`FB_CurveEval` against the NumPy evaluation on the same samples: 640 of 640 verdicts equal, largest element difference 9.5e-07. Whole station against the plant, 20 parts per group and method: no good part rejected; reject codes of the chosen method per defect are in `results/summary.json` (`plc_loop.nok_codes_pullret`).

### 7.3 Sensitivity: what moves the false rejects

| Change (limits unchanged) | Pull-stroke windows | Windows + return stroke | Envelope |
|---|---|---|---|
| baseline | 0.20 % | 0.14 % | 0.27 % |
| spring wind-up spread x1.5 | 0.58 % | 0.45 % | 0.31 % |
| pivot friction spread x1.5 | 1.41 % | 1.71 % | 0.32 % |
| cable free-play spread x1.5 | 0.62 % | 0.31 % | 3.45 % |
| release point spread x1.5 | 0.36 % | 0.12 % | 0.70 % |
| detent load spread x1.5 | 0.81 % | 0.31 % | 0.31 % |
| end-stop spread x1.5 | 1.25 % | 0.50 % | 0.29 % |
| load cell noise x3 | 0.16 % | 0.11 % | 0.23 % |
| rig 10 % softer than compensated | 0.09 % | 0.09 % | 0.29 % |
| force gain +1 % | 0.15 % | 0.11 % | 0.29 % |

For the chosen method the friction spread moves the false rejects most. The envelope reacts most to the cable free play. Figure: `docs/img/sensitivity_false_reject.png`.

## 8. Assumed and sourced

Sourced: the 30 g value and the calculation rule (R1, R2), the Type-1 formulas and criteria (G1, G2), the OEE terms (K1), the kinds of evaluation element (M1), the spring formulas (D1).

Assumed: all masses, spring data, friction, latch load, tolerances and their distributions (`mechanism.py`, `NOM` and `SPREAD`); the wrong-variant spring (1.6 mm wire); defect sizes; rig stiffness, noise and calibration errors; axis acceleration; takt, defect rates, micro-stops, breakdowns, operator times (`line.py`).

## 9. FMEA of the test station

| Failure | Effect | What the design does |
|---|---|---|
| Rig deflection not compensated or stiffness changed | Travel elements biased (stop travel 0.67 mm) | Compensation in the PLC; master part shows the bias; 10 % softer rig changes false rejects from 0.14 % to 0.09 % |
| Load cell gain drifts by 1 % | Force elements shift | False rejects 0.11 %; master part at shift start |
| Load cell does not return to zero | Wrong forces | Tare check, fault 4 |
| Chute sensor stuck high | Lock could not be released | Edge, not level, releases the lock; station stays locked (safe side) |
| Chute sensor triggered by something else | Reject back on the line | Release needs the part to have left the fixture first; residual risk remains [not solved] |
| Variant sensor fails | Wrong hand pulled, or every part rejected | Pattern check: exactly one sensor must be on |
| Safety stop during the pull | Part with unknown result | Part becomes a reject (code 24) |
| Pull too fast | More than 60 N on the grip | Speed in the recipe, force limit in the PLC; the limit acts only after the sample |

## 10. Verification and validation

| Requirement | Evidence | Result |
|---|---|---|
| R-01 | `tests/test_model.py` (Annex 4 example, balance at 30 g); detection table | 100.0 % of sub-limit springs rejected; masked case 100 % |
| R-02 | Detection table, `tests/test_plc.py` | All but small particles and slight binding |
| R-03 | Fresh good parts | 0.17 % (95 % interval 0.14 to 0.21 %) |
| R-04 | Type-1 table | Met with compensation |
| R-05, R-06 | `tests/test_plc.py` | Pass in simulation |
| R-07 | Speed table | 54 N at 50 mm/s: met with little margin |
| R-08 | Section 5.4 | 4.24 s of 12 s |

Validation against a real handle and a real rig has not been done. First steps with hardware: measure friction and spring torque of 50 units, run the Type-1 study on the real rig, compile the SCL in TIA Portal and check the cycle load of the 2 ms interrupt.

## 11. Limits of this work

Quasi-static model without inertia or stick-slip. One latch simulator instead of a real latch. Normal and log-normal spreads without correlation. One defect per part, except the masked case. Windows at mean plus or minus k sigma, although the friction element is skewed. The translator runs only the SCL subset used here.

## 12. References

See `docs/SOURCES.md`: R1 UN Regulation No. 11 (03 series, OJ L 120, 13.5.2010); R2 FMVSS 206 (49 CFR 571.206); G1, G2 Type-1 gauge study; K1 OPC 40501-1 Annex C for ISO 22400-2; M1 process-monitoring manual; D1 Shigley chapter 10 slides.
