# Archeology — repo reorganization (started 2026-08-04, Alan)

**This is a large, multi-session project, started but far from finished.**
The first pass moved `docs/` and `sessions/` into a real structure and
fixed the paths that would otherwise have silently broken. It did NOT
yet re-examine or update any individual document's *content* for
accuracy — that's the actual "pull each bit out, re-examine it" work,
still to come, doc by doc.

## Why this split

The whole project runs on one dominant fork (`points.md` #107): the
FULL cell (`unicell64_v3.v`, the original "dream" architecture) and the
STRIPPED/nano cell (`unicell_stripped_v1.v`, the "reality" line, active
since 2026-08-01 and the one currently proven on silicon). Almost all
existing documentation was written for or about the FULL cell, simply
because it existed first. Splitting by which line a doc actually
describes — rather than leaving everything undifferentiated in one
`docs/` folder — is the point of this sweep: it makes visible what's
actually been written for the ACTIVE line (currently: nothing) versus
what's historical/FULL-cell material that may or may not still apply.

## Structure

```
current/                    — the three "live" documents
  START.md                  — session catch-up checklist
  PLAN.md                   — active task path
  latest.md                 — fast catch-up (most recent session state)

archeology/
  full-cell/docs/           — FULL cell ("dream" line) — nearly everything
    core/                   — ARCHITECTURE, CELL_INTERNALS, V3_COMMAND_CONTRACT,
                               COMPOUND_OPCODES, BRANCH_DECISION_TREE,
                               addressing_note, NATIVE_FS
    hardware/               — PCIE_ARRIA10_NOTES (the FULL cell's own PCIe
                               bring-up, top_arria10_zone1_v3.v-era)
    design-notes/           — all 13 FULL-cell design-note files (v3
                               addressing/auth, cmd_latch 64-bit, hybrid
                               hard-IP, card capabilities, interconnect,
                               placement, etc.)
    diagrams/               — boot sequence, cell internal, compile
                               pipeline, Pond architecture, security
                               layers, ward state machine, wired-OR/NAND/NOR
    archive/                — the OLD docs/archive/ subtree wholesale:
                               numbered OS/microkernel docs (00-10),
                               COMMAND_REFERENCE, COMPILER_NOTES, session
                               logs, architecture_positioning, audits/,
                               design-notes/, results/, plus VERILOG_SPEC.md
                               (the even-older "UniCell v2" spec)

  stripped-cell/docs/       — the active nano line. CURRENTLY EMPTY except
                               for a README explaining why (see below) —
                               its real documentation today is points.md
                               #88 onward, plus RTL header comments.

  shared/docs/               — genuinely cross-cutting material
    software/                — ICM_FORMAT, MIF_FORMAT, FORMAT_DEFINITION_GUIDE,
                               TRIX_ECOSYSTEM, COMPILER_TILE_CONFIG, VISION,
                               PRELOAD_MODEL, TYPED_NEURAL, LLVM, EXAMPLES,
                               RUNNING, LIBRARY, VM_GETTING_STARTED,
                               PAPER_DRAFT, IDEAS, INDEX, sidecar semantic
                               index note, math_frontend_design,
                               manual.html + build_manual.py (both later
                               moved to docs/ root, #162 -- an active
                               tool, not archeology holding material),
                               cell_capability_table.html,
                               lif_neuron_reference.v, BENCHMARKS_README
    hardware/                — HARDWARE_SETUP, LINUX_SECOND_MACHINE_SETUP,
                               FPGA_HARDWARE (same physical board/toolchain
                               regardless of which cell is loaded)
    figures/                 — gray_scott_demo.gif, wavefront_paper.png

  sessions/                  — every DATED/ARCHIVED session file (everything
                               that was in sessions/ except latest.md, which
                               moved to current/). Pure history, kept exactly
                               as written — per Alan: "they are history but
                               important history."
```

## Honest gaps and judgment calls, not glossed over

- **The `stripped-cell/docs/` folder is empty on purpose, not an
  oversight** — see `stripped-cell/docs/README.md` for the full
  explanation. This is arguably the single most useful finding from
  this sweep so far: the active line has no standalone documentation at
  all yet, only points.md's narrative.
- **A `shared/` bucket was added beyond the two branches Alan named**
  (full-cell, stripped-cell), for material that's genuinely target-
  agnostic (the `.icm` format, the toolchain/hardware setup notes that
  apply to the same physical board either way, etc.). Flagged here in
  case that's not what was wanted — easy to fold into one of the two
  branches instead if so.
- **Some categorizations are judgment calls, not certainties** — e.g.
  `NATIVE_FS.md` went to full-cell (the addressing/Pond model it
  describes was designed against the FULL cell's Tier-2 layer), but a
  native filesystem is conceptually something either line could host
  eventually. `COMPILER_TILE_CONFIG.md` went to shared even though the
  actual compiler currently ONLY targets the FULL cell in practice — per
  #136's stated intent that it needs to become multi-target. Worth a
  second look once someone's actually re-reading these files for content,
  not just filing them.
- **No file CONTENT has been changed or fact-checked in this pass** —
  only moved, with internal path references fixed in the three `current/`
  documents and the top-level `README.md` (which was already known
  stale — see `current/PLAN.md`'s own pre-release checklist — and still
  needs the real rewrite that was already on file as pending work).
  Everything inside `archeology/full-cell/docs/archive/` in particular
  is already flagged, in `current/PLAN.md` itself, as needing real
  rework, not a light pass, once it's picked up.

## What's still to do (the actual "large project")

Pull each document out of its `archeology/` folder in turn, re-read it
against current reality, and either: confirm it's still accurate and
promote a cleaned version to a real living-docs location, mark it
explicitly superseded, or fold its still-useful content into something
newer. Not started yet — this sweep only built the shelving, not the
re-examination.

**Started (2026-08-04):** a new top-level `docs/` folder now holds the
actual re-examined output, as pieces get done — see `docs/README.md`
for the convention. First piece: `docs/SYSTEM_MECHANICS.md`, the
overview of what's genuinely shared between both cell lines, verified
directly against both RTL files rather than assumed. This is the model
for how everything else in `archeology/` should eventually get pulled
out and either confirmed, rewritten, or retired.

**Full triage pass completed the same day — see `TRIAGE.md`.** Checked
every remaining file in `full-cell/docs/` and `shared/docs/` against the
"genuine shared idea between the two cells" test. Two passed and were
promoted (`ICM_FORMAT.md`, `MIF_FORMAT.md` — both target-agnostic
formats, spot-checked against real code). Everything in `full-cell/docs/`
confirmed genuinely FULL-cell-specific, with a note that several files
(`core/ARCHITECTURE.md`, `core/CELL_INTERNALS.md`, the reclassified
`archive/FPGA_HARDWARE.md`) describe an even older "v2" generation,
already superseded — worth knowing before treating them as current
FULL-cell reference in a later phase. The `shared/docs/hardware/` set
turned out to be stale rather than genuinely current-and-shared (flagged
for a rewrite, not promoted as-is); `shared/docs/software/` is mostly a
different axis (compiler/VM/application layer) than what this pass was
checking for, deferred rather than force-fit.
