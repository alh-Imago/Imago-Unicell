# S-Core: write-up before the larger build (19 Nov 2026, ledger #1424)

Written for Alan, who is not a programmer. Every claim is marked: **measured** (a real run on the card or a real simulation, with the ledger entry), **read from the RTL** (checked against the Verilog, not measured), or **reasoned** (my reading, not tested). Where the ledger and this page differ, the ledger and `current/latest.md` win.

## 1. What it is, in five lines

- S-Core is a pool of 1-bit RISC-V (RV32I) cores with no interrupts. One program runs at any width: neighbouring 1-bit slices can be **fused** into a 2, 4, 8 or 16 lane core for one job, so width is a speed dial, never a change of result.
- A **job** is one program plus one set of data. A **batch** is up to 16 jobs sharing a 128-word code store and 256 words of shared data (numbers for the 2x8 build, reported by the card).
- You supply both the method (the program) and the data; the machine is a pool, not a fixed engine.
- The target is a Kintex-7 XC7K480T card (open openXC7 flow, JTAG only, no PCIe). The Tang Nano 20K was the first target and is kept.
- Everything the host does (compile jobs, choose widths, run, compare with the right answer) is Python in `s-core/`; the card only sees compiled numbers.

## 2. What has been proven, and how

| claim | status |
|---|---|
| Telemetry job set, 24 of 24 correct, JTAG link, S=4 and S=16 builds; DDR3 far RAM build | **measured** on the card (README, `k7/`) |
| Runtime fusion: 2x4 slices with a 4-lane unit: 1.85x (lw 1), 3.3x (lw 2); 2x8 with an 8-lane unit: 1.84x, 3.09x, 5.78x (lw 3); 94.04 MHz (2x4), 85.48 MHz (2x8) | **measured** (README; #1378 to #1386) |
| Three user job kinds written by hand (vmin, vxor, vcount) and the ladder of commands | simulation and interpreter; vsum/vmax/vxor **measured** on the card via the shell (#1421) |
| The shell (`score_shell_v1.py`): typing jobs, save/open, plan, run, compare | **measured**: first run 3 of 3 correct, 87,180 clocks (#1421) |
| `make` (new job kinds from recipes) | **measured** on the card: 3 kinds, 5 of 5 correct, 69,287 clocks (#1423); 80 random recipes agree with Python on the interpreter (#1422) |
| Multi-block top (several blocks, one host bridge, one far-RAM arbiter) | **simulation only** (#1347) |
| Critical-job design (reserved cores, jump, suspend) | **design only**, logged, not built (#1410) |

## 3. The software stack (all in `s-core/`)

- **Job file** (JSON, host side only): programs and jobs. `scblocks.py` compiles them into batches (`jobcomp_v2.py`), loads far RAM, runs, and compares each result with the right answer computed in Python.
- **Width per job** (`lw` 0..4: 2**lw slices fused): fixed, or `--lw auto` using a **card profile** made by `sc_calibrate_v1.py` (`--profile NAME`).
- **Submit order** inside a batch: `--submit-order auto` is the default (wide jobs first when that helps).
- **Length estimate** (`lengthest_v1.py`, `--estimate`): the host counts a job's instructions on the reference interpreter, turns that into clocks with a model fitted on the card, and picks a width per job. Optional; off by default.
- **Own programs**: `PROGRAMS.md`, `programs/template.s`, `register`. **New kinds without assembly**: `make` in the shell (`jobmaker_v1.py`; recipes of add/sub/xor/and/or/shl/shr/not with an optional `then sum|xor|or|and|min|max`).
- **Shell** `score_shell_v1.py` (help: `SHELL.md`): Tab completion, optional live colours (needs `prompt_toolkit` visible to the Python that runs it).

## 4. What the 19 Nov card runs established

**Measured:**
- Cost of a job, in clocks per instruction on width 0: crc32 133.5; vsum 145.9; vgain 135.8; vmax 145.1; vprefix 151.2 (#1412). The estimate model reproduces single crc32 jobs within 1.7% and identical-job batches (mean 0.9%) offline; in mixed batches 7 of 8 were within 6.3% and one was 21% short, unexplained (#1411, #1412).
- **Cold and warm differ.** Every card build keeps learned job durations that order the bulk queue and survive a reset (`LONGEST=1`, read from the RTL, #1415; this corrects #1405). The first run of an image after a fresh load is slower by a fixed amount (all-lw2 on one file: 48,256 to 48,262 clocks cold, 35,487 to 35,494 warm). **Rule: measure warm (run twice, use the second) or from a fresh load, and say which.** Confirmed by `cold_test_v1.sh` (#1417).
- **Wide-first against wide-last** with a long wide job: 36,23x against 51,96x clocks (#1408, repeats with a 7-clock spread, #1409). The critical flag did not change that test (#1407).
- `--estimate` equals the best fixed width on two of three job files; the third could not be judged because of the cold/warm effect (#1414).
- On three smaller builds, the identical-job profile **lost** on mixed jobs by 14% to 62%; the widest-everything rule was best or near-best on most (#1403). On a 2x4 build with one unit, lw 1 was slower than lw 0 (#1403).

**Withdrawn:** "a mixed-width batch beats every uniform width" (#1408, #1409): a warm all-lw2 run (35,490) was as fast as the mix (36,23x). No proven gain of `--estimate` over a uniform lw 2 exists yet.

**Unexplained:** why the cold wide-first mix is about 7,060 clocks slower than warm; one mixed-batch estimate 21% short; lw 1 behaviour for N >= 4 jobs.

## 5. Limits you will meet

- A batch holds at most 16 jobs, 128 code words and 256 shared words on the 2x8 build; the compiler splits the rest into more batches (a made kind costs about 15 to 30 code words).
- Library calls change only t0, t1, a0, a1; RV32I only, `lw`/`sw` only, no multiply or divide; no preemption: a job runs to the end.
- The estimate uses crc32's cost for kinds it has not measured (vmin, vxor, vcount, every made kind).
- The estimate and the profile are **fitted to the 2x8, 3-unit build** (`profiles/example_2x8_nu3_v2.json`). They are not valid for a different build until re-measured.
- Not covered on the card yet by `make`: constants above 12 bits, shifts by `arg`, the min/and/or/xor endings, widths above 0 (this is what the second card test, section 6, is for).

## 6. The second card test (for tonight or first thing)

`made_demo2_v1.score` (12 jobs, 6 made kinds, 2 batches: code 123/128 and 117/128 words): big constants, shifts by `arg` (including `arg=37`, low 5 bits), every ending, a one-word job, 17-word jobs, and the same job at widths 0, 1, 2, 3 (answers must be identical). It runs twice; the second run is warm.

    cd ~/Imago-Unicell-score && git pull && cd s-core
    nix shell nixpkgs#openocd --command python3 score_shell_v1.py -f made_demo2_v1.score

Pass = "12 of 12 jobs correct" on both runs, all MATCH. A failure names the job; paste the output. The width comparison is by answers only (clock differences between widths here are not a speed test).

## 7. Before kicking off the larger build

I do not know the build's size (slices per block, blocks, unit width, far RAM type); fill these in before the morning run: ______ .

1. **Timing first.** Look at the timing report; never load a bitstream that failed timing (`k7/README.md`). Power-cycle before loading a different design.
2. **Wrong-bitstream guard**: the calibration program checks the build (#1402); if the board reports other slices or blocks than you built, stop.
3. **Re-measure the profile for the new build** (the old one does not apply): `python3 sc_calibrate_v1.py run --name NEWNAME --blocks N --unit-lw X --units Y --quick`, then `show profiles/NEWNAME.json`. Use the real unit settings of the build (`--unit-lw` = log2 of the lanes of a unit; `--units` = units per block).
4. **Smoke tests in the shell** (start with the openocd wrapper): `made_demo_v1.score`, then `made_demo2_v1.score`; both twice.
5. **Warm vs cold**: after loading, run each test twice and log both; do not compare a cold run with a warm one.
6. **Only then** the width questions: `set profile NEWNAME`, `set lw auto`, `plan`, `run`; compare with `set lw 2`. The estimate (`set estimate on`) needs the per-kind timings re-fitted (`lengthest_v1.py fit-kinds`) for the new build.
7. **Do not trust the old numbers** in section 4 for the new build: they are 2x8, 3-unit figures.

## 8. Commands you will use

| you want | type |
|---|---|
| start the shell with the card | `nix shell nixpkgs#openocd --command python3 score_shell_v1.py` |
| live colours too | add Python with prompt_toolkit: `nix shell --impure --expr 'with import <nixpkgs> {}; buildEnv { name = "score-env"; paths = [ openocd (python3.withPackages (ps: [ ps.prompt-toolkit ])) ]; }' --command python3 score_shell_v1.py` (worked on your machine once) |
| run a file of commands | add `-f FILE.score` (and `-q` to leave after) |
| jobs | `add KIND data... [arg=N] [lw=N]`, `list`, `show`, `save F.json`, `open F.json` |
| new kind | `make NAME steps... [then ending]`, `code NAME`, `programs` |
| widths | `set lw auto`, `set profile NAME`, `set estimate on` |
| look and run | `plan` (no card), `run` |
| the long way (no shell) | `python3 scblocks.py jtag jobs.json [--lw auto --profile NAME] [--estimate --estimate-margin 0.10]` |

## 9. Where things are

`README.md` (files and quick start), `BATCH_FORMAT.md` (batch, script, SUBMIT word, dispatcher facts), `PROGRAMS.md` (own programs, `make`), `LADDER.md` (commands from one job to your own program), `SHELL.md` (shell commands), `k7/README.md` (Kintex build), `current/latest.md` (live state), `points/` (the ledger: #1378 to #1386 fusion, #1397 to #1403 calibration and profile, #1404 to #1409 order and critical, #1411 to #1415 estimate and cold/warm, #1418 to #1423 programs, ladder, shell, make).

## 10. Open items

- Why wide-first equals wide-last in #1407 while the model says wide-first should win by 19%.
- The warm model for the estimate (not built; needs warm numbers from more batches).
- A critical-job mechanism (reserved cores, out-of-queue jump, suspend, or "critical = full width"): your design notes are in #1410; not built.
- Whether `PROGRAMS.md` and `LADDER.md` can be followed by you unaided: untested on a person.
- A friendlier shell message when OpenOCD is missing; calibration and bitstream load as shell commands.
- The ledger: `points_active.md` grows about 15 KB a day; seal at about 350 KB.
