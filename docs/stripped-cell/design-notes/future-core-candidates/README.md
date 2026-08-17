# Future core candidates — "LEGO for FPGA" (`points.md #378`)

Three raw combinational ALU building blocks, contributed by Alan
(2026-08-17), saved here for whenever the real, still-deferred "LEGO
for FPGA" work (a snap-in third-party core-plugin ecosystem, `#353`)
gets picked up. `core_select` values 6-31 are already real, reserved
headroom in the live RTL for exactly this kind of thing (`#317`).

**None of these are Unicell-S cores yet.** They're plain combinational
arithmetic — no `core_select` dispatch, no two-arrival capture, no
`downstream_mask`/`upstream_mask` offering protocol, none of the real
`SuperCell` integration surface every existing core (`ram_cell_v1.v`,
`adder_cell_v1.v`, etc.) actually has. Wrapping any of these into a
real core is itself a real, separate piece of work, not attempted here.

## Status of each, checked directly before saving, not assumed

- **`bitwise_subtractor_32bit.v`** — clean. The zero-extend-then-
  subtract trick for borrow detection is a standard, correct pattern.
  No issues found.

- **`bitwise_multiplier_32bit.v`** — functionally correct, verified
  with `iverilog` against real test cases (`123456 × 789012`, and the
  `0xFFFFFFFF × 0xFFFFFFFF` edge case) — both matched exactly. 32
  partial products summed through an adder tree; a reasonable
  combinational multiply structure.

- **`bitwise_divider_32bit.v`** — as submitted, contains a real syntax
  error at line 37 (`</generate>` instead of `endgenerate` — looks like
  a stray HTML-style tag from a copy/paste) and does NOT compile as-is
  (confirmed with `iverilog -g2012`, not assumed). Saved here
  UNMODIFIED, exactly as submitted, so this file is not silently
  "fixed" behind anyone's back — the fix is one word. With that one
  fix applied locally, the restoring-division algorithm itself is
  correct, verified with `iverilog` across `100/7`, `0xFFFFFFFF/3`,
  `0/5`, `7/100`, and divide-by-zero (`42/0` → `quotient=0xFFFFFFFF`,
  `remainder=42` — a real, deterministic consequence of the algorithm
  when nothing ever "fits" as negative, not a crash, but not
  necessarily meaningful either; a real core wrapper would want an
  explicit zero-check).

## A real, substantive concern worth remembering for whenever this is
## picked up, not just a note in passing

The divider is 32 sequential subtract-and-shift stages, each depending
on the previous stage's own result — one long, unbroken combinational
critical path. This architecture's entire premise is wire-delay-based
timing with real, hard per-hop requirements (the super carrier shell's
own real number: 200.76 MHz, `#322`). A 32-deep unrolled combinational
divider dropped into one physical cell would very likely blow that
timing budget badly. Real thought about pipelining or a multi-tick
iterative version belongs in the same conversation as wrapping this as
a real core — not something to discover after the fact.
