# Session Log — 2026-06-07 (continued)

## Status at session end
Last commit: 92bc675 — MUX selector bug fixed
Suites: 101/101 compiler_int32, 233/233 fp_tiles, 22/22 MUX cases

## Done this session

### MUX selector bug — FIXED (PLAN item 5)

Three compounding root causes identified and fixed:

**Root cause 1: GS_PASS vs GS_PASS_B in padding chains**
`_pad_int32_to_depth` used `GS_PASS|GS_LATCH_IN`. GS_PASS outputs
preloaded A (=0), not the arriving B value. Padding chains never
relayed runtime values — they output 0 always. Fixed: `GS_PASS_B|GS_LATCH_IN`.
Controller pre-arms these so single-arrival works correctly.

**Root cause 2: IR-space vs tile-space timing**
Tile records process before IR records in the forward simulation.
Zero-comparison fast path (a>0, a<0 etc.) built IR AND/NOT trees.
When the MUX preload sim ran, IR addr sim_vals were still 0. The MUX
preloaded sel=0 → always selected false branch.

Fix layer 1: Replaced IR-based zero-comparison fast path with
tile-based comparisons (_place_int32_lt_s_tile). All results in
tile-space, correctly ordered in forward sim.

Fix layer 2: _compile_if wrapping — if cond_addr < 0x200000 (IR-space),
emit GS_PASS_B relay to tile-space. This plus fixing the padding cells
means runtime values propagate correctly.

Special case: a!=0 used OR of two LTS results. IR OR node has the
same ordering problem. Fixed by emitting a tile-space GS_OR cell
with gt_pos preloaded (A) and lt_neg as trigger (B).

**Root cause 3: Integer node IDs in IR graph**
Constants 0 and 1 fell through to parent IR path, returning IRNodes.
`to_node()` called `graph.add_node('PASS', [integer_addr])` — integer
used as string node_id. graph.get(integer) → None → crash.
Fixed: all integer constants in int32 context → `_compile_int32_literal`.

**Other fixes:**
- TILE_SPACE_BASE check in _place_int32_mux (IR vs tile addr detection)
- _recover_constant_from_branch for IRNode constants with None addr
- Zero-comparison rewrites: LtE→LT_S(x,1), GtE→LT_S(-1,x)
- Constants 0/1 now always _compile_int32_literal in int32 context

**All 22 MUX test cases passing:**
a>b, a>0, a<0, a>=0, a<=0, a==0, a!=0 (with arithmetic and constant branches),
nested ifs, all combination operators — both TRUE and FALSE branch selection.

## Next session priorities
1. Multi-param compiler bug (PLAN item 6) — first param excluded from re-injection
2. Arria 10 bring-up (budget next month — USB Blaster + SATA power adapter)
3. Open-source release prerequisites now: only multi-param bug remaining
   (MUX bug done, Arria 10 demo deferred)
4. Add MUX tests to test_compiler_int32.py (currently implicit in session tests)

## Arria 10 bring-up attempt — 2026-06-08

### What was discovered
- Card is alive on PCIe (PCI Device, no yellow triangle, correct VEN_1172/DEV_2494)
- Card is Mustang-F100-A10E2-R10, chip 10AX066H2F34E2SG (GX660)
- Onboard USB programmer is FTDI FT2232H (VID_0403/PID_6010)
- FTDI enumerated ONCE on first cold boot, then stopped presenting on USB bus
- Driver staged correctly (oem84.inf, usb-blaster driver package)
- Power confirmed: SATA-to-6pin adapter seated, PCIe slot power, A0 on display, green LED
- All cables and ports tested — hardware is not the issue
- FTDI chip on this unit appears to have a firmware/hardware fault on the USB controller

### What's needed
- Waveshare USB Blaster V2 (£32, Amazon Prime) — connects to 10-pin JTAG header on board
- This bypasses the faulty onboard FTDI entirely
- Card PCIe interface is fine — just needs external programmer
- Deferred to next month with budget

### Known good state
- Quartus 25.1 installed on F:\Q
- usb-blaster driver staged as oem84.inf
- jtagconfig working (Version 25.1std.0)
- Correct device: 10AX066H2F34E2SG
- Once Waveshare arrives: Tools → Programmer → Hardware Setup → USB-Blaster → scan chain

## Arria 10 bring-up attempt — 2026-06-08

### What was discovered
- Card is Mustang-F100-A10E2-R10, chip 10AX066H2F34E2SG (GX660)
- Card is alive on PCIe — correct VEN_1172/DEV_2494, no yellow triangle
- Onboard USB programmer is FTDI FT2232H (VID_0403/PID_6010)
- FTDI enumerated ONCE on first cold boot then stopped presenting on USB bus
- Driver staged correctly (oem84.inf, usb-blaster package)
- Power confirmed: SATA adapter seated, A0 on display, green LED
- FTDI chip on this unit has a fault on its USB controller circuit

### What's needed to unblock
- Waveshare USB Blaster V2 (~£32) — connects to 10-pin JTAG header on card
- Bypasses faulty onboard FTDI entirely
- Card PCIe interface is fine, just needs external programmer
- Deferred until budget recovers

### Quartus state on Windows machine
- Quartus 25.1 installed on F:\Q
- usb-blaster driver staged as oem84.inf
- jtagconfig working (Version 25.1std.0)
- Correct device to select: 10AX066H2F34E2SG
- Once Waveshare arrives: Programmer → Hardware Setup → USB-Blaster → scan chain
