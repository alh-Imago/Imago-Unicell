# `.icm` File Format Specification

*Imago Cell Map — format_version: 2*

An `.icm` file is a portable, self-describing program for the Imago UniCell
architecture. The same file runs on the Python VM, any supported FPGA, and
future ASIC without modification.

---

## Structure

An `.icm` file is a JSON object. Fields appear in this order by convention:

```
header fields        — identity, metadata, target
port declarations    — inputs, outputs, input_types, output_types
model references     — models
cell records         — records
integrity            — record_hash
composer data        — composer_meta (optional, for round-trip editing)
```

---

## Minimal valid `.icm`

```json
{
  "format_version": 2,
  "address_width": 32,
  "name": "not_gate",
  "inputs":  {"a": 4096},
  "outputs": {"result": 4097},
  "models":  [],
  "records": [
    {"gs": 1, "in": 4096, "out": 4097, "init": null}
  ]
}
```

`gs: 1` = `GS_NOT`. `in`/`out` are bus addresses (decimal integers).

---

## All Fields

### Identity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format_version` | int | yes | Always `2` for current format. |
| `address_width` | int | yes | `32` for VM/Kintex-7. `16` for iCEBreaker (addresses truncated). |
| `program_id` | string | no | Unique identifier, e.g. `"notgate1"` |
| `name` | string | yes | Human-readable program name |
| `os_name` | string | no | Authoring tool (`"Claudette"`) |
| `os_version` | string | no | Tool version |
| `created_at` | float | no | Unix timestamp of creation |
| `description` | string | no | Human-readable description |
| `author` | string | no | Author name |
| `tags` | array of string | no | Classification tags |

### Target

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | string | no | FPGA target: `"vm"`, `"icebreaker"`, `"kintex7"`. Absent = no specific target. |
| `cell_budget` | int or null | no | Cell count limit for the target. `null` = unlimited (VM). |
| `vm_only` | bool | no | `true` = design exceeds target budget or contains VM-only models. |

### Port Declarations

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inputs` | object | recommended | `{name: bus_address}` — named input ports. |
| `outputs` | object | recommended | `{name: bus_address}` — named output ports. |
| `input_types` | object or null | no | `{name: type_name}` — type for each input. |
| `output_types` | object or null | no | `{name: type_name}` — type for each output. |
| `inputs_32` | object or null | no | `{name: [addr0..addr31]}` — full 32 bit-addresses for int32 inputs, LSB first. |
| `outputs_32` | array or null | no | `[addr0..addr31]` — 32 output bit-addresses for int32 result, LSB first. |

**Type names:** `"numeric"` · `"signed"` · `"alpha"` · `"datetime"`

### Cell Records

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `records` | array of object | yes | Ordered list of cell configurations. |

Each record object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `gs` | int | yes | `gate_state` — 32-bit cell configuration word (decimal). |
| `in` | int | yes | `input_address` — bus address the cell listens on. |
| `out` | int | yes | `output_address` — bus address the cell writes to. |
| `init` | int or null | no | Initial value pre-loaded into `a_data` at load time. Used for NOT cells (`0xFFFFFFFF`) and preloaded comparators. `null` if not applicable. |

> **Retired fields** (format_version < 2, ignored by current loader):
> `inB` (input_b_address), `alt` (alternate output), `stor` (storage flag).
> These are silently ignored when present. Do not emit in new files.

### Integrity

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `record_hash` | string | no | SHA-256 hex digest of the canonical record list. |
| `security_context` | object or null | no | Reserved. Always `null`. |

### Composer Round-Trip

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `composer_meta` | object | no | Opaque blob for Composer round-trip editing. Ignored by VM/FPGA loader. |

---

## `gate_state` Reference

The `gs` field is a 32-bit integer encoding topology + mode flags + system flags.

### Topology (bits 0–9, `gs & 0x3FF`)

Selects the NOR-gate tree configuration (which of the 9 internal NOR gates are active):

| Value (hex) | Constant | Function |
|-------------|----------|----------|
| `0x000` | `GS_PASS` | Wire / pass-through (output = B) |
| `0x001` | `GS_NOT` | NOT(A) — use with `init=0xFFFFFFFF` |
| `0x002` | `GS_NOT_B` | NOT(B) |
| `0x004` | `GS_NOR` | NOR(A, B) |
| `0x007` | `GS_AND` | AND(A, B) |
| `0x024` | `GS_OR` | OR(A, B) |
| `0x027` | `GS_NAND` | NAND(A, B) |
| `0x02C` | `GS_PASS_B` | Pass B (relay cell pattern) |
| `0x030` | `GS_ZERO` | Output constant 0 |
| `0x03C` | `GS_XNOR` | XNOR(A, B) |
| `0x0B0` | `GS_ONE` | Output constant 0xFFFFFFFF |
| `0x0BC` | `GS_XOR` | XOR(A, B) |

### Mode Flags (bits 10–25)

| Bit | Value (hex) | Constant | Description |
|-----|-------------|----------|-------------|
| 10 | `0x00000400` | `GS_EDGE_MODE` | Fire on 0→1 data transition (edge trigger) |
| 25 | `0x02000000` | `GS_LATCH_IN` | Latch mode: `a_arrived` stays set after fire. Single arrival fires. Used for: relay cells (`GS_PASS_B \| GS_LATCH_IN`), NOT cells, sentry cells. |

### System Flags (bits 23–24)

| Bits | Value (hex) | Constant | Description |
|------|-------------|----------|-------------|
| 23–24 = `00` | `0x00000000` | `GS_DTYPE_NUMERIC` | Cell output is numeric (default) |
| 23–24 = `01` | `0x00800000` | `GS_DTYPE_SIGNED` | Cell output is signed integer |
| 23–24 = `10` | `0x01000000` | `GS_DTYPE_ALPHA` | Cell output is character data |
| 23–24 = `11` | `0x01800000` | `GS_DTYPE_DATETIME` | Cell output is timestamp |

### Control Flags (bits 26–31)

| Bit | Value (hex) | Constant | Description |
|-----|-------------|----------|-------------|
| 26 | `0x04000000` | `GS_OUT_POSEDGE` | Output releases on rising edge |
| 27 | `0x06000000` | `GS_OUT_NEGEDGE` | Output releases on falling edge |
| 28 | `0x08000000` | `GS_PRIORITY` | Priority cell (Ward scheduling) |
| 29 | `0x10000000` | `GS_TRACE` | Trace all firings to debug log |
| 30 | `0x20000000` | `GS_BREAKPOINT` | Halt array on fire (debug) |
| 31 | `0x40000000` | `GS_ONE_SHOT` | Fire once then disarm (self-clearing) |
| 32 | `0x80000000` | `GS_LOOP_BACK` | Feed output back to own input each tick |

### Common Combinations

| Value (hex) | Pattern | Use case |
|-------------|---------|----------|
| `0x00000001` + `init=0xFFFFFFFF` | NOT with preloaded A | Standard NOT cell |
| `0x0000002C \| 0x02000000` = `0x0200002C` | `GS_PASS_B \| GS_LATCH_IN` | Relay cell (routes B to A-side of downstream cell) |
| `0x0000003C \| 0x02000000` = `0x0200003C` | `GS_XNOR \| GS_LATCH_IN` | BranchPoint comparator cell |
| `0x00000007` | `GS_AND` | AND in preloaded-A pattern |
| `0x00000024` | `GS_OR` | OR in preloaded-A pattern |
| `0x000000BC` | `GS_XOR` | XOR in preloaded-A pattern |
| `0x40000000` | `GS_ONE_SHOT` | One-shot AND/OR in reduction tree |
| `0x80000000` | `GS_LOOP_BACK` | Feedback/counter cell |
| `0x82000000` | `GS_LOOP_BACK \| GS_LATCH_IN` | Counter cell |

Full reference: [gate_states.py](../gate_states.py)

---

## Two-Arrival Model

Each cell operates on **two sequential arrivals** at its `input_address`:

1. **First arrival** → stored in `a_data`, `a_arrived` set. No output.
2. **Second arrival** → gate fires: `result = gate_tree(a_data, arrival_value)`. Output emitted.

**`GS_LATCH_IN`** overrides this: `a_arrived` stays set after fire, so every subsequent arrival fires immediately (single-arrival mode). Used for relay cells, NOT cells, and sentry cells.

**Preloaded-A pattern**: `init` field pre-loads `a_data` at load time, setting `a_arrived=True` before execution. The cell then fires on the first arrival of B. This is the standard pattern for all binary-op cells (AND, OR, XOR, XNOR etc.) in compiled tiles.

---

## Version History

| Version | Changes |
|---------|---------|
| 1 | Original format. `inB`, `alt`, `stor` fields in records. |
| 2 | `inB`/`alt`/`stor` retired. `init` added. `format_version` and `address_width` required. Two-arrival model documented. `GS_LATCH_IN`, `GS_ONE_SHOT`, `GS_LOOP_BACK`, `GS_EDGE_MODE` added. |
