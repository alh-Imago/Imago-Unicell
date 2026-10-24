# hexn_joint: DDR3 latency probe and the Hex-N core in ONE bitstream (not built yet, nothing run on the card)

What it is: the `hexn_ram` design (ypcb's uberddr3 top level with `memlat` in place of `memtest`) with the Hex-N core and its JTAG bridge added INSIDE `memtest.v`, so ypcb's generated top level, its pins and its USER1 debug register stay exactly as they are. The Hex-N bridge is on JTAG USER2 (IR 0x03).

- `memtest.v`: same module name and ports as ypcb's `memtest.v` (as in `hexn_ram`), plus an instance of `hexn_jtag_bridge_v1` (CHAIN 2) and `hexn_core_v2` on the module's `clk`.
- `prebuild.py`: runs ypcb's own `designs/uberddr3/prebuild.py` unchanged (same arguments and environment), then writes `gen_01_hexn.v` (the defines and the Hex-N RTL) into the build folder. Settings: `YPCB` (default `~/ypcb-00338-1p1`), `HEXN_REPO`, `HEXN_SHAPE` (default hex7), `HEXN_NCELL` (default 7).
- `memlat.v`: copy of `../hexn_ram/memlat.v`.
- Host scripts are the ones in `../hexn_ram` (`memlat.py`, `run_with_openocd.py`, `jtagdr_openocd.py`) and the Hex-N tools in `tools/`.

Checked in the sandbox only: the prebuild writes the Hex-N file (with a stand-in for ypcb's prebuild) and the joint `memtest` elaborates with iverilog. NOT checked: a real build against ypcb's generated top level.

## Build (from `~/ypcb-00338-1p1`, in the openXC7 nix shell, CHIPDB exported, NO sudo)
    git -C ~/hexn-wt pull origin Hex-N
    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_joint designs/hexn_joint
    mkdir -p /mnt/hdd/hexn_builds/joint_hex7 && ln -sfn /mnt/hdd/hexn_builds/joint_hex7 designs/hexn_joint/build_joint_hex7
Then the SAME command line (same extra settings, same top-module argument) that built `designs/hexn_ram`, with these changes: design `designs/hexn_joint`, `BUILD=build_joint_hex7`, and `HEXN_REPO=~/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=7` added.

## Load and test (right after the load, in this order)
    ~/openFPGALoader/build/openFPGALoader -c digilent_hs2 designs/hexn_joint/build_joint_hex7/hexn_joint.bit
(if the .bit has another name, `ls designs/hexn_joint/build_joint_hex7/*.bit`)
1. Hex-N on USER2 (the BIST wants to run first after a load):
   `nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_bist_v1.py --cells 7 --wires 18 --aw 7`
2. DDR3 on USER1: `nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/fpga/ypcb/hexn_ram/run_with_openocd.py designs/uberddr3/check.py`
3. Latency probe: `... run_with_openocd.py ~/hexn-wt/fpga/ypcb/hexn_ram/memlat.py --len 10`
Pass: BIST PASS, check.py PASS (calibration complete), and the same latency figures as the stand-alone probe (about 10 cycles).

## Known risk
The Hex-N core runs on the DDR3 controller clock (83.33 MHz) here. Stand-alone, the hex7 / 7-cell build was estimated at 82.0 / 92.4 MHz by nextpnr, so 83.33 MHz is near its limit, and the flow's timing check only tests 50 MHz. If the DDR3 tests pass and the BIST does not (or is flaky), this is the first suspect; the fix is to run the Hex-N core from a slower clock, which needs a look at the generated top level's clocks.
