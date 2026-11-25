# Changelog

## 1.0.1 (2026-11-25)
- Both SCL blocks keep their working values in static variables and write their outputs once, at the end of every call; FB_CurveEval has no early RETURN any more.
- TIA Portal V18 compile: 0 errors, 0 warnings (results/tia_compile.txt, scripts/tia_build.ps1).
- Translator: whole-array copy. Two more tests.

## 1.0.0 (2026-11-25)
- Handle mechanism model (lever, torsion spring, pivot friction, latch load with release step, end stop), seven defect models.
- Minimum spring preload from the 30 g inertial load rule of UN R11; the sample calculation of its Annex 4 as a test.
- Rig model (compliance, sampling, noise, touch detection), Type-1 gauge study with and without compliance compensation.
- Four evaluation methods set to the same false-reject target; detection per defect, severity sweeps, sensitivity.
- SCL blocks FB_CurveEval and FB_HandleStation, run in the loop through the SCL translator; station poka-yoke tests.
- One simulated week on a three-shift line with OEE terms; nine figures; dossier; CI.
