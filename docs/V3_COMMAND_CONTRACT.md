# UniCell v3 Command Contract (AUTHORITATIVE)

**Last verified against RTL: 2026-07-09, `fpga/verilog/unicell64_v3.v`.**
**Proven on silicon: Arria 10 GX660, transit smoke test, same date.**

> Any new bridge — DSP, PCIe, AXI, Avalon, or a host tool — **must derive its
> encodings from this document**, not from existing code. Several files in this
> repo still encode the OLD 8-bit auth scheme and will silently refuse every
> config command. See "Known-stale files" at the end.

---

## 1. The auth scheme — 11 bits

This is the single most common source of silent failure. A wrong token does not
error; the cell simply ignores every config command while still accepting
address-lane writes. Symptom: `input_addr` lands, but `topology`/`armed`/
`output_addr` stay zero.

| Field | Location | Width |
|---|---|---|
| `auth_token` | `cmd_bus[29:19]` | 11 bits |
| `auth_mask` (stored) | `cmd_latch[63:53]` | 11 bits |

```verilog
wire [10:0] auth_mask  = cmd_latch[63:53];
wire        auth_boot  = (auth_mask == 11'h0);      // boot state accepts anything
wire        auth_ok    = auth_boot || (auth_token == auth_mask);
wire [10:0] auth_token = cmd_bus[29:19];
```

**Auth is write-once, boot-only.** `CMD_BOOT_COMMIT` stores the mask as
`{3'b0, cmd_data[23:16]}` — i.e. the low 8 bits come from the boot word, the
upper 3 default to zero. After boot (`physical_mode == 0`) the auth mask can
never be rewritten. Opcodes may change a cell's *function*, never its *auth*.

### Deriving the config-word prefix

With the conventional boot token `0xA5`:

```
boot word:  0x00A5_0000   ->  stored auth_mask = 0x0A5
prefix:     0x0A5 << 19   =   0x0528_0000
```

So every auth-gated command word is `0x0528_00PP` where `PP` is the opcode.

---

## 2. Command reference

### Auth-gated (need `auth_ok`; prefix `0x0528....`)

| Opcode | Name | Word | Also needs `config_match`? |
|---|---|---|---|
| `0x02` | `CMD_SET_INPUT_ADDR` | `0x05280002` | **yes** |
| `0x03` | `CMD_SET_OUTPUT_ADDR` | `0x05280003` | **yes** |
| `0x04` | `CMD_RECONFIGURE` | `0x05280004` | no — `auth_ok` only |
| `0x08` | `CMD_ARRAY_RESET` | `0x05280008` | no — broadcast to all cells |
| `0x12` | `CMD_SWAP_AB` | `0x05280012` | **yes** |
| `0x17` | `CMD_LOAD_AT` | `0x05280017` | **yes** (via `addr_match`) |
| `0x22` | `METH_SET_ROUTING` | `0x05280022` | **yes** |
| `0x23` | `METH_SET_TRANSIT` | `0x05280023` | **yes** |

### Not auth-gated

| Opcode | Name | Word | Notes |
|---|---|---|---|
| `0x07` | `CMD_BOOT_COMMIT` | `0x00000007` | data `0x00A5_xxxx`; only acts while `physical_mode == 1` |
| `0x18` | `SET_TARGET` | `0x00000018` | handled in the **top level**, latches `load_target`; data = `CELL_ID` |
| `0x01` | `CMD_DATA_WRITE` (INJECT) | `0x00000001` | routed to the **cpu path**, not the command path |

---

## 3. The addressing invariant (guarded)

**Config targets `CELL_ID`. Injection targets `input_address`. They are different
comparators and must never be conflated.**

```verilog
wire config_match = (bus_addr_r == CELL_ID);       // config commands
wire addr_match   = (bus_addr_r == input_address); // data delivery
```

- `CELL_ID = (ZONE_ID << 5) + local_index` — the cell's permanent physical
  identity, baked at synthesis. **Not** writable.
- `input_address` — the mutable address the cell *listens* on. Defaults to
  `CELL_ID` at reset; set at boot from `cmd_data[15:0]`.

Therefore:
- `SET_TARGET` before an auth-gated config command must carry the **`CELL_ID`**.
- `INJECT` must carry the **`input_address`** in `cmd_data[31:16]`.

If you boot a cell with `input_address = CELL_ID` (e.g. both zero), the two
coincide and the distinction is invisible — which is why it is easy to get wrong.

---

## 4. Key payload encodings

### `CMD_RECONFIGURE` (`0x05280004`) — `cmd_data`

| Bits | Field |
|---|---|
| `[9:0]` | topology |
| `[10]` | `command_cell` flag |
| `[11]` | `start_flag` (arm) |
| `[17]` | **`latch_in`** |
| `[30:20]` | `auth_mask` — **boot-only**, ignored in RUN |

A `PASS_B` relay, armed, that fires on a single arrival:

```
topology 0x02C | start(1<<11) | latch_in(1<<17)  =  0x5282_082C
```

> **`latch_in` is required.** Without bit 17 the cell will not fire on an injected
> arrival. A word with `latch_in == 0` (`0x5280_082C`) looks correct and does
> nothing.

### `METH_SET_ROUTING` (`0x05280022`) — `cmd_data[3:0]`

`routing_mask` = **WHERE** the fire goes. Bitmask, **simultaneous multicast**:

| Bit | Direction |
|---|---|
| 0 | N |
| 1 | S |
| 2 | E |
| 3 | W |

East only → `cmd_data = 0x4`.

### `METH_SET_TRANSIT` (`0x05280023`) — `cmd_data[0]`

`transit_only` = **WHETHER** the local cluster is included.

| Value | Behaviour |
|---|---|
| `0` | data is *for here*: present on the local bus, **and** route across if `routing_mask` bits set |
| `1` | data is *only passing through*: route across per `routing_mask`, do **not** present locally |

### `CMD_DATA_WRITE` / INJECT (`0x00000001`)

Excluded from `cmd_valid` at the top level and routed to the cpu path:

```
cmd_data[31:16] = target address (must equal the cell's input_address)
cmd_data[15:0]  = value
```

---

## 5. Priming a cold cell

A `latch_in` cell needs a genuine two-arrival completion. Its first-ever value
will not fire it on its own.

1. `SET_TARGET` → `CELL_ID`
2. `CMD_SWAP_AB` (`0x05280012`) — sets `a_arrived` (loads `a_data` from `cmd_data[12:0]`)
3. `INJECT` — the second arrival; the cell fires

> `preload_sel` (formerly `cmd_bus[18:17]`) has been **removed from the RTL**. Any
> code using a preload word is a no-op. Use `CMD_SWAP_AB`.

---

## 6. Resetting

`CMD_ARRAY_RESET` (`0x05280008`) is broadcast and auth-gated. It reverts **every**
cell to boot state: `physical_mode <= 1`, `input_address`/`output_address` back to
`CELL_ID` identity, `cmd_latch`/`frozen`/`a_arrived`/`one_shot_fired` cleared.

This is the JTAG-accessible equivalent of a reflash and the correct way to clear
stale state between runs.

> `CMD_BOOT_COMMIT` only sets `input_address` while `physical_mode == 1`. A cell
> already committed to RUN **ignores** a new boot. Without `CMD_ARRAY_RESET` first,
> a fresh boot silently does nothing and the cell keeps its old listen address.

---

## 7. A known-good sequence (silicon-proven)

```
0x05280008  0x00000000    ; ARRAY_RESET   -> all cells to boot
0x00000007  0x00A50000    ; BOOT_COMMIT   -> RUN, input_address=0, auth_mask=0x0A5
0x00000018  0x00000000    ; SET_TARGET    -> CELL_ID 0
0x05280003  0x00000200    ; SET_OUTPUT_ADDR 0x200
0x05280004  0x5282082C    ; RECONFIGURE   -> PASS_B, armed, latch_in
0x00000018  0x00000000    ; SET_TARGET    -> CELL_ID 0
0x05280022  0x00000004    ; ROUTING       -> east
0x00000018  0x00000000    ; SET_TARGET    -> CELL_ID 0
0x05280023  0x00000001    ; TRANSIT       -> route-across-only
0x00000018  0x00000000    ; SET_TARGET    -> CELL_ID 0
0x05280012  0x00000000    ; SWAP_AB       -> prime a_arrived
0x00000001  0x000000AA    ; INJECT        -> addr 0, value 0xAA -> fires
```

Result on die: value crosses the east bridge; the local cluster bus stays quiet.
With `TRANSIT = 0` the same sequence also drives the local bus.

Note each auth-gated, `config_match`-gated command needs its own `SET_TARGET`
immediately before it — the target latch does not persist across commands.

---

## 8. Known-stale files (encode the OLD 8-bit auth)

These use the retired `0x14A0....` prefix (token at `[28:21]`), which decodes to
`0x294` under the live 11-bit scheme and will be **silently refused**:

```
fpga/icm64_readstate.tcl        fpga/icm64_shift.tcl
fpga/icm64_add_entry.tcl        fpga/shift_primitive.tcl
fpga/or_chain.tcl               fpga/shift_primitive_v2.tcl
fpga/zone_adder.tcl             fpga/zone_emit.tcl
pcie/axi_unicell_bridge.v       (8-bit auth at axi_wdata[23:16])
```

Plus several testbenches predating the 11-bit migration. They are not wrong as
history; they are wrong as templates. **Do not copy encodings from them.**

Current, correct examples: `fpga/transit_smoke.tcl`, `fpga/transit_diag.tcl`,
`fpga/verilog/tb_silicon_seq.v`, `fpga/verilog/tb_v3_transit_obs.v`.
