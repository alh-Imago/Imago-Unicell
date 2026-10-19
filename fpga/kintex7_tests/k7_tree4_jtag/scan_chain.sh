#!/bin/sh
# scan_chain.sh -- step A: does OpenOCD see the chip through this cable? Prints the JTAG chain; changes nothing.
# Run inside the openXC7 Nix shell, with OpenOCD added:   nix shell nixpkgs#openocd   (then run this).  Use sudo env "PATH=$PATH" if it says permission denied.
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; scan_chain; shutdown"
