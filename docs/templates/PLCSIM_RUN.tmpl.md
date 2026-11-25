# Running the compiled blocks in S7-PLCSIM

This page is generated from `docs/templates/PLCSIM_RUN.tmpl.md` by `scripts/make_docs.py`.

**Status: prepared, not run in PLCSIM.** The test project compiles in TIA Portal V18 and the same sources pass in the Python translator. S7-PLCSIM was not available where the project was built. The record of the PLCSIM run is the last section of this page and is still empty.

## What the test bench does

The test project holds the two blocks of the repo, unchanged (`FB_CurveEval`, `FB_HandleStation`), and a test bench from `plc/test/` that runs by itself in OB1. It needs no input, no watch table and no forcing.

| Block | Source | Role |
|---|---|---|
| `DB_TestData` | `plc/test/DB_TestData.scl`, written by `scripts/make_plcsim_bench.py` | {{b.curves}} recorded force-travel curves from the Python model ({{b.samples}} samples, {{b.data_bytes/1000:.0f}} kB of Real data), the limits and the envelope of the study, and for every replay case the verdict, NOK code and element values of the NumPy evaluation |
| `FB_TestPlant` | `plc/test/FB_TestPlant.scl` | Stand-in for axis, clamp and handle: the force comes from a recorded curve at the present travel |
| `FB_TestBench` | `plc/test/FB_TestBench.scl` | Runs the cases, compares, counts |
| `DB_TestResult` | `plc/test/DB_TestResult.scl` | The result. This is the block to look at |
| `InstTestBench`, `Main` (OB1) | `plc/test/OB_Main.scl` | Instance of the bench and its call in every cycle |

Part 1, {{b.replay_cases}} replay cases. A recorded curve goes sample by sample into `FB_CurveEval`: the pull samples, then the return samples. After the last sample the bench compares the verdict, the NOK code, the nine elements (FpG1, FrG1, FMean, FHyst, FpG2, FPeak, XPeak, FStep, XStop) and the two envelope counts with the values in `DB_TestData`. An element may differ by {{b.tolerance}} (N or mm). The generator refuses a case that lies closer than {{b.margin}} to a limit it is judged by, so a difference in the last bit cannot turn a verdict.

Part 2, {{b.station_cases}} station cases. `FB_HandleStation` runs against `FB_TestPlant` with 2 ms of station time per scan. {{b.translator.station.CntTotal}} units are judged; all but the RH unit are pulled.

{{bench_case_table(b)}}

The station cases check more than the code: counters, state, that the axis and the clamp did not move for the RH unit, that the lock stayed closed and that the start stayed blocked. The checks are listed in the header of `FB_TestBench.scl`.

## What is known before PLCSIM

- TIA Portal V18, blocks alone: `{{t.blocks.compile}}` (`results/tia_compile.txt`).
- TIA Portal V18, whole test project for the same CPU (S7-1513, 6ES7 513-1AL02-0AB0, V2.9): `{{t.bench.compile}}` (`results/tia_compile_testbench.txt`). `Main` is OB 1 in SCL; all blocks are consistent.
- Translator (`tests/test_plcsim_bench.py`, in CI): the same seven source files, data blocks and OB1 included, give **{{b.translator.CasesPassed}} of {{b.translator.CasesTotal}} cases passed** after {{b.translator.BenchCalls}} OB1 cycles; largest element difference {{b.translator.MaxFeatError:.1e}}.
- The tests also change the data on purpose (a wrong expected element, verdict or code; a station scenario whose defective unit is good; a station block without the reject lock) and check that the bench then reports the right case and check number. So a pass is not empty.

What the translator cannot show: that the S7-1500 computes the Real expressions to the same last digits, and that the compiled blocks behave like their translation. That is what the PLCSIM run is for.

## How to run it

The archive is not in the repo. It is written by:

```
powershell -ExecutionPolicy Bypass -File scripts\tia_build.ps1 -Blocks "FB_CurveEval,FB_HandleStation,test\DB_TestData,test\DB_TestResult,test\FB_TestPlant,test\FB_TestBench,test\OB_Main" -OutDir C:\TIA_build\plcsim -ProjectName handle37_plcsim_test -ArchiveDir C:\TIA_build\plcsim -ArchiveName handle37_plcsim_test.zap18 -ResultFile results\tia_compile_testbench.txt
```

Last build: `{{t.bench.archive_file}}`, {{t.bench.archive_bytes}} bytes ({{t.bench.header}}). The project is already compiled and has "Support simulation during block compilation" switched on ({{t.bench.simulation}}).

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
| `CasesTotal` | {{b.translator.CasesTotal}} |
| `CasesRun` | {{b.translator.CasesRun}} |
| `CasesPassed` | {{b.translator.CasesPassed}} |
| `CasesFailed` | {{b.translator.CasesFailed}} |
| `FirstFailedCase` | {{b.translator.FirstFailedCase}} |
| `FirstFailedCheck` | {{b.translator.FirstFailedCheck}} |
| `CasePass[1]` to `CasePass[{{b.translator.CasesTotal}}]` | TRUE (`CasePass[{{b.translator.CasesTotal + 1}}]` to `[32]` stay FALSE) |
| `CaseCheck[1]` to `CaseCheck[32]` | 0 |
| `CaseNok[1]` to `CaseNok[{{b.translator.CasesTotal}}]` | {{", ".join(str(v) for v in b.translator.CaseNok)}} |
| `MaxFeatError` | below {{b.tolerance}} (translator: {{b.translator.MaxFeatError:.1e}}; the last digits may differ on the CPU) |
| `BenchCalls` | {{b.translator.BenchCalls}} (the bench works a fixed amount per call, so the count does not depend on the cycle time) |

`Done`, `AllPassed`, `CasesPassed = {{b.translator.CasesPassed}}` and `CasesFailed = 0` are the verdict; the other rows help if something is different.

A second place to look, not needed for the verdict: `InstTestBench.Station` must show `CntTotal` {{b.translator.station.CntTotal}}, `CntOk` {{b.translator.station.CntOk}}, `CntNok` {{b.translator.station.CntNok}}, `CntRejectConfirmed` {{b.translator.station.CntRejectConfirmed}}, `State` 0.

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
