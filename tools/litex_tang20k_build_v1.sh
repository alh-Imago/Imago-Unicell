#!/bin/sh
# litex_tang20k_build_v1.sh -- how the LiteX test image with SD card and flash window for the Tang Nano 20K was built (28 Oct 2026). New file. A record of the steps, not a one-click script.
# 1. apt-get install gcc-riscv64-unknown-elf; python3 -m venv venv; pip install -U pip setuptools wheel meson ninja (the system setuptools breaks migen's build).
# 2. Clone LiteX; fetch litex_setup.py; clone https://github.com/m-labs/migen.git first (the M-Labs server is refused by the workspace network); python3 litex_setup.py --init --install --config=standard.
# 3. A shim named nextpnr-himbaechel in venv/bin that runs yowasp-nextpnr-himbaechel-gowin.
# 4. python3 litex-boards/litex_boards/targets/sipeed_tang_nano_20k.py --toolchain apicula --with-sdcard --with-spi-flash --sys-clk-freq 48e6 --output-dir build1 --build
#    The BIOS compiles; the yosys step then fails because the WASM yosys cannot read files outside its start folder.
# 5. Copy VexRiscv.v into build1/gateware, change the two read_verilog lines in the .ys to relative names, run sh build_sipeed_tang_nano_20k.sh there.
# Result: 48 MHz sys clock, timing met (max 122.6 MHz), bitstream sipeed_tang_nano_20k.fs, same size (7,261,470 bytes) as our own test bitstreams.
