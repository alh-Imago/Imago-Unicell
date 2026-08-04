# Archeology triage — 2026-08-04

Full pass over every file under `archeology/{full-cell,shared}/docs/`
(excluding `archeology/sessions/`, which is pure history, not "docs" in
this sense), checking each against the test: **is this a genuine shared
idea between the FULL cell and STRIPPED cell?** Two files passed and
were promoted; everything else is triaged below with a reason, so the
next phase (FULL-cell-specific docs, STRIPPED-cell-specific docs) has a
clear starting map rather than an unexamined pile.

## Promoted to `docs/` (verified, genuinely shared)

- **`ICM_FORMAT.md`** — the `.icm` program format is target-agnostic by
  design (points.md #136's own finding, re-confirmed here against
  `bootloader/generate_icms.py`'s actual record construction).
- **`MIF_FORMAT.md`** — pipeline-internal arithmetic format, applies
  regardless of which cell executes the tiles. Spot-checked against
  `fp_tiles.py`.

## `archeology/full-cell/docs/` — confirmed cell-specific, not shared

Every file in `core/`, `design-notes/`, `diagrams/`, `hardware/`, and
`archive/` was checked and is genuinely about the FULL cell specifically
— its addressed shared-bus model, `cmd_latch`/`gate_state` field
proposals, Pond/Ward/Shore OS layer, or v3-specific command contract.
None mention the STRIPPED cell at all (checked directly: grepped the
whole tree for "stripped cell"/"nano cell" — zero matches outside
`manual.html`). Two additional findings worth flagging, not silently
absorbed into "full-cell":

- **`core/ARCHITECTURE.md` and `core/CELL_INTERNALS.md` and
  `hardware/FPGA_HARDWARE.md` (moved to `shared/` initially, reclassified
  below) all describe a THIRD, even older generation** — "Protocol v2.3",
  `gate_state`/`GS_*` flags, dual-edge (posedge/negedge) triggering, a
  single shared wired-OR bus at a different granularity than either
  current cell. This predates both the current FULL cell (v3,
  `unicell64_v3.v`, `cmd_latch`-based) and the STRIPPED cell entirely.
  Already superseded by `V3_COMMAND_CONTRACT.md`/`core/CELL_INTERNALS.md`'s
  own successor docs for the FULL cell's actual current state — these
  v2-era files are historical, not currently-accurate FULL-cell reference,
  and should be treated that way whenever the FULL-cell-specific phase
  picks them up (verify against `unicell64_v3.v`, not `unicell.v`).
- **The whole `design-notes/` set is PROPOSALS, not built RTL**, almost
  uniformly — most files say so explicitly in their own header ("PROPOSED",
  "not yet RTL", "DESIGN / next-axis spec", "PONDER → DESIGN"). Worth
  checking against `unicell64_v3.v`'s actual current state one at a time
  in the FULL-cell phase to see which (if any) actually landed since
  being written.

## `archeology/shared/docs/hardware/` — reclassified, NOT promoted

All three initially bucketed as "shared" on the first pass (same board/
toolchain regardless of cell) turned out, on actual reading, to be
stale in a way that matters:

- **`FPGA_HARDWARE.md`** — "Protocol v2.3, ground truth `unicell.v`" —
  the same superseded v2-era generation as `ARCHITECTURE.md` above.
  Reclassify as full-cell/historical, not shared.
- **`HARDWARE_SETUP.md`** — describes the OLD UART-bridge multi-target
  setup (iCEBreaker/Kintex-7 era), NOT the current Quartus/JTAG/Arria10
  workflow this project actually uses today (confirmed against
  `current/START.md`'s own hardware section and `points.md`'s
  hard-won JTAG findings — none of that current knowledge appears here
  at all). Genuinely stale, not just differently-scoped.
- **`LINUX_SECOND_MACHINE_SETUP.md`** — a real runbook, closer to
  current (references "July 2026 JTAG instability"), and the underlying
  IDEA (toolchain/JTAG setup is genuinely identical regardless of which
  cell you're loading) is sound. But it references `HARDWARE_SETUP.md`
  as its baseline, which is itself stale — needs to stand on its own or
  be rewritten together with a fresh hardware-setup doc.

**Recommendation, not yet acted on:** a genuinely useful, ACCURATE,
shared "current toolchain setup" doc is worth writing fresh — Quartus
25.1, Windows-authoritative flashing, the Linux `usbfs_memory`/
autosuspend fixes, the JTAG-wipes-BAR0 reboot discipline — all of which
is currently real, current, and scattered across `points.md` rather
than living in one setup doc. This is a rewrite-from-current-knowledge
job, not a promote-as-is job. Not done in this pass.

## `archeology/shared/docs/software/` — different axis, deferred

The remaining files (`COMPILER_TILE_CONFIG.md`, `FORMAT_DEFINITION_GUIDE.md`,
`TRIX_ECOSYSTEM.md`, `TYPED_NEURAL.md`, `PRELOAD_MODEL.md`, `LLVM.md`,
`EXAMPLES.md`, `RUNNING.md`, `LIBRARY.md`, `VM_GETTING_STARTED.md`,
`IDEAS.md`, `INDEX.md`, `PAPER_DRAFT.md`, `BENCHMARKS_README.md`,
`math_frontend_design.md`, `sidecar_semantic_index_design_note.md`,
`cell_capability_table.html`, `manual.html`, `lif_neuron_reference.v`)
are all genuinely compiler/VM/application-layer material, not cell RTL
mechanics. They're "shared" only in the trivial sense that the compiler
currently has exactly one target — that's a different question from
"is this a genuine idea common to both cell architectures," which is
what this pass was checking for. Deferred to a separate software-docs
phase, not triaged item-by-item here — flagging the distinction so
they're not silently forgotten, and not falsely promoted as "cell
architecture" material either.

`VISION.md` deserves a specific note: its underlying PHILOSOPHY
(portability, one program format, substrate-independence) is genuinely
the project's enduring intent and arguably applies to both lines, but
the document as written is v2-era (`gate_state`, "one bus," iCEBreaker/
Kintex-7) and factually inaccurate about the current architecture (there
is no longer "one bus" — the STRIPPED cell deliberately has none). Same
category as the hardware docs above: needs a rewrite from the real
current state, not a copy, before it could honestly be promoted.

## Next

No file content beyond `ICM_FORMAT.md`/`MIF_FORMAT.md` was rewritten in
this pass. The FULL-cell-specific phase (whenever picked up) should
start from `V3_COMMAND_CONTRACT.md` and `core/CELL_INTERNALS.md`'s
successor material against real `unicell64_v3.v`, treating the v2-era
files as historical background at most. The toolchain-setup rewrite
(hardware setup doc, genuinely shared once accurate) is a good small
next win if wanted before tackling either cell-specific phase.
