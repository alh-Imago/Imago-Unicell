# The Composer, retargeted: a viewer and editor for flex layouts

*Scoped 2026-10-06 at Alan's request ("scope that out"). This is design
only; no code exists. It follows `composer_scope.md` (#385: the
Composer's job is placement/routing review, not authoring) and
`composer_full_editor_scope.md` (#677: the drag-and-drop "adjust" half,
never built). Both of those target the Arria-era workbench grid. This
note retargets the same job at the current line's layout engine,
`tools/flex_layout_v1.py`.*

## Why retarget now

The Composer was re-scoped at #385 because placement and routing is
NP-complete, and people are good at it by eye. On the Arria-era grid that
stayed hypothetical: designs had tens of cells.

The current line has a real instance of the problem:

- The whole fp adder (#990) is a **hand-written placement template**
  (`tools/fp_add_v1.py`). Routing (`route_nets`) and timing balance
  (`balance()`) are automatic, but positions are not. "A placer that
  decides positions itself" is open in the status audit.
- Routing the adder hit planarity walls that needed a new core (the
  crossing tile, #999).
- Today the only view of a layout is `Grid.dump()`, a one-character-per-
  square text map, plus `problems()` as a list of tuples.

Measured on the balanced fp32 adder (`Grid(34, 330)`, `fp_add(g, FP32)`):

| | |
|---|---|
| cells | 1,755 (1,603 relay `ram`s, 64 adders, 36 multipliers, 44 comparators, 8 `cross`) |
| links / routes / crossings | 1,822 / 96 / 8 |
| extent | rows 1-31, columns 2-191 |
| deepest hop | 514 |
| `problems()` before `balance()` | 12, fixed by 6 detours |
| build + balance | 1.8 s |

A viewer has to handle that scale: about 1,800 squares, mostly relays,
on a long thin board.

## The ground rule: the layout engine stays the single source of truth

`flex_layout_v1.Grid` already holds everything a Composer needs:
- `nodes`: name to row, col, core, cfg, addon and preload;
- `links`, including second-word links;
- `routes`: each relay chain, keyed by (from, to);
- `crossed`: each crossing tile and the two routes it serves;
- `sources()`, `hops()` and `xdelay`: the generator's timing model;
- `problems()`: operand ties and minuend-order faults;
- `balance()`: the repair;
- `records()`: the ICM output.

The Composer **adds no layout logic of its own**. It is a client that:
1. takes a snapshot of a `Grid` and draws it, and
2. (later) asks the `Grid` to make a change and redraws.

That keeps the generated RTL as the oracle, as it is today. It also
means the Composer cannot drift from what `records()` produces. The other
session currently owns `flex_layout_v1.py`; this plan touches it only in
phase 1, and only by adding small methods it agrees to.

## Phase 0: a read-only layout viewer (no changes to anyone's files)

**New module `tools/flex_layout_view_v1.py`.** It has one function,
`snapshot(g) -> dict`, which only reads `Grid` attributes and calls its
public methods (`hops()`, `problems()`, `sources()`):

```json
{
  "rows": 34, "cols": 330,
  "cells": [{"name": "...", "r": 3, "c": 17, "core": "adder", "hop": 212,
             "cfg": {}, "addon": {}, "preload": null, "route": ["src", "dst"]}],
  "links": [{"a": "...", "b": "...", "second": false}],
  "routes": [{"from": "...", "to": "...", "relays": ["..."], "second": false}],
  "crossings": [{"name": "...", "owner": ["a", "b"], "crossing": ["c", "d"]}],
  "problems": [{"cell": "...", "kind": "tie|order", "early": "...", "late": "..."}],
  "summary": {"cells": 1755, "by_core": {}, "max_hop": 514}
}
```

A cell that is a relay in a route carries that route's key, so the page
can draw a whole route as one line rather than 1,600 boxes.

**Where layouts come from.** A layout is built by Python code (a builder
such as `fp_add(g, fmt)`), not saved in a file. The viewer therefore
takes either:
- a **named builder** from a small registry in the new module, e.g.
  `"fp_add/fp32"`, `"fp_add/fp16"`, `"normalise_chain/fp32"`; each is a
  function that returns a balanced `Grid`, or
- a **snapshot JSON file** written by `python3 tools/flex_layout_view_v1.py
  fp_add/fp32 -o layout.json`, so a layout can be looked at without
  rebuilding.

**The page.** It lives in the front panel as `/composer`, using the
shared look (`nano/ui_theme_v1.py`). This replaces the stale "Composer —
not built yet" box on "Other tools". It shows:
- **The board:** an SVG with pan and zoom (wheel and drag) and
  fit-to-view. Logic cells are drawn as squares coloured by core
  (adder, mul, comparator, constant ram, entry/exit), with their
  names visible when zoomed in.
- **Routes:** each relay chain is one polyline, not individual boxes;
  second-word routes are dashed and crossing tiles are drawn as ✕.
  Hovering a route highlights it end to end and shows its length.
- **Timing:** a hop-depth heat tint, toggleable. Hovering a cell shows
  its hop and its sources' hops.
- **Problems panel:** lists `problems()` for the snapshot. Clicking one
  zooms to the cell and draws its two operand paths, the tie in amber
  and the order fault in red. A balanced layout shows an empty list.
  The useful view there is the **pre-balance** snapshot (an option),
  which shows the 12 problems and where `balance()` put its 6 detours.
- **Search** by cell name, and a legend.

**Size.** The new module is about 150 lines of Python plus one page of
about 400 lines of HTML/JS. There are no changes to `flex_layout_v1.py`,
the fp tools, the VM or any test the other session relies on.

**Checks.**
- `snapshot()` agrees with the `Grid` it came from: the same cell
  count, the same `hops()` and `problems()`, and `records()` unchanged.
- The page renders the fp32 adder in Chromium at desktop and phone
  widths, with no script errors.
- A pre-balance snapshot shows exactly the problems `problems()`
  reports.

## Phase 1: assisted adjustment (needs the other session)

Drag a **logic cell** (never a relay) to a new square. The server then:
1. unroutes that cell's routes,
2. moves the node,
3. re-routes with `route_nets`,
4. runs `balance()`, and
5. returns a new snapshot, or the `LayoutError` text when the move
   cannot be routed.

The drop target shows green or red from a dry run. An undo stack keeps
the snapshots.

**What it needs from the layout engine:** two small public methods,
`move(name, r, c)` and `unroute_all(name)`. These should be added by, or
agreed with, the session that owns `flex_layout_v1.py`, not patched in
from outside.

**Decision needed: where an edit is kept.** Layouts are Python
templates, so a dragged position must go somewhere the builder will read
next time:
- (a) a positions-override JSON that `fp_add()` and other builders
  accept (`overrides={"name": (r, c)}`). This is the smallest change and
  keeps the template as the base. **(recommended)**
- (b) an ICM file written from `records()`. That is exact, but it loses
  the template, so a format change would not carry over.
- (c) the viewer prints the edited coordinates for a person to paste
  into the template.

## Phase 2: a block library

The fp assembler's blocks (`normalise_chain`, `align_sticky`,
`round_rne`) would be placeable units. The idea is to drag a whole block
onto the board, move it as one piece, and re-route its ports. This is
`composer_full_editor_scope.md`'s library panel, fed from the fp
assembler instead of the Arria-era tile catalogue. It depends on each
block reporting its footprint and port cells, which the blocks do not
yet expose.

## Decisions for Alan

1. **Arrange, not author** (as at #677). The Composer moves and
   re-routes cells that a builder created; it does not invent new
   connections. Authoring stays in the builders and the compilers.
   **Recommended**; it keeps the RTL oracle unchanged.
2. **Where edits are kept** (phase 1): (a), (b) or (c) above.
   Recommended: (a).
3. **Where the page lives:** front panel `/composer`
   (**recommended**: it is the current line's tool) or a workbench tab.
   The Composer features already in the workbench (#606-#609: shell
   compatibility, connection hints, ICM save/load) stay there; they
   serve the Arria-era grid.
4. **Phase 1 timing:** after the other session's routing work settles,
   since phase 1 needs `move()`/`unroute_all()` in `flex_layout_v1.py`.

## Not in scope

Authoring a design from a blank board; any RTL or hardware change; an
automatic placer (open separately in the status audit; the Composer
would sit beside one, not replace it); and the Arria-era workbench grid.
