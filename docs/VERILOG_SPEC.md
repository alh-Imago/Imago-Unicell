# Verilog Specification — UniCell v2

*Documents the Verilog implementation, silicon bring-up findings, timing issues,
and parity status between the Python VM and the synthesised hardware.*

---

## Files

```
fpga/verilog/
  unicell.v           — single cell implementation (primary file)
  unicell_array.v     — configurable cell array, wired-OR bus
  uart_bridge.v       — UART host bridge (115200 baud, 13-byte packets)
  top_icebreaker.v    — iCEBreaker top-level (SB_HFOSC 24MHz, validated)
  top_icestick.v      — iCEstick top-level
  top_basys3.v        — Basys 3 top-level
  top_arty_a7.v       — Arty A7 top-level
  top_orangecrab.v    — OrangeCrab ECP5 top-level
  top_tinyfpga_bx.v   — TinyFPGA BX top-level
  top_ulx3s.v         — ULX3S top-level
  top_debug.v         — debug top-level (all dbg_* wires exposed)
  blink_test.v        — LED blink (bring-up sanity check, no UART)
  uart_hello.v        — UART loopback test (stage 2 bring-up)
  unicell_array_stub.v — stub for integration testing
```

All files are Verilog-2001 (`\`timescale`, no SystemVerilog constructs).
Synthesise on iCE40 (yosys + nextpnr), ECP5 (nextpnr-ecp5), and
Xilinx 7-series (Vivado) without modification.

---

## Silicon Bring-Up — May 2026

**Board:** iCEBreaker v1.0e (iCE40UP5K sg48)
**Date:** 14 May 2026
**Result:** All three variants validated. Architecture confirmed in silicon.

### Bring-up sequence followed

| Stage | Test | Result |
|-------|------|--------|
| 1 | LED blink (`blink_test.v`) | ✓ FPGA alive |
| 2 | UART loopback (`uart_hello.v`) | ✓ TX/RX wiring correct |
| 3 | NOT gate (1 cell, `not_gate.icm`) | ✓ NOT(0)=1, NOT(1)=0 |
| 4 | Two-input NAND (2 NOT cells, wired-OR) | ✓ All 4 combinations correct |
| 5 | Bridge pair (INBOUND + OUTBOUND) | ✓ Multi-cell isolation |
| 6 | 8-cell array scale | ✓ 3,780 ICESTORM_LC (71%) |

Validated at **24 MHz** using `SB_HFOSC` internal oscillator.
Gate error rate: **0** across all tests.

---

## Timing Issues Found and Resolved

### Issue 1 — Dual-edge registers (negedge on iCE40)

**Problem:** The original unicell.v used `always @(negedge clk)` for output
buffer drain and `GS_LATCH_IN` re-evaluation. iCE40 synthesis (yosys) does
not support negedge-triggered flip-flops — it produces negedge using combinational
inversion of the clock, which breaks timing analysis and fails at 24 MHz.

**Symptom:** NOT gate produced correct logic but with inconsistent latency.
Occasionally produced 0 when NOT(0)=1 was expected on the first cycle.

**Resolution:** Replaced all negedge logic with an `odd_phase` toggle register
that flips each posedge:

```verilog
reg odd_phase;
// In posedge always block:
odd_phase <= ~odd_phase;

// "Negedge" actions now happen when odd_phase=1:
if (odd_phase && out_buf_valid && !out_buf_posedge) begin
    out_addr  <= out_buf_addr;
    out_data  <= out_buf_data;
    out_valid <= 1'b1;
    ...
end
```

Effective timing is identical at half-cycle granularity. The output buffer
loads on posedge N and drains on the next posedge when `odd_phase=1` — same
behaviour as the original negedge drain, but using only posedge registers.

**Impact:** All three variants now use this pattern. No negedge registers
anywhere in the design.

---

### Issue 2 — External crystal clock pin discrepancy

**Problem:** The iCEBreaker 12 MHz crystal is on physical pin 35. Documentation
inconsistency: the schematic says pin 2, the hardware manual says pin 35.
Early attempts to use the external crystal with `SB_GB_IO` on pin 2 produced no
clock — the array stayed in reset.

**Resolution:** Switched to `SB_HFOSC` internal oscillator. No external clock
pin needed. No pin constraint required. No documentation to reconcile.

```verilog
SB_HFOSC #(.CLKHF_DIV("0b01")) osc (  // 48MHz / 2 = 24MHz
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);
```

**HFOSC divider settings:**
| Setting | Frequency | Notes |
|---------|-----------|-------|
| `"0b00"` | 48 MHz | May fail timing on some routing paths |
| `"0b01"` | 24 MHz | **Validated on hardware** — recommended |
| `"0b10"` | 12 MHz | Nominal, actual ~12.26 MHz measured |
| `"0b11"` | 6 MHz | Safe but slow |

**Lesson:** Never use the iCEBreaker external crystal until the pin discrepancy
is resolved with a scope. Use `SB_HFOSC` for all bring-up and production.

---

### Issue 3 — CONFIG_ADDRESS vs input_address collision at address 0

**Problem (v1.1):** In the original design, cell configuration used the same
address space as runtime data. Cell 0 had CONFIG_ADDRESS=0. Any data transaction
on the bus at address 0 would be interpreted as the start of a configuration
sequence if the cell was in CFG_IDLE state.

**Symptom:** After configuring cells, the first NOT gate test would sometimes
reconfigure cell 0 if the data value happened to match `LOAD_PATTERN`.

**Resolution (v1.2):** CONFIG_ADDRESS is now a synthesis-time parameter
(`localparam` derived from `CELL_ID`), completely separate from the runtime
`input_address` register. Configuration can never be triggered by data traffic.

```verilog
module unicell #(
    parameter CELL_ID        = 0,
    parameter CONFIG_ADDRESS = CELL_ID   // synthesis-time only
) ( ... );

// Config check uses CONFIG_ADDRESS — synthesis parameter, never changes
if (bus_addr == CONFIG_ADDRESS[31:0] && bus_data == LOAD_PATTERN) begin
    cfg_state <= CFG_LOAD_GS;
```

```verilog
// Data check uses input_address — runtime register, loaded during config
end else if (bus_addr == input_address && start_flag) begin
```

These two checks are in separate branches — they cannot interfere.

---

### Issue 4 — Wired-OR bus address arbitration

**Problem:** When multiple cells fire in the same cycle and write different
addresses, `or_addr` in `unicell_array.v` takes the last cell's address
("last writer wins"). This is non-deterministic across synthesis tools.

**Current state:** For the wired-OR semantics to be correct, all cells firing
in the same cycle must write the *same* address (that is the point of wired-OR).
When cells write different addresses, the current implementation forwards only
one address to the host. In practice the compiler ensures cells that need to
communicate use the same output address — this has not caused test failures.

**Future fix:** Per-address OR reduction:
```verilog
// For each possible address in the used set:
// out_data[addr] = OR of all cell_out_data[i] where cell_out_addr[i] == addr
```
This requires a more complex bus fabric — deferred until there is a routing
conflict in practice.

---

## Gate Function Parity

Current parity between `gate_states.py` (Python VM) and `unicell.v` (Verilog):

| Feature | gate_state (v2.3) | Python | Verilog | Notes |
|---------|-----------|--------|---------|-------|
| GS_NOT (topology) | 0x00000001 | ✅ | ✅ | Validated on iCEBreaker |
| GS_PASS (topology) | 0x00000000 | ✅ | ✅ | |
| GS_AND_V2 | 0x00000007 | ✅ | ✅ | |
| GS_OR_V2 | 0x00000024 | ✅ | ✅ | |
| GS_XOR_V2 | 0x000000BC | ✅ | ✅ | |
| GS_NAND_V2 | 0x00000027 | ✅ | ✅ | |
| GS_XNOR_V2 | 0x0000003C | ✅ | ✅ | |
| GS_NOR_V2 | 0x00000004 | ✅ | ✅ | |
| GS_EDGE_MODE | bit 10 = 0x00000400 | ✅ | ✅ | edge_mode in cmd_latch[10] |
| GS_INVERT_OUT_BIT | bit 25 = 0x02000000 | ✅ | ✅ | invert_out in cmd_latch[25] |
| GS_LATCH_IN | bit 26 = 0x04000000 | ✅ | ✅ | latch_in in cmd_latch[26] |
| GS_FALL_EDGE | edge_mode\|invert_out = 0x02000400 | ✅ | ✅ | negedge = edge_mode + invert_out |
| GS_LOOP_BACK | bit 31 = 0x80000000 | ✅ | ✅ | loop_back in cmd_latch[31] |
| GS_ONE_SHOT | bit 30 = 0x40000000 | ✅ | ✅ | one_shot in cmd_latch[30] |
| dtype (SIGNED) | bits 24:23 = 0x00800000 | ✅ | ⚠️ | Bits stored, not acted on by gate tree |
| dtype (ALPHA) | bits 24:23 = 0x01000000 | ✅ | ⚠️ | Bits stored, not acted on by gate tree |
| dtype (DATETIME) | bits 24:23 = 0x01800000 | ✅ | ⚠️ | Bits stored, not acted on by gate tree |
| GS_PRIORITY | bit 27 = 0x08000000 | ✅ | ❌ | Scheduling — not in silicon |
| GS_TRACE | bit 28 = 0x10000000 | ✅ | ❌ | Debug only |
| GS_BREAKPOINT | bit 29 = 0x20000000 | ✅ | ❌ | Debug only |
| GS_SYNC_WAIT | — | — | — | RETIRED — two-arrival is the default, no flag needed |
| GS_SELECT | — | — | ❌ | RETIRED — branch design uses PTT dispatch |

*All hex values are cmd_latch bit positions (v2.3). Ground truth: `fpga/verilog/unicell.v` and `gate_states.py`.*

**Legend:** ✅ Full parity · ⚠️ Partial / metadata only · ❌ Not implemented

---

## Two-Arrival Model — Implemented

The two-arrival model (previously called GS_SYNC_WAIT) is **fully implemented**
as the default cell behaviour. `GS_SYNC_WAIT` (old bit 15) is retired.

True two-input firing is now the default:
two-input cells: the cell waits until both A (posedge) and B (negedge) have
arrived before firing. This is how AND, OR, XOR, NAND, XNOR work in the Python
VM with a single cell.

Without `GS_SYNC_WAIT` in the Verilog, two-input logic requires the v1 approach:
two cells sharing an output address (wired-OR bus does the work). This is correct
and validated on silicon — NAND via two NOT cells sharing an output address was
confirmed working in the May 2026 bring-up. It just uses 2 cells instead of 1.

**Implementation plan for GS_SYNC_WAIT:**

```verilog
// Additional registers needed per cell:
reg a_arrived;
reg [31:0] a_data;
reg [31:0] input_b_address;  // loaded during config (5th config word)

// On posedge (A input):
if (bus_addr == input_address && start_flag) begin
    if (gate_state[15]) begin  // GS_SYNC_WAIT
        a_arrived <= 1'b1;
        a_data    <= bus_data;
    end else begin
        // ... existing single-input path
    end
end

// On odd_phase (B input, emulates negedge):
if (gate_state[15] && a_arrived &&
    bus_addr == input_b_address && bus_valid) begin
    // Both inputs arrived — fire
    a_arrived <= 1'b0;
    // compute using a_data (A) and bus_data (B)
    out_buf_valid <= 1'b1;
    ...
end
```

Config sequence extension for SYNC_WAIT cells:
```
1. LOAD_PATTERN
2. gate_state         (with GS_SYNC_WAIT set)
3. input_address      (A input address — posedge)
4. output_address
5. input_b_address    (B input address — negedge)  ← new
```

This is the path to full v2 two-input parity in silicon. Target: Kintex-7
bring-up session (Jul 2026).

---

## GS_TYPE Bits — Stored but Transparent

The type bits (27-28, GS_TYPE_SIGNED/ALPHA/DATETIME) are stored in the
`gate_state` register and travel with the cell through configuration. The gate
tree does not act on them — they pass through the `case(gate_state[8:0])`
without effect.

This is correct. The type system is metadata handled by the host software
(Python VM, WORKSPACE, PTT). The silicon stores and forwards the type bits
transparently. When the host reads `dbg_gate_state` it sees the type bits.
When the UART bridge sends a `RSP_STATUS`, the gate_state is available for
the host to inspect.

No silicon changes needed for type bit support — they work correctly today.

---

## Resource Usage

Measured on iCE40UP5K (iCEBreaker):

| Config | ICESTORM_LC | Utilisation | Clock |
|--------|-------------|-------------|-------|
| 8 cells | ~470 | 9% | 24 MHz |
| 32 cells | ~1,880 | 36% | 24 MHz |
| 64 cells | ~3,760 | 71% | 24 MHz |
| 72 cells | ~4,230 | 80% | 24 MHz (tight) |
| 80 cells | ~4,700 | 89% | may fail P&R |

Rule of thumb: **59 LCs per cell** on iCE40UP5K (including array overhead).
The array itself (bus fabric, counters, UART) uses ~100 LCs fixed overhead.

For Kintex-7 XC7K480T (Vivado, target Jul 2026):
- ~47 LUTs per cell (Artix-7 estimate — Kintex-7 similar)
- 15,120 LUTs available → ~315 cells (conservative)
- With DSP/BRAM offload for counters: 400–500 cells realistic

---

## Synthesis Notes

### iCE40 (OSS CAD Suite — yosys + nextpnr-ice40)

```bash
yosys -p "synth_ice40 -top top -json unicell.json" \
      verilog/unicell.v verilog/unicell_array.v \
      verilog/uart_bridge.v verilog/top_icebreaker.v

nextpnr-ice40 --up5k --package sg48 \
              --json unicell.json \
              --pcf fpga/constraints/icebreaker.pcf \
              --asc unicell.asc

icepack unicell.asc unicell.bin
iceprog unicell.bin
```

**Do not use `--timing-allow-fail`** — if timing fails at 24 MHz, drop to 12 MHz
(change `CLKHF_DIV` to `"0b10"`). Timing failures are rare at 24 MHz but can
occur on dense routing around the UART module.

### Xilinx 7-series (Vivado ML Standard)

Use the included `top_arty_a7.v` or `top_basys3.v`. Set the target part in
Vivado project settings. The constraint files in `fpga/constraints/` contain
the clock constraint (12 MHz external crystal or internal MMCM).

`\`timescale` is present on all files — Vivado requires it. The design uses no
Xilinx-specific primitives so it is genuinely portable across families.

---

## What Needs Doing Before Kintex-7

In priority order:

1. **GS_SYNC_WAIT implementation** — true two-input cells, 5th config word
2. **GS_SELECT** — conditional routing cell (`output = sel ? a : b`)
3. **Multi-output bus arbitration** — handle cells firing to different addresses
4. **XDC constraints file for Kintex-7** — board-specific pin assignments
5. **Vivado TCL build script** — reproducible build without GUI

GS_ADDR_LATCH, GS_PRIORITY, GS_TRACE, GS_BREAKPOINT are debug/OS features.
They are not needed for basic silicon validation.
