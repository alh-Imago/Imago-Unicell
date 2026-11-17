#!/bin/sh
# build_load.sh -- build the k7_freeze_load (v3) bitstream and load it into the card's SRAM (never flash). Run inside the openXC7 nix shell (nix develop ~/toolchain-nix), as for the earlier kits.
# It copies ../k7_freeze_load next to the blinky project so ../openXC7.mk is found. DEMO defaults to ~/demo-projects; set DEMO=... if yours is elsewhere.
set -e
DEMO=${DEMO:-$HOME/demo-projects}
SRC="$(cd "$(dirname "$0")/../k7_freeze_load" && pwd)"
[ -f "$DEMO/openXC7.mk" ] || { echo "no $DEMO/openXC7.mk: set DEMO to the folder that holds blinky-ypcb003381p1 and openXC7.mk"; exit 1; }
rm -rf "$DEMO/k7_freeze_load"
cp -r "$SRC" "$DEMO/k7_freeze_load"
cd "$DEMO/k7_freeze_load"
make
make program JTAG_LINK="-c ft232"
echo "loaded. LEDs: yellow blinking, green on, red off = ready."
