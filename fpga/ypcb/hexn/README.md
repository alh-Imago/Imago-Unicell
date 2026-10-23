# Hex-N on the YPCB-00338-1P1 (Kintex-7 XC7K480T)

The Hex-N core (`rtl/hexn_core_v1.v`, no UART) behind a JTAG byte bridge (`rtl/hexn_jtag_bridge_v1.v`, BSCANE2 USER1, 160-bit frames with CRC16 and resend). The same suites that ran on the Tang Nano 20K over serial run here unchanged over JTAG.

**Status:** the bridge and the core are simulated together (iverilog: 0 differing answers, also with injected bit errors). The full design passes the repo's yosys step (hex19, 19 cells: 13346 LUT, 5480 FF, 24 DSP, 2 RAMB18). It has NOT yet been placed, routed or run on the card.

## Install (once)
    ln -s ~/Imago-Unicell/fpga/ypcb/hexn ~/ypcb-00338-1p1/designs/hexn
Branch `Hex-N` must be checked out in `~/Imago-Unicell`. Environment (all optional): `HEXN_REPO` (default `~/Imago-Unicell`), `HEXN_SHAPE` (hex7 or hex19, default hex19), `HEXN_NCELL` (default 19).

## Build, load, check (from `~/ypcb-00338-1p1`)
    fpga build designs/hexn
    fpga load designs/hexn/build/hexn.bit
    fpga check designs/hexn
Back up the flash before writing it; never touch pin AC24 or the fuses (the repo's flow keeps that safe). `check.py --sim` runs the same checks against the simulation; `--skip-write` skips the write-rule stage.

LEDs: led0 heartbeat, led1 core activity, led2 toggles when the core sends a byte.
