# Changelog

## 1.1.1 (2026-11-25)
- Test project run in S7-PLCSIM Advanced V7.0 Upd1 under TIA Portal V20 Update 7 (project upgraded from V18; two CPU protection settings set by hand so that the hardware compiles): 20 of 20 cases passed, BenchCalls 102, MaxFeatError 7.629395E-06. Record, observed values and screenshots in docs/PLCSIM_RUN.md; README and dossier say what was run. No source changed.

## 1.1.0 (2026-11-25)
- Test bench that runs inside the PLC (plc/test): recorded curves and expected values in a generated data block, plant stand-in, bench block, result data block, OB1. 20 cases.
- Translator: global and instance data blocks, organization blocks, access to instance inputs and nested instances. The bench runs in pytest and in CI.
- scripts/tia_build.ps1 builds, compiles and archives the test project; record in results/tia_compile_testbench.txt. docs/PLCSIM_RUN.md says how to run it in S7-PLCSIM. The PLCSIM run itself is not done.

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
