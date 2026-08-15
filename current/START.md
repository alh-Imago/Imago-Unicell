# Session Start — Imago UniCell

**NOTE (2026-08-04 archeology sweep): this file now lives in `current/`,**
**alongside `PLAN.md` and `latest.md` — the three "live" documents.**
**Everything else has moved to `archeology/`, split into `full-cell/`**
**(the FULL cell / "dream" line, #107's fork — nearly all pre-existing**
**docs), `stripped-cell/` (the active nano line — currently has NO**
**standalone docs yet, see `archeology/stripped-cell/docs/README.md`**
**for why), and `shared/` (genuinely cross-cutting material). All paths**
**below are relative to the REPOSITORY ROOT (run these from a terminal**
**opened at the repo root, not from inside `current/`).**

## Read these first (in order)
```bash
git pull
cat fpga/verilog/unicell_stripped_v1.v                # GROUND TRUTH -- the ACTIVE line (#107's "reality" fork). Verilog logic wins every argument.
cat fpga/verilog/cell_wrapper_v2.v                    # host/JTAG path -- full parity with the cell's own internal mechanisms (#127)
cat fpga/verilog/cell_command_v1.v                    # the (tiny) command-cell companion module
cat archeology/full-cell/verilog/unicell64_v3.v       # the FULL cell -- separate "dream" line (#107), untouched since 2026-07-31, moved into archeology 2026-08-04 (#175)
cat archeology/full-cell/docs/core/ARCHITECTURE.md    # overall scheme + design intent (KNOWN OUT OF DATE vs current RTL, still gives conceptual grounding -- Alan, 2026-08-04)
cat archeology/shared/docs/software/VISION.md         # systems-view/ward-sentinel/PTT layers -- read for #152's freeze/ward connection
cat docs/shared/SYSTEM_MECHANICS.md               # NEW (2026-08-04): what's genuinely shared between both cell lines, verified against real RTL -- the first piece of the cleaner re-examined structure
cat docs/stripped-cell/CELL_INTERNALS.md          # NEW (2026-08-04): the nano cell's first standalone documentation -- field map, mechanisms, port list, built by reading unicell_stripped_v1.v directly
cat docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md  # NEW (2026-08-13): living cross-cutting reference table -- every core/wrapper built so far, what's standalone-Quartus-proven vs. aggregate-only vs. sim-only
cat docs/shared/TOOLCHAIN_SETUP.md                # NEW (2026-08-04): current Quartus/JTAG/Arria10 setup -- Windows is currently authoritative (Linux paused on this machine), the reboot-after-JTAG rule, replaces stale HARDWARE_SETUP.md
cat docs/full-cell/CELL_INTERNALS.md              # NEW (2026-08-04): the FULL cell's own field map, built by reading unicell64_v3.v directly -- flags the RTL's own known-stale header comment (wrong auth_mask position)
cat current/VM_CORE_GAP_ANALYSIS.md               # NEW (2026-08-08): full sweep of all 77 root Python files vs the nano cell -- zero target it, 35 target the old format, 8 real gaps mapped against the VM-core rebuild plan (points.md #216/#217)
cat current/latest.md                                 # current state + recent decisions (most recent at TOP) -- READ THE CRITICAL CORRECTION AT THE TOP FIRST (points.md #228)
cat points.md                                         # the FULL detailed narrative, #1 onward -- #115-#157 is this session's entire body of work
cat current/PLAN.md                                   # what needs doing
```

**A large, multi-day session (2026-08-01 through 2026-08-04) rebuilt the
STRIPPED cell almost entirely — memory/comparator mechanisms, a full
command/programming redesign (twice), a branch/routing mechanism ported
from the FULL cell, and real zone-scale measurement up to 750 cells. Read
`current/latest.md` for the compressed summary before diving into
`points.md`'s full narrative.**

## GROUND TRUTH
**`fpga/verilog/unicell_stripped_v1.v` is the ACTIVE line — build everything on it (#107's "reality" fork).**
`fpga/verilog/unicell64_v3.v` remains the FULL cell's own ground truth for that SEPARATE "dream" line
(#107) — untouched since 2026-07-31, not currently being developed, but not abandoned either.
Verilog LOGIC (not comments) wins every argument, on EITHER cell. But ground truth can have bugs:
verify the Verilog's INTERNAL consistency (does the logic match the field map?), not just
contract-vs-Verilog. Two real bugs and a missing-flags error were found this way on the FULL cell
(2026-07); a latent bug (`a_reemit_active` never requiring `a_arrived`) was found the same way on
the stripped cell this session (#144). The FULL cell's header carries an AUTHORITATIVE FIELD MAP —
trust that block, re-verify against logic when in doubt.

Core discipline: sim-first then silicon; smallest-test-first; isolate-the-variable; clone don't
modify proven files; prose over heavy formatting; honest assessment over enthusiasm.

## Canonical STRIPPED-cell stack (active line, #107's "reality" fork)
- `fpga/verilog/unicell_stripped_v1.v`      — THE stripped cell (ground truth, this session's whole focus)
- `fpga/verilog/cell_wrapper_v2.v`          — host/JTAG path, full parity (PROGRAM/COLLECT/SET_CTRL/CLR_CTRL/DIAG)
- `fpga/verilog/cell_command_v1.v`          — command-cell companion (trigger -> hold -> release on program_done)
- `fpga/verilog/top_stripped_grid5x5_*.v`   — 25-cell campaign tops (baseline/wrapper/command/both)
- `fpga/verilog/top_stripped_zone50_v1.v`   — 50-cell zone base figure
- `fpga/verilog/top_stripped_zone750_v1.v`  — 750-cell zone, Alan's actual per-zone target (16 zones x 750 = 12,000 cells)
- `fpga/quartus/Unicell-Q-stripped-*.qsf`   — build from these (one per test above)

## Canonical v3 (FULL cell) stack — separate "dream" line, untouched since 2026-07-31
- `fpga/verilog/unicell64_v3.v`        — THE cell (ground truth)
- `fpga/verilog/unicell_array64_v3.v`  — array
- `fpga/verilog/unicell_zone64_v3.v`   — zone (pass .DEBUG_SELECT(1) for per-cell readback+bank switch)
- `fpga/verilog/top_arria10_zone1_v3.v`— silicon top (has DEBUG_SELECT(1))
- `fpga/quartus/Unicell-Q-zone1-v3.qsf`— build from THIS (references the v3 top, not the old one)

## Sim — STRIPPED cell (primary active line — testbenches are oracles, not smoke tests)
```bash
cd fpga/verilog
iverilog -o /tmp/t.vvp -g2012 tb_stripped_v1_program.v unicell_stripped_v1.v && vvp /tmp/t.vvp          # variable-length ID-tagged programming
iverilog -o /tmp/t.vvp -g2012 tb_stripped_v1_branch.v unicell_stripped_v1.v && vvp /tmp/t.vvp            # comparator-driven routing (branch mechanism)
iverilog -o /tmp/t.vvp -g2012 tb_stripped_v1_commandcell.v unicell_stripped_v1.v && vvp /tmp/t.vvp       # bit-10, config-driven command-emit
iverilog -o /tmp/t.vvp -g2012 tb_wrapper_v2.v cell_wrapper_v2.v unicell_stripped_v1.v && vvp /tmp/t.vvp  # full wrapper (all 5 opcodes)
iverilog -o /tmp/t.vvp -g2012 tb_wrapper_freeze_cascade.v cell_wrapper_v2.v unicell_stripped_v1.v && vvp /tmp/t.vvp  # freeze cascade via SET_CTRL
```

## Sim — FULL cell (v3, separate line, primary verification — testbenches are oracles, not smoke tests)
```bash
cd fpga/verilog
iverilog -o /tmp/t.vvp -g2012 tb_v3_twoslot.v      unicell64_v3.v && vvp /tmp/t.vvp   # 15/15 decoder+compose+auth
iverilog -o /tmp/t.vvp -g2012 tb_v3_auth_relocate.v unicell64_v3.v && vvp /tmp/t.vvp   # 11-bit auth @ [63:53]
iverilog -o /tmp/t.vvp -g2012 tb_v3_bank.v          unicell64_v3.v && vvp /tmp/t.vvp   # op26 bank switch
```
VM tests: `PYTHONPATH=. python3 tests/vm/test_fp_tiles.py` and `tests/vm/test_compiler_int32.py`.

## SILICON — reflash FIRST
Mustang-F100 Arria 10 config is VOLATILE SRAM (PCIe-powered) — any host restart/sleep/PCIe
re-enumeration WIPES it. JTAG IDCODE still enumerates (misleading). Reflash before any quartus_stp test.
- When in doubt, run `fpga/icm64_readstate.tcl` as the KNOWN-GOOD baseline (it authenticates
  correctly, lands config, reads a real latch, and has a cycle-tick snapshot-health check).
- Our test tcl auth framing must MATCH what the bitstream's boot stores (a mismatch = config
  silently auth-rejected — the cause of the long silicon chase; auth GATE works on silicon).
- Debug/readback path (ISSP bridge, DEBUG_SELECT) is a SECURITY DOOR — strip + lock JTAG in production.

## Real fitted numbers — STRIPPED cell (active line, Quartus 25.1, 2026-08-09)
**CRITICAL (points.md #228): the old 25-cell isolated baseline below
("293 ALMs, 11.72/cell") is INVALID as a per-cell figure — confirmed
only 3 of that test's 25 nominal cells were ever genuinely live, the
other 22 fully pruned by Quartus. Do not cite it as "what one cell
costs." Use the real, confirmed reference instead: ~100-106 ALM/cell
for genuinely live cells, consistent across both 240-cell and 750-cell
scale (points.md #209/#224).**

**ALSO CRITICAL (points.md #241, fixed and re-verified #242/#247):
every Fmax/slack figure from the `#176`-`#227` timing arc was measured
against a phantom auto-derived ~1GHz clock — the SDC constraint file
was never actually applied (a project-folder workflow gap, confirmed
via Quartus's own "file not found" message). ALM counts were NOT
affected — confirmed by direct before/after comparison at two
independent scales below. The numbers below are the corrected,
SDC-confirmed-applied figures.**
- 25-cell isolated baseline (retained for history, NOT a per-cell
  figure — see correction above): 293 ALMs, 192.75 MHz (#146).
- 240-cell zone (controlled clone of the 750-cell build, ROWS-only
  change): 28,930 ALMs, 214.87 MHz, **+0.346ns slack — PASSING**
  (#242, SDC confirmed applied; supersedes #223/#224's invalidated
  28,900 ALM/238.66MHz/-3.190ns figure — ALM barely moved, 0.1%
  difference, confirming resource usage was never contaminated).
- 750-cell zone (Alan's actual per-zone target, `top_stripped_zone750_v5`):
  **89,778 ALMs, 210.79 MHz, +0.256ns worst slack — PASSING at the real
  200MHz target** (#247, SDC confirmed applied; supersedes #198's
  invalidated 89,818 ALM/259.61MHz/-2.852ns figure — ALM moved 0.04%,
  same confirmation as the 240-cell case). Genuinely interior cells:
  100.1-106.2 ALM/cell, avg 102.8 (#209, ALM-based, unaffected by the
  SDC issue).
- **Real per-card capacity estimate (#229): ~1500-1700 cells at an 80%
  utilization ceiling — a ~7-8x downward revision from the 16-zone/
  12,000-cell target below.** Extrapolated from two real ALM data
  points (240 cells @ 11%, 750 cells @ 36%); untested above 36%
  utilization, where routing congestion commonly becomes non-linear in
  real FPGA designs — treat as a real estimate, not a confirmed number,
  until a build somewhere in the 1000-1500 range exists. This estimate
  is ALM-based and was never affected by the SDC issue.
- ~464 ALM/cell (FULL cell, below) vs. ~100-106 ALM/cell (stripped,
  genuinely live cells) — the comparison that actually matters for
  #107's fork rationale; the old "~11.7-16.4 ALM/cell" figure
  previously cited here shared the same #171 baseline flaw and should
  not be used either.

## Real fitted numbers — distribution system & sentinel (Quartus 25.1, 2026-08-13)

**Full assembled distribution system** (`top_full_tree_system_v1.v` —
2-level mux tree, 4-stage relay chains, 2 real adders, 2-level combiner
tree, real BRAM round trip): **275 ALM, 192.09 MHz, 655,360 real M20K
bits confirmed inferred** (`points.md #286`). Reaching this number
required fixing THREE separate real Quartus synthesis traps found via
actual builds, not predicted — worth knowing before touching this
design again: constant-propagation on the self-test's own literal
addresses (`#283`), a hierarchy-depth RAM-inference failure fixed by
`bram_controller_v2.v`'s registered read address (`#284`), and
constant-propagation again on the self-test's own literal data values
(`#286`). **`bram_controller_v2.v`, not `v1`, is now the standard
memory core for anything more than ~2 hierarchy levels deep from a
real Quartus instantiation.**

**Sentinel system, first real hardware confirmation** (`Unicell-Q-
sentinel-issp-test-v1`, `points.md #291`): channel-alive over real
JTAG confirmed (cycle counter genuinely advancing), power-on-frozen
state confirmed correct on real silicon, the `chain_length=0`
degenerate-case fix confirmed correct on real silicon. `diff` tracking
and actual error-triggering (as opposed to error-absence) remain
sim-only confirmed — a ready-to-run exercise script exists
(`fpga/sentinel_issp.tcl`'s own `sn_full_exercise`, `#292`) but hasn't
been executed yet.

**A real hierarchy-depth RAM-inference limitation, worth remembering
for ANY future design:** the exact same unmodified Verilog can infer
correctly as real M20K when close to the top of the hierarchy but fail
(silently synthesizing as ~650K plain registers instead) once wrapped
several levels deeper — a documented Intel/Altera Quartus limitation,
not a bug in the RTL itself. The fix is registering the read address
inside the memory module (the canonical Quartus RAM template), not
changing the logic.

- Logic 74% (185,445/251,680 ALMs); 16 zones x 25 = 400 cells; ~4.6% marginal per zone (loaded);
  ~464 ALM/cell. DSP 0/1687, BRAM 0, PLL 0/64, HSSI 0/24 — all hardened silicon IDLE.
- FMAX 56.2 MHz — THE number to watch (>logic%); likely wired-OR-bus-limited; island separation
  should raise it. Card gains packing efficiency when fully loaded (single zone ~6% -> 4.6% loaded).

## Where the project is (2026-07)
Strategic pivot: stop forcing the FPGA to be silicon. TWO versions on a shared foundation:
- PURE-CELL (VM-first, demonstrates the thesis, hosts compiler + Tier-2) — proceeds now.
- HYBRID (card: cells for topology/control, DSP+BRAM for math/storage via bridges) — data prereq
  now closed (see arria10_card_capabilities.md).
Deployment = CAFÉ: 8 cards + 1 SBC (SBC runs host-side ward+PTT; cards compute). Card = a POND
(surfaces via PTT; workbench reads it). BRAM = universal primitive (buffer + PCIe-port + program
store); PCIe DMAs to BRAM direct (no I/O cells). Backpressure = command-cell watchdog freeze (no
interrupts); propagates upstream; keep feedback loops zone-local. Product: uni-lab parallel platform,
EOL GX660 ~£450 café to seed / current GX1150 ~£1050 to sustain (128 models/café).

## NEXT (agreed order, 2026-08-13 — this is what a fresh session picks up first)

**Read `current/latest.md` for the current-state summary before starting
— `archeology/sessions/archive-2026-08-13.md` has the full narrative if
more detail is needed than the summary gives.**

1. **DONE (2026-08-14, `points.md` #306/#307): `#298`'s self-test bug
   root-caused and fixed.** Two distinct bugs, not one intermittent
   case as originally reported — a config-race (deterministic on every
   pass, not just pass 3) and a separate test-stimulus flaw (fixed
   collect-count no longer safe once feed_target grew past 10). Fixed
   in `top_sentinel_discrete_test_v2.v`; `v1` retained as the
   historical bug record. Confirmed clean out to 34,000+ passes.
   `tb_top_sentinel_discrete_test_v2.v` is the keepable regression
   check. **`v2` is ready for a real Quartus build — not yet done,
   the next concrete step.**
2. **Wire the sentinel system into a real chain** — `sentinel_counter_
   v1.v`/`v2.v`'s `out_wrap_pulse`/`feed_pulse`/`collect_pulse` inputs
   remain unconnected to any real chain's own events.
3. **Wire `shared_bram_arbiter_v1.v` into the full tree system** —
   proven standalone (`#282`), not yet replacing the two-separate-memory
   design in `top_full_tree_system_v1.v`.
4. **The DSP bus-contention question** — real column data exists
   (`#274`-`#277`), not yet reasoned through.
5. **A real 3-level tree** — both the mux tree and combiner tree only
   proven at 2 levels so far.
6. **No software/loader path exists for any new cell type** — every
   `cfg_valid`/`cfg_data` load has been testbench-only stand-ins.
7. **Addon headroom work and the two long-queued Quartus experiments**
   (`#206`'s OPTIMIZATION_MODE, `#200`'s duplication-flags) — genuinely
   meaningful now against real confirmed baselines.

**Also queued:** the `#210` programming-delivery decision, the VM core
rebuild (`#216`/`#217`), the BRAM+DSP hybrid integration (`#220`).

## Git
```bash
git config user.email "session@imago.local"; git config user.name "Imago Session"
git remote set-url origin https://<PAT>@github.com/alh-Imago/Imago-Unicell.git
git ls-remote   # confirm actual remote state ("ahead N" in status is a false alarm)
```
