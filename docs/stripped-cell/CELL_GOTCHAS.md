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
