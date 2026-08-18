# DSP chain connectivity vs. BRAM connectivity — a real, asymmetric hardware fact

*Captured 2026-08-17 (day 3), following up on `#377` (DSP-column-aware
placement). Real Arria 10 documentation checked directly before writing
any of this down — nothing here is recalled from memory alone.*

## The core finding

**DSP blocks and M20K/BRAM blocks connect to the rest of the chip in
genuinely different ways, not just different capacities.** This
matters directly for how a future DSP-backed or BRAM-backed Unicell-S
core would actually integrate — they are NOT the same kind of problem
just because both are "hard IP."

### DSP: a dedicated, hardwired, column-local cascade bus

Arria 10 variable-precision DSP blocks have a real `chainin`/
`chainout` interface — confirmed directly from Intel's own
documentation, not assumed:
- **64-bit wide**, tied to the DSP block's own output register.
- **Hardwired, not general fabric routing.** It connects a DSP block
  directly to its physically adjacent neighbor in the SAME DSP column.
  A cascade chain "can continue as far as a full column" — it does not
  route sideways or through general interconnect.
- **Real consequence:** because the chain is fixed silicon wiring
  between specific physical block instances, WHICH block instances your
  design occupies (and therefore where in the column your own chain
  segment starts and ends) is decided entirely at Quartus place-and-
  route time. There is no runtime addressing on this bus at all — once
  programmed, the entry/exit points are fixed for the life of that
  bitstream.
- **What this means for Unicell-S:** chain position is a PLACEMENT
  decision, not a runtime protocol field. It's the same kind of thing
  `loader_v1.py` (`#375`) already owns for row/col placement — a DSP
  chain's start/end point would be resolved the same way, at bind time,
  not carried as a `core_config` field a compiled program has to know
  about in advance.

### BRAM/M20K: normal, addressed fabric connectivity

M20K blocks, by contrast, connect through the SAME general local/
direct-link interconnect any LAB uses — confirmed directly, not
assumed. They are true dual-port RAM with a configurable address/data
width, accessed like any other addressed resource on the chip. **There
is no dedicated M20K-to-M20K cascade bus analogous to the DSP chain.**

**Real consequence for item 7 (memory functions):** a BRAM-backed RAM
core doesn't face the same "which physical chain position" placement
problem a DSP-backed core does. The real open questions for memory
connection are different in kind — address/data WIDTH matching against
M20K's own native configurations, and general fabric routing/timing,
not chain-position binding. Whatever `loader_v1.py`'s eventual memory-
aware placement work looks like, it should NOT be assumed to need the
same "entry/exit point" concept the DSP work does -- that would be
importing a DSP-specific problem into a place it doesn't actually
apply, per this real, checked distinction.

## The MathTrix/MIF precedent — real, but doesn't directly transplant

Alan's own recollection of the (now-archived) MathTrix system's real
`MIF` format (`MathTrix Internal Float`, confirmed directly by
extracting the archive and reading `cell_format.py`, not from memory)
splits a value across two cells -- but NOT as an even bit-count split:

- **Cell 1 ("control"):** exponent (8 bits), sign, `is_nan`/`is_inf`/
  `is_zero` flags, guard bits.
- **Cell 2 ("mantissa"):** the 24-bit significand.

The real, documented reasoning: *"Exponent arithmetic is fast because
exponent lives alone in control cell nibbles — no decompose tree
needed. Mantissa cell untouched for routing and compare-only
operations."* This is an ASYMMETRIC split by FUNCTION, not by bit
count -- it only makes sense because an IEEE-754 float has a genuinely
different, separable exponent and mantissa that different operations
touch differently.

**A flat 64-bit DSP accumulator/product value has no such natural
boundary** -- it's very likely a plain two's-complement number, not a
structured float. MIF's own specific split doesn't apply here. What
DOES carry over is the underlying PRINCIPLE (split on what each half
will actually be used for, not just on bit count) -- which, for a flat
64-bit value with no internal structure, collapses back to a plain
high-32/low-32 split across two cells. Not a coincidence that this
matches Alan's own proposed "steal the idea, two cells take half each"
-- it's the same reasoning, arriving at a different concrete split
because the data shape is different.

## Real, honest open questions, not resolved here

- **Exactly what's inside the 64 bits** for a specific DSP operational
  mode (an already-finished accumulator value vs. something needing a
  shift/rounding step first) has NOT been verified against a specific
  Quartus DSP IP configuration. Worth checking before finalizing a
  two-cell split design.
- **32-bit trim vs. full 64-bit two-cell split** is a real, workload-
  dependent tradeoff, not decided here: 32-bit is simpler (one cell,
  one hop) but discards the headroom that's the actual reason to use
  the DSP's own hardware accumulator instead of software accumulation.
- **The BRAM side's own real integration design** (address/data width
  matching, M20K-aware placement) is genuinely unstarted -- this note
  only establishes that it's a different kind of problem from the DSP
  side, not what the actual design should be.

This note exists to make sure the real distinction Alan noticed
("it's very different from the BRAM side") doesn't get lost or
flattened into "DSP and BRAM connection are basically the same problem"
by the time item 7 (memory functions) is actually picked up.

## The real architectural conclusion (Alan, same session)

**DSP needs its own specialist wrapper core type -- not a mode or field
on an existing core.** Matching exactly how BRAM would also need its
own dedicated interface handling, DSP is a genuinely separate kind of
hard-IP integration, not a variant of anything already built. This is
`core_select` 6-31 headroom territory (`#317`), the same "LEGO for
FPGA" concept already on record (`#353`), not a modification to any of
the current 6 real cores.

**The 64-bit chain resolves into TWO PARALLEL 32-bit-wide chains, not
one wide interface.** Rather than one wrapper cell trying to carry a
64-bit value through the fabric (which has no existing wide-value
convention anywhere), the design is: two independent lanes of
DSP-wrapper cells, each handling exactly 32 bits (a "high" chain and a
"low" chain), each propagating its own half using the SAME native
32-bit value convention every other core already uses (`ram`'s own
`init_data` and `comparator`'s own `threshold` are both real, already-
working 32-bit fields -- this isn't a new width being introduced, it's
reusing the one the fabric already speaks).

**Worth noting explicitly: this is structurally the SAME solution MIF
already arrived at, independently, for a different reason.** MIF splits
a value across exactly two standard-width cells because a float has a
natural exponent/mantissa boundary to split ON. The DSP case has no
such boundary (a flat accumulator, confirmed above) -- but the
resolution converges on the same STRUCTURAL shape anyway: multiple
standard-width cells representing one wider logical value, rather than
inventing a new wide-value mechanism for the fabric to support. Two
independent, unrelated design problems landing on the same real
pattern is a genuine, useful signal that "N standard-width cells,
not one wide cell" is probably the right general answer for wide
hard-IP interfaces on this substrate, not just a DSP-specific hack.

**Real, honest, still-open pieces this doesn't resolve:** how the two
32-bit lanes stay correctly PAIRED as they propagate (do they need to
travel through the fabric together, e.g. always placed as adjacent
cells, or is correctness maintained some other way); whether the
"high" and "low" DSP-wrapper cells are the SAME core type with a
role field, or two genuinely distinct core types; and everything
already listed above (exact bit content per DSP mode, the 32-bit-trim
tradeoff). A real scoping conversation for whenever "LEGO for FPGA"
is actually picked up, not resolved in this note.

## The 64-bit chainout/chainin format, confirmed against the primary source

Checked directly against Intel's own Arria 10 Core Fabric handbook
(§3.4.7, the same document `#26` already sourced), not assumed from
the earlier structural reasoning alone.

**The 64 bits have NO internal structure at all -- a plain, flat 64-bit
two's complement signed integer.** No embedded valid bit, no status
field, no sub-fields of any kind. This confirms (doesn't just support)
the earlier conclusion above that a flat accumulator has no natural
exponent/mantissa-style boundary to split on.

**Three real control signals govern what happens to that value at each
stage -- and they are NOT part of the 64-bit payload:**

| Function | NEGATE | LOADCONST | ACCUMULATE | What it does |
|---|---|---|---|---|
| Zeroing | 0 | 0 | 0 | Accumulator disabled |
| Preload | 0 | 1 | 0 | Adds a preload value (exactly one bit of it may be "1" -- controlled rounding at any bit position) |
| Accumulation | 0 | X | 1 | Adds current result to the running total |
| Decimation + Accumulate | 1 | X | 1 | Converts current result to two's complement first, then adds -- effectively a subtract |
| Decimation + Chainout Adder | 1 | 0 | 0 | Converts current result to two's complement, adds to the PREVIOUS block's chainout -- the cascade mechanism itself, and it can subtract, not just add |

**A real, checked answer to "are these baked in at synthesis time, or
programmable" (the same class of question already settled for
`cardinal_edge`):** confirmed these are real, DYNAMIC input ports on
the DSP primitive, not compile-time parameters -- Intel's own errata
describes them as things a design "asserts or deassserts" at runtime,
and separately states "two signals allow for dynamic control." Because
they're genuine wires, whatever drives them from the fabric side
decides whether they're fixed or dynamic. **A Unicell-S DSP-wrapper
core can legitimately hold NEGATE/LOADCONST/ACCUMULATE as ordinary
`core_config` fields, reprogrammable through the exact same
`program_in`/`PROG_ID` mechanism every other core already uses.** No
new class of mechanism needed for this -- the same pattern as
everything else, just three more bits in a wrapper core's own config.

**A real, hard constraint found and worth stating plainly, not
glossed over:** these ports are NOT functional in `m27x27` or
`m18x18_full` operation modes -- Intel's own words: "the DSP core does
not perform any operations enabled by these ports" in those modes,
even though the ports remain physically present and connectable. Given
the GX660 supports 27×27 multiply as one of its real modes (`#26`),
this is a real, direct tradeoff: full 27-bit precision multiply loses
dynamic accumulate/negate/preload control entirely, regardless of what
drives those wires.

## A real, honest scope note on why that tradeoff isn't costly right now

The current Unicell-S value model is flat 32-bit fields with no signed
representation and no fixed-point convention anywhere in the design.
There is currently no format in the substrate that would know what to
DO with 27-bit-precision results beyond truncating them back down
regardless. Giving up `m27x27` to keep dynamic accumulate/negate/
preload control is therefore not really a tradeoff at the CURRENT
stage of the project -- it's trading away something the system has no
way to use yet, for something it can use immediately.

**Stated more broadly, Alan's own framing, worth keeping honest and
explicit rather than losing in the DSP-specific detail above: the
substrate as a whole remains genuinely narrow in scope.** Six real
cores, unsigned-ish 32-bit integers, no negative-number representation,
no fixed point, branching that costs real physical cells per outcome
(`#371`'s own already-logged insight). The DSP work in this whole
thread adds real precision and real throughput on TOP of that existing
value model -- it does not, on its own, broaden the value model itself.
Whether signed values or a fixed-point convention ever get added to
the substrate is a separate, real, entirely unstarted design question,
not something this DSP thread has touched or assumed an answer to.
