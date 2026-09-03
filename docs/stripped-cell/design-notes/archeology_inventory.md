# Archeology inventory — real map for a future dedicated review pass

*Captured 2026-09-04, per Alan's own direct proposal to spend a real
session or two going through the old full-cell work systematically,
not just when a specific question happens to send someone back there.
This is a real, organized MAP of what exists, built from each
archive's own real, already-recorded metadata (`onion -i`, no
decompression needed for this pass) -- not a deep read of contents.
The goal: make the real future review sessions targeted, not ad hoc.*

25 real archives exist in `archeology/onion/`. Two have been actually
opened and read this session (`old_llvm_frontend.onion`, `#612`;
`old_full_cell_tile_library.onion`, `#612`/`#631`) -- both yielded
real, substantial, still-applicable value. The other 23 are
genuinely unexplored beyond their own archival metadata.

## Tier 1 — real, concrete, already-hinted relevance to CURRENT open work

- **`old_composer_tool.onion`** — the old standalone visual UniCell
  Composer. Its own real archival note already flags it as "a real,
  useful CONCEPT reference for the future Stage 5 composer" -- visual
  cell placement, a library panel, in-browser simulation before
  hardware. Directly relevant whenever Composer work resumes beyond
  today's real workbench-embedded UI.
- **`old_root_misc_files.onion`** — contains
  `flowtrix_cylinder_result.json`, a real, VALIDATED data output
  (Re=100 cylinder flow, Strouhal number match) explicitly flagged as
  "worth remembering for the real FlowTrix demo plan already agreed
  for later." Directly relevant to the standing FlowTrix demo roadmap
  item -- a real, existing reference result to validate a future
  Unicell-S FlowTrix build against.
- **`old_trix_domain_family.onion`** — the full TRIX domain-model
  family (MathTrix/FlowTrix/NeuroTrix/MidiTrix/NetTrix/OptiTrix/
  SensorTrix) plus `cell_format.py`, its own real domain-typing layer.
  Confirmed genuinely inseparable from the old compiler pipeline (code
  doesn't port) -- but the real domain-modeling CONCEPTS likely connect
  directly to the CURRENT, active concept-graph/bridge-paper research
  thread (27 domains, 265 concepts, `concept_inference.py`). Worth a
  real, dedicated look for conceptual overlap, not code reuse.
- **`old_papers_drafts.onion`** — old paper drafts tied to
  `cell_format.py`'s own real SI_CHECK/bridge/confidence system
  (dimensional verification, confidence-weighted bridges between
  domains). This METHODOLOGY -- not the code -- looks directly
  relevant to the current bridge-inference engine's own real
  confidence-weighted path-finding (`concept_inference.py`, modified
  Dijkstra maximizing confidence product). Real, concrete candidate
  for the next targeted dive.

## Tier 2 — real, likely conceptual value, less directly tied to a named current thread

- **`old_community_models.onion`** / **`old_models_folder.onion`** —
  the old community-model registration ecosystem (Trix-family models,
  a real JSON schema for user-contributed models). Both real archival
  notes flag "a real future community-model ecosystem for Unicell-S
  remains unbuilt" -- worth a look if/when that direction is picked up,
  for the real design questions it already worked through (parameter
  schemas, domain tagging, base-model extension).
- **`old_full_cell_ui_and_gpu.onion`** — the old address/gate_state-
  keyed workbench, visualizer, and array-based GPU backend. Already
  confirmed which parts are dead under cardinal wiring (real, direct
  line-level audit, per `workbench_scope.md`) -- but the VISUALIZATION
  approach itself (not the addressing) might hold real, reusable UI/UX
  ideas for `nano/vm_introspection_v1.py`'s own future work.
- **`old_misc_utilities.onion`** — includes `packed_adder_cells.py`/
  `packed_shift_adder.py`, real, old packed-cell-graph adder
  implementations. Confirmed not needed today (Unicell-S has its own
  native adder core) -- but worth a glance for any real, transferable
  bit-packing/graph-composition IDEAS, even with zero code reuse.

## Tier 3 — real, but scope-recalibrated or narrowly hardware-era-specific

- **`old_full_cell_os_pond_layer.onion`** — the Companion/Shore/Ward/
  Pond distributed OS layer. Already explicitly marked "genuinely out
  of current scope" (Alan's own real project-scope recalibration,
  2026-08-16) -- low priority unless that scope decision changes.
- **`pcie_legacy.onion`** / **`old_hardware_bringup.onion`** /
  **`fpga_bridge_legacy_pair.onion`** / **`old_bootloader.onion`** —
  real, but entirely full-cell-era hardware/bridge work (old iCEBreaker/
  UART era, old addressed bus). Real PCIe work remains a standing,
  not-yet-started roadmap item -- these are worth a real look
  specifically WHEN that work starts, for any transferable protocol/
  bring-up lessons, not before.
- **`old_claudette_patch.onion`** — a real, old bus-collision fix.
  Own real note already states plainly: "none needed -- Unicell-S has
  no shared bus to have collisions on at all." Real, honest
  confirmation this one's genuinely inapplicable, not just unexamined.

## Tier 4 — confirmed, low real priority (own metadata already resolves them)

`PAPERS_root_duplicate.onion`, `composer_backups.onion`,
`old_data.onion`, `old_demo_algorithms.onion`, `old_examples.onion`,
`old_experiments_pre_v3_adders.onion`, `old_frontend.onion`,
`old_imago_cli_package.onion`, `old_sketches.onion` — each one's own
real archival note already identifies a direct, current replacement or
states plainly that nothing is needed. Real, low priority for a future
dive; captured here for completeness, not urgency.

## Not yet done, stated plainly

This is a real, organized MAP, not a review -- none of the 23
unopened archives have actually been read yet, only their own
already-recorded metadata. The real next step, whenever the proposed
session(s) happen: start with Tier 1, in the order listed, extracting
and reading each one directly (matching `#612`'s own real method --
`onion -d`, then grep/read for real, substantive content, not just
metadata) -- not attempted here.
