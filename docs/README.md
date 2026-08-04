# docs/

This is the NEW documentation folder — distinct from `archeology/`,
which holds everything moved but not yet re-examined (2026-08-04 sweep).

Where `archeology/full-cell/`, `archeology/stripped-cell/`, and
`archeology/shared/` are the "pull each bit out, re-examine it" holding
areas, this folder is where a piece lands once it's actually been
re-examined, verified against current reality, and rewritten or
confirmed accurate — the cleaner, more structured version Alan asked
for. Started with `SYSTEM_MECHANICS.md`, per Alan: "the overview of the
system mechanics and the logic that is in both, that's the first place
to start."

## Contents so far

- **`SYSTEM_MECHANICS.md`** — what's genuinely shared between both cell
  lines' RTL (gate computation, `cmd_latch` field alignment, firing/
  freeze principles), verified directly against both `.v` files.
- **`ICM_FORMAT.md`** / **`MIF_FORMAT.md`** — the portable program and
  arithmetic formats, target-agnostic by design, spot-checked against
  the actual generator/tile code.

See `../archeology/TRIAGE.md` for the full pass over everything else in
`archeology/` — most of it turned out to be genuinely cell-specific or
a different axis entirely (compiler/VM/application layer, not cell
mechanics), with reasons recorded rather than silently skipped.

## Convention going forward

Each file here should be verified against the actual current RTL/code,
not carried over from an `archeology/` doc's prose as-is — several
`archeology/full-cell/docs/` files describe intentions or states that
were never fully implemented, or have since diverged from the real
Verilog (this is exactly why the sweep happened). A doc landing here
should say how it was verified, the same way `SYSTEM_MECHANICS.md` cites
exact file/line references rather than asserting from memory.
