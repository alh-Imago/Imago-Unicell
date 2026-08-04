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

- **`shared/SYSTEM_MECHANICS.md`** — what's genuinely shared between both
  cell lines' RTL (gate computation, `cmd_latch` field alignment, firing/
  freeze principles), verified directly against both `.v` files.
- **`shared/ICM_FORMAT.md`** / **`shared/MIF_FORMAT.md`** — the portable
  program and arithmetic formats, target-agnostic by design, spot-checked
  against the actual generator/tile code.
- **`stripped-cell/CELL_INTERNALS.md`** — the stripped/nano cell's first
  ever standalone documentation. Built by reading `unicell_stripped_v1.v`
  directly, start to finish: full `cmd_latch` field usage, every
  mechanism (hold/memory, branch, programming, armed, ready/ack,
  relay/consume), port list, known bugs, real silicon numbers.
- **`full-cell/CELL_INTERNALS.md`** — the FULL cell's own field map and
  structure, built by reading `unicell64_v3.v` directly. Flags a real
  trap: the RTL's own header comment is known stale (wrong `auth_mask`
  position) — built from the file's own later "verified current" block
  instead.

- **`shared/TOOLCHAIN_SETUP.md`** — current Quartus/JTAG/Arria10 setup,
  replacing the stale `HARDWARE_SETUP.md` (which claimed "Linux is the
  primary platform," no longer true — Windows is currently
  authoritative). Genuinely shared regardless of which cell is being
  built.
- **`shared/design-notes/`** — a DIFFERENT category from everything
  above: concept-stage proposals, not yet built, nothing to verify
  against. Currently one entry: modular/composable cell builds +
  capability-aware `.icm` (the natural next step after #170's
  comparator gate) — captured deliberately unimplemented per Alan:
  "this may have legs, but it needs careful planning."

See `../archeology/TRIAGE.md` for the full pass over everything else in
`archeology/` — most of it turned out to be genuinely cell-specific or
a different axis entirely (compiler/VM/application layer, not cell
mechanics), with reasons recorded rather than silently skipped.

## Structure

```
docs/
  shared/          — genuinely shared between both cell lines
  stripped-cell/    — the active nano line's own documentation
  full-cell/         — the FULL cell's own documentation (CELL_INTERNALS.md)
```

**Note (Alan, 2026-08-04):** the FULL cell is expected to be revisited
and made functional again, carrying back some of what's been discovered
on the stripped cell (the routing self-consistency approach from #155,
the armed/COMPLETE-LSB convention from #156 — both already noted as
candidates in `current/latest.md`'s NEXT list). `docs/stripped-cell/`
was written first specifically because it had zero prior documentation
and because its discoveries are expected to feed back into that FULL-cell
work — worth having the nano cell's own mechanics written down clearly
before adapting them elsewhere.

## Convention going forward

Each file here should be verified against the actual current RTL/code,
not carried over from an `archeology/` doc's prose as-is — several
`archeology/full-cell/docs/` files describe intentions or states that
were never fully implemented, or have since diverged from the real
Verilog (this is exactly why the sweep happened). A doc landing here
should say how it was verified, the same way `SYSTEM_MECHANICS.md` cites
exact file/line references rather than asserting from memory.

**Exception: `shared/design-notes/`.** That subfolder is deliberately
NOT held to the verified-against-code bar above — it's for concept-stage
proposals with nothing yet built to verify against. Each entry there
says so plainly at its own top, so the distinction from the rest of
`docs/` stays honest rather than diluting what "verified" means
everywhere else.
