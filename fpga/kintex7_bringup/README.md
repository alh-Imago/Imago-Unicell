# Kintex-7 bring-up (XC7K480T card, YPCB-00338-1P1)

DRAFT written 15 Oct 2026, before the card has been powered stand-alone.
Nothing here has been built into a bitstream or run on the card.

Plan, in order, each step only after the one before worked:
1. Power the card from its own 12 V supply through the 1x-to-16x riser (1x side
   unplugged), JTAG lead only to the PC.
2. `sudo openFPGALoader -c ft232 --detect` - expect a Kintex-7 480T in the chain.
3. Build and load `blink_k7_v1` (three LEDs at three speeds, 50 MHz clock).
4. Only then anything bigger.

Files: `blink_k7_v1.v` (design), `blink_k7_v1.xdc` (pins), `tb_blink_k7_v1.v`
(simulation, PASS 31/63/127 toggles in 512 cycles), `build_k7_blink_v1.sh`.

Checked here: simulation and yosys `synth_xilinx` (25 flip-flops, 7 carry cells, one
clock buffer, 3 output buffers). Not checked: place and route, the openXC7
toolchain (not installed in the cloud workspace), and every pin.

Known risks, stated plainly:
- The 50 MHz clock pin (AA28) and LED pins (P30/M30/N30) come from the old board
  file, not from a measurement. If the card has no LED blink, that may be the
  pins or the oscillator, not the design.
- Whether the card's 50 MHz oscillator runs without the PCIe side is unknown.
- Load into volatile memory only; never write the card's flash.
- Never load a bitstream that failed timing (what damaged the card before).

## 17 Oct 2026 first contact (ledger #1189)
`sudo openFPGALoader -c ft232 --detect` read IDCODE 0x23751093 (Xilinx, manufacturer 0x049) at 6 MHz, then stopped with "Unknown device" because the loader has no entry for that ID. JTAG, power and wiring work. Nothing was loaded. Confirm the IDCODE (UG470 / BSDL) and how to name the part to the loader before loading `blink_k7_v1` (SRAM only, never flash).

## Building the bitstream with Vivado (ledger #1192)
`build_blink_vivado_v1.tcl` builds `blink_k7.bit` with Vivado (batch mode, stops if timing fails, never touches the card). Not run by Claude: no Vivado here. The pins and the config-voltage lines are unverified placeholders (see the file header).

## Open-source route (ledger #1193)
openXC7 has a demo for this exact board model (`demo-projects/blinky-ypcb003381p1`, same pins as `blink_k7_v1.xdc`). Run inside `nix develop github:openxc7/toolchain-nix`; load with `make program JTAG_LINK="-c ft232"` (SRAM only). Try the demo first; it proves the toolchain and the pins. Not run by Claude.
