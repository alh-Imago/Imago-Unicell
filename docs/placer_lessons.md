# Placer and layout-engine lessons (kept by Alan's request, 8 Oct 2026)

What each design taught the placer / layout engine (`tools/flex_layout_v1.py`, `tightplace_v1.py`, `netplace_v1.py`, `fp_mul_tight_v1.place_net_tight`). Newest first. Each lesson says what went wrong, what fixed it, and what the tools could do about it.

## From the 2-D flow medium (#1034)
1. **Exits pinned to the tile edge.** Left to the annealer, an exit cell can end up inside the tile, walled in by the tile's own relays: its lane cannot leave. Pin entries to the west column AND exits to the east column (`_place_pinned` in `flow2d_flex_v1.py`). *Tool idea:* make `place_net_tight` pin `outs` the way it pins `entries`.
2. **Stubs.** One relay on an open face of every exit and entry that a lane will use, placed before any lane is routed, so lanes laid earlier cannot close the pin in. Check the stub opens onto free space (flood fill), not a pocket; re-place the tile with the next seed if not.
3. **Pair spacing.** Repeating pairs need a gap AFTER the last tile of a pair as well as inside it (`pw = A + gap + B + gap`); with no gap the east exits of one pair touch the west entries of the next and nothing routes. Size every repeat from measured widths, not guesses.
4. **Short lanes by construction.** Split a cell into "work out" (A) and "add what arrives" (B) tiles so the lateral lanes between neighbours are one pair wide; the one long lane (the amount from step t to t+1) is routed first or early.
5. **Route the shortest, most constrained lane first** (the within-pair lane), while both ends are still open.
6. **Fan-out is four faces, input included.** A cell can feed three others. A value that must go to four places needs a relay tree (`Da`, `Db`); `place_map` says "more connections than faces" when it is wrong.

## From the 1-D flow medium (#1033)
7. **A subtract's minuend must arrive first, and when its lane is the LONG one the balancer cannot fix it.** Negate the other term with a multiplier by -1 (a 32-bit all-ones constant) and ADD: an add needs no operand order, only no tie.
8. **A spacer relay in front of a multiplier whose second operand is an entry** (both would arrive in hop 1: a tie).

## From the LIF neuron (#1030/#1031)
9. **A subtract whose operands both descend from the same cell** (`v - (v >> k)`) confused the engine's minuend test; fixed in `Grid.problems()` (#1031): the operand that IS the declared minuend wins. The multiply-add form `(v*(2^k-1) + 2^k-1) >> k` avoids the question entirely.
10. **Put one small tile per time step / repeat, placed on its own scratch grid and transplanted**, rather than annealing one huge netlist: the big one made the balancer spin for minutes, the tiles place in seconds.
11. **The balancer needs a ROUTED path to stretch.** Two operands joined by direct adjacency cannot be separated; give one a spacer relay.
12. **Entries on the top edge** (`place_map` port side 'N') are available for tiles stacked in a row.

## From the fp64 adder and multiplier (#1027, #1029)
13. **Constants are word-wide.** `-1` is `(1 << W) - 1`, not a 32-bit constant.
14. **Retry loops with seeds, snapshot/restore.** A placement that cannot route is undone and tried with the next seed; stop retrying on errors that are not "taken or outside the grid".
15. **Route long lanes first;** shuffle the order only when a fixed order cycles.
16. **A block whose result needs more bits than the word** is split into limb products with a jammed sticky; a flags word that no longer fits becomes a small code.
