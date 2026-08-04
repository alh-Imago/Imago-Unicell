# Root Python dependency map (2026-08-04)

**Built by scanning every remaining root-level `.py` file's actual
`import`/`from` statements (`ast`-parsed, not grepped/guessed) after
`points.md` #175/#177 moved the FULL-cell and nano-active code out.
77 files remain at root. This is a map, not a plan — the actual
restructuring decision (per Alan: "most of those systems will survive
in some form, but... intelligence moving to the host... they will not
survive in that form") still needs to happen; this document exists so
that decision has real ground to stand on.**

## The central, unavoidable finding

**Every one of the 77 remaining files traces back, through this
dependency graph, to `unicell.py`/`unicell_array.py`/`gate_states.py` —
and `unicell.py` is confirmed `*** LEGACY (2026-07-31) ***` by its own
docstring** (the pre-v3.1 protocol, modeling the already-archived
`unicell.v`). Nothing in this entire ecosystem — the compiler, the tile
library, the whole Trix suite, Pond/Ward/Shore — currently connects to
`unicell_v3.py` (now archived), `unicell_automaton_v1.py` (the active
nano cell, now in `nano/`), or `unicell_gate_core.py` (the shared core)
at all. It's a complete, self-contained island sitting on a foundation
two architecture generations behind where the actual RTL is.

## The layers, by actual measured depth (deepest/most-depended-on first)

| Module | Dependents | Role |
|---|---|---|
| `imago_log.py` | 29 | logging, used everywhere |
| `fp_tiles.py` | 29 | the tile/gate-composition library (already known to carry #72's invalid broadcast-cost assumption) |
| `controller.py` | 27 | the card-level controller abstraction |
| `gate_states.py` | 23 | gate-state representation (v2-era, matches `unicell.py`'s own model) |
| `unicell_array.py` | 13 | multi-cell array wrapper around legacy `unicell.py` |
| `pond.py` | 11 | OS-layer storage abstraction |
| `mathtrix_laplacian_1d_mif.py` | 9 | shared base for most `mathtrix_*_mif` variants |
| `pond_ptt.py` | 9 | Pond's "physical-to-topology" mapping |
| `cell_format.py` | 8 | shared format used by the whole Trix runner family |
| `pond_types.py` | 8 | Pond's type system |
| `unicell.py` | 7 | **the confirmed-legacy cell model everything ultimately rests on** |
| `compiler.py` | 6 | |
| `ir.py` | 6 | |
| `shore_v2.py` | 6 | |
| `companion.py` | 5 | |
| `compiler_int32.py` | 4 | |

## Rough groupings (by what actually imports what, not by filename guessing)

- **Cell-model floor (legacy):** `unicell.py`, `unicell_array.py`,
  `gate_states.py` — the thing everything above ultimately rests on.
- **Infra:** `imago_log.py`, `controller.py`.
- **Compiler/tile layer:** `fp_tiles.py`, `compiler.py`,
  `compiler_int32.py`, `compiler_pond.py`, `ir.py`, `model_library.py`,
  `program_builder.py`, `program_image.py`, `llvm_frontend.py`,
  `llvm_ir_mapper.py`, `branch.py`, `sequencer.py`, `pipeline_queue.py`,
  `sort.py`, `postcode_sort.py`, `packed_adder_cells.py`,
  `packed_shift_adder.py`, `gol.py`.
- **Trix ecosystem (already flagged genuinely shared/target-agnostic in
  `archeology/TRIAGE.md`, a different axis than cell architecture):**
  `mathtrix*.py` (13 files), `flowtrix*.py` (3 files), `neurotrix*.py`
  (2), `nettrix_runner.py`, `optitrix_runner.py`, `sensortrix_runner.py`,
  `miditrix_lif.py`, `cell_format.py`, `gpu_array.py`.
- **Pond/Ward/Shore OS layer:** `pond.py`, `pond_types.py`, `pond_ptt.py`,
  `ward.py`, `shore.py`, `shore_v2.py`, `shorekeeper.py`, `workspace.py`,
  `workbench.py`, `companion.py`, `run_companion.py`, `device_bridge.py`,
  `command_interface.py`, `cast.py`, `fs_search.py`, `uniflex_fs.py`,
  `packet_spec.py`, `display_pond.py`, `unicell_deployed.py`,
  `unicell_server.py`, `unicell_model_library.py`, `fpga_bridge.py`,
  `fpga_bringup.py`, `multi_dimm.py`, `vm_image.py`, `visualiser.py`.

## Genuinely isolated -- zero local dependencies AND zero dependents

`sentinel_core.py`, `shore_core.py`, `ward_core.py` (plus `conftest.py`,
which is expected -- pytest config, not project code). These three are
completely disconnected from everything else in the entire 77-file
graph -- nothing imports them, they import nothing local. Worth flagging
as a genuinely separate, much easier question than the rest of this map:
either dead code from an abandoned earlier design, or alternate/newer
stub implementations that were never actually wired in. Either way,
lowest-risk thing in this whole picture to resolve, since nothing
depends on the answer.

## What this map does and doesn't tell us

**Does:** shows the real shape of the tangle -- which files are load-
bearing (high dependent counts) versus peripheral, and confirms the
single-foundation finding precisely (everything really does trace to
the same legacy floor, not several independent legacy pockets).

**Doesn't:** say what should happen to any of it. That's the actual
decision still ahead, per Alan's own framing -- most of this "will
survive in some form" (the Trix ecosystem's own status was already
independently confirmed as genuinely target-agnostic in the archeology
triage; the compiler/tile layer's logic is largely reusable in
principle), but the intelligence-on-host shift means the CURRENT shape
(built assuming an addressed, in-fabric-intelligent cell) isn't the
shape any of it ends up in. This map is the "what depends on what"
Alan asked for -- the actual restructuring plan is separate, deliberate
work, not something to infer from this list alone.
