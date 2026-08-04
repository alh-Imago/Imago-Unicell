# Session Log — Imago UniCell Project

---

## Session: 5 May 2026 — First Silicon Validation

**Board:** iCEBreaker v1.0e (iCE40UP5K sg48)
**Toolchain:** OSS CAD Suite (yosys 0.64+181, nextpnr-ice40 0.10, icepack, iceprog)
**OS:** Windows 11
**Clock:** Internal HFOSC ~12.26MHz (external 12MHz oscillator pin TBD)

---

### Summary

The iCEBreaker arrived today. By end of session, the Imago UniCell architecture
was validated on real silicon — NOT gate and wired-OR NAND both producing correct
results. The founding architectural property (multiple cells writing the same
address, outputs combined by OR on the bus) is proven in hardware.

---

### Steps taken

**1. Board arrived — cable hunt**
Board shipped without a micro USB cable. A charge-only cable from a torch
was tried first — no data lines. A proper data cable found. Board powered up:
green PWR LED, blue CDONE (factory bitstream loaded from flash).

**2. Windows driver setup**
OSS CAD Suite installed. iCEBreaker presents as two FTDI interfaces:
- Interface 0 (Channel A): SPI programmer → replaced with WinUSB via Zadig
- Interface 1 (Channel B): UART → remained as COM4

**3. First synthesis — fixing compilation errors**
Running yosys on the Verilog revealed several simulation-only constructs:
- `BASE_ADDRESS` parameter missing from `unicell_array` module header
- Local `reg` declarations inside `always @(*)` block (SystemVerilog only)
- Dual-edge always blocks (`posedge` and `negedge`) — iCE40 requires single-edge
  Fixed with `odd_phase` toggle register emulating negedge behaviour
- `NUM_CELLS=64` exceeded iCE40UP5K capacity (585%) → reduced to 8 cells (83%)
- PCF pin assignments wrong throughout (clock=35 was GND, TX/RX swapped)

**4. Clock pin hunt**
Multiple wrong clock pins tried (35=GND, 20, 3, 13=TEST/GND).
Resolved from schematic: external 12MHz oscillator OUT → FPGA OSCI pin.
Working solution: internal HFOSC at 12MHz nominal (actual ~12.26MHz).
External clock pin remains to be confirmed for precise timing.

**5. UART bring-up — uart_hello.v**
Wrote minimal UART transmitter (no RX, no commands) to prove TX path.
Confirmed:
- FTDI Channel B → COM4 correct (loopback test: shorting PMOD pins stalled TeraTerm)
- TX pin = 9 (IOB_16A), RX pin = 6 (IOB_13B) — confirmed from schematic
- LEDR = pin 11, LEDG = pin 12

**6. Full design UART debugging**
uart_hello worked but full uart_bridge produced no output.
Root causes found and fixed in sequence:
- All registers needed explicit initial values (`= 1'b0`) — iCE40 FFs can
  power up to unknown state without explicit initialisation in bitstream
- `tx_bit_cnt` not resetting between bytes
- Stop bit bleeding into next byte start bit — fixed with full CPB idle gap
  (state 3 in TX state machine)
- HFOSC ~2% fast — causing corruption from byte 3 onward (accumulated
  phase error). Fixed by correcting CLK_FREQ to 12_257_280 (CPB=106)
- TX queue used indexed array `queue[q_pos]` — synthesis mux had timing
  issues. Replaced with 88-bit shift register `q_sr`, always reads top byte

**7. Command processor fixes**
- Single-byte commands (0x04 status, 0x03 reset, 0x06 freeze, 0x07 release)
  never executed — `cmd_pos` starts at 1, check was `cmd_pos==0` (never true).
  Fixed: execute single-byte commands immediately on first byte received.
- RX parser `else: break` left unknown bytes at front of buffer permanently,
  blocking all responses. UCOK startup bytes blocked every status response.
  Fixed: discard unknown bytes, only break on known-but-incomplete packets.
- RX echo debug code left in Verilog — was consuming `q_valid` on every
  received byte, preventing cell-fired responses from being queued.

**8. Cell configuration not working**
- `BASE_ADDRESS=0x1000` in Verilog but Python sending to address 0x0001.
  Fixed: `BASE_ADDRESS=0` so cell N has CONFIG_ADDRESS=N.
- All unicell registers needed explicit initial values — `cfg_state` powering
  up non-zero means LOAD_PATTERN never recognised. Fixed with `= 2'h0` etc.

**9. Cell firing — wrong output**
- NOT gate outputting 1 for both inputs (NOT(0)=1 correct, NOT(1)=1 wrong).
- Root cause: `input_val = data_reg[0]` is combinational, but `data_reg <=
  bus_data` is registered. Cell computed output using PREVIOUS data_reg value,
  not the incoming bus_data. First input was always 0 (data_reg initial value).
- Fixed: `input_val = bus_valid && address_match ? bus_data[0] : data_reg[0]`
  Combinational block now uses incoming bus_data directly when valid.

---

### Final validation output

```
[FPGA] Connected to COM4 at 115200 baud
[FPGA] Armed cells: 0
[FPGA] Cycle count: 55325917

NOT gate:
  NOT(0) = 1  ✓
  NOT(1) = 0  ✓

NAND via wired-OR (two NOT cells, shared output address 0x3000):
  NAND(0,0) = 1  ✓
  NAND(0,1) = 1  ✓
  NAND(1,0) = 1  ✓
  NAND(1,1) = 0  ✓

Status:
  Armed cells: 4
  Cycles:      79461586
  Fired:       10
  Errors:      0
```

---

### What this proves

The wired-OR bus works on real silicon. Two independent cells, each computing
NOT of their respective inputs, both writing to address 0x3000. The bus
combines their outputs by OR. The result is the correct NAND truth table.

This is not a simulation result. This is not a theoretical argument.
This is real logic, on real flip-flops, on a real iCE40UP5K device.

The founding premise of the Imago architecture — that NOR universality plus
wired-OR produces a complete computational substrate — is validated in hardware.

---

### Commits this session

- Fix: BASE_ADDRESS parameter missing from unicell_array
- Fix: eliminate dual-edge always blocks for iCE40 synthesis
- Fix: correct iCEBreaker PCF pin assignments from schematic
- Fix: TX/RX pins corrected (TX=9, RX=6 from schematic)
- Fix: UART TX state machine stop bit gap, shift register queue
- Fix: single-byte commands execute immediately
- Fix: RX parser discards unknown bytes
- Fix: unicell register initial values
- Fix: input_val uses incoming bus_data not stale data_reg
- SILICON VALIDATED: NOT gate and wired-OR NAND confirmed

