# Stripped/nano cell — documentation status

**UPDATE (2026-08-04, later same day): no longer empty.** Real
documentation now exists at `../../../docs/stripped-cell/CELL_INTERNALS.md`
— built by reading `unicell_stripped_v1.v` directly, start to finish.
The gap described below is now closed for the cell's own internal
structure; the hardware bring-up doc and eventual `ARCHITECTURE.md`
mentioned below are still not written.

---

**Original finding from the 2026-08-04 archeology sweep, kept for
context: this folder was empty, and that was accurate, not an oversight.**

The stripped cell (`fpga/verilog/unicell_stripped_v1.v`, informally
"unicell-nano") has no standalone `docs/` presence anywhere in the
pre-sweep repository. Every existing doc in `archeology/full-cell/docs/`
predates the stripped cell's own existence (the line started
2026-08-01) or was written specifically against the FULL cell
(`unicell64_v3.v`).

Before this update, the stripped cell's actual documentation lived in
two other places instead:

1. **`current/latest.md` / `archeology/sessions/*`** — session-by-session
   narrative.
2. **`points.md` #88 onward** — the real, detailed, field-by-field
   record: the cmd_latch layout, every mechanism (memory/comparator/
   branch/programming/freeze/armed/OR-combine), every real bug found and
   fixed, every silicon confirmation. Still the deepest, most complete
   record — `CELL_INTERNALS.md` distills it, doesn't replace it.
3. **Header comments inside `unicell_stripped_v1.v` itself** — each
   mechanism's own block carries a `points.md #N` cross-reference
   explaining what it is and why.

**What still belongs here eventually:** a hardware bring-up doc specific
to the stripped cell's grid-scale silicon path (freeze exercise, armed
gate, the #150/#151 routing-corruption class of bug), and eventually its
own `ARCHITECTURE.md` once the "reality" line (#107's fork) has enough
settled shape to describe on its own terms rather than only in contrast
to the FULL cell. Not written yet.
