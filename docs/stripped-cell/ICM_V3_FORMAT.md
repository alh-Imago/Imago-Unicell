# ICM v3 Format — the super cell's own program format

*Implemented and verified 2026-08-16; brought up to date 2026-10-06 (ledger
#986): ten cores, the fine shift, the second-output flags, `min_bit_width`
and the per-target capability table. Implementation: `nano/icm_v3.py`.
Tests: `tests/vm/test_icm_v3.py` (31 tests) and
`tests/test_icm_min_bit_width_v1.py`. The original verification: Cross-checked bit-for-bit
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

Matches `unicell_super_v1.v`'s header (lines 17-43), plus the fine
shift added at #683/#684:

| Bits | Field | Width |
|---|---|---|
| `[4:0]` | `core_select` | 5 |
| `[46:5]` | `core_config` | 42 (union, reinterpreted per core) |
| `[66:47]` | `addon_config` | 20 |
| `[68:67]` | `shift_fine` | 2 (#683/#684; a separate range because `[66:47]` was fully allocated) |
| `[79:69]` | reserved | 11 |

`shift_fine` is packed and unpacked as if it were one more
`addon_config` key, so callers see a single add-on dict
(`encode_super_latch()` / `decode_super_latch()`).

`core_select` values 0-9 are assigned. Values 10-31 are future headroom
(#317). The RTL's output mux treats an unassigned value as inert (all
outputs zero, not X), and `icm_v3.decode_super_latch()` mirrors that by
returning `{"core": "reserved_N", "core_config": {"_raw": ...}}` rather
than raising.

| `core_select` | core | first RTL shell with it |
|---|---|---|
| 0 | `nano` | v1 |
| 1 | `ram` | v1 |
| 2 | `adder` | v1 |
| 3 | `accumulator` | v1 |
| 4 | `comparator` | v1 |
| 5 | `latch` | v1 |
| 6 | `sequencer` | v2 (#609) |
| 7 | `branch` | v3 (#542) |
| 8 | `mul` | VM core since #757; table added #823 |
| 9 | `priority` | VM core since #751; table added #823 |

A saved file's `cell_type` is derived, not declared: the minimum shell
that can run every core in it (`minimum_shell_version()`, so
`unicell_super_v3` when a `branch` is used).

## Per-core `core_config` field tables

These are transcribed from `nano/icm_v3.py`'s `CORE_FIELD_TABLES` (the
code is authoritative). Each was originally taken from that core's own
`.v` header (`cfg_data[N:0] field map`) and checked against the RTL
logic. Bit numbers are **within that core's own share** of
`core_config`. Bit 0 here is `core_config` bit 0, which is
`super_latch` bit 5.

All `*_mask` and `*_dir` fields use the one-hot convention used by every
core: **bit0=N, bit1=S, bit2=E, bit3=W**. `icm_v3.py` accepts either a
raw int or a list like `["n", "e"]` for any of them.

**nano** (0). Only a subset of nano's 128-bit `cfg_data` is reachable
through the super cell:

| Field | Bits | Notes |
|---|---|---|
| `topology` | `[9:0]` | the gate selection |
| `ready` | `[10]` | |
| `routing_mask` | `[16:11]` | 6-bit, 3D-ready |
| `cardinal_edge` | `[22:17]` | 6-bit |
| `hold_in` | `[23]` | #650 |
| `fb_internal_in` | `[24]` | #650 |
| `a_reemit_in` | `[25]` | #650 |
| `a_update_in` | `[26]` | #650 |
| `a_self_update_in` | `[27]` | #650 |
| `dynamic_route_en` | `[28]` | comparator-driven routing (`nano_gate_v4.v`), #650 |
| `pattern_low` / `pattern_equal` / `pattern_high` | `[32:29]` / `[36:33]` / `[40:37]` | 4-bit routing patterns, #650 |

Bit 41 is spare. The feedback and dynamic-routing fields are what the
bounded loop ring (#637/#638) and the LLVM frontend's loop compilation
(#652/#653/#661) are built on. **RTL caveat (#879/#880):** the
carrier's first RTL build ties `hold_in`/`a_reemit_in` and their
siblings to inactive defaults. Designs that rely on them run in the
VM; in RTL they need the standalone `nano_gate_v4` or a carrier
extension.

**ram** (1):

| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `fixed_mode` | `[8]` |
| `load_data_valid` | `[9]` |
| `init_data` | `[41:10]` (32-bit) |

**adder** (2):

| Field | Bits | Notes |
|---|---|---|
| `downstream_mask` | `[3:0]` | |
| `upstream_mask` | `[7:4]` | |
| `subtract_mode` | `[8]` | |
| `second_output` | `[12]` | also deliver the carry (0/1 word; subtract = NOT-borrow) as a second word. Alias `carry_mode`. #976/#980 |
| `second_downstream_mask` | `[16:13]` | faces the second word leaves by; empty = same as `downstream_mask`. #981 |

**accumulator** (3):

| Field | Bits |
|---|---|
| `inc_dir` | `[3:0]` |
| `dec_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |
| `step_amount` | `[19:12]` (8-bit) |
| `pulse_mode` | `[20]` |
| `threshold` | `[36:21]` (16-bit) |

**comparator** (4). It gives a result bit only (signed `>= threshold`,
0 or 1) and has no value pass-through. That is a ruling (#978): value
pass-through is the branch's job, or a ram fan-out beside the
comparator.

| Field | Bits |
|---|---|
| `downstream_mask` | `[3:0]` |
| `upstream_mask` | `[7:4]` |
| `threshold` | `[39:8]` (32-bit, signed) |

The std VM loads the threshold as the raw unsigned field, so a negative
threshold behaves differently there than in either RTL family (#947,
not patched; the compiler never emits one). At a width other than 32,
FlexGrid wraps it to a W-bit signed register (#972).

**latch** (5):

| Field | Bits |
|---|---|
| `set_dir` | `[3:0]` |
| `clear_dir` | `[7:4]` |
| `downstream_mask` | `[11:8]` |
| `toggle_dir` | `[15:12]` |

**sequencer** (6). The field names are uppercase because the RTL's own
comment uses them (#609). It has no upstream field (nothing to capture):

| Field | Bits |
|---|---|
| `VALUE_0` … `VALUE_3` | `[7:0]`, `[15:8]`, `[23:16]`, `[31:24]` (8-bit each) |
| `SEQUENCE_LEN` | `[33:32]` |
| `downstream_mask` | `[37:34]` |

**branch** (7). It uses all 42 bits:

| Field | Bits |
|---|---|
| `upstream_dir` | `[1:0]` (an int code, not a mask) |
| `value_source_low` / `_equal` / `_high` | `[2]` / `[3]` / `[4]` |
| `fixed_value_low` / `_equal` / `_high` | `[11:5]` / `[18:12]` / `[25:19]` (7-bit each) |
| `emit_low` / `_equal` / `_high` | `[26]` / `[27]` / `[28]` |
| `route_low` / `_equal` / `_high` | `[32:29]` / `[36:33]` / `[40:37]` |
| `rolling_mode` | `[41]` |

**mul** (8):

| Field | Bits | Notes |
|---|---|---|
| `downstream_mask` | `[3:0]` | |
| `upstream_mask` | `[7:4]` | |
| `second_output` | `[12]` | also deliver the high half of the 2W product. Alias `wide_mode` (#853/#854, #980) |
| `second_downstream_mask` | `[16:13]` | faces the high word leaves by; empty = same as `downstream_mask`. #981 |

**priority** (9). The ranks are 2 bits each (#814). The width of
`scheduling_mode` is a generous 2 bits, not a hardware-confirmed width:

| Field | Bits |
|---|---|
| `upstream_mask` | `[3:0]` |
| `downstream_mask` | `[7:4]` |
| `priority_rank_n` / `_s` / `_e` / `_w` | `[9:8]` / `[11:10]` / `[13:12]` / `[15:14]` |
| `scheduling_mode` | `[17:16]` (0 strict, 1 weighted round-robin, 2 sequenced channel) |

Mode 2 exists only in the VM. No RTL implements it, and a saved file
does not record its turn order (#926/#927). The sub/flex compile path
(`tools/flexsub_compile_v1.py`) rewrites it to strict mode 0 with
explicit ranks (#929/#930).

## `addon_config[19:0]` (plus `shift_fine`)

These fields are identical across every core. The add-ons sit on the
periphery and do not depend on the core (`unicell_super_v1.v` lines
337-349):

| Field | Bits |
|---|---|
| `nibble_mask` | `[7:0]` |
| `mask_en` | `[8]` |
| `shift_amt` | `[13:9]` (5-bit) |
| `shift_en` | `[14]` |
| `direction` | `[15]` |
| `lane_cut` | `[18:16]` |
| `invert_en` | `[19]` |
| `shift_fine` | latch `[68:67]` (2-bit; see above) |

The VM applies them in the order nibble mask → fine shift → coarse
lane shift and `lane_cut` → invert. It applies them to every core's
offered value except the nano's.

**One shift number, interpreted by the target (#985/#986).** The ICM
carries one amount (`shift_amt`, with `shift_fine` as part of how it
is programmed) and a direction:

| target | what it can make |
|---|---|
| std (the VM's original cells) | coarse taps, plus fine 0-3 |
| flex / nano | **any** amount 0-31. The flex shift is plain wiring; coarse + fine are just how the total is written. `lane_cut` with a non-tap amount is refused. |
| sub | coarse taps only, no fine |

Any other amount would silently do nothing in that target's VM or RTL,
so `target_capabilities_v1.check_records` refuses it when a target is
named. At W = 36 the 5-bit field cannot express amounts above 31 (open).

**The mask at other widths (#968).** There are always 8 mask bits. Each
covers `ceil(W/8)` data bits: 4 bits per mask bit at W = 32 (the
original nibble), 3 at W = 24, 5 at W = 40. Below 32, the same mask
value therefore means different bits at different widths. This was
accepted.

## Target-agnostic flags and the capability table

The ICM never names a target. It states what a design **needs**, and
each target either meets it or refuses:

- `second_output` / `second_downstream_mask` (above). The compiler sets
  `second_output` only when a program needs both results; the default
  is off (#977/#979). A design or user may force it with
  `place(..., params={"second_output": 1})`. Giving an alias and the
  canonical name with different values is an error. The key is stored
  canonically, so a file that used `wide_mode` hashes differently after
  a round-trip (#980).
- `nano/target_capabilities_v1.py` says which targets can meet each
  need. When a target is passed to the compiler
  (`compile_dag(..., target=)`, `compile_program_ir_vix(..., target=)`),
  it refuses at compile time; with no target, the ICM is produced
  unchanged (#981/#986).

| need | std | flex | sub |
|---|---|---|---|
| `second_output` | mul only (sequential, same faces) | adder, mul | — |
| `second_downstream_mask` | — | adder, mul | — |
| shift amount | coarse + fine | any 0-31 | coarse only |

The std VM (`SuperGrid`) refuses `second_output` on an adder and any
`second_downstream_mask`. `FlexGrid` accepts and mirrors both.

## Scope

- **Feedback and dynamic routing** are real fields in the nano table
  (#650).
- **Not covered:** nano's command-cell mode and the dedicated dynamic
  reprogramming channel have no field here. The VIX Carrier generation
  (`command_cell_v4.v`, `unicell_vix_carrier_v1.v`, #628-#666) is
  described by ICM-VIX (`ICM_VIX_FORMAT.md`), not by this 42-bit
  layout. Widening this layout is separate, unstarted work.

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
  "record_hash": "<sha256 of canonical records>",
  "min_bit_width": 18
}
```

- `min_bit_width` (#958/#959) is optional and written only when set.
  It is a requirement: "this design needs **at least** N bits" (1-64).
  When it is absent the width is 32, and every existing file
  serialises byte for byte as before. When present it is covered by
  `record_hash` (the hash gains a `|min_bit_width=N` suffix), so editing
  it by hand is caught on load. Values are always stored sign-extended
  in the ordinary 32-bit fields. Spare-bit sign encodings for a
  particular target are that target's own business, declared in the
  file when used, and not part of the ICM (#959). A consumer that builds
  32-bit designs accepts any declared minimum up to 32 and refuses a
  larger one; it never truncates. The flex/sub generators record
  `min_bit_width` and `built_width` in `ASSEMBLY.json`. The same flag
  exists in ICM v4 (top level) and ICM-VIX (inside `header`); see
  `nano/icm_width_v1.py`.

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

1. **The original 16 tests** (now 31, `tests/vm/test_icm_v3.py`), each checking a
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

## Since built, and still open

The three items this section originally listed as not built are now
done. **VM dispatch:** `SuperGrid` runs any loaded ICM v3 file, and
`FlexGrid` mirrors the flex family. **A compiler path:** the DSL, the
Python-AST frontend, and LLVM IR via `nano/llvm_cli_v1.py` or
`tools/flexsub_compile_v1.py`. **Wiring derived from masks plus grid
position:** `tools/flexsub_icm_netlist_v1.py` derives the real netlist
and refuses dangling or unheard faces.

Still open:

- A saved file does not record which cell is the program's result. The
  flex/sub compile path marks it with `io_name='result'`; stock
  `llvm_cli` files rely on sink inference (#940).
- The priority mode-2 turn order is not saved (#926). This is handled on
  sub/flex by #930's rank rewrite, not by a format change.
- An ICM way to name a second word's consumer from the DAG dispatcher
  (VIX `place` can already name it, #981), and an automatic trigger
  from the program graph (for example LLVM `uadd.with.overflow`).
- The loader's fit check for a `min_bit_width` below 32 (#959) waits
  for the first generator that builds narrower than 32.
