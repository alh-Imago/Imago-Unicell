# Compiler/Dispatcher/Library Audit — points.md #750–793

Scope note: this covers the arc from `#750` (first hand-built DAG) through
`#793` (formalized opcode library) — the thread that's been active this
session and the one generating the "messy" feeling. It does **not** cover
`#1`–`#749`. That's a real, separate, substantial body of work (six archived
files, ~350KB each) and deserves its own pass rather than a rushed skim
appended here. Flag when you want that done and it can be scoped properly.

Organized by thread, not strictly chronologically, since dependencies matter
more than the order things happened in.

---

## Thread 1 — Rats-nest placement pipeline (`#759`–`#767`)

**The idea:** place things loosely first (generous slack, no attempt at
compactness), then tighten toward a minimum footprint afterward — "rat's
nest" placement, per Alan's own proposal.

**What got built, in dependency order:**
- `#760` — general Manhattan router (`rats_nest_router_v1.py`) — the "loose"
  half. Proven on a hand-built N=4 reduction tree.
- `#761` — nexus-point detection + iterative shrink-and-revalidate tightening
  (`rats_nest_tighten_v1.py`). 186 cells → 90.
- `#762` — measured whether full VM simulation was needed to validate
  tightening (it wasn't, for isolated connections) — `tighten_leaf_
  connection_fast()`, ~6x faster.
- `#763` — nexus-to-nexus tightening (moving a whole solved sub-piece as one
  rigid block). 186 → 34 cells, 82% reduction.
- `#764` — symbolic timing model (`rats_nest_timing_v1.py`) for the
  relay-padded case, where `#750`'s original collision hazard applies.
- `#765` — timing model generalized to composed-piece sources; general N-way
  reduction compiler (`vix_n_way_reduction_v1.py`), proven for N=2/4/8/16.
- `#767` — architectural correction: the compiler tracks its own convergence
  strategy at build time rather than re-discovering it by inspecting a
  finished design afterward.

**Status: fully built and tested, as standalone modules.**

**The gap:** none of this is wired into the dispatcher that actually exists
today (`vix_dag_dispatcher_v1.py`, Thread 3). `compile_dag()` places
correctly but never tightens — `#780` names this directly as "correct, but
not minimal." The router/tightening/N-way modules are real, proven, callable
code sitting unconnected to the current compiler path.

---

## Thread 2 — Convergence-shape discovery (`#769`–`#778`)

**The idea trail, each one correcting or sharpening the last:**

| # | Finding |
|---|---|
| 769 | A single `priority` cell maxes at 3 real inputs; a plain adder can't sum 3+ values (only combines first two); 5-way needs *composing* two `priority` cells |
| 770 | **Correction to `#751`**: operand order is NOT "solved for free" by rank — only true when both paths are equidistant. Proven false in general with a direct counter-case |
| 771 | Fix: pad the shorter path so both operands arrive with equal length (this became **`STAGGER`**) |
| 772 | Alternative fix: a third `priority` mode, "sequenced channel" (this became **`SEQUENCER`**) — found and fixed a real bug along the way (`bool(2) == True == 1`) |
| 773 | Non-power-of-2 N needs a sequential fold; the same `#770` hazard recurs when one operand is a computed result, not just a raw leaf |
| 774 | A genuinely dynamic value should be normalized into a `ram` queue first; `SEQUENCER` is the *only* robust fix once timing is truly unknowable — `STAGGER` is structurally inapplicable there |
| 775 | `SEQUENCER` controls order, never *how many* a plain adder can combine — a 3rd value still needs a real composed tree (already proven in `#773`) |
| 776 | **Major correction**: fan-out needs none of the old frontend's relay/tap/drop/trigger machinery — ordinary multicast + the router (`#760`) is sufficient |
| 777 | Formalized 4-shape catalog: `PLAIN_CHAIN` / `PRIORITY` / `STAGGER` / `SEQUENCER`, via `choose_convergence_shape()` |
| 778 | Shape orientation matters, measurably — 50% more cells, 75% more hops for a mismatched orientation. `choose_two_way_orientation()` built |

**Status: every finding here is proven and tested.** `vix_convergence_
shapes_v1.py` and `vix_shape_orientation_v1.py` are real, standalone, tested
modules — this is solid ground.

**The gap, stated precisely:** `#780`'s dispatcher (the thing that actually
runs) made a deliberate, honest decision to **never use `STAGGER`** — it
always falls back to `SEQUENCER` for non-commutative convergence, because
the dispatcher doesn't yet compute the precise per-branch arrival-tick math
`STAGGER` needs to be safe (branches grow to unpredictable lengths in the
growing-frontier model). So `#771`'s own fix is proven correct in isolation
but **unused by the real compiler path today.** This is named honestly in
`#780`'s own commit, not hidden — but it's a real, open item: building the
real timing math would let `STAGGER` actually get used, avoiding
`SEQUENCER`'s head-of-line-blocking cost where it isn't needed.

**Second gap:** `#775`'s "3rd value needs a composed tree" and `#773`'s
non-power-of-2 fold are both proven *by hand*, not wired into `compile_dag()`
at all. The dispatcher only ever handles exactly 2 operands per instruction.
N-way reduction (`#765`) exists as a completely separate function
(`compile_n_way_reduction()`) that the dispatcher never calls.

---

## Thread 3 — The dispatcher itself (`#779`–`#780`)

**`#779`** — first attempt: pre-compute absolute positions, route blindly
between them. **Failed** — repeated, coincidental routing collisions once
fan-out and convergence combined. This code no longer exists; it was
rewritten, not patched.

**`#780`** — rebuilt around Alan's own correction: grow the whole design as
one connected structure, each new piece adjacent to a known frontier.
**This succeeded and is the real, current system** — `vix_dag_dispatcher_
v1.py`, `compile_dag()`.

**Status: this is the active backend.** All later work (`#781`–`#793`)
builds on it directly.

**Named gap (from `#780` itself):** the tightening pass (Thread 1) isn't
invoked — see above.

---

## Thread 4 — Per-core hazard/immunity testing (`#781`–`#789`)

Every core in the project's own core library, tested one at a time against
the `#777` shape catalog:

| Core | # | Result |
|---|---|---|
| `nano_gate` (all 12 topologies) | 781, 782 | 8 safe with `PRIORITY`, 4 order-sensitive (need `STAGGER`/`SEQUENCER`) |
| `sequencer` | 783 | Its own category, `PURE_EMISSION` — outside the 4-shape catalog entirely (zero operands) |
| `comparator` | 784 | OR-combines simultaneous arrivals rather than comparing them; safe as `PLAIN_CHAIN` only |
| `priority` (weighted round-robin mode) | 785 | Works correctly, still just `PRIORITY` |
| `nano_hold_trigger` | 786 | Order-sensitive, same hazard as `subtract` |
| `accumulator` | 787 | **Immune** — `inc`/`dec` are dedicated, separate faces, not a shared slot |
| `latch` | 788 | **Immune**, same reason as `accumulator` |
| `branch` | 789 | Order-sensitive, same hazard as `subtract` — confirms `#742`'s own earlier finding |

**Status: every one of these has real, permanent tests.** This is the
"checklist" work — genuinely complete for every core the VM can run.

**The gap:** of these 8, only `nano_gate` (as `and`/`or`/`xor`) has an actual
`LibraryEntry` (Thread 6). `sequencer`, `priority`'s weighted mode, `nano_
hold_trigger`, `accumulator`, `latch`, and `branch` are all tested, proven
safe or hazardous, and named in `#777`'s framework — but **none of them are
reachable from `compile_dag()`.** There's no `DagInstr` opcode for any of
them. Proven-in-isolation and wired-into-the-compiler are two different
states, and six of eight cores are stuck at the first one.

---

## Thread 5 — `mul` (`#790`–`#791`)

**`#790`** — found (empirically, not assumed) that `core="mul"` had **no VM
dispatch at all** — a real build gap, not a testing gap. Built it, matching
`adder`'s shape.

**`#791`** — wired into the dispatcher's library. Confirmed correct
end-to-end, including genuine convergence.

**Status: fully working, in both the VM and the new dispatcher.**

**The gap, explicitly raised and left unanswered:** the *old* LLVM IR
frontend (`llvm_ir_frontend_v1.py`) still has no `mul` at all — and adding it
there is real, multi-site work (10+ places, some of which, like loop-
direction detection, `mul` must NOT be added to). This raised an open
architectural question that was never resolved: does `mul` (and future
opcodes) get backported into the old frontend, or does the old frontend get
left behind entirely in favor of a new frontend that speaks to `compile_dag`
directly? **This is a real, live decision point, not a settled one.**

---

## Thread 6 — Library formalization (`#792`–`#793`)

**`#792`** — first `LibraryEntry`-shaped abstraction: `and`/`or`/`xor` added
as real, working opcodes, routed through `nano_gate`'s different port shape.

**`#793`** — formalized as its own module, `vix_opcode_library_v1.py`. Real
fields: `target` (opcode), `tile` (the ICM description — reused, not
reinvented), `is_commutative` + `port_style` (the two separate "shape"
facts), `timing` (pulled live from the tile, never duplicated). The
dispatcher now calls `library_lookup()` for everything — confirmed by grep,
zero opcode-specific strings remain in the placement code.

**Status: 6 real entries exist** — `add`, `sub`, `mul`, `and`, `or`, `xor`.

**The gaps, both named explicitly in `#793` itself, not discovered now:**
1. **No hardware-`target` dimension.** Every entry today picks a tile based
   on opcode alone — there's no way for the same opcode to resolve to a
   different tile depending on which board it's targeting (e.g., a generic
   `core_select` `mul` on one board vs. a dedicated DSP-wrapper cell on
   another).
2. **BRAM/DSP integration not attempted**, though real, already-proven
   infrastructure for both was found to already exist in this repo (`dsp_
   wrapper_tile_library_v1.py`/`dsp_wrapper_automaton_v1.py`, `sentinel_
   bram_automaton_v1.py`) — these are deliberately separate hardware classes
   from `core_select`, not more entries in the same mux. Scoping how the
   library incorporates them (rather than duplicating or conflicting with
   them) is real, separate, unbuilt work.
3. **Only 6 of the ~14 tested cores have entries** (see Thread 4's own gap).

---

## Thread 7 — The unresolved compiler-architecture question

This is the one that cuts across everything above, surfaced but never
settled in conversation:

- There are **two separate backends today**: the old `compile_program_ir()`
  (takes `ProgramIR`, the shared shape both the DSL parser and the LLVM IR
  frontend produce) and the new `compile_dag()` (takes `DagInstr`/
  `DagOperand`, a different, minimal shape). Neither has been retired; only
  one (`compile_program_ir()`) has real frontends feeding it.
- **No frontend feeds `compile_dag()` at all.** Every test built this
  session constructed `DagInstr`/`DagOperand` by hand. The new, proven
  backend has no real, automated way to get LLVM IR or DSL text into it.
- The old frontend supports 10 real opcodes (`add`, `sub`, `icmp`, `select`,
  `shl`, `lshr`, `ashr`, `and`, `or`, `xor`) plus counting loops. The new
  library has 6, none of which include control flow.
- Alan's own stated intent ("the old version is effectively superseded") is
  a real, sound architectural call — but it's a decision about *direction*,
  not yet a completed migration. Old-system capability (loops, comparisons,
  bitwise ops, real frontend parsing) doesn't disappear just because a
  better foundation was found; it has to be rebuilt on the new one,
  deliberately, opcode by opcode, the same way `mul` and `and`/`or`/`xor`
  already were.

---

## Summary: what's solid vs. what's open

**Solid, tested, trustworthy:**
- The shape catalog and orientation logic (`#777`/`#778`)
- The growing-frontier placement mechanism (`#780`)
- Per-core hazard classification for all 8 tested cores (`#781`–`#789`)
- The library abstraction itself and its first 6 entries (`#792`/`#793`)
- The rats-nest router/tightening/N-way pipeline, as standalone, proven code (`#760`–`#767`)

**Open, named, waiting on a decision or more work:**
1. Tightening pass never invoked by `compile_dag()` — output is correct but not minimal
2. `STAGGER` built but never actually selected by the real dispatcher (always falls back to `SEQUENCER`)
3. N-way reduction (`#765`) and non-power-of-2 folding (`#773`) exist but aren't reachable from `compile_dag()`
4. 6 of 8 tested cores (`sequencer`, `priority`'s weighted mode, `nano_hold_trigger`, `accumulator`, `latch`, `branch`) have no library entry at all
5. No hardware-`target` dimension — one opcode, one tile, always
6. BRAM/DSP integration scoped as "existing infrastructure found," not started
7. **No real frontend feeds `compile_dag()`** — this may be the biggest single gap, since everything above is otherwise a correct, tested backend with nothing automated driving it
8. The old LLVM IR frontend still lacks `mul`, and the old-vs-new frontend question is unresolved

Item 7 is probably worth prioritizing before the others — a backend this
well-tested with no way to feed it real programs is the largest single
piece of "solid work with no path to actually using it."
