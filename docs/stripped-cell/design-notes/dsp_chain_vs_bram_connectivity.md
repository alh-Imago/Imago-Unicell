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
