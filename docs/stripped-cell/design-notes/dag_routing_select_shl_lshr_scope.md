# DAG routing for select/shl/lshr — real scoping, no build (Alan/Claude, 2026-09-08)

## Real status of general DAG routing so far

`add`/`sub` and every real `icmp` predicate (`slt`/`sle`/`sgt`/`sge`/
`eq`/`ne`) now fully support general DAG references, including
multiple consumers per producer (`#701`/`#710`/`#712`/`#713`). This
note scopes the three remaining opcodes named as excluded since
`#701`'s own original restriction -- `select`, `shl`, `lshr` -- by
actually checking each one's own real topology, not assuming from the
original framing that all three share one problem. **They don't.**

## `shl`/`lshr` — the easy case, likely simpler than `add`/`sub` was

Checked directly against the real emission code: the shift cell uses
ONLY `in="w"`, `out="e"` (`addon.shift_en` etc. are config, not real
wired ports). **North and south are both completely free** -- no
restructuring needed at all, unlike `icmp_eq`/`icmp_ne`'s own real
port-scarcity problem (`#712`).

Better still: `shl`/`lshr` have only ONE real dynamic operand (the
value to shift) -- the shift amount is compile-time config, never a
second live arrival. That means there is no A-vs-B arrival-order
question at all, unlike `icmp`'s own `slt`/`sle` (`#710` had to test
this empirically; here the question wouldn't even arise).

**Real, honest expectation, not yet verified by building anything:**
widening the existing chain-shape check to allow `shl`/`lshr` as a
DAG-referencing consumer, and wiring `in_a`-equivalent (`in`) to
south when `is_dag_reference`, should work with close to the same
effort as `add`/`sub` did (`#701`) -- likely the smallest of the
three real remaining gaps.

## `select` as a DAG reference SOURCE (its own result tapped later)
## — likely easy, for a real, specific reason

`select`'s own real result lives at `or_gate`'s output. `or_gate` is
a `nano_gate` core -- confirmed directly, these have no `upstream_mask`
at all (accept from any wired neighbor) and their own `routing_mask`
is already a real, multi-bit field, matching the SAME "fan out to an
extra direction" pattern already used for `add`/`sub`'s own producer
side (`FieldIR("out", ["e","s"] if ... else "e")`, `#701`).

**Real, honest expectation, not yet verified:** tapping `select`'s own
result for a later DAG reference is plausibly a small, additive
change -- add south to `or_gate`'s own routing_mask when needed, the
same real mechanism already proven elsewhere.

## `select`'s own `cond` as a DAG reference CONSUMER — the real hard
## case, structurally identical to `icmp_eq`/`icmp_ne`'s own problem

`cond` maps directly onto `mask`'s own `in_a` port. `mask` is a
`subtractor` -- and its own FOUR real ports are ALL already spoken
for in the ordinary case: west (`in_a`, `cond`), north (`in_b`, a
preloaded zero), east (feeds `and_true`), south (feeds `not_mask`).
**Confirmed directly, not assumed: there is no free port for a DAG
relay's own drop to land on, the exact same real conflict `icmp_eq`/
`icmp_ne` had before `#712`'s own restructuring.**

The real fix is almost certainly the same shape as `#712`'s: insert a
`fanout` subcell that takes over feeding BOTH `and_true` (east) and
`not_mask` (south), freeing `mask`'s own south port for the DAG
relay. Not attempted here -- a real, separate, contained task once
there's time for it, following the exact template `#712` already
proved out.

**A real, separate, additional restriction worth naming, not
resolved here:** `select`'s own `cond` currently must be "the
immediately preceding instruction, AND that instruction must be an
ordinary icmp" (`#674`'s own real check, `prev_icmp_predicate`). A DAG
reference for `cond` would need to relax BOTH the adjacency
requirement AND confirm the referenced instruction is genuinely an
icmp (not just "any earlier value") -- a real, extra piece of scope
verification `add`/`sub`/`icmp`'s own DAG references never needed,
since those don't have a "must be a specific opcode" constraint on
what they reference.

## Real, honest priority ordering, if/when this gets picked up

1. `shl`/`lshr` as consumers -- smallest, most add/sub-like, no known
   structural blocker.
2. `select` as a DAG source -- small, additive, reuses an existing
   fan-out pattern.
3. `select`'s own `cond` as a consumer -- the real, harder one,
   needing both a `#712`-style restructuring AND a real, additional
   "is this an icmp" scope check that nothing else has needed yet.

## Status

Scoping only. No RTL, no frontend code changed, no tests added or
run. Real findings above are from directly reading the existing
composed-tile and frontend emission code, not from building and
testing anything -- the "likely easy"/"expected" language for
`shl`/`lshr` and `select`-as-source is a real, grounded expectation
based on confirmed topology, not a verified result the way `#710`'s
own empirical tests were. Worth confirming by actually building and
testing before treating either as done.
