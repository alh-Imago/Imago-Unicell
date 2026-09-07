# The shift_fine/shift_lane_v2 addon rollout — real status, 2026-09-07

*Captured following `#683`'s real RTL build and `#684`'s real wiring
into the shells. Not a new proposal — the design itself (`shift_fine_
addon_v1.v` + `shift_lane_addon_v2.v`) was already sim-verified in
`#683`; this note tracks the real rollout across every place that
mechanism now needs to be reflected, per Alan's own direct request
("make a note of the things to update").*

## What's real and done, checked directly, not assumed

**RTL, all 8 shells (`unicell_super_v1.v`–`v8.v`):**
- `shift_fine[1:0]` allocated from `super_latch[68:67]` — 2 of the 13
  genuinely-reserved bits (`#317`); **11 bits remain real, unused
  headroom**.
- The addon chain is now `nibble_mask → shift_fine_addon_v1 →
  shift_lane_addon_v2 → invert`, replacing the old single `shift_lane_
  addon_v1` instantiation. `shift_fine_addon_v1`'s own `shift_amount_
  out` carries the applied fine amount into `shift_lane_addon_v2`'s
  `shift_fine_in`, so `lane_cut`'s own boundary-crossing math sees the
  real total shift (coarse + fine), not the coarse amount alone —
  exactly the failure mode Alan named before it became a bug.
- **Every version with an existing testbench (v1, v3–v8) still passes
  fully, unchanged, at the default `shift_fine=0`** — confirmed by
  actually re-running each one against the new RTL, not assumed
  backward-compatible from reading the diff alone. v2 (no dedicated
  testbench exists) confirmed via clean `iverilog` elaboration.
- `unicell_super_v3_wrapped_experimental.v` deliberately left
  untouched — confirmed via `shell_compat_v1.py`'s own real shell-
  discovery logic that this variant is already excluded from the
  active/real shell set, so it isn't part of what "everything else"
  means here.

**Python regression:** full suite unaffected, 619 passed + 1 skipped,
unchanged — expected, since the software VM doesn't parse the `.v`
files, but confirmed by an actual run rather than assumed.

**The assembler (`tools/project_assemble_v1.py`) — this one WOULD
have actually broken, not just gone stale:** `V3_DEPENDENCIES` and
`V4_DEPENDENCIES` are hardcoded file lists (not a derived scan of
real module instantiations) and both named the now-unused `shift_
lane_addon_v1.v` explicitly. Fixed both to the real two-file chain.
Verified end-to-end: a real `--shell v3 --cells 4` build now correctly
includes `shift_fine_addon_v1.v`/`shift_lane_addon_v2.v` in its
generated `.qsf` and physically copies both files into the output
directory.

## Real, honest, concrete checklist — what's still open, per area

**`VIX_DEPENDENCIES` (the third hardcoded list in `project_assemble_
v1.py`) — deliberately NOT fixed.** The VIX Carrier's own v4-
generation cells (`nano_gate_v4.v`, `accumulator_cell_v4.v`, etc.)
each carry their OWN copy of the OLD addon chain, carved out of their
own per-core `addon_config` slice (confirmed directly — this is a
genuinely different wiring situation from the shared, top-level
`addon_config` the old lineage uses, see the earlier live discussion
this session). Wiring the new fine+coarse chain into all 9 v4-
generation cells is real, separate work — a second rollout, not a
trivial extension of this one, since it means editing 9 files instead
of 8, each with its own local `addon_config` slice rather than one
shared shell-level field.

**The compiler / `icm_v3.py`** — `addon_config`'s own field table
(`docs/stripped-cell/ICM_V3_FORMAT.md`'s own documented layout:
`nibble_mask`/`mask_en`/`shift_amt`/`shift_en`/`direction`/`lane_cut`/
`invert_en`, `[19:0]`) has no `shift_fine` field yet — and can't,
without also widening past `SUPER_LATCH`'s own reserved-bit boundary,
since `addon_config` itself is `[66:47]` and `shift_fine` deliberately
lives in the SEPARATE reserved range `[68:67]`, not inside `addon_
config` itself. A real, honest design question, not decided here:
does `icm_v3.py` gain a new, separate `shift_fine` field alongside
`core_config`/`addon_config` (matching where the RTL actually put it),
or does the Python-side abstraction present it as if it were part of
`addon_config` for a cleaner caller-facing shape? Either is buildable;
neither is chosen yet.

**The VM (`nano/unicell_super_automaton_v1.py`) — a real, meaningful
gap, not a cosmetic one.** `apply_addons()` is a genuine Python
re-implementation of the RTL's own nibble_mask→shift→invert chain,
already used to keep the software VM behaviorally honest against real
hardware. It does not know about `shift_fine` yet. Today this is
harmless (nothing can set the bit through any real path yet), but the
moment `icm_v3.py` exposes it, the VM's own `apply_addons()` needs the
matching update or it will silently diverge from what real silicon
would do for any nonzero `shift_fine` value — exactly the kind of
software/hardware drift this project's own discipline exists to catch
before it ships, not after.

**The workbench (`nano/workbench_v1.py`)** — no UI currently exposes
`addon_config` at all (checked directly: no `nibble_mask`/`shift_amt`/
`invert_en` field anywhere in the workbench's own grid render or
inject/deliver controls). Nothing is broken by this rollout, but this
is the natural, real place a person would eventually want to set
`shift_fine` (and the existing coarse shift/mask/invert fields too) by
hand while testing — genuinely unbuilt, not merely undiscovered.

**Composer readiness** — `composer_full_editor_scope.md`'s own real
minimal-next-increment (draggable placement, port highlighting, a
library panel) never touched addon configuration at all; per-cell
addon fields (including this new one) are exactly the kind of
secondary, per-cell knob a real placement/config UI should expose
once built. Not a blocker for Composer's own current scope, but worth
keeping in view: whatever UI eventually exposes `core_config` should
almost certainly expose `addon_config` (and now `shift_fine`)
alongside it, not as an afterthought bolted on later.

**The LLVM IR frontend (`nano/llvm_ir_frontend_v1.py`)** — `shl`/
`lshr`/`ashr` still have no real compilation target anywhere in this
project. This fine+coarse addon chain is the real, concrete mechanism
`promotable_specialist_modules.md`'s own Addendum already named as the
natural home for them — but getting there needs: (1) the `icm_v3.py`
field-table decision above resolved, (2) a real way for the DSL/tile
layer to SET a specific cell's `addon_config`/`shift_fine` (today,
`super_tile_library_v1.py`'s own tiles have no path to configure
addon fields at all — every tile's own `place()` call only ever
touches `core_config`, never `addon_config`), and (3) the actual LLVM
IR instruction-lowering code itself. None of these three exist yet;
this rollout makes them buildable, not built.

## Real, deliberate scope note

This entry is itself a checklist, matching Alan's own direct request
— not a commitment to build all six items above in any particular
order. The RTL wiring and the assembler fix were real, necessary
"does everything still work" work, done in this same pass; everything
else here is real, honestly-scoped future work, named so it doesn't
get silently rediscovered later the way the original shift gap itself
was (`#616`).
