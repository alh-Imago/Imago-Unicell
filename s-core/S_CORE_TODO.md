# S-Core to-do list (living file; edit it, tick items off as they are done)

Kept for Alan, who may not come back to a thread for a week or more. The ledger (points/) says what happened and is append-only; this file says what is still to do. Last updated: ledger #1538, 27 Nov 2026. Each tick names the ledger entry that shows it.

## A. Builds on the card (Alan runs these)
- [x] Three hj builds run; all met timing (#1526).
- [x] Sizes and slack recorded, manifests filled (#1526).
- [x] hj4s16u16n1i128 on the card, all correct (#1527)
- [x] hj4s16u16n1i1024 on the card, all correct (#1528)
- [x] hj8s32u32n1i1024 basics, one job and eight jobs on 8 blocks correct (#1529)
- [x] hj8s32u32n1i1024 lw 0 to 4 with --unit-lw 5 correct (#1530)
- [x] Cause of the lw 5 failure found and fixed in simulation: sc_sys_v22 (#1531)
- [x] hk4s16u16n1i1024 and hk8s32u32n1i1024 built, timing met (#1532)
- [x] hk8s32u32n1i1024 on the card: lw 0 to 5 correct, 8 jobs at once at lw 5 (#1533)
- [ ] hk4s16u16n1i1024 on the card (optional; same dispatcher as the 8 x 32 one, #1533)
- [ ] Check whether v16 to v20 (the hh and hj lines) fail the same shared-store test in simulation (#1531)
- [ ] A compute-heavy job on the card (like sum100 / crc32 in the simulation) to show the fetch fix; the vector ladders are too small (#1527)
- [ ] A program above 128 code words on hj4s16u16n1i1024 (run with `--imem 1024`; the planner defaults to 128, #1528)
- [ ] Make scblocks.py ask the board for the code-store size, as it does for the shared RAM size (new file version; #1528) (first-read test first after load; single job; 16-job set; shared RAM; far RAM; fusion at lw 0..5 for the 32-lane build).
- [ ] Decide whether to card-test a `hi` (grouped arbiter) bitstream (#1491; parked, whole top unsimulated).
- [x] 16 x 16 and 8 x 32 plain builds on the card (#1496 to #1510); fusion build hh4s16u16n1 on the card (#1512).

## B. Design changes
- [x] 32-lane fusion unit, generators make_unit v6 to v9, stand-alone gate passes (#1514).
- [x] Dispatcher sc_sys_v19 (32-lane branch) passes the pool test (#1515).
- [x] Bottleneck found: a unit got one instruction per S clocks (#1516).
- [x] Fix 1, unit steals free code-store clocks: sc_sys_v20 (#1517).
- [x] Code store in block RAM, bigger store possible: sc_sys_v21 (#1518).
- [ ] Whole-top simulation of the hj top (v17) (unsimulated; builds and card are the test so far).
- [ ] Check the host and tools at code-store sizes above 128 words (--imem, plan and compile).
- [ ] Explain why the card's fusion speedups (hh4s16u16n1) kept rising to lw 4 while the v19 pool simulation flattened (#1516 note; may be job mix).
- [ ] Further fetch ideas if needed after the hj results: fetch buffer, second code-store read port (#1516).
- [ ] Expand the RAM side: data RAM per block, far RAM addressing (64K words now, 16-bit far addresses), possibly 512K or DDR3 (Alan: "may need to expand the addressing").
- [ ] Reload cases (program larger than the card, results passed back for another stage): scale tests T9, T10.
- [ ] Open questions: why Vivado puts 4 to 6 thousand LUTs in the host bridge (`br`); why slack falls with size; critical-path reports.
- [ ] Optional: serial status readout to cut `br` LUTs; narrower far-RAM link.

## C. Front end and the user's own builds

- [x] First full manual written, s-core/S_CORE_MANUAL_v1.md (#1550); [ ] Alan reads it through and marks what is wrong or missing; [ ] re-run the chapter 4.4 build commands once to confirm them; [ ] S-Core manual generator of its own (html) if wanted; [ ] interpreter / higher-level language side (later, Alan)

- [x] Large designs in waves: many jobs, huge data set, staged pipeline (#1547, scwaves_v1.py, score_shell_v4.py, scwin_v9.py); [x] `batch batches/waves_demo.score` on the card (#1548, 300 jobs in 7 waves, 3-stage pipeline, all correct); [ ] confirm v11 shows no duplicate log lines and used squares after a run; [ ] cores: which slices ran (needs a long job or a slice-used latch on the card); [ ] a design that really exceeds the card (auto-halving on the card); [ ] stage that reads several jobs / feeds a long job; [ ] per-wave timing summary; [ ] Plan panel during waves; [ ] keep earlier waves' answers on disk if a wave fails

- [x] Batch scripts in shell and window; cores panel as squares (#1541, score_shell_v3.py, scwin_v5.py); [x] batch selector and commands run well in the window (Alan, #1542); [x] v6 flicker fixed (screenshot, #1543); [x] v8 cores panel confirmed in the browser (#1546); [x] `batch batches/ladder6_compare.score` on the card (4 runs, 8 of 8 each, #1543)

- [x] Browser window carries the build store: scwin_v3.py, BUILDS panel with use/load (#1538); [x] seen in a real browser by Alan (#1540, screenshot; layout fixed in scwin_v4.py); [ ] check the v4 layout and paste fix, and load from the window on the card
- [x] Manifest writer and board profiles (Kintex, Tang Nano 20K), make_manifest_v1.py, targets_v1.json, make_mb_v12.py (#1522).
- [x] Front end: store folder setting (#1534, score_shell_v2.py)
- [x] Front end lists builds, shows what fits on which board, sets blocks/unit-lw/imem from the build (#1534)
- [x] Front end checks the loaded board (slices, code words) against the build and refuses a failed-timing build (#1534); [x] `load` tried on the real card (#1536); [x] `run` through the shell on the card (#1537, two small jobs); [x] eight-job ladder through the shell on the card (#1540, 13.4 times at lw 5); [ ] a longer job where the cores can be seen running
- [ ] Decide: extra fields (blocks, unit lanes, units) in the host's 'V' reply (needs a new build) (#1520).
- [ ] Add slack, bitstream checksum and git commit to the manifest after a build (#1522).
- [ ] "Design size to Verilog" function for users: size check against board limits, neutral output (Verilog plus file list) for their own toolchain, then load their bitstream (#1519, #1520).
- [ ] Measured sizes still missing for units of 2, 4, 8 lanes (16 and 32 are in); code store cost is in (about 374 LUTs per block at 1,024 words, #1526).
- [x] (withdrawn, #1532) why slack fell with v21: single-build slack at 4 x 16 varies by 3 ns between builds (+0.358 to +3.699), so no cost is shown
- [ ] Get block-RAM counts from the Vivado reports to see whether the code store is in block RAM.
- [ ] Tang Nano 20K: no S-Core pool built for it, so its fit verdict stays "unknown" until one is.

## D. Scale tests and manual (S-Core only)
- [ ] Scale tests T1 to T10, start with T4 and T3 (USAGE_MANUAL_AND_SCALE_TESTS_PLAN_v1.md).
- [ ] Write a NEW manual generator for S-Core_go; do not reuse or edit docs/build_manual.py (UniCell's) (#1524).
- [ ] Manual chapters: programming (job format, limits per build, fusion widths, running examples), setup for a user's own build, front end use. Tables generated from manifests and build reports.
- [ ] Short lineage note: which ideas came from UniCell and Hex-N and which are new (offered, not yet asked for).
- [ ] Keep the S-Core package self-contained (works without the UniCell or Hex-N files).

## E. Standing rules
- Never write the card's flash; SRAM load only. Never load a bitstream whose timing failed.
- Ledger is append-only; new versions are new files; no secrets in files.
