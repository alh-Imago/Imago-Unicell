# System Mechanics — what's actually shared between the two cell lines

**Status: first document in the new `docs/` folder (started 2026-08-04,
per Alan: "the overview of the system mechanics and the logic that is
in both... the first place to start"). Everything below was verified
directly against the real RTL — `fpga/verilog/unicell64_v3.v` (FULL
cell) and `fpga/verilog/unicell_stripped_v1.v` (STRIPPED/nano cell) —
by direct grep/diff of both files, not from memory or from either
cell's own header comments taken at face value. Line numbers cited are
accurate as of this pass; re-verify if either file has changed since.**

## Why this document, and why now

The project runs on one dominant fork (`points.md` #107): the FULL cell
(the original "dream" architecture) and the STRIPPED cell (the "reality"
line, active since 2026-08-01, the one currently proven on real
silicon). Nearly all existing documentation (now under
`archeology/full-cell/docs/`) describes the FULL cell specifically. This
document instead asks a narrower, more useful question: setting aside
which line is "the" architecture, what mechanics do the two ACTUALLY
share, confirmed by reading both files side by side — not assumed
because they're "obviously" the same architecture, and not dismissed
because they're "obviously" different implementations.

## 1. The NOR-universal gate core — genuinely identical, gate for gate

This is the one piece with zero daylight between the two cells. Both
compute from the exact same 10-bit topology code, in the exact same
`cmd_latch` bit position, through byte-identical NOR-tree logic.

**Topology field position** — identical:
```
unicell64_v3.v:496:          wire [9:0] topology = cmd_latch[9:0];
unicell_stripped_v1.v:241:   wire [9:0] topology = cmd_latch[9:0];
```

**The NOR-tree itself** — identical, term for term:
```verilog
wire [31:0] g0 = ~(input_val  | input_val);    // NOT(A)
wire [31:0] g1 = ~(second_val | second_val);   // NOT(B)
wire [31:0] g2 = ~(g0 | g1);                   // AND(A,B)
wire [31:0] g3 = ~(g2 | g2);                   // NAND(A,B)
wire [31:0] g4 = ~(input_val  | second_val);   // NOR(A,B)
wire [31:0] g5 = ~(g4 | g4);                   // OR(A,B)
wire [31:0] g6 = ~(input_val  | g4);           // NOR(A, NOR(A,B))
wire [31:0] g7 = ~(second_val | g4);           // NOR(B, NOR(A,B))
wire [31:0] g8 = ~(g6 | g7);                   // XNOR(A,B)
wire [31:0] g9 = ~(g8 | g8);                   // XOR(A,B)
```
(`unicell64_v3.v` ~728-737, `unicell_stripped_v1.v` ~446-455.)

**The topology→gate decode table** — identical, all 12 codes:

| Code | Function | Code | Function |
|---|---|---|---|
| `10'h000` | PASS(A) | `10'h024` | OR(A,B) |
| `10'h02C` | PASS(B) | `10'h027` | NAND(A,B) |
| `10'h001` | NOT(A) | `10'h0BC` | XOR(A,B) |
| `10'h002` | NOT(B) | `10'h03C` | XNOR(A,B) |
| `10'h004` | NOR(A,B) | `10'h030` | ZERO |
| `10'h007` | AND(A,B) | `10'h0B0` | ONE |

Same codes, same functions, same fallback (unrecognized topology →
PASS(A)), in both files.

**What genuinely differs here:** only how `input_val`/`second_val`
(A and B) themselves get populated — see §3. The computation once you
have A and B is not an approximation of "the same," it is the same.

## 2. `cmd_latch` — the shared 128-bit config-time substrate

Both cells hold state in a `reg [127:0] cmd_latch`. Beyond the topology
field (§1), several more fields occupy the SAME bit positions in both —
a deliberate alignment, not a coincidence (confirmed by
`unicell_stripped_v1.v`'s own header comments citing this explicitly,
e.g. points.md #140: "SAME aligned bit positions").

| Field | Bits | FULL cell | STRIPPED cell |
|---|---|---|---|
| `topology` | `[9:0]` | wired, 10 bits | wired, 10 bits |
| `routing_mask` | `[69:64]` | wired, 6 bits (3D-ready) | wired, 6 bits (3D-ready) |
| `cardinal_edge` | `[75:70]` | wired, 6 bits | wired, 6 bits |
| `pattern_low` | `[81:76]` | wired, full 6 bits | same slot, only low 4 bits wired |
| `pattern_equal` | `[87:82]` | wired, full 6 bits | same slot, only low 4 bits wired |
| `pattern_high` | `[93:88]` | wired, full 6 bits | same slot, only low 4 bits wired |
| `dynamic_route_en` | `[94]` | wired | wired |

The pattern-field difference is real but narrow: both reserve the
identical 6-bit slot per field (3D-ready, for a future up/down axis);
the STRIPPED cell currently only wires the low 4 bits of each (N/S/E/W)
— confirmed this is deliberate, not a mismatch, by checking the actual
bit ranges rather than trusting either file's comments at face value.

**What this buys, concretely:** a routing_mask, cardinal_edge, or
comparator-pattern value computed or hand-written for one cell type
reads correctly as the same semantic value on the other, provided only
the low 4 bits are populated. `unicell_stripped_v1.v`'s own header
notes this was tested directly: "One ICM value works unmodified on both
cell types."

**Where the two `cmd_latch` layouts diverge, stated plainly:** beyond
these shared slots, each cell claims large stretches of the remaining
bits for entirely its own purposes — the FULL cell's addressing/auth
fields (`input_address`, `output_address`, `auth_mask`, `config_match`),
the STRIPPED cell's `ready`/`out_buffer`/programming-mechanism bits.
Neither cell's full field map should be assumed to apply to the other
outside the table above.

## 3. Two-arrival firing — shared PRINCIPLE, different MECHANISM

Both cells operate on the same conceptual model: a cell captures a
first arriving value, and a second arrival triggers the actual gate
computation and fire — causality comes from when values physically
arrive, not from a global clock sequencer stepping through instructions.
This "topology is computation, wire delay is causality" idea is the
architecture's own stated foundation and genuinely holds in both.

**But the two cells implement "arrival" completely differently, and
that difference is real, not cosmetic:**
- **FULL cell:** arrival is an address-matched event on a shared bus —
  `bus_hit = !frozen && start_flag && output_set && bus_valid_r &&
  !cmd_valid && addr_match` (`unicell64_v3.v` ~832). Multiple cells can
  share the same physical bus; a wired-OR reduction happens naturally
  when several cells targeting the same address fire the same cycle
  (points.md #32).
- **STRIPPED cell:** arrival is a dedicated point-to-point signal per
  cardinal direction (`arrived_n/s/e/w`), no address matching, no shared
  bus at all — this was a deliberate architectural departure (#107's
  fork rationale: the FULL cell's shared-bus contention was the reason
  behind its 25-cell/zone cap). The STRIPPED cell recreates the wired-OR
  bus's free N-way-combine property on genuinely separate wires instead
  (`points.md` #153), specifically because it does NOT have a shared bus
  to get that property from for free the way the FULL cell does.

**Do not assume a bus-contention argument that applies to one cell
applies to the other** — this is precisely the axis they were designed
to differ on.

## 4. Freeze — shared PRINCIPLE, different MECHANISM

Both cells have a concept of a frozen cell not capturing or firing.
Also genuinely shared in principle, genuinely different in plumbing:

- **FULL cell:** `frozen` is an internal `reg`, set by an opcode
  (`CMD_FREEZE`) during command processing (`unicell64_v3.v` line 491
  declares it, line 1205 is one of several opcode-driven set points) —
  config-time/command-driven, not a live external control line.
- **STRIPPED cell:** `freeze_in` is a genuine live external wire, fed
  continuously by whatever's driving it (the wrapper's persistent
  `SET_CTRL`/`CLR_CTRL` latch, in every grid-scale build so far) —
  `effective_freeze = freeze_in || error_frozen || !armed`
  (`unicell_stripped_v1.v`, points.md #154/#156) folds in two more
  STRIPPED-cell-only conditions that have no FULL-cell equivalent at all
  (see §5).

## 5. What is explicitly NOT shared — to prevent false generalization

Checked directly, not assumed:

- **`ready`/`pending_ack` backpressure** (`unicell_stripped_v1.v`,
  points.md #89/#90) — grepped for `ready`/`pending_ack` in
  `unicell64_v3.v`: no match beyond unrelated field-map comments. The
  FULL cell has no per-cell ready/ack handshake at all; its bus model
  doesn't need one the same way. STRIPPED-cell-only.
- **The `armed` gate** (points.md #156) — inspired by and modeled
  directly on the FULL cell's `start_flag`/`CMD_RELEASE` concept, but
  currently exists ONLY on the STRIPPED cell, scoped specifically to its
  own incremental ID-tagged programming path. The FULL cell's
  `start_flag` is a real, separate, older mechanism (`unicell64_v3.v`
  #83/#449/#621-940) — related in spirit, not the same signal, not
  cross-wired.
- **Addressing entirely** — `input_address`, `output_address`,
  `auth_mask`, `config_match`, the whole address-matched command-bus
  decode is, per `unicell_stripped_v1.v`'s own header, "DELIBERATELY
  ABSENT, NOT MERELY DISABLED" from the STRIPPED cell. Its boot config
  path (`cfg_valid`/`cfg_data`, a plain synchronous load) has no FULL-
  cell equivalent either — the FULL cell configures via its addressed
  command bus, always.
- **The programming/command mechanisms themselves** — the STRIPPED
  cell's variable-length ID-tagged `program_in`/`PROG_ID_*` scheme
  (points.md #140) and its `cell_command_v1`/`cell_wrapper_v2` companion
  modules have no direct FULL-cell counterpart; the FULL cell's own
  command-cell concept (`cmd_latch[10]`, `COMMAND_EMIT`) inspired one
  piece of the STRIPPED cell (points.md #143) but the delivery mechanism
  around it is entirely different.

## What this document is not

Not a replacement for either cell's own docs (`archeology/full-cell/
docs/` for the FULL cell; the STRIPPED cell still has none written, see
`archeology/stripped-cell/docs/README.md`). Not exhaustive — it covers
what was checked in this pass (gate computation, `cmd_latch` field
alignment, firing model, freeze). Other candidate shared mechanics
(command-emit cells, the branch/comparator mechanism ported in points.md
#140, out_buffer conventions) have not been cross-checked yet and should
not be assumed shared or assumed different without the same direct-diff
treatment given here.
