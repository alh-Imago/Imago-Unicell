# Stripped/nano cell — documentation status

**Honest finding from the 2026-08-04 archeology sweep: this folder is
currently empty, and that's accurate, not an oversight.**

The stripped cell (`fpga/verilog/unicell_stripped_v1.v`, informally
"unicell-nano") has no standalone `docs/` presence anywhere in the
pre-sweep repository. Every existing doc in `archeology/full-cell/docs/`
predates the stripped cell's own existence (the line started
2026-08-01) or was written specifically against the FULL cell
(`unicell64_v3.v`).

Right now, the stripped cell's actual documentation lives in two other
places instead:

1. **`current/latest.md` / `archeology/sessions/*`** — session-by-session
   narrative.
2. **`points.md` #88 onward** — the real, detailed, field-by-field
   record: the cmd_latch layout, every mechanism (memory/comparator/
   branch/programming/freeze/armed/OR-combine), every real bug found and
   fixed, every silicon confirmation. This is the closest thing to a
   spec the stripped cell currently has.
3. **Header comments inside `unicell_stripped_v1.v` itself** — each
   mechanism's own block carries a `points.md #N` cross-reference
   explaining what it is and why.

**What belongs here eventually, once written:** a real `CELL_INTERNALS`-
equivalent distilled from points.md's narrative (field map, mechanism
list, gating rules), a hardware bring-up doc specific to the stripped
cell's grid-scale silicon path (freeze exercise, armed gate, the #150/
#151 routing-corruption class of bug), and eventually its own
`ARCHITECTURE.md` once the "reality" line (#107's fork) has enough
settled shape to describe on its own terms rather than only in
contrast to the FULL cell.

Not written yet -- flagged here so it isn't silently assumed to exist,
consistent with `points.md`'s own "own mistakes/gaps directly" discipline.
