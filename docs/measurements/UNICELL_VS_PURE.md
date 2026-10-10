# UniCell against a pure Verilog design: each argument run as a test (ledger #1036 addendum 59)

Test bed: the CORDIC z-convergence example (4 stages, 32-bit), the UniCell design against the hand-written baselines in `fpga/baselines/cordic_z_v1/` (see `CORDIC_BASELINE.md`). Tool: `tools/unicell_vs_pure_v1.py`; tests: `tests/vm/test_unicell_vs_pure_v1.py`; numbers: `docs/measurements/unicell_vs_pure_v1.json`. Everything here is simulation, synthesis and place-and-route; nothing was run on a board. One design, one run each unless stated.

## Verdicts

| # | argument | verdict on this test bed |
|---|---|---|
| 0 | the fairer comparison, the sub family and streaming | **Does not beat pure on size.** Throughput matches on sub, halves on flex. |
| 1 | authoring effort and defects | **Not measured.** No evidence either way. |
| 2 | change a design without re-synthesis | **Not supported on the Tang.** Untested where cells load as data. |
| 3 | determinism | **Holds, but is not unique.** A pure pipeline is as deterministic. |
| 4 | freeze, save, reload | **Supported in the VM**, with a gap found in the checkpoint file. Not on hardware. |
| 5 | one description for every target | **Holds on four targets here.** Verilog is portable too. |

## 0. Sub and streaming

All designs take 64 random items back to back and return all 64 correct and in order (an order caveat: the repo's own merge test says order is only guaranteed with one item in flight; this passed, which is not a guarantee).

| design | latency (cycles) | steady rate (cycles per item) | LUT + ALU | flip-flops | Fmax range (MHz) |
|---|---|---|---|---|---|
| hand pipeline, same handshake (`hs`) | 4 | 1.0 | 179 | 132 | 166 to 183 |
| UniCell flex | 20 | **2.0** | 763 | 933 | 265 to 277 |
| UniCell sub | 16 | 1.0 | 1,090 (716 + 374) | 792 | 260 to 289 |

Your point about flex is confirmed: the ack costs half the speed (2 cycles per item). The sub streams at one item per cycle like the hand pipeline, so on throughput it is the fair match, but it has 4 times the latency, and it is **larger than the flex version** in logic (1,090 against 763; 379 of its LUTs are single-input ones; I did not investigate why). Against the hand design the sub is about 6 times the logic.

## 1. Authoring effort and defects (not measured)

Only line counts exist: hand-written Verilog 27 to 42 lines per version, the UniCell program 749 lines of hierarchical JSON (a tool draws it; lines are not what a person types), the generated flex top 348 lines. By lines the pure design is smaller. There is no timing of a person and no defect rate for either. The one anecdote, n = 1 and written by an AI that already knew CORDIC: the hand version was quick to write; my first draft was needlessly large (two adders per stage) and I only noticed by comparing it to UniCell's numbers; no hand version had a wrong answer. A real test needs a person building an unfamiliar function both ways, timed, with defects counted.

## 2. Changing the design (not supported on the Tang)

Change one constant (K1 26565 to 26566) and time how long until something runs:

| form | time |
|---|---|
| pure Verilog, edit to placed on the Tang part (one seed) | 3.5 s |
| UniCell flex on the Tang, edit to placed (regenerate 0.09 s) | 25.2 s |
| UniCell in the VM, edit to first correct result (-405, as expected) | 0.002 s |
| pure Verilog, simulator compile | 0.01 s |

On this small design nothing takes minutes, and on the Tang the UniCell build is slower because it is larger. The flex RTL bakes configuration in at synthesis, so there is no "load as data" on the Tang today. The advantage can only exist on the carrier line and silicon, where cells are loaded as data; that was not tested here. For large designs synthesis takes far longer, which would change the picture; also not measured.

## 3. Determinism (holds, not unique)

The standard VM and FlexGrid both give the model's answer on 67 inputs (edge cases and random) and both take **20 ticks**, equal to the flex RTL's 20 cycles (316 inputs checked in `CORDIC_BASELINE.md`). So the VM predicts the hardware exactly for flex. But the hand pipeline is just as deterministic (always 4 cycles), so determinism does not separate them for this block; it matters when many blocks are composed, which was not tested. The sub RTL takes 16 cycles; the standard VM says 20, and I found no separate VM mirror of the sub family, so the VM does not predict the sub's latency.

## 4. Freeze, save, reload (supported in the VM; one gap found)

The run was cut at every tick while an item was in flight (20 cuts x 4 inputs = 80 per grid mode), the cells saved to a file with the repo's checkpoint tool (every second cut through the file, hash-checked), reloaded into a fresh grid built from the same program, and finished. In both the standard VM and FlexGrid: **80 of 80 gave the same value and the same finish tick as the uninterrupted run.**

**Gap found:** the checkpoint file stores the cells but not the words in flight between cells, which the grid holds separately (`_pending`). With cells only, **all 80 restores failed** (the item never arrives). A real checkpoint needs both. In hardware those words sit in the cells' own registers, so a hardware freeze at a clock edge would capture them, but the Tang has no readout path yet (addendum 53), so none of this is shown on hardware. A pure design has no equivalent unless scan logic is added; that was not tried.

## 5. One description for every target (holds, and is shared by Verilog)

The same program gave the right answer in the standard VM, FlexGrid, the flex RTL and the sub RTL (64 random items). The carrier line and silicon were not run for this. Hand-written Verilog also runs everywhere Verilog does, so portability alone is not unique; what UniCell adds is the VM and the carrier reference from the same description.

## What this leaves

On one 4-stage design, what survives the test is: exact VM-to-RTL agreement, and freeze-and-reload in the VM (once the in-flight words are included). Size and flex throughput go to the pure design, change time on the Tang does not favour UniCell, and authoring effort is untested. The arguments that remain open need other experiments: a timed authoring comparison, the carrier line, a Tang state-readout path, and larger designs.


**Update (addendum 60):** the checkpoint gap in point 4 is closed in the VM by `nano/mixed_grid_checkpoint_v2.py`, which also stores the words in flight; the cut-at-every-tick test passes (`tests/vm/test_mixed_grid_checkpoint_v2.py`). Still not shown on hardware.

**Correction (addendum 65):** the statement above that a pure design has no equivalent of freeze-and-reload is too strong. A hand-written CORDIC with a freeze input and a scan chain does it (`docs/freeze/PURE_VERILOG_FREEZE.md`) for about one LUT per state bit. What UniCell may add is uniformity and automatic insertion; that is not measured.
