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
- [x] (partly) A compute-heavy job on the card: vstress, 5 to 16 million clocks, 8 of 8 correct at lw 0 and lw 5 on hk8s32u32n1i1024 (#1554); [ ] crc32 or a longer compute job (the original wish, to show the fetch fix); the vector ladders are too small (#1527)
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

- [x] Large designs in waves: many jobs, huge data set, staged pipeline (#1547, scwaves_v1.py, score_shell_v4.py, scwin_v9.py); [x] `batch batches/waves_demo.score` on the card (#1548, 300 jobs in 7 waves, 3-stage pipeline, all correct); [x] v11 shows no duplicate line (Alan, #1552); [x] used squares after a run, and cores caught running, seen in the browser (Alan, #1555); [ ] live view at PCIe speed (later, new PC and card); [x] `batch batches/compute_heavy.score` run on the card (#1554); [x] the card guard (shell v5) caught a wrong design on the card (#1554); [ ] try score_shell_v5 / scwin_v13 (what is on the card; v12 was blank, #1553); [ ] cores: which slices ran (needs a long job or a slice-used latch on the card); [ ] a design that really exceeds the card (auto-halving on the card); [ ] stage that reads several jobs / feeds a long job; [ ] per-wave timing summary; [ ] Plan panel during waves; [ ] keep earlier waves' answers on disk if a wave fails

- [x] Batch scripts in shell and window; cores panel as squares (#1541, score_shell_v3.py, scwin_v5.py); [x] batch selector and commands run well in the window (Alan, #1542); [x] v6 flicker fixed (screenshot, #1543); [x] v8 cores panel confirmed in the browser (#1546); [x] `batch batches/ladder6_compare.score` on the card (4 runs, 8 of 8 each, #1543)

- [x] Browser window carries the build store: scwin_v3.py, BUILDS panel with use/load (#1538); [x] seen in a real browser by Alan (#1540, screenshot; layout fixed in scwin_v4.py); [ ] check the v4 layout and paste fix, and load from the window on the card
- [x] Manifest writer and board profiles (Kintex, Tang Nano 20K), make_manifest_v1.py, targets_v1.json, make_mb_v12.py (#1522).
- [x] Front end: store folder setting (#1534, score_shell_v2.py)
- [x] Front end lists builds, shows what fits on which board, sets blocks/unit-lw/imem from the build (#1534)
- [x] Front end checks the loaded board (slices, code words) against the build and refuses a failed-timing build (#1534); [x] `load` tried on the real card (#1536); [x] `run` through the shell on the card (#1537, two small jobs); [x] eight-job ladder through the shell on the card (#1540, 13.4 times at lw 5); [x] a longer job where the status polls catch cores running (#1554, 110 and 329 ms at lw 0; Alan to say whether the squares showed)
- [x] Label in far RAM and block probe, shell v6 and window v14, fake-card tests (#1556); [x] measured on the card (#1557): low far RAM stores data, probe counts 8, shell load and card ok; [x] reload clears the label, measured (#1558); [x] scwin_v14 seen in the browser (#1559-60: status lines correct, scrolled out of view); [x] scwin_v15 seen in the browser (#1561); [x] `card stamp` and the wrong-build refusal measured (#1562); [x] blocks guard and stamp refusing a different-size build measured on the card; hj link failure traced to a loose header board (#1563); [ ] label found empty once with the design still answering (probably the loose connection, unconfirmed); [x] link check built (#1564: shell v7, window v16, link_check_v1.py); [x] `link_check_v1.py usb` and `ping` tried on the machine (#1565); [x] shell v7 `card` with the header board pulled and reseated (#1566); [x] `run` refused with the header pulled and passing with the link good, measured (#1567); [ ] [x] better advice texts and the stale-label wording built (#1568: link_check_v2, shell v9); [ ] try `set openocd PATH` and `card` on the machine (#1568); [ ] shell v8 idea: close the shell's openocd after each command so helpers never talk to a stale one (awaiting Alan); [ ] note: stamp cannot tell hj from hk (same geometry).
- [ ] Decide: extra fields (blocks, unit lanes, units) in the host's 'V' reply (needs a new build) (#1520). The label (#1556) covers existing builds; this is for a hardware-asserted name (also JTAG user code).
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

## F. Language and instruction set (from the manual, #1551; ideas to decide, nothing designed)
- [ ] **Multiply and divide**: the core has none (programs shift and add, as `vgain.s` does; `jobiss.py` refuses them). Decide how to add: a software multiply/divide routine in the code library (host side only, no new build), or hardware in the fusion unit (new build). Measure what a shift-add multiply costs per call first.
- [ ] **Byte and halfword loads and stores** (`lb lh sb sh`): not available, the shared RAM is word-wide; programs for text or packed data must do the shifting themselves. Decide: library helpers, or hardware byte lanes.
- [ ] **Which RV32I / RV32M / RV32C parts are wanted at all**: write down the exact instruction list the core runs today (from the RTL, not from memory) as a table in the manual, and say what is missing against RV32I.
- [ ] **Interpreter / higher-level language** (Alan, later): grow the `make` recipe language (more steps, conditions, loops over a window), let it write `from=` pipelines; or a small compiler to the job programs. Decide the scope first; check the Onion archive for prior art.
- [ ] Keep the manual (`S_CORE_MANUAL_v1.md`) in step: when any item here is done, change chapter 8 (rules) and chapter 11 and log it.

## E. Standing rules
- Never write the card's flash; SRAM load only. Never load a bitstream whose timing failed.
- Ledger is append-only; new versions are new files; no secrets in files.
