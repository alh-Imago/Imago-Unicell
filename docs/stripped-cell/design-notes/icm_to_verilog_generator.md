# ICM-to-Verilog: generating the physical shape from the same file that
# already proves the sequence

*Captured 2026-08-19, following the real Quartus-build work on
`top_collector_mechanism_v1.v` (`points.md` #403/#404). Alan's own
framing: "the icm describes the shape, the vm proves the sequence...
can that be used in the creation of the verilog, you know the shape of
each part, you have the verilog for that, you have the connections."
Not started -- a real, concrete idea worth building toward, recorded
before it's lost, not a design decision made yet.*

## The real observation this is built on

An `IcmV3Record` (`nano/icm_v3.py`) already carries everything a
Verilog generator would need to know about one cell's physical shape:
`row`/`col` (placement), `core` (which of the 6 real core types), and
`core_config`/`addon_config` -- the exact same fields `icm_v3.py`
already packs into `unicell_super_v1`'s real 80-bit `cfg_data` port for
the VM.

`SuperGrid.neighbor_pos()` (`nano/unicell_super_automaton_v1.py`) is
the piece that makes this concrete, not just plausible: it already
derives cardinal adjacency PURELY from `row`/`col` arithmetic --
```python
def neighbor_pos(self, row, col, direction):
    dr, dc = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}[direction]
    ...
```
That is exactly the same information a Verilog generator needs to
decide "cell A's `data_out_e` wires to cell B's `data_in_w`." The VM
isn't just simulating cell BEHAVIOR from the ICM -- it's already
computing physical TOPOLOGY from it. `#402`'s own 27-leaf VM proof is a
real, independent confirmation this reasoning holds at real scale, not
just the flat 3-cell case.

## What a real generator would do

`nano/icm_to_verilog_v1.py` (name chosen, not yet built):
1. Walk `IcmV3File.records`.
2. For each record, emit one `unicell_super_v1` instantiation, with
   `cfg_data` as a localparam built via `icm_v3.py`'s own existing
   encode logic (not reinvented).
3. For each record, compute its 4 neighbors exactly as
   `neighbor_pos()` already does, and wire cardinal ports pairwise
   between every adjacent pair -- `data_in_X`/`arrived_X`/`ready_in_X`/
   `ack_in_X` from the neighbor's own `data_out_opposite`/
   `fire_opposite`/etc., matching the SAME pairwise convention
   `top_collector_mechanism_v1.v` and `tb_full_collector_mechanism_v1.v`
   already hand-wire.
4. Tie off any unconnected edge (grid boundary) to the same safe
   defaults the hand-written tops already use.

Verified by cross-checking generated output against a KNOWN-GOOD
hand-wired case (the 3-header mechanism, already built and RTL-proven)
before trusting it on anything larger -- matching this project's own
standing discipline, not a new one invented for this.

## Why this is worth building, stated precisely (not just "less typing")

The bugs found building `top_collector_mechanism_v1.v` (`#403`/`#404`
-- five of them) were NEVER in the wiring itself -- the cardinal
connections were copied verbatim from the proven testbench and were
correct throughout. Every real bug was in the hand-written SELF-TEST
FSM (config ordering, ready-gating races, a width-truncation bug, a
drain/reprogram/capture ordering inversion). A generator would not
have prevented a single one of those five bugs on its own.

What it WOULD do: make the WIRING itself correct-by-construction at any
scale, including scales where hand-wiring becomes genuinely
error-prone in a way it wasn't for 3 headers -- the 27-leaf tree (`#402`)
is exactly that case: 40 cells, each needing 4 cardinal connections
correctly matched to its neighbors' own ports. Hand-wiring that
reliably is a real, separate risk this project hasn't yet taken on.

## Where this sits relative to existing work

This is the concrete, buildable half of `#352`'s own long-range note
("the FPGA design side route... lowering the compiler's own output
past ICM v3 configuration to real, synthesizable Verilog") -- but
approached from the LOADABLE-MODEL direction rather than the
compiler-output direction. ICM files are already real, git-committable
artifacts today (any `SuperGrid.from_icm()`-loadable model), so this
doesn't wait on the compiler pipeline to be the source -- any ICM,
however it was produced (DSL, Python-AST, hand-built JSON model),
becomes a real Verilog-generation candidate the moment this exists.

## Real, honest open question, not solved by this note

The ICM describes STATIC shape -- position, core type, config. It does
NOT describe a sequence of events over time. For a mechanism like the
collector (which needs a command sequencer driving `advance_trigger`
at the right moments, and a self-test or real host driving stimulus),
the STIMULUS is a genuinely separate concern the ICM doesn't capture at
all. This note is scoped to the SHAPE-generation half of the problem
only -- the sequencing/stimulus half remains real, separate, unstarted
work, whatever form it eventually takes (a second, event-sequence-
aware format; real host-driven commands; something not yet designed).

## Status

Not started. A real, concrete, buildable idea with a clear first proof
target (regenerate `top_collector_mechanism_v1.v`'s own wiring from an
ICM and confirm identical connectivity) -- not committed to as the next
priority-list item, just recorded so it isn't lost before it's needed.
