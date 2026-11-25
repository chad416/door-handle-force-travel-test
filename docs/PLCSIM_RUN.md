# Running the compiled blocks in S7-PLCSIM

This page is generated from `docs/templates/PLCSIM_RUN.tmpl.md` by `scripts/make_docs.py`.

**Status: prepared, not run in PLCSIM.** The test project compiles in TIA Portal V18 and the same sources pass in the Python translator. S7-PLCSIM was not available where the project was built. The record of the PLCSIM run is the last section of this page and is still empty.

## What the test bench does

The test project holds the two blocks of the repo, unchanged (`FB_CurveEval`, `FB_HandleStation`), and a test bench from `plc/test/` that runs by itself in OB1. It needs no input, no watch table and no forcing.

| Block | Source | Role |
|---|---|---|
| `DB_TestData` | `plc/test/DB_TestData.scl`, written by `scripts/make_plcsim_bench.py` | 10 recorded force-travel curves from the Python model (5932 samples, 47 kB of Real data), the limits and the envelope of the study, and for every replay case the verdict, NOK code and element values of the NumPy evaluation |
| `FB_TestPlant` | `plc/test/FB_TestPlant.scl` | Stand-in for axis, clamp and handle: the force comes from a recorded curve at the present travel |
| `FB_TestBench` | `plc/test/FB_TestBench.scl` | Runs the cases, compares, counts |
| `DB_TestResult` | `plc/test/DB_TestResult.scl` | The result. This is the block to look at |
| `InstTestBench`, `Main` (OB1) | `plc/test/OB_Main.scl` | Instance of the bench and its call in every cycle |

Part 1, 14 replay cases. A recorded curve goes sample by sample into `FB_CurveEval`: the pull samples, then the return samples. After the last sample the bench compares the verdict, the NOK code, the nine elements (FpG1, FrG1, FMean, FHyst, FpG2, FPeak, XPeak, FStep, XStop) and the two envelope counts with the values in `DB_TestData`. An element may differ by 0.001 (N or mm). The generator refuses a case that lies closer than 0.02 to a limit it is judged by, so a difference in the last bit cannot turn a verdict.

Part 2, 6 station cases. `FB_HandleStation` runs against `FB_TestPlant` with 2 ms of station time per scan. 5 units are judged; all but the RH unit are pulled.

| Case | What runs | Evaluation mode | Expected verdict | Expected NOK code (`CaseNok`) |
|---|---|---|---|---|
| 1 | Replay: good, nominal part | 3 (windows + return stroke) | OK | 0 |
| 2 | Replay: good, random part | 3 (windows + return stroke) | OK | 0 |
| 3 | Replay: missing spring | 3 (windows + return stroke) | NOK | 2 |
| 4 | Replay: weak spring, 70 % wind-up (below the 30 g limit) | 3 (windows + return stroke) | NOK | 2 |
| 5 | Replay: wrong-variant spring (1.6 mm wire) | 3 (windows + return stroke) | NOK | 2 |
| 6 | Replay: binding pivot, +0.35 N m | 3 (windows + return stroke) | NOK | 3 |
| 7 | Replay: latch lever unhooked | 3 (windows + return stroke) | NOK | 5 |
| 8 | Replay: wrong-hand spring | 3 (windows + return stroke) | NOK | 2 |
| 9 | Replay: particle at the end stop, 2.0 mm | 3 (windows + return stroke) | NOK | 9 |
| 10 | Replay: weak spring (70 %) hidden by +0.10 N m pivot friction | 3 (windows + return stroke) | NOK | 2 |
| 11 | Replay: weak spring (70 %) hidden by +0.10 N m pivot friction | 2 (pull-stroke windows) | OK | 0 |
| 12 | Replay: particle at the end stop, 2.0 mm | 1 (peak force only) | OK | 0 |
| 13 | Replay: good, nominal part | 4 (envelope) | OK | 0 |
| 14 | Replay: weak spring, 70 % wind-up (below the 30 g limit) | 4 (envelope) | OK | 0 |
| 15 | Station: good LH unit is clamped, pulled and passed | 3 | OK | 0 |
| 16 | Station: RH unit on an LH recipe is rejected with code 20 and never pulled | 3 | NOK | 20 |
| 17 | Station: the reject lock ignores a chute signal while the part is in the fixture, refuses a new part, and opens when the chute sensor sees a part after the fixture is empty | 3 | stays locked, then opens | 20 |
| 18 | Station: unit with unhooked latch lever is pulled and rejected with code 5 | 3 | NOK | 5 |
| 19 | Station: third reject in a row asks for the master part and blocks the start | 3 | NOK, start blocked | 5 |
| 20 | Station: after the acknowledge a good unit is pulled and passed | 3 | OK | 0 |

The station cases check more than the code: counters, state, that the axis and the clamp did not move for the RH unit, that the lock stayed closed and that the start stayed blocked. The checks are listed in the header of `FB_TestBench.scl`.

## What is known before PLCSIM

- TIA Portal V18, blocks alone: `COMPILE Success errors=0 warnings=0` (`results/tia_compile.txt`).
- TIA Portal V18, whole test project for the same CPU (S7-1513, 6ES7 513-1AL02-0AB0, V2.9): `COMPILE Success errors=0 warnings=0` (`results/tia_compile_testbench.txt`). `Main` is OB 1 in SCL; all blocks are consistent.
- Translator (`tests/test_plcsim_bench.py`, in CI): the same seven source files, data blocks and OB1 included, give **20 of 20 cases passed** after 102 OB1 cycles; largest element difference 9.5e-07.
- The tests also change the data on purpose (a wrong expected element, verdict or code; a station scenario whose defective unit is good; a station block without the reject lock) and check that the bench then reports the right case and check number. So a pass is not empty.

What the translator cannot show: that the S7-1500 computes the Real expressions to the same last digits, and that the compiled blocks behave like their translation. That is what the PLCSIM run is for.

## How to run it

The archive is not in the repo. It is written by:

```
powershell -ExecutionPolicy Bypass -File scripts\tia_build.ps1 -Blocks "FB_CurveEval,FB_HandleStation,test\DB_TestData,test\DB_TestResult,test\FB_TestPlant,test\FB_TestBench,test\OB_Main" -OutDir C:\TIA_build\plcsim -ProjectName handle37_plcsim_test -ArchiveDir C:\TIA_build\plcsim -ArchiveName handle37_plcsim_test.zap18 -ResultFile results\tia_compile_testbench.txt
```

Last build: `C:\TIA_build\plcsim\handle37_plcsim_test.zap18`, 858466 bytes (TIA Portal V18, CPU OrderNumber:6ES7 513-1AL02-0AB0/V2.9, 2026-11-25 04:20). The project is already compiled and has "Support simulation during block compilation" switched on (simulation support during block compilation: True).

1. TIA Portal V18: **Project > Retrieve**, choose `handle37_plcsim_test.zap18`, choose a target folder. The project opens.
2. Select **PLC_1** in the project tree and press **Start simulation** (toolbar, or Online > Simulation > Start). Confirm the message about the online interfaces. S7-PLCSIM starts with an unconfigured CPU.
3. The dialog "Extended download to device" opens: PG/PC interface **PLCSIM**, **Start search**, select the CPU that is found, **Load**. In "Load preview" press **Load**; in "Load results" choose **Start module** and **Finish**.
4. If the CPU is not in RUN, press **RUN** in PLCSIM. The bench starts with the first cycle and is finished within a few seconds.
5. Project tree: **PLC_1 > Program blocks > DB_TestResult**, open it and press **Monitor all**.

To run it again: STOP and RUN in PLCSIM. All data blocks are non-retentive, so the bench starts from the beginning.

If TIA Portal asks to switch on "Support simulation during block compilation" (project properties > Protection), switch it on, compile PLC_1 (Software, rebuild all) and download again.

## Values that mean pass

Monitor values of `DB_TestResult` after the bench has finished:

| Tag | Must show |
|---|---|
| `Done` | TRUE |
| `AllPassed` | TRUE |
| `CasesTotal` | 20 |
| `CasesRun` | 20 |
| `CasesPassed` | 20 |
| `CasesFailed` | 0 |
| `FirstFailedCase` | 0 |
| `FirstFailedCheck` | 0 |
| `CasePass[1]` to `CasePass[20]` | TRUE (`CasePass[21]` to `[32]` stay FALSE) |
| `CaseCheck[1]` to `CaseCheck[32]` | 0 |
| `CaseNok[1]` to `CaseNok[20]` | 0, 0, 2, 2, 2, 3, 5, 2, 9, 2, 0, 0, 0, 0, 0, 20, 20, 5, 5, 0 |
| `MaxFeatError` | below 0.001 (translator: 9.5e-07; the last digits may differ on the CPU) |
| `BenchCalls` | 102 (the bench works a fixed amount per call, so the count does not depend on the cycle time) |

`Done`, `AllPassed`, `CasesPassed = 20` and `CasesFailed = 0` are the verdict; the other rows help if something is different.

A second place to look, not needed for the verdict: `InstTestBench.Station` must show `CntTotal` 5, `CntOk` 2, `CntNok` 3, `CntRejectConfirmed` 3, `State` 0.

If a case fails: `FirstFailedCase` is the case number of the table above and `FirstFailedCheck` says what differed. Replay: 1 verdict, 2 NOK code, 3 FpG1, 4 FrG1, 5 FMean, 6 FHyst, 7 FpG2, 8 FPeak, 9 XPeak, 10 FStep, 11 XStop, 12 envelope nodes outside, 13 envelope nodes evaluated. Station: 21 verdict, 22 NOK code, 23 state, 24 counter, 25 axis or clamp, 26 lock opened too early or a part started while locked, 27 lock not opened by the chute, 28 master-part request, 29 time-out. `Done` staying FALSE means the bench did not finish: note `CasesRun` and `BenchCalls`.

## Record of the PLCSIM run

**Not run yet. Fill in after the run; until then nothing in this repo claims a PLCSIM pass.**

| | |
|---|---|
| Date | |
| TIA Portal / S7-PLCSIM version | |
| CPU in PLCSIM | |
| Archive used (file, size) | |

| Tag | Observed |
|---|---|
| `Done` | |
| `AllPassed` | |
| `CasesTotal` | |
| `CasesRun` | |
| `CasesPassed` | |
| `CasesFailed` | |
| `FirstFailedCase` | |
| `FirstFailedCheck` | |
| `MaxFeatError` | |
| `BenchCalls` | |

Screenshot of `DB_TestResult` in "Monitor all": *to be added as `docs/img/plcsim_db_testresult.png`*
