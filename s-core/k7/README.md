# S-Core on the Kintex-7 card (stage 1)

Same pool as the Tang build (sub-slices, shared RAM, copy engine, batch sequencer) with three changes: the host link is the JTAG user register 1
(`fpga/jtag_link_v1.v`, no UART on this card), the far RAM is block RAM (`fpga/farram_bram_v1.v`, 64K words = 256 KB), and the pins are the card's
(50 MHz clock AA28, three LEDs P30 red / M30 green / N30 yellow, active high).  Board version reply 12, so `scbatch.py` works unchanged.

Status: built with the openXC7 nix toolchain (Yosys 0.67, nextpnr-xilinx, 59.84 MHz estimated maximum against the 50 MHz clock; 12,617 LUT sites, 6,699 FF, 64 RAMB36 + 14 RAMB18) and loaded into SRAM on the card on 2026-11-16: telemetry workload 24 of 24 jobs correct over the JTAG link (see latest.md).

Build (inside `nix develop github:openxc7/toolchain-nix`; first check `echo $KINTEX7_CHIPDB; ls -l $KINTEX7_CHIPDB` so nothing regenerates the chip database):
    cp -r k7 <demo-projects>/sc_k7_v1 ; cd <demo-projects>/sc_k7_v1
    S_CORE=$HOME/Imago-Unicell-score/s-core sh stage.sh
    make
Look at the timing report before loading; never load a bitstream that failed timing.  Load: `make program JTAG_LINK="-c ft232"` (SRAM only).

Run (new shell with OpenOCD: `nix shell nixpkgs#openocd`; the card must be loaded and the cable connected):
    python3 scbatch.py jtag jobs_telemetry.json
`jtag` starts OpenOCD itself with `k7/openocd_ft232h.cfg`; `jtag:127.0.0.1:6666` connects to one you started.

LEDs: red = launch error or a job trapped; green = heartbeat (about 1.5 Hz); yellow = JTAG activity or a task finished.
Open points: the clock is 50 MHz straight from the pin (no PLL, no timing constraint in the xdc, so nextpnr times it at its 12 MHz default; add `PNR_ARGS="--freq 50"` for a proper target); the block RAM needed no patched nextpnr; the ABC crash seen with the cloud Yosys 0.33 does not occur with the nix Yosys 0.67; a latch is inferred for `kk` in sc_sys_v12.sv:593 (not yet checked against the Tang build).
