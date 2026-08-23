# SHAPE files

A SHAPE file is the real, per-compiled-design cell-to-cell adjacency
graph — extracted from a specific top-level Verilog file's own real
instantiations by `tools/shape_extract_v1.py`, per `points.md` #449.

**Don't confuse this with a MAN file** (`docs/man/`). MAN describes a
card *model*, authored once, rarely changing. SHAPE describes one
*compiled design's own real layout*, extracted fresh whenever that
design's RTL changes.

## Files

- `top_sentinel_gather_shared_bram_v3.shape.json` — extracted from the
  real, current v3 host-driven mechanism, confirmed against known-correct
  design intent (every direct H1/H2/H3 → COLLECTOR → QUEUE edge found
  matches the actual, hand-verified wiring exactly).

## How it works, and its real, honest limit

The extractor works by finding every named wire that connects **exactly
two instance ports** within a top-level file's own instantiation list —
in a structural netlist, two ports sharing the same net name *is* the
physical connection. This correctly finds every **direct** wire-to-wire
adjacency (confirmed against this project's own known-correct RTL).

**It does NOT trace through intermediate registered or combinational
logic.** This is a real, important limitation, not a minor edge case —
found directly while testing this tool against `#431`'s own original
motivating question (which cells border the BRAM interface set-piece).
The real answer is H1/H2/H3, but the actual RTL relationship is:

```verilog
h1_arrived_n <= shared_rdata_valid && (read_owner == 2'd0);
```

`shared_rdata_valid` is `SHARED_BRAM`'s own real output port name;
`h1_arrived_n` is `H1`'s own real input port name. But they're never the
*same net* — the connection is mediated through a registered, conditional
assignment inside an `always` block, not a direct wire. The current tool
has no way to see this: it only looks at instantiation port lists, not
the logic between them. So as built, `boundary_cells` correctly finds
`SHARED_BRAM ↔ BRIDGE` (a real, direct connection) but misses
`SHARED_BRAM ↔ H1/H2/H3` (the architecturally important one) entirely.

**Real, honest next step, not yet built:** a one-hop dataflow trace —
follow `<=`/`=` assignments to link an always-block's own left-hand-side
signal back to whatever real port names appear on its right-hand side —
would close this specific, common pattern. This project's own RTL uses
the "capture continuously" pattern (registering values from real ports
inside `always` blocks) extensively, so this gap is not a rare corner
case; it likely affects most of the architecturally interesting
adjacency this tool was built to find. Until that's built, real boundary-
cell/set-piece adjacency should be confirmed by direct RTL reading, the
same way `#431`'s own original question was answered this session — not
assumed solved by this tool's current output.

## Two real bugs found and fixed while building this, both by actually
running the tool against real RTL, not by inspection alone

1. **Group-numbering bug:** nested named regex groups shift positional
   group indices — `m.group(3)` silently returned the wrong field.
   Fixed by naming every group explicitly.
2. **False-positive instantiation match:** `else if (h1_arrived_n)
   h1_fresh <= 1'b1;` matched the instantiation pattern
   (`module_type='else'`, `instance_name='if'`), and its own overly
   broad match span silently swallowed the real `SENT1` instantiation
   sitting just after it — confirmed directly (`SENT1` was missing from
   a real extraction run before this was found and fixed). Fixed with a
   negative lookahead that stops the regex from ever starting a match at
   a control-flow keyword, rather than just rejecting the match after
   the fact (rejecting alone isn't enough — `re.finditer`'s cursor still
   advances past whatever the rejected match consumed).
