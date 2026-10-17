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

## First light, 17 Oct 2026 (ledger #1194)
The openXC7 demo `blinky-ypcb003381p1` was built on Alan's PC and loaded into the card's SRAM with `make program JTAG_LINK="-c ft232"`; the loader reported Load SRAM 100%, Done, `isc_done 1 init 1 done 1`, and Alan reported the LEDs running ("a christmas tree"). Recipe that worked: install Nix (daemon), enable flakes, `nix develop github:openxc7/toolchain-nix`, clone `openXC7/demo-projects`, in `blinky-ypcb003381p1` remove the trailing `;# 50 MHz` from line 3 of `ypcb003381p1.xdc` (nextpnr-xilinx cannot parse it), `make` (the first run builds the xc7k480t chip database, long and memory-hungry on a small PC; it is kept in `../chipdb/`), then `make program JTAG_LINK="-c ft232"`. Place-and-route: Fmax 387.15 MHz against 50 MHz. Bitstream 18,735,109 bytes. Nothing written to flash.
LED report (ledger #1195): a steady green LED (power?, not driven by the design); the driven LEDs cycle all three, red, green, yellow (Alan; "all off" also mentioned, not in the demo code). My reading: led[0]=red P30, led[1]=green M30, led[2]=yellow N30, active-high; not confirmed pin by pin.

Own blink (ledger #1196): blink_own/ has our files plus a Makefile for demo-projects; not built yet.

Own blink on the card (ledger #1197): built through openXC7 by Alan (Fmax 416.32 MHz), loaded to SRAM; yellow fast, green and red slower. Pins: P30 red, M30 green, N30 yellow.
