# FULL cell — Internal Structure & Register Model

**Ground truth: `fpga/verilog/unicell64_v3.v` (1,479 lines, Protocol
v3.1). Built 2026-08-04 by reading the RTL directly — specifically the
file's OWN later "verified current" comment blocks, not its own header,
which explicitly documents having drifted stale once already (see the
warning below). If this doc and the Verilog disagree, the Verilog
wins — and specifically, the LOGIC wins over any comment, including
this one.**

For what this cell shares with the STRIPPED/nano cell (gate computation,
several `cmd_latch` field slot positions), see `../shared/
SYSTEM_MECHANICS.md` — not repeated here. This document covers what's
specific to the FULL cell: addressing, auth, the two-state boot/run
model, and its own much larger opcode set.

## A real trap in this file, worth knowing before reading it yourself

`unicell64_v3.v`'s own header (top of file) contains a `cmd_latch`
field-map summary that is **known stale** — it still shows `auth_mask`
at `[18:11]`, a position it was relocated OUT of. The file's own later
comment block (~line 417) says so directly: *"This summary block must
be updated in the SAME commit as any change to a cmd_latch field... This
block drifted out of date once already... caught only when someone
asked 'how full is the lower 32' and had to re-derive the true answer
from the individual field declarations."* The AUTHORITATIVE block is
the one explicitly marked "verified current" (~line 422 onward) plus
the actual `wire` declarations that follow it — this doc was built from
those, not the header. Anyone reading the RTL fresh should do the same.

## Why this cell exists, and its relationship to the STRIPPED cell

This is the original "dream" architecture (`points.md` #107's fork) —
an addressed, shared wired-OR bus, full auth/security model, and a much
richer opcode set than the STRIPPED cell's deliberately minimal design.
The STRIPPED cell exists specifically because this cell's shared-bus
contention was measured to cap it at roughly 25 cells/zone in practice —
the STRIPPED line asks what's possible with no shared bus at all.
Untouched since 2026-07-31; not currently under active development, but
not abandoned — Alan has indicated (2026-08-04) it will be revisited to
carry back discoveries made on the STRIPPED cell (the routing
self-consistency approach from `points.md` #155, the armed/`COMPLETE`-
LSB convention from #156, which was itself inspired by this cell's own
`start_flag`/`CMD_RELEASE`).

## Two-state boot/run model

- **BOOT state** (`physical_mode=1`, the reset default): the cell
  exposes its baked-in `CELL_ID` on the address bus. A boot controller
  finds the cell by `CELL_ID`, sends the logical address + `auth_mask`
  in one transaction, then `CMD_BOOT_COMMIT` flips the cell to RUN state
  permanently (`physical_mode` clears and stays cleared).
- **RUN state**: two genuinely separate address match paths (verified
  at RTL lines 826-827):
  - `addr_match = (bus_addr_r == input_address)` — the MUTABLE LISTEN
    point. Freely re-pointable at runtime; this is NOT identity.
  - `config_match = (bus_addr_r == CELL_ID[15:0])` — the PERMANENT
    IDENTITY. ALL config/reconfigure targets the cell by `CELL_ID`,
    never by the current listen address.

This addressing model — mutable listen point vs. permanent identity,
both auth-gated — has no equivalent on the STRIPPED cell at all, which
has neither address concept (per its own header: "DELIBERATELY ABSENT,
NOT MERELY DISABLED").

## `cmd_latch` — 128 bits, current verified field usage

### Topology latch, `cmd_latch[31:0]`

| Bits | Name | Notes |
|---|---|---|
| `[9:0]` | `topology` | shared with STRIPPED cell, see `SYSTEM_MECHANICS.md` |
| `[10]` | `is_command_cell` (`command_cell`) | shared bit position with STRIPPED cell's own command-emit concept |
| `[12:11]` | `cell_mode` | reserved/placeholder, relocated here from the routing latch, not yet wired to any behavior |
| `[19:13]` | free | 7 bits genuinely open |
| `[20]` | `latch_A_dis` | disable A-latch store — live value flows through as PASS(B) |
| `[21]` | `latch_B_dis` | disable B-arrival trigger — documented but confirmed NOT wired into any firing condition anywhere in this file (dead field, kept for field-map fidelity) |
| `[22]` | `start_flag` | armed — set by `CMD_RELEASE`. The concept #156 on the STRIPPED cell was directly modeled on. |
| `[24:23]` | `dtype` | NUMERIC/SIGNED/ALPHA/DATETIME — stored, not yet interpreted anywhere |
| `[25]` | `invert_out` | applied at the output/drain stage only |
| `[26]` | `latch_in` | single-arrival re-fire mode, also updates the held value on each new arrival |
| `[27]` | `priority` | high-priority scheduling — inert without a real scheduler |
| `[28]` | `trace` | log every fire — inert without tracing infrastructure |
| `[29]` | `breakpoint` | halt array on fire — inert without that infrastructure |
| `[30]` | `one_shot` | fires once, then `start_flag` clears permanently |
| `[31]` | `loop_back` | feeds `computed_output` back as the next A input |

### Methodology latch, `cmd_latch[63:32]`

| Bits | Name | Notes |
|---|---|---|
| `[39:32]` | `m_nibble_mask` | per-nibble BLOCK(1)/PASS(0) on the input operand |
| `[40]` | `m_mask_en` | |
| `[46:41]` | `m_shift_amt` | |
| `[47]` | `m_in_shift_en` | shift `bus_data` left before the gate |
| `[48]` | `m_out_shift_en` | shift `computed_output` right on emit |
| `[51:49]` | `m_lane_cut` | 3 bits, cut bits at the 3 inter-byte boundaries (bit8/16/24) |
| `[63:53]` | `auth_mask` | **11-bit, current/authoritative location** — NOT `[18:11]`, see the trap note above |

### Routing latch, `cmd_latch[95:64]` (added `points.md` #49/#51)

Identical slot positions to the STRIPPED cell's own routing latch (see
`SYSTEM_MECHANICS.md` §2) — `routing_mask[69:64]`, `cardinal_edge[75:70]`
(here, per-OUTGOING direction — the STRIPPED cell reinterprets the same
slot per-INCOMING, a genuine difference, not a documentation error on
either side), `pattern_low[81:76]`, `pattern_equal[87:82]`,
`pattern_high[93:88]`, `dynamic_route_en[94]`. This cell wires the full
6 bits of each pattern slot; the STRIPPED cell wires only the low 4.

`cmd_latch[127:96]` is genuinely free, unclaimed as of this writing.

## Command-emit cells

A cell with `is_command_cell` set (`cmd_latch[10]`) drives its stored
command word onto the COMMAND bus (targeted by `output_address`) on
fire, instead of a gate result onto the data bus — the mechanism that
lets the fabric command itself (Shore and the tile system are built
from cells; without this, nothing in-fabric could issue a command). The
cell stays "dumb" — it holds no program flow; the command content is
assembled as ordinary data upstream, and ordering comes from fabric
topology, not any cell's own intelligence. Same bit position
(`cmd_latch[10]`) as the STRIPPED cell's own re-emit concept — the
STRIPPED cell's version (`points.md` #143) was explicitly modeled on
this one.

## Comparator / dynamic routing

Pure combinational, no stored state: `cmp_gt = (bus_data_r > a_data)`,
`cmp_lt = (bus_data_r < a_data)` (equal is implicit — neither). Selects
one of the three stored patterns as "wanted" for this fire.
`dynamic_route_en=0` (default) preserves the pre-#49 static behavior
exactly (`effective_routing = routing_mask`); `1` makes routing
genuinely data-dependent, per fire. This is the mechanism `points.md`
#140 ported to the STRIPPED cell, with the same comparator convention.

## Opcode set (256 possible, well under 256 actually defined)

Far larger than the STRIPPED cell's 8-code ID-tagged scheme. Categories,
not an exhaustive list (see the RTL's own `localparam CMD_*`/`METH_*`
declarations, ~lines 276-410, for the authoritative current set):

- **Addressing/config**: `CMD_SET_INPUT_ADDR`(2), `CMD_SET_OUTPUT_ADDR`(3),
  `CMD_RECONFIGURE`(4) (loads a full `cmd_latch` word, auth-gated),
  `CMD_BOOT_COMMIT`(7) (BOOT-state only: sets logical addr + `auth_mask`,
  transitions to RUN), `CMD_ARRAY_RESET`(8) (system-wide auth hard
  reset, all cells back to BOOT state).
- **Freeze/release**: `CMD_FREEZE`(5)/`CMD_RELEASE`(6) — BROADCAST,
  `auth_ok`-gated only (disarms/arms EVERY cell, a real limitation
  flagged in the RTL's own comment); `CMD_FREEZE_AT`(39)/
  `CMD_RELEASE_AT`(40) — TARGETED, `config_match`-gated, single-cell.
- **Targeted reconfigure**: `CMD_LOAD_AT`(23) (`addr_match`-gated,
  per-cell heterogeneous config, auth-verified), `CMD_LOAD_DONE`(27)
  (programming-cycle-3 completion marker, `config_match`+auth gated).
- **Routing latch**: `CMD_SET_ROUTE_LATCH`(37) (whole latch, one word),
  `CMD_SET_ROUTE_LATCH_AT`(38) (targeted single-cell version).
- **Methodology**: `CMD_SET_METHOD`(25) (the 64-bit two-slot four-state
  decoder), `METH_SET_MASK`(30), `METH_SET_LANE`(33), and others for
  shift/nibble-mask setup.
- **Topology presets**: `CMD_TOPO_*` (48-71), each preset pair COLD/
  (unnamed = armed) — e.g. `CMD_TOPO_NOR_COLD`(52)/`CMD_TOPO_NOR`(53) —
  "armed = opcode LSB," the exact convention `points.md` #156 named
  directly when building the STRIPPED cell's own armed gate.
- **Misc**: `CMD_PING`(9), `CMD_LATCH_IN_ON/OFF`(10/11), `CMD_MEM_CALL`(12),
  `CMD_REARM`(13), `CMD_SWAP_AB`(18), `CMD_CAPTURE_REARM`(19),
  `CMD_CLEAR_ARRIVED`(16), `CMD_RESET_CELL`(17).
- **Deprecated, kept for compatibility**: `CMD_SET_LOGICAL`(14) (use
  `CMD_BOOT_COMMIT`), `CMD_PRELOAD`(15)/`CMD_PRELOAD_HI`(22) (use
  `preload_sel` bits on the command bus instead).

## What this doc does not cover

Not a line-by-line catalog of all 1,479 lines or every opcode's exact
behavior — that level of detail lives in `points.md`'s own narrative
(the #40s-70s range covers most of this cell's real design history) and
in the RTL itself. This is the field-map/structural orientation a
newcomer needs before reading either. The array-level semantics (wired-
OR collision/composition, the four-role SENDER/TARGET/WATCHER/COUNTER
loader) are covered by `unicell_array_v3.py`'s own docstring and
`points.md`, not duplicated here.
