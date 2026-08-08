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

## Real fitted numbers — STRIPPED cell (active line, Quartus 25.1, 2026-08-08)
**CRITICAL (points.md #228): the old 25-cell isolated baseline below
("293 ALMs, 11.72/cell") is INVALID as a per-cell figure — confirmed
only 3 of that test's 25 nominal cells were ever genuinely live, the
other 22 fully pruned by Quartus. Do not cite it as "what one cell
costs." Use the real, confirmed reference instead: ~100-106 ALM/cell
for genuinely live cells, consistent across both 240-cell and 750-cell
scale (points.md #209/#224).**
- 25-cell isolated baseline (retained for history, NOT a per-cell
  figure — see correction above): 293 ALMs, 192.75 MHz (#146).
- 240-cell zone (controlled clone of the 750-cell build, ROWS-only
  change): 28,900 ALMs, 237.93 MHz (correct H2 device) — genuinely
  interior cells: 100.2-106.8 ALM/cell, avg 103.8 (#224).
- 750-cell zone (Alan's actual per-zone target, `top_stripped_zone750_v5`):
  89,818 ALMs, 259.61 MHz, -2.852ns worst slack (#198) — genuinely
  interior cells: 100.1-106.2 ALM/cell, avg 102.8 (#209).
- **Real per-card capacity estimate (#229): ~1500-1700 cells at an 80%
  utilization ceiling — a ~7-8x downward revision from the 16-zone/
  12,000-cell target below.** Extrapolated from two real data points
  (240 cells @ 11%, 750 cells @ 36%); untested above 36% utilization,
  where routing congestion commonly becomes non-linear in real FPGA
  designs — treat as a real estimate, not a confirmed number, until a
  build somewhere in the 1000-1500 range exists.
- ~464 ALM/cell (FULL cell, below) vs. ~100-106 ALM/cell (stripped,
  genuinely live cells) — the comparison that actually matters for
  #107's fork rationale; the old "~11.7-16.4 ALM/cell" figure
  previously cited here shared the same #171 baseline flaw and should
  not be used either.

## Real fitted numbers (FULL cell, full card, standalone64, 25 cells/zone, Quartus 25.1, 2026-06-28)
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

## NEXT (agreed order, 2026-08-08 — this is what a fresh session picks up first)

**Read `current/latest.md` for the full itemized history before starting
this section is deliberately just the forward-looking plan. Read the
CRITICAL correction at the top of `current/latest.md` (points.md #228)
before trusting any per-cell ALM comparison from before today.**

1. **Drop the target clock to a level that reliably PASSES timing** —
   the real floor (points.md #213/#214), not a chased maximum.
2. **That floor becomes genuine headroom for future addons.**
3. **Every future addon gets tested against a FULL-CARD build
   specifically**, not small-scale (points.md #224's own finding: small-
   scale numbers don't necessarily predict behavior near real capacity).
4. **Build a real map of addon timing costs** from those full-card
   measurements — size AND timing per addon, combinations measured
   directly rather than assumed additive (points.md #214).

**Also queued, not yet started:** the programming-delivery architecture
decision (points.md #210 — single-hop/addressed delivery vs. accepting
full broadcast as the load-bearing cost of genuine any-cell-any-time
reprogrammability); the VM core rebuild (points.md #216/#217, gap
analysis at `current/VM_CORE_GAP_ANALYSIS.md`, deliberately not started
while RTL is still settling); the BRAM+DSP hybrid integration (points.md
#220, design already substantial in `current/PLAN.md`); feeding #229's
corrected ~1500-1700-cell capacity estimate back into the multi-card/
lab-cage planning, which is currently sized against the old 12,000-cell
target.

## Git
```bash
git config user.email "session@imago.local"; git config user.name "Imago Session"
git remote set-url origin https://<PAT>@github.com/alh-Imago/Imago-Unicell.git
git ls-remote   # confirm actual remote state ("ahead N" in status is a false alarm)
```
