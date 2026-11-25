# Changelog

## 1.0.0 (2026-11-25)
- Handle mechanism model (lever, torsion spring, pivot friction, latch load with release step, end stop), seven defect models.
- Minimum spring preload from the 30 g inertial load rule of UN R11; the sample calculation of its Annex 4 as a test.
- Rig model (compliance, sampling, noise, touch detection), Type-1 gauge study with and without compliance compensation.
- Four evaluation methods set to the same false-reject target; detection per defect, severity sweeps, sensitivity.
- SCL blocks FB_CurveEval and FB_HandleStation, run in the loop through the SCL translator; station poka-yoke tests.
- One simulated week on a three-shift line with OEE terms; nine figures; dossier; CI.
