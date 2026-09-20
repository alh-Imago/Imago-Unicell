# Bounded-canvas rotation/folding and bitmap-based collision detection — a real extension to the tightening thread (Alan/Claude, 2026-09-17)

*Per Alan's own direct proposal, walking through a real idea he wasn't
sure had translated correctly: on a space-constrained target, letting
a growing chain turn a corner or fold back on itself (like a snake),
rather than only ever growing straight -- and using an established,
game-development collision-detection technique (occupancy bitmaps) to
check it efficiently. Confirmed directly against the codebase: nothing
like this exists today. A real scoping pass only, matching this
project's own established discipline (`composer_scope.md`,
`compile_dag_frontend_scope.md`) -- nothing built yet.*

## Where this connects, and why it isn't a standalone idea

This is a real, more ambitious extension of a gap already named and
left open: `#780`'s own dispatcher grows every shape correctly but
never tightens afterward ("correct, but not minimal" -- see the
compiler audit's own Thread 1). The rats-nest pipeline (`#761`-`#767`)
already solves a version of this problem -- grow loose everywhere,
then shrink afterward in a second pass. What Alan is describing is a
genuinely different approach to the same real goal: grow WITH
awareness of turning/folding from the start, on a target where space
is actually bounded and scarce, rather than shrinking after the fact
on a canvas that was never bounded to begin with.

**The real, honest reason this matters specifically for the card
target, not the VM:** the growing-frontier model (`#780`) has no
concept of bounded space at all -- `_pad()` always grows straight,
indefinitely, because on an unbounded canvas there's never a reason to
economize. A real, physical card has a known, fixed cell budget (the
Tang Nano 20K: 20,736 LUT4 cells). A long chain forced to grow only in
straight lines can genuinely run out of real, physical room where a
chain permitted to turn a corner or fold back on itself would fit.
This is a real, direct consequence of targeting real silicon that
doesn't apply to the VM's own unbounded simulation space at all.

## Part 1 — the collision-detection mechanism: bitmap vs. dict, and why the answer depends on boundedness

**Confirmed directly, not assumed: the current `occ` mechanism
(`vix_dag_dispatcher_v1.py`) already IS a form of occupancy-map
collision detection** -- a real Python dict, `(row, col) -> cell_id`,
checked by every `manhattan_route()` call before placing a new cell.
This is a real, sparse occupancy map, the same underlying idea game
development uses for unbounded worlds (chunked terrain, open-world
collision) -- confirmed real, not a new idea to introduce.

**The real, honest correction to an earlier dismissal in this same
conversation:** a PER-SHAPE footprint bitmap (checking whether one
shape's own bounding box overlaps another's) was correctly ruled out
earlier, since nothing in the growing-frontier model ever compares two
shapes' footprints against each other -- placement grows adjacent to a
known frontier, never pre-allocated into a box. That real dismissal
still stands. What's different here is a WHOLE-CANVAS occupancy
bitmap -- and for a bounded target, this is a real, legitimate
upgrade over the sparse dict, not a redundant one:

- **Sparse dict (today's real mechanism):** correct for any canvas
  size, unbounded or bounded, but each occupancy check is a real,
  individual hash lookup.
- **Dense bitmap (the real alternative for a KNOWN, bounded canvas):**
  the entire occupied region becomes one real, fixed-size bit array;
  checking whether a real, multi-cell path (including a bent or folded
  one) collides with anything already placed becomes one real, fast
  bitwise AND across the whole shape at once, rather than one lookup
  per cell. This is the exact, established mechanism real-time games
  (Tetris, Snake) use for the same real reason: known bounds, fast
  bitwise overlap checks.

**Real, honest scope call, not yet decided:** whether this justifies
switching the CARD-target placement path to a dense bitmap while
leaving the VM-target path on the existing sparse dict (since the VM
has no real, fixed bound to make a dense array practical) is a real,
open design decision for whoever scopes the actual build -- not
answered here. What IS confirmed here is that the two real,
established techniques exist, that the tradeoff between them is real
and well-understood outside this project (not something to invent),
and that boundedness is the real, deciding factor for which one fits.

## Part 2 — the real, harder problem: letting a chain actually turn or fold

**This is the genuinely new capability, and it's real, non-trivial
design work, not just a mechanism swap.** Every real shape grown by
`#780`'s own `_pad()`/`_grow_plain_chain`/`_grow_convergence` extends
in exactly one fixed direction for its whole length. Nothing today
lets a chain change direction mid-growth, and nothing lets it fold
back toward space it's already passed near. Real, open questions a
proper build would need to answer, named here so they aren't
discovered mid-implementation:

- **When does a chain decide to turn, rather than continue straight?**
  A real, concrete rule is needed -- e.g., "turn when continuing
  straight would exceed the real, remaining bounded space in that
  direction," or a more general, always-considered pathfinding choice
  at every real step. This is a real design decision, not an
  implementation detail.
- **How does a genuinely bent or folded path's own real timing work?**
  `#773`'s own sharpened rule (equal real ARRIVAL TICK, not equal hop
  COUNT, for a composed source) already established that path length
  in hops and real timing aren't the same thing once a source is
  composed. A folded path changes its own real hop count relative to a
  straight one covering the same real distance -- any future STAGGER-
  style timing calculation (the still-unused shape from the compiler
  audit's own Thread 2) would need to account for this directly, not
  assume straight-line hop counts.
- **Does a folded path ever risk re-approaching or crossing its own
  earlier segments?** A real, genuine self-collision case a straight-
  growing chain can never hit today, since it never turns back at all.
  The occupancy-bitmap mechanism from Part 1 is the real, direct
  answer to checking this efficiently once folding is possible --
  confirming Part 1 and Part 2 are genuinely connected, not two
  separate ideas that happen to be discussed together.

## Real, honest, deliberate scope limit

**Nothing in this note proposes a specific pathfinding algorithm,
turning heuristic, or bitmap data structure to build.** Per Alan's own
established, proven process ("start small, and test, build out from
there"), any real implementation should begin with the smallest real
case that demonstrates the idea -- one real chain, on a real, small,
deliberately bounded canvas, forced to turn at least once to fit,
checked for correctness against the VM the same way every other real
shape in this project has been -- before any claim about efficiency,
compactness, or card-readiness is made.

## Summary: how this fits into the existing, named work

- This is a real, more ambitious alternative/complement to the
  already-scoped-but-unwired rats-nest tightening pass
  (`#761`-`#767`), aimed specifically at bounded, real-silicon targets
  rather than the VM's own unbounded canvas.
- It reuses `#780`'s own real, existing growing-frontier model as its
  starting point -- this is an extension of how a shape grows, not a
  replacement for the frontier/tap/orientation machinery already
  proven this session.
- It connects directly to `#773`'s own real, sharpened timing rule,
  which already anticipated that composed/non-straight paths need
  careful, direct timing treatment, not an assumption that hop count
  and real arrival tick are interchangeable.
- The collision-detection half (Part 1) is confirmed to already be
  represented, in simpler form, by the existing `occ` dict -- the real
  open question is whether a bounded, card-specific target justifies
  a dense-bitmap alternative, not whether occupancy tracking itself is
  a new idea.
