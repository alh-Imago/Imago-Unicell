# points.md — ACTIVE part (currently entries #1416 onward)

**This is the real, currently-open tail of the single, canonical
points.md ledger — the file new entries get appended to.** Split
across multiple files purely because GitHub won't render a file over
~512KB in the browser; no entry content was changed, reworded, or
reordered. See `points/INDEX.md` for the full real map of which part holds
which entries, and `points.md` (repo root) for the short, canonical pointer
every session should still start from.

**Naming convention, for future-me:** this file keeps the stable name
`points_active.md` (no entry range in the filename) for as long as
it's still being appended to, so appending never requires a rename.
Once it approaches ~350KB, seal it — rename to `points_NN_XXX-YYY.md`
with its real final range, start a fresh, empty `points_active.md`
for continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## #1416 (19 Nov 2026) -- THE LEDGER IS SEALED THROUGH #1415 (part 14), AND THIS FILE STARTS FRESH

*Asked by Alan (19 Nov, 20:58):* "yes seal and start a new one, it gets full fast" (answering my question after the status test failed on size: `points_active.md` was 465,537 bytes, limit 450 KB of `tests/test_status_files_v1.py`; the failure came with my entry #1415 and I had committed and pushed it before reading the test result: my mistake, noted).
*The seal.* `points_active.md` (#1236-#1415) is now `points/points_14_1236-1415.md`; this file starts fresh at #1416. Proof it is lossless: everything after the part's header is byte-for-byte the body of the old active file (the body, from the `## #1236` heading to the end, is 464544 bytes, sha256 `1b7e745aa08e97f238773ccdca6d8e15c26e0562623981a7b48edd61cb71b3e0`; the old whole file was 465537 bytes, sha256 `c29bd95ccb7413f4931e11206dc2fdb382d2dddf964d263e1db73d105d863e87`; checked by reading the new part back and comparing). Only a header was added, in the same words as part 13's with the range changed. No entry was edited, renumbered or reordered. The old file is also in git (the commit before this one).
*Pointers updated:* `points/INDEX.md` (a row for part 14, the open file's row, the "of N" note), root `points.md`, `current/START.md` (the lines that name the newest sealed part), `CLAUDE.md` (the ledger line and the sealed part to read), `current/latest.md`. Not changed: `tests/test_status_files_v1.py` and `_v2.py` both still exist (which one to keep is still Alan's call).
*Size note:* the open file filled to 455 KB over #1236-#1415 (180 entries in 31 days, about 15 KB a day with the width work); at this rate it reaches the 350 KB sealing mark in roughly three weeks, so sealing is likely to come up again.

## #1417 (19 Nov) -- Card: after a fresh load the FIRST run of each image is slow by a fixed amount and every later run is fast; confirms the reading of #1415 (learned durations order the queue)

**Run (Alan, 19 Nov, about 21:00; `cold_test_v1.sh`: bitstream reloaded before each group; `jobs_order_test2.json`, one block, NU=3 build; all 16 runs 9 of 9 correct).**

| group | run 1 | run 2 | run 3 | run 4 |
|---|---|---|---|---|
| A: load, all lw2 x4 | 48,260 | 35,491 | 35,492 | 35,493 |
| B: load, estimate x4 | 43,286 | 36,228 | 36,233 | 36,229 |
| C: load, all lw0, then all lw2 x3 | 117,087 (lw0) | 48,262 | 35,494 | 35,492 |
| D: load, all lw3 x2, then all lw2 x2 | 39,607 (lw3) | 39,612 (lw3) | 48,256 | 35,492 |

**Reading (measured).**
1. **The first run of an image after a load is slow, the next is fast, with no gradual settling:** all lw2 48,256 to 48,262 on its first run (three here, 48,261 in #1414, 48,262 in #1408: five values within 6 clocks) against 35,487 to 35,494 afterwards (12 runs over #1415 and #1417); the estimate's mix 43,282 to 43,289 on its first run (four values with #1408, #1414, #1415) against 36,228 to 36,267 afterwards. The "odd" run of #1408 and the 48,26x reference are the first-run values, reproducible to a few clocks.
2. **It is per width (class and width key), not per file or per load:** in D the lw3 runs show no penalty (39,607 and 39,612, the first no different from the second: with all jobs at lw3 they run one after another, so the order of the queue cannot matter), and the first lw2 run after them is slow again (48,256) although lw3 was already learned; in C the first lw2 run after a lw0 run is slow (48,262), the same as straight after the load in A (48,260).
3. **The 39,100 of #1415 run 1 is a different case:** a first lw2 run after other files had left their own values under the same keys; one run later it was 35,509. Not reproduced here.
4. **The predictions of #1415, checked:** "the first run after a load is not faster than later ones, later runs settle near 35,49x and 36,23x": yes. "In C the lw2 runs after lw0 may start from other values than A": no, the same. "If every first run equals the settled value the reading is wrong": it is not.
5. **The first-in-first-out model of #1411 matches the cold state for all lw2** (49,178 modelled against 48,26x: +1.9%) and for lw0 (115,807 against 117,087: -1.1%); it is 21% too fast for the cold wide-first mix (34,132 against 43,286: the same -21% as the wide-first run of #1407) and 12% too slow for lw3 (44,292 against 39,61x). In the warm state it is wrong for all lw2 (49,178 against 35,49x: +39%). The rough warm variant of #1415 (all jobs queued at once, highest predicted bucket first; not committed) gives 37,293 for all lw2 (+5%), 34,132 for the mix (-6%), 44,292 for lw3 (+12%), 102,339 for lw0 (-13%).

**What this means for use (reasoning from the above, not tested):** a card that has just been loaded runs each new (program number, width) combination slowly once. A warm-up run of the same batch removes the cost for all later runs; the cost is 12,800 clocks (36%) for all lw2 on this batch and 7,060 (19%) for the mix. Comparisons of widths must say whether the runs were cold or warm; the numbers of #1408 and #1409 are a mixture, and a fair rule is to compare the second run of each. Whether the host can seed the duration values before the first run (it cannot today: no command for it is known to me) was not checked in the host link.

**Not done.** A warm mode for the model (queue by bucket, `--estimate` choosing for the warm state) is not built: the offline variant was tried on one batch only; it needs the warm numbers of more batches (`jobs_order_test.json`, `jobs_many_small.json`, `jobs_curve_*`) taken twice in a row after a load. Open: why the cold wide-first mix is 7,060 clocks slower than the warm one (the model does not show it); the lw1 case with 4 or more jobs; the tie of #1407.

## #1418 (19 Nov) -- Own programs: a plain guide (`PROGRAMS.md`) and two new worked examples (`vmin`, `vxor`), checked on the host and in the whole-board simulation; not run on the card

**Asked (Alan, 19 Nov, 21:07 and 21:10):** the user of S-Core supplies the method as well as the data, unlike a fixed engine; the likely use is to make writing a program easy, and examples of how a program is formed will be needed. (My answer, in the conversation: three layers, method + data, a library that hides the method, and execution choices like width that are being automated; Alan: the second is closer to actual use.)

**What already existed (read, not new):** `programs/template.s` (the empty program with the rules in comments), four examples (`crc32`, `vgain`, `vmax`, `vprefix`) with Python answers in `programs/examples.py`, `progs.register()` which checks a program at load time (assembles, fits the code store, trial run on the interpreter, agrees with the Python answer), `jobs_own_example.json`, `test_progs.py`, `test_ownprog_sim.py` (whole board in simulation). What was missing was a guide a non-programmer can follow.

**Added.** `PROGRAMS.md`: the five parts of every program, the rules of the core (RV32I only, no multiply/divide, word loads and stores, the registers the library keeps, the code store limit), `vmax.s` line by line in words, how `vmin` and `vxor` were made from `vmax` and the template, the three steps to use a program (write it, write the answer in Python, name it in a job file), what the host then does (batching, widths, the estimate), a table of the examples. New: `programs/vmin.s` (smallest word; made from `vmax` by changing the start value, the comparison and adding an empty-input line), `programs/vxor.s` (each input XOR the job's `arg`; the template with one changed line plus reading `arg`), `programs/examples_v2.py` (their Python answers; `examples.py` is untouched), `jobs_own_examples2.json` (5 jobs: three vmin including an empty input and two all-ones words, two vxor), `test_own_examples_v1.py`.

**Checks (measured here, none on the card).** (1) `test_own_examples_v1.py`: 9 checks pass (registry load; the interpreter agrees with the Python answer on all five jobs; vxor with too little output room is refused with status 2 and nothing produced; the five jobs compile into one batch). (2) **Whole-board simulation, `python3 test_ownprog_sim.py jobs_own_examples2.json` (iverilog, the RTL cores):** all 5 jobs status 1 and the outputs equal the Python answers (vmin 5, 0xfffffffe, 0; vxor 0xfe 0xfd 0xfc 0xffffff00 and 10 20 30); batch of 34 script steps, code 82 of 128 words, shared 74 of 256 words, 25,997 board clocks; the SDRAM model reports no timing violations. (3) `scblocks.py --plan jobs_own_examples2.json --blocks 1` works (one batch, two kinds). The 71, 51, 38, 70 and 62 instructions of the five jobs are counted by the interpreter.

**Not done.** Not run on the card. The estimate uses the crc32 clocks per instruction for the two new kinds (no measured value; `cpi_run_v1.sh` covers only the four library kinds). The guide is untested on a person: whether Alan can follow it unaided is not known.

## #1419 (19 Nov) -- A ladder from one command to a program of your own (`LADDER.md`, four job files, `ladder_show.py`, `vcount`); host and whole-board simulation checked; not run on the card

**Asked (Alan, 19 Nov, 21:18):** "run from the simplest single set of commands, through to a small program". Read as: a graded walk-through with exact commands, from one job on the card up to a program of his own.

**What it is.** `s-core/LADDER.md`, six steps, each with the same three moves (look first with no card; run on the card with `--out`; compare): step 0 get the card ready (pull, load `sc_k7_fu2s8u8n3.bit`); 1 one job (`ladder_1_one_job.json`: vsum 1+2+3+4 = 10); 2 three jobs of different kinds in one file (`ladder_2_three_jobs.json`: vsum 60, vmax 99, vprefix 1 3 6 10 15); 3 more data with `{"seq": [start, count, step]}` (`ladder_3_more_data.json`: 5050, 134650, 242, 9649; the host splits it into two batches by itself); 4 how wide (the same file at `--lw 0`, `--lw 2` and `--lw auto --profile ... --estimate`, each run twice, compare the second, #1417); 5 a program of his own (`programs/vcount.s`: counts inputs bigger than `arg`, made from `vmax.s`; `ladder_5_my_program.json`: 3, 0, 50; then an exercise: copy it, swap one comparison to count the inputs SMALLER than `arg`, write the one-line Python answer, run it). New files: `ladder_1_one_job.json`, `ladder_2_three_jobs.json`, `ladder_3_more_data.json`, `ladder_5_my_program.json`, `ladder_show.py` (prints what a job file should give; with a result file made by `scblocks.py ... --out` it puts the card's numbers next to the right ones: MATCH or DIFFERENT, exit 1 if any differ), `programs/vcount.s`, `programs/examples_v3.py` (its Python answer; the earlier example files are untouched), `test_ladder_v1.py`.

**Checks (measured here, none on the card).** (1) `test_ladder_v1.py` 12 checks pass: the four job files give the answers the guide promises; all compile; step 3 needs two batches; `ladder_show` says MATCH for a right result file and DIFFERENT (exit 1) for a wrong number; **the exercise of step 5 works** (swapping `bgeu t5,t0,skip` for `bgeu t0,t5,skip` makes the program count the inputs below `arg`; the interpreter agrees with the Python answer). (2) Whole-board simulation (`test_ownprog_sim.py`, iverilog, the RTL cores): `ladder_5_my_program.json` all 3 jobs status 1 and equal to the answers (3, 0, 50), 2 batches, 26 script steps, no SDRAM timing violations; `ladder_2_three_jobs.json` all 3 jobs correct (60, 99, 1 3 6 10 15), 1 batch, 22 steps, 19,899 board clocks, no violations. (3) `scblocks.py --plan` works on all four, also with `--lw 2` and with `--estimate` for step 4 (the estimate chose lw2 for both batches of step 3).

**Not done.** Not run on the card. Steps 1 and 3 were not run in the whole-board simulation (host checks and `--plan` only; the vsum and vmax kinds are covered by earlier sim tests). The `--out` result file and `ladder_show` pairing was tested with a made-up result file in the format `scblocks.py` writes (read from the code), not with a real card output. Step 4 numbers were not measured. Whether Alan can follow it unaided is not known.

Next entry: #1420.
