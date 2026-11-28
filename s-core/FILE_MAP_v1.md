# S-Core file map (ledger #1608, 28 Nov 2026)

Made by script from the files in `s-core/`: for every file family that has numbered versions (`name_v<N>.ext`) it lists the versions present, the newest, and the first line of the newest. Older versions stay because newer files are clones of them or tests and build scripts still use them; the ones nothing uses any more were packed into `archeology/onion/s_core_old_scripts_tests_2026-11-28.onion` (index next to it). The newest version of a family is the live one; this map says nothing about whether a build was made or run: the ledger and `builds_measured_v1.json` do.

| folder | family | versions | newest | what the newest says it is |
|---|---|---|---|---|
| . | DSP_FACTS.md | 1 | v1 | DSP blocks and the cost of multiply: facts so far (ledger #1573, 27 Nov 2026) |
| . | HP_BUILD.md | 1 | v1 | The hp / hq builds: high half, byte and halfword loads, byte stores, timing fix (ledger #1598) |
| . | K7_BUILDS_AND_LOADING.md | 1 | v1 | S-Core on the Kintex-7 card: which build to load, how to build it, how to check it (DRAFT v1, 26 Nov 2026) |
| . | MUL_UNIT_BUILD.md | 1 | v1 | The multiply unit: what was built, and how to build and test it (ledger #1584) |
| . | MUL_UNIT_DESIGN.md | 1,2 | v2 | Memory-mapped multiply unit: design note v2 (ledger #1581, 27 Nov 2026; v1 was ledger #1580 and stays) - a plan for Alan to approve, nothing |
| . | SHELL.md | 2..12 (11 files) | v12 | The S-Core shell (`score_shell_v12.py`): commands |
| . | S_CORE_MANUAL.md | 1 | v1 | The S-Core manual (v1, DRAFT, 27 Nov 2026) |
| . | USAGE_MANUAL_AND_SCALE_TESTS_PLAN.md | 1 | v1 | S-Core: usage manual gap list and scale-test plan (DRAFT v1, 26 Nov 2026) |
| . | WRITEUP.md | 1 | v1 | S-Core: write-up before the larger build (19 Nov 2026, ledger #1424) |
| . | asm_ext.py | 1 | v1 | the assembler extension for the byte and halfword instructions (ledger #1598), installed by jobio_ext_v2.install WITHOUT editing runtests.py |
| . | bigjobs.py | 1 | v1 | jobs longer than a build's shared RAM allows: split the data on the host, run the pieces as separate jobs, combine the answers (ledger #1428 |
| . | bigrun.py | 1 | v1 | bigrun_v1: write a long test run for the window (ledger #1439) and size it. HOST ONLY, no board needed. |
| . | builds_measured.json | 1 | v1 | _note": "Vivado results per build (Kintex XC7K480T, 50 MHz). Setup/hold slack are Vivado's WNS/WHS, single builds, not Fmax. Source: builds_ |
| . | card_label.py | 1 | v1 | a LABEL in the card's far RAM that says which build the shell loaded, and a PROBE that counts the card's blocks (ledger #1556). |
| . | cold_test.sh | 1 | v1 | the pool keeps its learned job durations across a reset and orders the bulk queue by them (LONGEST=1 in every card build; ledger #1415). |
| . | cpi_run.sh | 1 | v1 | one job of each kind at width 0 on one block: gives the clocks per instruction of each kind (ledger #1411, for lengthest_v1.py fit-kinds). |
| . | curve_run.sh | 1,2 | v2 | like curve_run_v1.sh but runs only the job files given as arguments (ledger #1397). |
| . | divconst.py | 1 | v1 | divide by a constant with ONE multiply and a shift (ledger #1590), for the cores that have no divide. |
| . | estimate_test.sh | 1 | v1 | does the length estimate (--estimate, ledger #1411/#1412) choose widths that are as fast as the fixed widths? Runs on the card. |
| . | far_dump.py | 1 | v1 | READ-ONLY dump of the card's far RAM (no writes of any kind), to compare what two different bitstreams left there after the same job. |
| . | far_ram_check.py | 1 | v1 | write a known pattern into the card's far RAM through the host commands (the same ones scblocks.py uses), read every word back and compare. |
| . | fit_search_tree.v | 2 | v2 | fit_search_tree.v (proven, left as is) with the three values that depend only on the job's width given as inputs: cur_w, cur_w - 1 and the m |
| . | jobcomp.py | 2 | v2 | jobcomp.py with two additions (ledger #1406). jobcomp.py stays as proven; this file re-uses everything from it except Task, PJob and compile |
| . | jobio_ext.py | 1,2 | v2 | ledger #1598, cloned from jobio_ext_v1.py which stays as it is): install(level, narrow=False): level = the multiply LEVEL (0 none, 1 low hal |
| . | jobiss.py | 2,3 | v3 | ledger #1598, cloned from jobiss_v2.py which stays as it is) - the same, plus (a) the HIGH half of the product at +12 (multiply level >= 2), |
| . | jobmaker.py | 1,2 | v2 | jobmaker_v1.py (ledger #1422) with more operands (ledger #1428). v1 is kept as it was; every recipe v1 accepts gives byte-identical code her |
| . | lengthest.py | 1 | v1 | lengthest_v1: HOST-ONLY estimate of how long a job runs, and a width chooser that uses it (ledger #1411). No board needed. |
| . | link_check.py | 1,2 | v2 | is the JTAG link to the card sound? (ledger #1564; v2, ledger #1568: advice for the all-ones read, "unable to claim usb device" and "no devi |
| . | made_demo.score | 1 | v1 | Card demo for `make` (ledger #1422). Start the shell with the card link and read this file: |
| . | made_demo2.score | 1 | v1 | Second card test for `make` (ledger #1424). Covers what made_demo_v1.score did not: constants too big for a 12-bit immediate (they live in a |
| . | made_demo3.score | 1 | v1 | Third card test (ledger #1429): the new `make` steps and long data in pieces. Everything is checked against the right answers computed here. |
| . | make_curve_jobs.py | 1,2 | v2 | job files for the width-curve test (ledger #1397). |
| . | make_manifest.py | 1,2,3,4,5 | v5 | ledger #1607, cloned from make_manifest_v4.py which stays as it is): level 4 = hr = hp plus byte and halfword loads on FUSED tasks (sc_sys_v |
| . | make_sys.py | 16,17 | v17 | writes sc_sys_v17.v from sc_sys_v16.v (v16 stays as proven) (ledger #1386, step I3a of FUSION_PLAN.md): NU fusion units per block instead of |
| . | make_unit.py | 1..10 (10 files) | v10 | make_unit_v10.py L - writes uc_unitm<W>.v and uc_unitx<W>.v (ledger #1607): byte and halfword LOADS (lb lh lbu lhu) in a FUSED unit. |
| . | matrix.txt | 3 | v3 | workload cfg(prio,bf) makespan critLat bulkLat worstWait |
| . | mmio_cost_calc.py | 1,2 | v2 | clone of mmio_cost_calc_v1.py (ledger #1581): the comparison with the software multiply uses ONLY the same width (v1 also printed lw 0 again |
| . | mul32_cost_calc.py | 1 | v1 | turns the four clock counts of batches/mul32_cost.score into the cost of a 32-bit shift-and-add multiply (ledger #1576). |
| . | mul_cost_calc.py | 1 | v1 | turns the three clock counts of batches/mul_cost.score into the cost of a shift-and-add multiply (ledger #1574). |
| . | mul_unit_cost_calc.py | 1 | v1 | turns the clock counts of batches/mul_unit_cost.score into the cost of one multiply WITH the unit (ledger #1584). |
| . | openocd_path.py | 1 | v1 | make the shell use ONE named openocd (ledger #1568). |
| . | order_repeat.sh | 1 | v1 | order_repeat_v1.sh FILE [N] - repeat the wide-first runs (B: width order, D: width order + crit) and the wide-last run (A) N times each, int |
| . | order_test.sh | 1,2 | v2 | order_test_v2.sh FILE - one batch, one block: one 4-slice job (vsum, lw 2) and eight single-slice jobs (vgain, lw 0). Submit order and criti |
| . | profile_compare.sh | 1 | v1 | on the build that is loaded on the card: calibrate (quick), then run two job sets at every fixed width, with the |
| . | profile_matrix.py | 3,3 | v3 | Whole-octave (coarse) vs half-octave (FINE) duration buckets, v3 simulator, same workloads as profile_matrix_v3b.py. |
| . | sc_calibrate.py | 1 | v1 | card setup program: measure how this card (this build, this user's setup) speeds up jobs at each width, fit a small |
| . | sc_lane_sel.v | 1 | v1 | sc_lane_sel: a lane whose controls and data come from EITHER its own slice's control (own_*) OR a block-level controller unit (unit_*), chos |
| . | sc_sys.v | 2..28 (27 files) | v28 | sc_sys_v27 plus byte and halfword LOADS for FUSED tasks (ledger #1607): the fused unit is uc_unitx<W> (make_unit_v10.py), which cuts and ext |
| . | sched_tests.py | 2,3 | v3 | Tests and experiments for sc_sys_v3 (request table + watcher, task table, priority dispatcher). |
| . | score_shell.py | 1..12 (12 files) | v12 | ledger #1598, cloned from score_shell_v12.py which stays as it is): jobio_ext_v2 (multiply LEVEL 0 to 3: high multiply lib_mulhu32, byte-sto |
| . | score_store.py | 1,2,3 | v3 | ledger #1598, cloned from score_store_v2.py which stays as it is): the multiply LEVEL from the build name letter when there is no manifest ( |
| . | scwaves.py | 1 | v1 | a design too big for one run, split into WAVES (ledger #1547). Pure host-side functions: no card, no printing. |
| . | scwin.py | 2..23 (20 files) | v23 | the S-Core window for the Kintex card: the shell (score_shell_v2.py) in a browser prompt, with panels for the builds, the cores, the jobs, t |
| . | shared_ram_check.py | 1 | v1 | look at one block's SHARED data RAM through the host commands M (write) and L (read), the same ones scblocks.py uses. Ledger #1476. |
| . | shared_ram_first.py | 1 | v1 | tells apart "the shared RAM's READ ADDRESS is stuck at word 0" from "the read data only updates ONCE after loading" (ledger #1477). Writes O |
| . | shared_ram_spaced.py | 1 | v1 | the shared-RAM test with every host request sent ON ITS OWN, with a pause after it (ledger #1477). Writes ONLY that block's shared RAM. |
| . | shared_ram_walk.py | 1 | v1 | find out HOW one block's shared RAM goes wrong (ledger #1477), through the host commands M (write) and L (read). Writes ONLY that block's sh |
| . | state_test.sh | 1 | v1 | does the same job image give the same clocks whatever ran before it? (ledger #1414: all lw2 on jobs_order_test2.json gave 48,261 and, |
| . | targets.json | 1 | v1 | _note": "Board profiles for the front end (ledger #1522). 'measured_from' says where each number comes from. Numbers for the Tang Nano 20K a |
| . | tb_sys.v | 2 | v2 | System testbench. +prog=<imem hex> +tasks=<3 words per task: arrival, code word addr, lw> |
| . | test_bigjobs.py | 1 | v1 | bigjobs_v1 + the shell's `addbig`: long data cut into pieces, the pieces' answers combined. The combining is checked against the reference I |
| . | test_bigrun.py | 1 | v1 | bigrun_v1: the long test run for the window (ledger #1439). Host only, no card. Checks the file format, that five jobs fill a batch, that th |
| . | test_calibrate.py | 1 | v1 | sc_calibrate_v1: fit, best width, wrong-answer guard, save/load, and the sweep with a fake card (ledger #1398). No board. python3 test_calib |
| . | test_card_label.py | 1 | v1 | ledger #1556): the label record and the block probe, on a FAKE card that obeys the rule read from host_bridge_v13.v ("O k with k >= NB is ig |
| . | test_divc.py | 1 | v1 | divide by a constant with one multiply (ledger #1590): divconst_v1.py and programs/vdivc.s on the host interpreter, with the software multip |
| . | test_fit_equiv.py | 2 | v2 | ledger #1594, clone of test_fit_equiv.py) - proves fit_search_tree_v2 (sc_sys_v25, width values given as inputs) and, through the same seria |
| . | test_hostext.py | 2 | v2 | host side of the high multiply, the byte/half loads and the byte-store unit (ledger #1598): asm_ext_v1.py, jobio_ext_v2.py, jobiss_v3.py, jo |
| . | test_hubnarrow.py | 1,2,3 | v3 | test_hubnarrow_v2.py plus NEWTOP=13 (far RAM as two banks, ledger #1475); v2 left as proven. test_hubnarrow_v1.py plus NEWTOP=12 (the comman |
| . | test_isa.py | 1 | v1 | what the S-Core core runs, checked on the RTL (ledger #1587). Every legal instruction of the core (read from uc_core_v2v.v) is run on the po |
| . | test_jobio_ext.py | 1 | v1 | the multiply library and unit count of jobio_ext_v1 (ledger #1582, #1584): software path, unit path (modelled in jobiss_v2), header word 7,  |
| . | test_jobmaker.py | 1,2 | v2 | jobmaker_v2 (more operands: min max gt lt eq ne rol ror sra mul diff prefix pair) through the shell's `make`: answers worked out by hand, a  |
| . | test_ladder.py | 1 | v1 | The ladder of LADDER.md on the host: the job files load, give the answers the guide promises, compile; ladder_show compares a result file; t |
| . | test_lengthest.py | 1 | v1 | lengthest_v1: the host-only length estimate, the dispatcher model and the width chooser (ledger #1411). No board. python3 test_lengthest_v1. |
| . | test_order_crit.py | 1 | v1 | jobcomp_v2: submit order and the critical flag; scblocks --submit-order / --crit (ledger #1406). No board. python3 test_order_crit_v1.py""" |
| . | test_own_examples.py | 1 | v1 | The own-program examples of ledger #1418 (vmin, vxor) on the host: registry checks, the reference interpreter against the Python answers, th |
| . | test_profile_plan.py | 1 | v1 | Per-batch automatic width from a card profile (scblocks --lw auto --profile, ledger #1401). No board. python3 test_profile_plan_v1.py""" |
| . | test_score_shell.py | 1..12 (8 files) | v12 | score_shell_v12 (clone of test_score_shell_v5.py, ledger #1556; the wave tests are in test_score_waves_v1.py): commands, job entry, save/ope |
| . | test_score_waves.py | 1 | v1 | score_shell_v4 waves (ledger #1547): a design too big for one run, many jobs, one huge data set, and a pipeline whose jobs read earlier answ |
| . | test_scwin.py | 2..23 (9 files) | v23 | clone of test_scwin_v9.py, ledger #1548): the browser window for the Kintex card, against a FAKE board in this process (no card, no simulato |
| . | test_sstore_versions.py | 1 | v1 | does each dispatcher version lose a shared store when a fused unit stores twice in quick succession? (ledger #1588; the question left open i |
| . | uc_core.v | 2..2 (8 files) | v2 | uc_core_v2w2 widened to 4 lanes: input lw = 0, 1, 2 gives W = 1, 2, 4 (F2 step, ledger #1357). uc_core_v2w2 kept. |
| . | window_run_big.score | 1 | v1 | Long test run for the window (ledger #1439): 500 heavy jobs in 100 batches |
| . | window_run_medium.score | 1 | v1 | Long test run for the window (ledger #1439): 100 heavy jobs in 20 batches |
| ./fpga | batch_seq.v | 2 | v2 | batch_seq plus clock counters and live progress (cloned from batch_seq.v, left as proven). While busy it counts the clocks of the whole run |
| ./fpga | blk_cmd.v | 1 | v1 | the command-decoding half of host_bridge_v12, moved INTO each block's side (ledger #1459). The bridge now broadcasts ONE raw command to all  |
| ./fpga | blk_rd.v | 1,2 | v2 | blk_rd_v1 with every status signal passed to the byte function as an extra (unused) argument. In simulation a function called from an assign |
| ./fpga | far_arb_grp.v | 1 | v1 | far_arb with SUB-ARBITERS: the blocks are put in groups of G (ledger #1494; Alan's idea, 26 Nov: a shared bus with a select instead of one |
| ./fpga | farram_bram.v | 1,2 | v2 | farram_bram_v1 with the far RAM held as TWO separate banks of 2**(AW-1) words, chosen by the top address bit (ledger #1475). |
| ./fpga | gen.py | 12,13 | v13 | F='/home/claude/imago-unicell/s-core/fpga/' |
| ./fpga | gen_top.py | 12 | v12 | F='/home/claude/imago-unicell/s-core/fpga/' |
| ./fpga | host_bridge.v | 2..13 (12 files) | v13 | host_bridge_v12 with the command decode moved out (ledger #1459): the bridge no longer drives about 450 decoded wires to every block; it pul |
| ./fpga | jtag_link.v | 1,2 | v2 | jtag_link_v1.v with the receive-window loss fixed (2026-11-17). v1 is untouched. |
| ./fpga | make_top_multiblock.py | 1 | v1 | writes sc_top_k7_v8.v: the Kintex top with NB blocks (sc_block), one host bridge (host_bridge_v11, 'O' selects the block), |
| ./fpga | sc_block.v | 2..9 (8 files) | v9 | sc_block_v8 with the dispatcher sc_sys_v28 (MULU 0 to 3 as before; fused units are uc_unitx, so byte and halfword loads also work on fused t |
| ./fpga | sc_top_k7.v | 1..21 (21 files) | v21 | sc_top_k7_v20 with sc_block_v9 (dispatcher sc_sys_v28; ledger #1607). Cloned from sc_top_k7_v20.v (left as proven). |
| ./k7 | make_fz.py | 1,2,3,4 | v4 | clock-test kit for the registered-decode units (ledger #1372): variants d4, d8, d16 (uc_unitd<W>, no RAM interface) and e4, e8, e16 (uc_unit |
| ./k7 | make_mb.py | 1..16 (15 files) | v16 | ledger #1607, cloned from make_mb_v15.py which stays as it is): the 6th argument 4 = hr = hp plus byte and halfword loads on FUSED tasks (sc |
| ./k7 | make_sizes.py | 1,2,3,4 | v4 | clone of make_sizes_v2.py (kept) for the dispatcher sc_sys_v15: writes Makefile.v15_sN and sc_k7_v15sN.v. |
| ./k7 | ram_scaling.py | 1 | v1 | table of the memories of the S-Core pool per size, from the files ram_scaling_v1.sh wrote to /tmp (Yosys, no place-and-route). |
| ./k7 | ram_scaling.sh | 1 | v1 | which memories the S-Core pool contains at each size, and what Yosys turns them into (block RAM, LUT RAM, flip-flops). Synthesis only, no pl |
| ./k7 | run_builds.sh | 1 | v1 | build several Vivado designs one after the other and write a summary (ledger #1500). Usage (from s-core/k7, after stage_mb_v9.sh): |
| ./k7 | run_fz_clk.sh | 4 | v4 | run the fusion clock tests one after the other and collect the numbers (ledger #1372). ONE build at a time. |
| ./k7 | sc_k7.v | 1,2,13,14,15 | v15 | GENERATED by make_sizes_v4.py: the stage 1 top with the dispatcher sc_sys_v15 (sc_top_k7_v7) and S=16 slices. |
| ./k7 | sc_k7.xdc | 1 | v1 | sc_top_k7_v1.xdc - pins for the S-Core pool on the YPCB-00338-1P1 (XC7K480T-FFG1156). Taken from docs/man/kintex7-ypcb00338.xdc (CLK AA28, L |
| ./k7 | seeds.sh | 1,2 | v2 | try placement seeds one after another, unattended (overnight), stop at the first one that routes. |
| ./k7 | sizes.sh | 1 | v1 | build the size sweep (S=4, 8, 16 by default) one after another, same seed and clock for all, one log per size. |
| ./k7 | sizetable.py | 1 | v1 | read the size-sweep build logs (build_sN.log) into one table and work out the cost per slice. |
| ./k7 | stage.sh | 13,14,15 | v15 | stage.sh plus the three files of the sc_sys_v15 build (sc_sys_v15, fit_search_tree, sc_top_k7_v7). Usage: S_CORE=$HOME/Imago-Unicell-score/s |
| ./k7 | stage_mb.sh | 2..15 (10 files) | v15 | stage_mb_v14.sh plus sc_sys_v28, sc_block_v9, sc_top_k7_v21 and the fused-load units uc_unitx / uc_unitm (the hr line: byte and halfword loa |
| ./k7/ddr3_gpl3 | clk_ypcb.v | 1 | v1 | clocks for the DDR3 build: one PLL from the 50 MHz pin. Derived from upstream/example_demo/ypcb_00338_1p1/clk_wiz.v (UberDDR3, |
| ./k7/ddr3_gpl3 | farram_ddr3.v | 1 | v1 | far RAM in DDR3 (one channel of the Kintex-7 card) behind the same request / acknowledge interface as sdram_ctl.v and farram_bram_v1.v. |
| ./k7/ddr3_gpl3 | loadtest.sh | 2 | v2 | clone of loadtest.sh (v1 kept unchanged). Same test per load, but a USB drop is told apart from a design failure. |
| ./k7/ddr3_gpl3 | sc_k7_ddr3.v | 1,2 | v2 | sc_k7_ddr3_v1.v with the pool sc_top_k7_v4 (fixed host link jtag_link_v2, 2026-11-17); build with make -f Makefile.v2 . Original text follow |
| ./k7/ddr3_gpl3 | sc_k7_ddr3.xdc | 1 | v1 | set_property LOC AA28 [get_ports {SYS_CLK}] |
| ./k7/ddr3_gpl3 | sc_k7_ddr3_ch1.xdc | 1 | v1 | set_property LOC AA28 [get_ports {SYS_CLK}] |
| ./k7/ddr3_gpl3/mod | ddr3_phy_ypcb.v | 1 | v1 | ============================================================================================================================================ |
| ./k7/ddr3_gpl3/mod | ddr3_top_ypcb.v | 1 | v1 | ============================================================================================================================================ |
| ./k7/vivado | clock50.xdc | 1 | v1 | clock50_v1.xdc - 50 MHz (20 ns) on the SYS_CLK port, the same target as the open builds (nextpnr --freq 50). Read after sc_k7_v1.xdc. |
| ./k7/vivado | inspect_shd.tcl | 1 | v1 | inspect_shd_v1.tcl - READ ONLY: open the routed checkpoint of a build and print how Vivado built the shared data RAM `shd` (block 0): the RA |
| ./k7/vivado | run_vivado.tcl | 1,2,4,5 | v5 | run_vivado_v5.tcl - clone of run_vivado_v4.tcl (left as it is). v4 (and v2/v3) read EVERY file in rtl/ (glob rtl/*.sv); rtl/ holds all the u |
| ./profiles | example_2x8_nu3.json | 2 | v2 | name": "example_2x8_nu3_v2", |
| ./programs | examples.py | 2,3,4,5,6,7 | v7 | Python answers for the programs of ledger #1598: vmulhu.s (high half of the product), vbyte.s (byte and halfword loads) and vbswap.s (byte a |

## Archived in the .onion of 28 Nov 2026

See `archeology/onion/s_core_old_scripts_tests_2026-11-28.INDEX.md` for the 29 files, each with the file that replaced it.
