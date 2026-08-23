# SHAPE files

A SHAPE file is the real, per-compiled-design cell-to-cell adjacency
graph — extracted from a specific top-level Verilog file's own real
instantiations by `tools/shape_extract_v1.py`, per `points.md` #449.

**Don't confuse this with a MAN file** (`docs/man/`). MAN describes a
card *model*, authored once, rarely changing. SHAPE describes one
*compiled design's own real layout*, extracted fresh whenever that
design's RTL changes.

## How to generate one

```
python3 tools/shape_extract_v1.py <verilog_file> --card-id <id> [options]
```

Runs on the **RTL source file directly** — no Quartus build, no `.sof`,
no JTAG connection, no hardware of any kind. It's a plain text/regex
parser over the actual Verilog. Confirmed to produce byte-identical
output (aside from the `generated` date and `git_commit` fields) whether
run in this project's own Linux sandbox or on Alan's real Windows
machine (`points.md` #454's own follow-up).

**Arguments:**

| Flag | Required? | Meaning |
|---|---|---|
| `<verilog_file>` | yes | Path to the top-level `.v` file to extract from |
| `--card-id <id>` | yes | Matches a MAN file's own `card_id`, so a consumer can tell which physical card model this SHAPE is meant to be compiled against |
| `--top <name>` | no | Top-level module name, recorded in the output metadata only (defaults to the filename) |
| `--set-piece-types <list>` | no | Comma-separated module types treated as fixed set-pieces for `boundary_cells` detection (default: `bram_controller_v1`) |
| `-o / --output <path>` | no | Write to a file instead of stdout |

**Example, the real command used to generate the file checked into this
directory:**

```
python3 tools/shape_extract_v1.py fpga/verilog/top_sentinel_gather_shared_bram_v3.v \
    --card-id mustang-f100-a10-01 \
    -o docs/shapes/top_sentinel_gather_shared_bram_v3.shape.json
```

Re-run this any time the RTL for that top-level file changes — nothing
about a SHAPE file is meant to be hand-edited after generation.

## Files

- `top_sentinel_gather_shared_bram_v3.shape.json` — extracted from the
  real, current v3 host-driven mechanism. Every field independently
  verified against known-correct real design intent, not just "the
  script ran without crashing" — see the schema breakdown below for
  what was checked.

## Output schema, field by field

```
{
  "shape_version": "1.0",          // schema version of this file format
  "card_id": "...",                // matches a MAN file's own card_id
  "generated": "YYYY-MM-DD",       // extraction date
  "source_file": "...",            // the .v file this was extracted from
  "top_module": "...",             // top-level module name
  "git_commit": "abc1234",         // short hash of the repo at extraction time, if run inside a git checkout
  "cells": [ ... ],
  "role_summary": { ... },
  "edges": [ ... ],
  "boundary_cells": { ... },
  "port_availability": { ... },
  "set_piece_types": [ ... ],
  "unresolved_ports": [ ... ],
  "fanout_nets": { ... }
}
```

### `cells`

One entry per real instantiation found in the top-level file:
`instance` (the instance name, e.g. `H1`), `module_type` (e.g.
`unicell_super_v1`), `cell_id` (the real `CELL_ID` parameter read back
from the source if present, `null` otherwise — only `unicell_super_v1`
instances carry one in the current RTL), and `role` (see below).

### `role_summary`

The same cells, grouped by `role`, for quick lookup without scanning
the full `cells` list.

### `role` / cell classification

Not a taxonomy invented for this tool — maps directly onto `#253`'s
own SHELL/CORE/ADDON model and `#293`'s own fourth category,
HOST-INTERFACE:

- **`programmable_substrate`** — `unicell_super_v1` instances. The one
  module type whose own behavior is chosen at ICM-load time
  (`core_select`), not fixed at synthesis — genuinely part of the
  user-programmable field.
- **`host_interface`** — bridges the fabric to something *outside* it
  (no cardinal ports, doesn't join the mesh). Currently:
  `host_bridge_bram_icm_v1`, `host_bridge_sentinel_gather_v1`,
  `sentinel_issp_bridge_v1`, `unicell_issp_bridge`.
- **`connection_point`** — everything else: fixed behavior baked in at
  synthesis time, never reprogrammed (`bram_controller_v1`,
  `collector_relay_v1`, `sentinel_counter_v1`, `addr_counter_v1`, ...).

A real, honest nuance: `role` tells you what a cell *type* is capable
of, not whether a *particular instance* in a *particular* design is
actually free for a user program. `QUEUE` in `v3` is a genuine
`unicell_super_v1` shell and correctly classifies as
`programmable_substrate`, even though this specific design wires it
into the mechanism as a fixed, dedicated queue.

### `edges`

Real, direct point-to-point structural connections. Found by locating
every named wire that connects **exactly two instance ports** — in a
structural netlist, two ports sharing the same net name *is* the
physical connection. Each edge: the shared `net` name, and `from`/`to`
each giving `instance`, `port`, and `direction` (`N`/`S`/`E`/`W` if the
port name carries a cardinal suffix, `null` otherwise — e.g. every port
on `collector_relay_v1` uses `a`/`b`/`c`/`data_out` naming, not N/S/E/W,
a deliberate design choice, `#427`/`#428`, since it never participates
in the cardinal mesh like a normal cell).

**Real, honest limit:** this only finds *direct* wire-to-wire
adjacency. It does **not** trace through intermediate registered or
combinational logic — see "Known limitations" below.

### `boundary_cells`

For each module type listed in `set_piece_types`, which
non-set-piece instances have a *direct* edge touching it. Answers
`#431`'s own original question ("which cells border this fixed
set-piece") — but only for direct connections; see the same limitation
below for why this currently under-reports for `v3`.

### `port_availability`

For each `programmable_substrate` cell, per cardinal direction (`N`/
`S`/`E`/`W`), whether the **input side** (`data_in_X`/`arrived_X`) and
**output side** (`data_out_X`/`fire_X`) are independently:

- **`used`** — a real edge exists on that specific port
- **`free`** — tied to a constant (`32'h0`, `1'b0`, ...) or left
  unconnected — genuinely nothing using it in this design
- **`ambiguous`** — a real, non-constant expression this tool can't
  confidently classify — reported honestly rather than guessed at

Input and output on the same direction are genuinely independent, not
assumed symmetric — confirmed directly against `v3`'s own real RTL.
`H1`'s south *output* is wired to the collector while its south
*input* is simultaneously free; `H2` uses north for *both* its own
input and output at once (a real, legitimate asymmetric pattern, not a
bug). Every value in the checked-in `v3` file was independently
verified against the known-correct real topology before being trusted.

This is the field a real loader/auto-placer actually needs: not just
"what's connected," but "where could a new chain attach."

### `set_piece_types`

Echoes back the `--set-piece-types` argument used for this run, so a
consumer knows what `boundary_cells` was computed against.

### `unresolved_ports`

Every port connection this tool couldn't confidently resolve into
either a real edge or a tied-off/unconnected classification — a real,
non-constant expression (a combinational condition, a bit-select
combined with logic, etc.). Flagged, not guessed at.

### `fanout_nets`

Named wires that connect to more than 2 instance ports, or to only 1
(a dead end) — real connectivity, but not a clean point-to-point edge,
so not folded into `edges`. Kept separately rather than dropped.

## Known limitations

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

**No physical placement.** Only logical adjacency — which cell is wired
to which, not real X/Y silicon coordinates. Those only exist in
Quartus's own post-fit output (Chip Planner/Fitter export), and
merging that in is real, separate, not-yet-started work.

**How physical placement WOULD get merged in, once available — a real
plan, checked against real Intel documentation, not yet built:**

A pre-fit or synthesis-only netlist has no placement data at all —
location only exists after the Fitter has actually placed and routed
the design. The real Quartus mechanism for extracting it: **Back-
Annotate Assignments** (Assignments menu → Back-Annotate Assignments,
after a completed Fit; also has a scriptable Tcl equivalent for a
future repeatable flow). This copies the Fitter's own real placement
decisions into a plain-text assignment file — `set_location_assignment
<LOCATION> -to <node_name>` lines, exportable as `.qsf`-format text or
CSV. This is the same class of data already used by hand in `#438`/
`#439`'s own real critical-path investigation (`SENT1|diff[2]|q` →
`FF_X143_Y44_N37`), just covering the whole design at once instead of
individually copied paths from the Chip Planner GUI.

**A real, honest granularity nuance, not glossed over:** this data is
per *placed primitive* (individual registers, LUTs), not automatically
grouped by RTL top-level instance name. `H1` as a whole doesn't get one
X/Y — dozens of `H1`'s own internal registers each get their own. Large
hard-IP blocks (a whole M20K, a whole DSP) map to one real resource
with one location, so those are simpler. For a normal cell like `H1`,
a real merge tool would need to read the hierarchy-path prefix off
each row (e.g. `H1|CORE_ACC|out_buffer[10]`) and aggregate — most
usefully as a bounding box — to get a meaningful "where is H1"
answer, not a single coordinate per row.

**Real, concrete next step:** run Back-Annotate Assignments on a real
Fit, export (CSV is likely easiest to parse), and build a real parser/
aggregator following the same pattern as `shape_extract_v1.py` — tested
against known-correct values before being trusted, same as every other
tool in this project.

**Real, honest next step, not yet built:** a one-hop dataflow trace —
follow `<=`/`=` assignments to link an always-block's own left-hand-side
signal back to whatever real port names appear on its right-hand side —
would close the boundary-cell gap. This project's own RTL uses the
"capture continuously" pattern (registering values from real ports
inside `always` blocks) extensively, so this gap is not a rare corner
case; it likely affects most of the architecturally interesting
adjacency this tool was built to find. Until that's built, real
boundary-cell/set-piece adjacency should be confirmed by direct RTL
reading, the same way `#431`'s own original question was answered this
session — not assumed solved by this tool's current output.

## Development history — real bugs found, all caught by actually
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
