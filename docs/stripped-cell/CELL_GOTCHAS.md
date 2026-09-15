# Cell Gotchas — real, per-cell/mechanism facts that will silently bite you

**What this file is for, and how it differs from `CORES_AND_WRAPPERS_
REFERENCE.md`:** that file answers "what exists, what's its status."
This file answers a narrower, sharper question — *for a specific cell
or mechanism, what do you have to already know, or you will not get
the correct working result, even though nothing looks wrong?* Alan's
own framing (2026-08-25): "certain cells have to have certain
structures around them at certain configurations... if cell A has this
setup it needs these around it or you will not get the correct working
part."

**Two real, different kinds of gotcha, kept in separate sections
below, because they need different fixes:**
- **Wiring/structural** — a cell only does what you want if specific
  OTHER cells are wired around it in a specific way. The fix for this
  kind is a **composed tile** (`composed_tile_library_v1.py`) that
  enforces the structure, not just a note describing it — a person
  should place one correct tile, not hand-wire N cells from a
  description and hope they got it right.
- **Single-cell behavioral** — a fact about how ONE cell works that
  isn't about wiring at all. No composed tile fixes this; the only
  real fix is knowing the fact. That's what belongs here.

Each entry links back to the `points.md` entry where it was actually
settled, so the reasoning is one click away, but the FACT itself is
visible immediately without archaeology.

---

## Single-cell behavioral gotchas

### Branch/comparator core — held-reference release (`#497`)
**Status: designed, not yet built.** The comparison reference value is
NOT a config field — it's the FIRST value captured after programming
(or after a release), held indefinitely. Every later arrival compares
against it. **Release only happens by reprogramming the cell
(`cfg_valid`)** — there is no live, in-band "release now" signal. If
you want to change what a branch cell is comparing against mid-run,
you must reprogram it; the held value passes through normally on
release, and the very next arrival becomes the new reference.

### Branch core — cannot be a direct external injection/entry point (`#742`)
**Real, confirmed directly against the VM's own `_deliver_branch()`,
matters for ANY code generator (LLVM IR frontend, DSL compiler,
hand-written ICM) placing a branch cell.** Every other real core's own
delivery handler checks a separate `injected` parameter alongside real
directional `arrivals` (`ram`'s own `_deliver_ram`, for instance,
explicitly ORs `injected` into the captured value). `branch` does not
— its own real delivery logic (`matched = [d for d in arrivals if d ==
self.br_upstream_dir]`) never looks at `injected` at all. **A branch
cell can never be marked as a real external entry point (`io_name`) or
receive a value via direct injection — it must always be fed by a
genuine cardinal neighbor**, even if that neighbor's own only job is
relaying an externally-injected or upstream-delivered value onward. Any
placement algorithm that tries to mark a branch cell itself as a design's
own real input point will silently fail (the value never arrives, with
no error) — this needs to be a real, checked PLACEMENT RESTRICTION a
compiler enforces before generation, not discovered by a person
debugging a stalled pipeline afterward.

### Branch core — establishing its own reference needs two, genuinely SEPARATE deliveries (`#742`)
**Real, confirmed directly, matters for scheduling/sequencing in any
real code generator, not just manual test harnesses.** Because a
branch cell's own held reference is "whatever arrived first" (see the
gotcha above this one), and because a single upstream `ram` relay's
own real delivery logic OR-combines whatever arrives on the SAME tick
into one value (it cannot hand branch "0, then the real value" as two
distinct deliveries if both would otherwise arrive together), a real
"compare a dynamic value against zero" pattern needs its own zero-
reference source to settle through to branch on ITS OWN, separate real
tick(s), BEFORE the real, dynamic value is ever injected or arrives.
Injecting both at once (or close enough in real time that they land
on the branch cell's own upstream on the same tick) OR-combines them
into a single, wrong reference. **Any compiler targeting `branch` for
a "compare against a compile-time-known constant" pattern needs to
generate a real settle/sequencing step** (or use `comparator` instead,
which takes its own threshold as a real, static config field, needing
no separate reference-establishment delivery at all — the better
choice for this exact use case, confirmed the hard way building a real
CORDIC pipeline, `#742`).

### Adder/mul core — two real operands arriving on the SAME tick silently loses one (`#748`)
**Real, confirmed directly, matters for any code generator or hand-
built design placing two operand sources equidistant from an adder (or
`mul`) cell.** `_deliver_adder()`'s own real logic processes only ONE
matched arrival per call: `if not self.adder_a_arrived: capture as A,
return` — it never checks whether a SECOND, different-direction
arrival landed in the very same `matched` dict on the same tick. If
both real operand sources are the same real distance from the adder
(e.g. both one hop away, injected at the same moment), both arrivals
land on the adder's own upstream on the exact same tick — but only
ONE of them gets captured as `A`; the other is silently dropped,
never becoming `B`, and the adder never fires at all (waiting forever
for a real "second" arrival that already came and went). **Real,
correct fix, confirmed by building and testing a real, working example
(`#748`):** stagger the two operand deliveries in real time — inject
(or let the first arrive) fully before the second is injected or
arrives, even by just one real tick. A design where the two operand
paths are genuinely different lengths (naturally staggered by the
real topology) avoids this without any explicit sequencing at all;
a design where they're equidistant (or one is a compile-time constant
injected at the same moment as the other) needs a real, deliberate
delay on one side. **Any compiler generating a two-operand placement
should default to giving the two operand paths genuinely different
real lengths, or explicitly stagger a same-tick injection/constant
delivery by at least one tick** — this is the same real class of
timing hazard as the branch/zero-reference gotcha above, one level
over: a "matched pair" capture core needs its two real deliveries
genuinely sequenced, not simultaneous, regardless of which core it is.

### Adder/mul core — TWO PRELOADED constants converging on the same consumer ALSO collide, not just a "dynamic vs. constant" case (`#750`)
**Real, sharpened generalization of the gotcha immediately above,
confirmed directly while hand-building the smallest real DAG that
isn't a linear chain.** The gotcha above frames the fix as "stagger
the dynamic operand" — but a real, direct test showed the SAME
collision happens with ZERO dynamic operands at all: two flowing-mode
`ram` cells, each seeded via `preload_value` (the correct, established
fix for re-contamination), are BOTH already `ram_data_valid=True` at
construction time — neither needs a trigger or injection to become
ready, each simply IS ready from tick zero. If both feed the SAME
consumer at the SAME real distance, both offer on the very first real
tick and OR-combine, exactly like the fully-dynamic case above, for a
genuinely separate reason: `preload_value` fixes re-contamination (a
drained cell won't keep re-offering forever); it does NOT, by itself,
fix simultaneous FIRST arrival between two independently-ready
sources. **The real, fully general rule, confirmed by building and
tracing a working fix (`#750`):** ANY two real values converging on
the same consumer — both dynamic, both constant, or one of each —
need genuinely different real path lengths to that consumer, full
stop; there is no "safe" combination that skips this. The working fix
is the same one already named above (pad one path with a real relay
hop) — this entry exists because the ORIGINAL framing ("stagger the
dynamic operand") could be misread as "two constants are safe," which
a real, direct test showed is false. **Any placement/codegen pass
generating a real convergence point — dataflow-depth-based grouping
or otherwise — must check every pair of paths converging on a shared
consumer for equal length, regardless of whether either side is a
compile-time constant.** Real, working example preserved at
`nano/examples/dag_diamond_hand_built.py`.

### Branch/comparator core — `in+N` direction resolution (`#494`)
**Status: designed, not yet built.** `in+1`/`in+2`/`in+3` (relative to
the arrival direction) is resolved to a real, ABSOLUTE direction mask
at ICM-PROGRAMMING time (by the compiler/Designer), not at runtime.
This means the core needs a SINGLE, fixed upstream direction — not a
multi-direction mask like the ordinary `comparator` core's own
`upstream_mask`. If a future edit ever tries to give this core a
multi-direction upstream, `in+N` stops having one well-defined meaning
and the whole addressing scheme breaks.

### DSP wrapper watchdog — simulation threshold vs. real JTAG timescale
Simulation uses a threshold around 50 cycles. Real, JTAG-paced hardware
needs roughly **162,500 cycles** for the same real elapsed time — found
on actual silicon, not derived. Using a sim-scale threshold on real
hardware will cause spurious watchdog trips that look like a hung cell
but aren't.

### DSP wrapper — per-operation hardware confirmation status
Only **ADD** has been run on real silicon and confirmed correct
(`#472`). SUB/MUL/GE/LE/NEQ share the identical real entity/protocol
path and are sim-verified, but individually UNPROVEN on real hardware.
Don't treat "same wrapper family as ADD" as equivalent to "hardware-
confirmed" for the other five operations.

### DSP wrapper IP entity naming — top-level name vs. internal Qsys kind
The real, instantiable top-level module name is whatever the `.qsys`
file/instance was NAMED in IP Catalog (e.g. `alterafpf_add_single`,
`alterafpf_ge_single_comb`) — NOT the internal Qsys component `kind`
(e.g. `altera_nios_custom_instr_floating_point_2_multi`), which only
exists one level inside the generated wrapper. Confirmed the hard way
twice (`#470`/`#471`) before this became a documented rule rather than
a guess.

### Nano core, reconstructed inside the super shell — reduced feature set
Nano run standalone has its FULL real feature set. Nano reconstructed
as a core inside `unicell_super_v1.v` only exposes `topology`/`ready`/
`routing_mask`/`cardinal_edge` — branching (`dynamic_route_en`/
`pattern_low`/`pattern_equal`/`pattern_high`), `hold_in`, `fb_internal_
in`, and `is_command_cell` are all real and present in the standalone
cell but NOT wired through the super shell's own `core_select=0` case.
See `CORES_AND_WRAPPERS_REFERENCE.md`'s own "standalone vs.
super-carrier" section for the full rule.

---

## Wiring/structural gotchas — real, enforced by a composed tile, not just described here

### A continuously-live constant source double-counts at a two-arrival (matched-pair) core (`#742`)
**Real, confirmed directly, matters for ANY code generator feeding a
compile-time-known constant into `adder` (or any future core with the
same real "capture A, then capture B" shape).** `adder`'s own real
two-arrival capture doesn't care WHERE its two arrivals came from —
only that two real, separate delivery events happened. A `ram` cell
in `fixed_mode` ("permanent ROM-style") re-offers its own held value
EVERY tick, forever, never draining. If that continuously-live source
is the only thing feeding one of `adder`'s own two upstream directions,
and the real, dynamic operand (from elsewhere) is even one tick late,
the fixed source's own repeated offers get captured as BOTH `a` and
`b` — silently producing `2×constant` instead of `constant + dynamic`,
with no error at all. **Real, correct fix, confirmed working end to
end building a real CORDIC pipeline (`#742`):** use a flowing-mode
(`fixed_mode=0`) `ram` cell seeded via the real, existing
`preload_value` mechanism instead of `fixed_mode`/`init_data` — a
flowing cell offers its own preloaded value exactly ONCE, then goes
quiet until something re-captures it, matching what a genuine
compile-time constant actually needs to do. **Any placement/codegen
routine generating a "feed this adder a fixed constant" pattern must
default to flowing-mode + `preload_value`, never `fixed_mode`, unless
the constant is genuinely meant to be re-offered forever** (a real,
different, rarer use case). *(No composed tile exists for this yet —
a real, concrete follow-up: a `const_feed` composed tile pairing a
flowing, preloaded `ram` with whichever consuming core needs a
one-shot constant, so this can't be hand-wired wrong.)*

### The recombiner — narrow branch-cell outputs into one wide word (`#497`)
**Status: designed, not yet built.** Reconstitutes a 32-bit word from
four 7-bit branch-cell classification codes. Requires an EXACT chain:
branch cell → shift(amount=8) → adder → shift(amount=8) → adder →
shift(amount=8) → adder, 6 extra cells for 4 input bytes. Get the shift
amount wrong (anything outside `shift_lane_addon_v1.v`'s own supported
set `{1,2,4,8,12,16,20,24,28}` silently no-ops, per that file's own
documented behavior) and the whole chain silently produces garbage —
no error, just a wrong number. **Real, honest limitation, not a bug:**
this reconstitutes CLASSIFICATIONS, not arbitrary values — a single
branch cell round-robining into the chain produces a degenerate,
repeated-code result; even four independent branch cells cap out at
`2^28` distinct outputs, not the full `2^32` range. If you need to
preserve one genuine 32-bit value untouched, use the branch cell's own
relay mode (`value_source`=0) directly — don't route it through the
recombiner at all.

*(No composed tile exists for this yet — real, concrete follow-up
once the branch cell itself is built: register a `recombiner_4way`
composed tile so this structure never has to be hand-wired.)*
