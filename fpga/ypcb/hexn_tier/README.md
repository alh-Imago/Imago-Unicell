# hexn_tier: Kintex memory tier + Hex-N core + DDR3 debug register in ONE bitstream (not built on the card, nothing run on the card)

Same plumbing as `../hexn_joint` (a drop-in `memtest.v`, so ypcb's generated uberddr3 top level, pins and USER1 debug register stay as they are), but the DDR3 Wishbone port now belongs to the memory tier.

| JTAG | IR | what | host |
|---|---|---|---|
| USER1 | 0x02 | ypcb's own DDR3 debug register (calibration status) | `designs/uberddr3/check.py` |
| USER2 | 0x03 | Hex-N core (default `HEXN_CORE=v9`: layer 1 bank, hold, layer 2 store v5; `v2` = the layer-1-only core that closed timing in hexn_joint) | `tools/hexn_card_bist_v1.py` etc. with `HEXN_CHAIN=2` |
| USER3 | 0x22 | memory tier command layer (`rtl/hexn_tier7_cmd_v1.v`: PUT, GET, FLUSH, COUNTERS, INFO, LEVEL, LINE) | `tools/hexn_tier7_card_v1.py` |

Settings for `prebuild.py` (environment): `YPCB` (default `~/ypcb-00338-1p1`), `HEXN_REPO` (the checkout, branch Hex-N), `HEXN_CORE` (v9 default, or v2), `HEXN_SHAPE` (hex7 default) and `HEXN_NCELL` (default 7), tier sizes `TIER_KW TIER_VW TIER_FB TIER_BMB TIER_RAMB TIER_SB` (defaults 24 24 10 17 14 17: 1,024 level-0 entries, 16,384 level-1 entries, 2^17 DDR3 lines of 8 entries).

## Build (same recipe as hexn_joint, from `~/ypcb-00338-1p1`, in the openXC7 nix shell, CHIPDB exported, NO sudo)
    git -C ~/hexn-wt pull origin Hex-N
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_tier designs/hexn_tier
    mkdir -p /mnt/hdd/hexn_builds/tier_hex7 && ln -sfn /mnt/hdd/hexn_builds/tier_hex7 designs/hexn_tier/build_tier_hex7
Then the SAME command line (same extra settings, same top-module argument) that built `designs/hexn_joint`, with design `designs/hexn_tier`, `BUILD=build_tier_hex7` and `HEXN_REPO=~/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=7` (add `HEXN_CORE=v2` for the older core).

## Load and test
    ~/openFPGALoader/build/openFPGALoader -c digilent_hs2 designs/hexn_tier/build_tier_hex7/hexn_tier.bit
1. `designs/uberddr3/check.py` through `run_with_openocd.py` (calibration complete).
2. The tier on USER3: `nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/tools/hexn_tier7_card_v1.py --steps 2000 --dump tier_dump.json` (INFO, self-test against the Python model, dump of every level to a JSON file).
3. Hex-N on USER2: as in hexn_joint with `HEXN_CHAIN=2`.

## What was checked here (sandbox only)
`prebuild.py` writes the combined RTL with a stand-in for ypcb's prebuild, and the combined `memtest` elaborates with iverilog for both cores. A native-yosys `synth_xilinx` of the combined `memtest` gave the size figures in docs/hex-n/HEXN_DESIGN.md (synthesis only; no place and route, no timing). NOT checked: a real build against ypcb's generated top level, timing at 83.33 MHz, the card.

## Known risks
- Clock: everything runs on the DDR3 controller clock (83.33 MHz). hexn_joint already flagged this for the Hex-N core; the tier adds a 576-bit wide path, so a timing failure is possible.
- USER1 memory-test fields read zero (the tier owns the DDR3 port); `errors` shows the tier's DDR3 error flag.
- The tier's presence counters and levels 0 and 1 live in FPGA memory: they are lost at a reload (the DDR3 contents may survive but cannot be used without them). Restore from a dump is not built.
