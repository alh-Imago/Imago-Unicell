# ICM v3 Format — the super cell's own program format

*Real, implemented, verified 2026-08-16. Implementation: `nano/icm_v3.py`.
Tests: `tests/vm/test_icm_v3.py` (16/16 passing). Cross-checked bit-for-bit
against `fpga/verilog/tb_unicell_super_v1.v`'s own proven test vectors,
compiled and run via iverilog against the real `unicell_super_v1.v` RTL
the same session — not just read from the header comment.*

## Why this is a new format, not v2 extended

`docs/shared/ICM_FORMAT.md` (v2)'s record shape — `gs`/`in`/`out`/`init` —
is a FULL-cell artifact. `in`/`out` are addressed-BUS addresses: they mean
something because the FULL cell (and everything v2 was ever built
against) matches on an address broadcast over a shared bus.

Neither nano nor any of `unicell_super_v1.v`'s other 5 cores (RAM, adder,
accumulator, comparator, latch) work that way. Every one of them wires
N/S/E/W to PHYSICAL cardinal neighbors via its own `downstream_mask`/
`upstream_mask` (nano uses `routing_mask`/`cardinal_edge` — same one-hot
N/S/E/W convention, different name for historical reasons). This matches
`nano/unicell_automaton_v1.py`'s own `CAGrid`: "fixed physical neighbors
only, no addressing/bus." So a v3 record carries **no bus-address field
at all** — connectivity intent lives entirely inside the selected core's
own `core_config`, exactly as the real RTL encodes it. What a v3 record
needs instead is a **grid position** (which physical cell this record
configures), not an address to match against.

This is a real, deliberate correction to v2's own self-description
("runs on the Python VM, any supported FPGA... without modification") —
that claim was already only true for the FULL cell's bus model. Being
honest that the wire format genuinely changed for the super cell, rather
than silently stretching v2's field list to cover it, is the point of
calling this v3 rather than v2.1.

## The 80-bit SUPER_LATCH, as implemented

Matches `unicell_super_v1.v`'s own header exactly (lines 17-43):

| Bits | Field | Width |
|---|---|---|
| `[4:0]` | `core_select` | 5 |
| `[46:5]` | `core_config` | 42 (union, reinterpreted per core) |
| `[66:47]` | `addon_config` | 20 |
| `[79:67]` | reserved | 13 |

`core_select` values 0-5 are assigned (nano/RAM/adder/accumulator/
comparator/latch); 6-31 are genuine future headroom, per `#317` — the
real RTL's output mux treats an unassigned value as inert (all outputs
zero), not X, and `icm_v3.decode_super_latch()` mirrors that: it returns
`{"core": "reserved_N", "core_config": {"_raw": ...}}` rather than
raising.

## Per-core `core_config` field tables

Every table below is a direct transcription of that core's own `.v` file
header comment (`cfg_data[N:0] field map`), verified against the actual
RTL logic reading those bits, not just the comment. Bit numbers are
**within that core's own share** of `core_config` — i.e. bit 0 here is
`core_config` bit 0, which is `super_latch` bit 5 (since `core_config =
super_latch[46:5]`).

**nano** (`core_select=0`) — only a subset of nano's own 128-bit
`cfg_data` is reachable through the super cell (see Scope note below):
| Field | Bits | Source |
|---|---|---|
| `topology` | `[9:0]` | `unicell_stripped_v1.v` topology field |
| `ready` | `[10]` | nano's `ready` bit |
| `routing_mask` | `[16:11]` | nano's routing_mask (6-bit, 3D-ready) |
| `cardinal_edge` | `[22:17]` | nano's cardinal_edge (6-bit) |
| `hold_in` | `[23]` | nano's hold_in bit — real, added `points.md` #650 |
| `fb_internal_in` | `[24]` | nano's fb_internal_in bit — real, added `#650` |
| `a_reemit_in` | `[25]` | nano's a_reemit_in bit — real, added `#650` |
| `a_update_in` | `[26]` | nano's a_update_in bit — real, added `#650` |
| `a_self_update_in` | `[27]` | nano's a_self_update_in bit — real, added `#650` |
| `dynamic_route_en` | `[28]` | enables `nano_gate_v4.v`'s own real comparator-driven routing — real, added `#650` |
| `pattern_low` | `[32:29]` | 4-bit routing pattern (dynamic routing) — real, added `#650` |
| `pattern_equal` | `[36:33]` | 4-bit routing pattern (dynamic routing) — real, added `#650` |
| `pattern_high` | `[40:37]` | 4-bit routing pattern (dynamic routing) — real, added `#650` |

Bit 41 remains real, spare headroom in this 42-bit budget. The five
`hold_in`-through-`a_self_update_in` fields and the four dynamic-
routing fields are the real, direct mechanism `#637`/`#638`'s own
proven bounded-loop-ring construction (and the LLVM IR frontend's real
loop compilation, `#652`/`#653`/`#661`) are built on.

**RAM** (`core_select=1`) — full 42 bits used:
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `fixed_mode` | `[8]` |
| `load_data_valid` | `[9]` |
| `init_data` | `[41:10]` (32-bit) |

**adder** (`core_select=2`) — only 8 of 42 bits used:
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |

**accumulator** (`core_select=3`):
| Field | Bits |
|---|---|
| `inc_dir` | `[3:0]` |
| `dec_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |

**comparator** (`core_select=4`):
| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `threshold` | `[39:8]` (32-bit, signed) |

**latch** (`core_select=5`):
| Field | Bits |
|---|---|
| `set_dir` | `[3:0]` |
| `clear_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |

All `*_mask`/`*_dir` fields use the one-hot convention confirmed
identical across every core that has one: **bit0=N, bit1=S, bit2=E,
bit3=W** (`ram_cell_v1.v`'s own comment, line 145-146). `icm_v3.py`
accepts either a raw int or a list like `["n", "e"]` for any of these.

## `addon_config[19:0]`

Identical across every core (the addons sit on the periphery,
core-independent — `unicell_super_v1.v` lines 337-349):

| Field | Bits |
|---|---|
| `nibble_mask` | `[7:0]` |
| `mask_en` | `[8]` |
| `shift_amt` | `[13:9]` |
| `shift_en` | `[14]` |
| `direction` | `[15]` |
| `lane_cut` | `[18:16]` |
| `invert_en` | `[19]` |

## Scope, stated honestly (matches `unicell_super_v1.v`'s own header)

**Updated 2026-09-07 (`#650` fired the trigger condition this section
originally named):** feedback (`fb_internal_in`/`a_reemit_in`/
`a_update_in`/`a_self_update_in`) and dynamic comparator-driven routing
(`dynamic_route_en`/`pattern_low`/`pattern_equal`/`pattern_high`) ARE
now real fields in the nano table above, added `points.md` #650 — the
real, direct mechanism the LLVM IR frontend's own loop compilation
(`#652`/`#653`/`#661`) needs and uses.

**Still genuinely out of scope, not yet added:** nano's own real
command-cell mode and the dedicated dynamic-reprogramming channel —
there is no field for either in the nano table above. Separately, and
more significantly: this entire ICM v3 format is scoped to the OLD
core lineage (`unicell_super_v1.v`-`v8.v`) only. The real, newer VIX
Carrier generation (`command_cell_v4.v`, `unicell_vix_carrier_v1.v`,
`points.md` #628-#666 — see `CORES_AND_WRAPPERS_REFERENCE.md`'s own
dedicated section) has NO portable, on-disk ICM format of its own yet;
it exists only in RTL simulation and the VM's own in-memory classes.
Widening this format (or building a genuinely new one) for that family
is real, separate, unstarted work, not attempted here.

## Record / file format

```json
{
  "format_version": "icm-v3",
  "cell_type": "unicell_super_v1",
  "name": "example_program",
  "description": "...",
  "records": [
    {
      "cell_id": "c0",
      "row": 0,
      "col": 0,
      "core": "adder",
      "core_config": {"downstream_mask": ["e"], "upstream_mask": ["n", "w"]},
      "addon_config": {},
      "super_latch_hex": "0x0000000000001282"
    }
  ],
  "record_hash": "<sha256 of canonical records>"
}
```

- `super_latch_hex` is computed, included for human inspection and as a
  redundant cross-check — `IcmV3File.load()` does NOT trust it; it
  re-derives the real latch from `core`/`core_config`/`addon_config`
  every time.
- `record_hash` IS trusted and checked on load — `IcmV3File.load()`
  raises `ValueError` if a loaded file's records don't hash to its own
  stated `record_hash`, catching hand-edited or corrupted files rather
  than silently loading them (same discipline v2's own `record_hash`
  established, canonicalized the same way: `sort_keys=True,
  separators=(",", ":")`, so the hash is reproducible across
  implementations, not just this one file's dict ordering).

## What's verified, and how

1. **16/16 real tests** (`tests/vm/test_icm_v3.py`), each checking a
   specific bit position against a value computed independently of
   `icm_v3.py`'s own field tables (plain shifts on literal bit numbers
   taken from the RTL comments), not merely re-asserting the module's
   own logic.
2. **Cross-checked against real, currently-passing RTL**, not just its
   header comment: `fpga/verilog/tb_unicell_super_v1.v` was compiled
   with `iverilog` against the actual `unicell_super_v1.v` and all 6
   real core modules, and re-confirmed passing (`PASS: unicell_super_v1
   -- core selection and isolation confirmed correct across all 6
   cores`). The exact 80-bit `SUPER_LATCH` hex words that testbench's
   own `pack()` function builds for every one of its 6 core-select test
   vectors (RAM/adder/accumulator/comparator/latch/nano) were then
   independently reconstructed via `icm_v3.encode_super_latch()` and
   diffed — **bit-for-bit identical in every case.** This is the
   strongest verification available short of a real Quartus/silicon
   run: the format encoder produces the exact same config word a
   simulator-proven testbench already produces by hand.

## Deliberately NOT built yet (per `current/START.md`'s own NEXT list)

- **VM dispatch** — actually running a grid of super cells from a
  loaded ICM v3 file (item 2). `nano/icm_v3.py` decodes a record back to
  a `core`/`core_config`/`addon_config` dict; nothing yet feeds that into
  a tick loop the way `nano/unicell_automaton_v1.py`'s `CAGrid` does for
  plain nano cells.
- **A compiler path** from a higher-level description down to real
  `core_config` bits (item 3) — today, `core_config` values are
  hand-specified per field, matching exactly what the RTL wants, with no
  higher-level authoring convenience on top.
- **Grid-level wiring validation** — nothing yet checks that a record's
  `downstream_mask`/`upstream_mask` (or nano's `routing_mask`/
  `cardinal_edge`) is *consistent* with its neighbors' `row`/`col` in the
  same file (e.g. a cell claiming `downstream_mask=["n"]` when there's no
  neighbor at `row-1` isn't currently flagged). Worth adding once real
  multi-cell programs are actually being authored, not before.
