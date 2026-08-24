# The Tile Designer — real scope, per #479's own five-tool architecture

*Captured 2026-08-24, before writing any code -- matching the same
"scope before build" discipline as `workbench_scope.md`/`composer_
scope.md`/`super_tile_library_scope.md`. Alan's own direct choice of
what to build next after `#485`/`#486`.*

## The real premise, precisely (from `#479`'s own table)

| | |
|---|---|
| **Input** | A user's own visual model design |
| **Output** | A real ICM file (v3 or v4, same format any built-in Tier-0/Tier-1 tile already produces), usable in either VM mode |
| **Dependency** | None -- no real hardware, no Composer/Walker step needed first |

This is NOT the old, archived Composer's original "model authoring"
premise revisited (`composer_scope.md`'s own note: that premise was
explicitly doubted, then reframed into PLACEMENT/ROUTING of an
already-compiled model). This is different, narrower, and newer: a
genuinely interactive way to BUILD a model by placing real, registered
tiles on a real grid and wiring their ports -- the DSL's own visual
sibling, not a competitor to it. The DSL remains the right tool for
anyone who'd rather type; the Tile Designer is for anyone who'd rather
click.

## What's genuinely reusable, checked directly against the current codebase

**The visual PARADIGM, per `composer_scope.md`'s own real finding
against the archived tool** (`archeology/onion/old_composer_tool.
onion`) -- canvas-based placement, a library panel, and SOME kind of
link gesture. The DATA MODEL under the old tool is still not reusable
(confirmed old `format_version: 2`, `gate_state` bus addressing --
`#364`-`#367`'s own archived, incompatible architecture).

**A real, deliberate DEPARTURE from the old tool's own link gesture,
stated plainly:** the old composer's "drag from an output port,
release on an input port" gesture matched a BUS-addressed system where
any cell could connect to any other cell regardless of physical
position. Unicell-S has no such freedom -- every real link is a
CARDINAL DIRECTION (`n`/`s`/`e`/`w`) chosen per port, and only means
anything once a physically-adjacent neighbor exists in that direction
(`unicell_super_automaton_v1.py`'s own `_OPPOSITE` convention). A
generic drag-anywhere-to-anywhere gesture would misrepresent the real
system. The Tile Designer's own real link gesture is: select a placed
instance, pick a real cardinal direction for each of its ports --
the UI can (and should) highlight whether a real neighbor already sits
in that direction, but the underlying ACTION is choosing a direction,
not drawing an arbitrary wire. This is a real, corrected paradigm
choice, not a lesser one -- it's what the hardware actually does.

**Already built, reused directly, nothing here gets reimplemented:**
- `tile_source_registry_v1.py` (`#485`) -- the real, generic list of
  every placeable Tier-0-shaped tile kind (currently: super-cell,
  DSP wrapper). The Tile Designer's own "library panel" is just this
  registry's contents, rendered.
- `composed_tile_library_v1.py` -- every registered Tier-1 tile
  (`sentinel`, `dual_threshold_monitor`, `twin_sentinel`,
  `dsp_add_and_hold`), placeable exactly the same way a Tier-0 tile is
  from the Designer's own point of view (`#486`'s own multi-kind
  generalization already makes this uniform).
- `place()`/`place_composed()` (every tile kind's own real placement
  function) -- the Designer's own "validate/export" step calls these
  DIRECTLY, the same functions the DSL compiler calls, so a Designer-
  built model is checked against the exact same real port/param
  contract a hand-written DSL program is, with zero duplicated
  validation logic.
- `icm_v3.IcmV3File`/`icm_v4.IcmV4File` -- the real output format,
  already built, already hash-verified, already loadable by
  `build_grid()`/the VM. The Designer's own export step just calls
  `.save()`.
- `workbench_v1.py`'s own real, already-proven architecture pattern:
  a thin, HTTP-unaware CONTROLLER (fully testable with plain Python
  calls, no live socket needed) plus a thin `http.server` dispatcher
  on top. The Tile Designer follows the identical split, for the
  identical reason (`workbench_scope.md`'s own precedent).

## A real, minimal first scope -- not the full vision

Matching `composer_scope.md`'s own explicit advice ("start with
visualizing... defer full drag-to-route to a later pass") applied
here to the SAME real tradeoff:

1. **Build and PROVE the controller first** -- add/move/remove a tile
   instance, set a port's direction, set a param, validate the whole
   design (calling each instance's own real `place()`/`place_
   composed()`, collecting real errors), export to a real ICM file.
   Entirely testable with plain Python calls, matching `Workbench
   Controller`'s own real precedent -- no browser, no live rendering,
   needed to prove this part correct.
2. **A real, functional HTML/JS page on top**, using the corrected
   direction-based link paradigm above (not blind-guessed drag/release
   pixel math) -- a real library panel, a real clickable grid, real
   per-port direction buttons, a real validate/export flow. Stated
   honestly: this part cannot be interactively verified in this
   environment (no live browser here) the way the controller's own
   logic can be with real automated tests -- so the CONTROLLER is
   where real correctness is proven; the page is real, working code,
   built carefully, but its own interactive polish is real, separate,
   future work once a person actually clicks through it and reports
   back what needs adjusting.
3. **Defer to later, real, separate work, stated honestly:**
   drag-to-move-by-mouse (v1 uses click-to-select-cell, then a
   move button/coordinate entry -- simpler, no pixel-perfect drag
   math to get wrong blind); real-time neighbor-highlighting as a
   port's direction is being chosen; loading an EXISTING ICM file
   back into the Designer for further editing (export-only for v1);
   any visual routing/pathfinding help for non-adjacent connections
   (out of scope for the underlying cardinal-adjacency model entirely,
   not just this tool).

## Real, honest, explicitly NOT scoped here

- Automated placement/layout suggestion -- that's `loader_v1.py`'s
  own real job (`bind_shape()`/auto-placement), not this tool's.
  The Tile Designer is the human-driven complement to it, matching
  `composer_scope.md`'s own original "partner, not replacement" framing.
- Any new core/cell/tile TYPE authoring -- the Tile Designer places
  and wires EXISTING registered tiles; defining a brand-new tile kind
  is `tile_source_registry_v1.py`/a new library module's own job
  (`#485`), unrelated to this tool.
- Any RTL, any hardware target -- software/VM-side only, same as
  every other tool in `#479`'s table except Composer/Walker.
- Round-tripping a Tile Designer session itself (saving/loading the
  IN-PROGRESS design, as opposed to its final ICM export) -- real,
  separate, future work; v1 exports once a design is complete.
