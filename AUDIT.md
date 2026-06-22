# Root Python Consolidation Audit (2026-06-22)

76 `.py` files at the repo root. This audit classifies them, proposes a package
layout, and flags the decisions only Alan can make. **No files moved** — moving
requires updating hundreds of import sites (see Execution risk) and resolving the
version-drift calls below first.

## Key findings (evidence-based, not naive)

- **`_core` files are fabric logic, NOT dead.** `shore_core`, `ward_core`,
  `sentinel_core` have import-degree 0 but are *deliberate*: they are the
  compilable ICM decision logic that runs on the array as cells, split from the
  stateful Python runtime (`ward.py` = runtime object; `ward_core.py` = the part
  that becomes silicon). These are precisely the Shore/Ward/Sentinel programs
  earmarked for on-card verification. A "nothing imports it → delete" pass would
  wrongly bin them. **Keep all `_core` files.**
- **The compiler trio is layered, not drifted.** `compiler` (base) →
  `compiler_int32` (adds int32 types) → `compiler_pond` (wraps both as a Pond).
  All three live (in-degrees 6 / 4 / 1; tests import them 17 / 22×). Keep all.
- **`mathtrix_laplacian_1d_mif` is a shared base** (in-degree 9): the other nine
  `mathtrix_*_mif` generators import it. It is not a leaf demo; it's the common
  scaffold. Package it as the base of the mif set, not as one of the leaves.
- **One genuine version drift:** `shore.py` (v0.1 "personal session state",
  in-degree 1) vs `shore_v2.py` (v2 "system registry", in-degree 6, 5 external
  consumers). `shore_v2` is live; `shore.py` is the early form. **Decision needed.**

## Proposed package layout

```
imago/
  vm/        controller, unicell, unicell_array, gate_states, command_interface,
             cast, ir, vm_image, imago_log, cell_format, fp_tiles,
             program_builder, program_image, packet_spec, model_library
  compiler/  compiler, compiler_int32, compiler_pond, llvm_frontend,
             llvm_ir_mapper, sequencer
  pond/      pond, pond_ptt, pond_types, display_pond, pipeline_queue,
             fs_search, uniflex_fs, multi_dimm
  security/  shore_v2, shore_core, shorekeeper, ward, ward_core, sentinel_core
             (runtime + on-fabric _core logic for Shore/Ward/Sentinel)
  trix/      mathtrix (+ mif/ subpkg: laplacian_1d_mif base + the 9 leaves),
             flowtrix_*, neurotrix_*, miditrix_lif, nettrix_runner,
             optitrix_runner, sensortrix_runner
  server/    unicell_server, unicell_model_library, workbench, workspace,
             companion, run_companion, device_bridge, fpga_bridge, fpga_bringup,
             unicell_deployed, visualiser
  examples/  gol, sort, postcode_sort, branch, gpu_array, packed_shift_adder,
             mathtrix_animate, mathtrix_laplacian_1d   (standalone demos)
root:        conftest.py (pytest — must stay at root)
```

Note: `composer/`, `imago/`, `models/`, `frontend/`, `hardware/` already exist as
package dirs — this finishes a half-done migration rather than starting one. The
target `imago/` package may already hold some of these; reconcile on execution.

## Decisions needed from Alan (cannot be made without you)

1. **`shore.py` (v0.1) — keep, archive, or fold into `shore_v2`?** Different scope
   on paper (personal session state vs system registry) but the `_v2` suffix and
   1-vs-6 consumer split says superseded. Likely → `archive/`.
2. **`model_library` vs `unicell_model_library`** — distinct roles (composed-model
   library vs the server's unified interface) or drift? Headers suggest distinct;
   confirm.
3. **`unicell_deployed` / `unicell_server`** — current, or superseded by something
   under an existing package dir?
4. **Demo vs paper artifact:** the `*_mif` generators and `*trix` runners may be
   figures/experiments behind entries in `PAPERS.md` (7 planned papers). Before any
   move to `examples/`, cross-check `PAPERS.md` so a paper's reproduction code
   isn't demoted/lost. Flag which demos are paper-bound.

## Execution risk (why moves come after decisions, with tests)

External consumers of root modules (from `tests/` + package dirs):
controller ×32, unicell* ×30, fp_tiles ×29, pond ×25, compiler* ×22, unicell ×20,
compiler ×17, pond_* ×9, ward ×5, shore_v2 ×5, mathtrix ×3, command_interface ×2,
model_library ×1, shore ×1.

Moving these changes hundreds of import statements that must all update together.
The safe sequence:
1. Alan rules on the decisions above.
2. Move one package at a time, rewrite imports for that package, run the VM test
   suite (`python3 tests/vm/test_*.py`) green before the next.
3. Leave thin `from imago.vm import *`-style shims at old paths only if external
   tooling needs them; otherwise update call sites.

This keeps the "one or two files to port" goal (a package ports as a unit) without
a big-bang move that risks leaving the tree broken — the same partial-update
failure mode that bit `unicell.v` this week, but at 76-file scale.
