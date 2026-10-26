#!/usr/bin/env python3
"""(v3: clone of hexn_card_run_v2.py, left untouched; adds lattice 18 (bank v19, loader) to the simulation choices. v2 text follows.) (v2: clone of hexn_card_run_v1.py, left untouched. With --sim the simulated design is chosen by environment: HEXN_SIM_CORE (v2|v3, default v2), HEXN_SIM_LAT (lattice version, 16|17, default 16), HEXN_SIM_NC (cells, default 1); a core v2/v3 is used, so the all-cells test can run in simulation.)
Run any of the serial-port test scripts (hexn_tang_cell_v1.py, hexn_tang_leak_v1.py, hexn_tang_bist_v1.py, ...) on the Kintex card over the JTAG link: the script asks for a serial port, this wrapper hands it the JTAG frame link instead. Nothing in the test script changes.
Usage (from ~/ypcb-00338-1p1):  nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/Imago-Unicell/tools/hexn_card_run_v1.py [--sim] tools/hexn_tang_cell_v1.py docs/hex-n/frontend/example_random19_script_v1.txt --cells 19 --trials 60
(the script path and its arguments are given as for the Tang; --port is not needed). Load the design first; reload before a run if an earlier one failed."""
import os, sys, types, runpy
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here); root = os.path.normpath(os.path.join(here, ".."))
import hexn_jtag_host_v1 as J
args = sys.argv[1:]; sim = "--sim" in args
if sim: args.remove("--sim")
if not args: sys.exit(__doc__)
target = args[0] if os.path.isfile(args[0]) else os.path.join(root, args[0])
rest = []
for a in args[1:]:
    if os.path.isfile(a) or os.path.isfile(os.path.join(root, a)): a = os.path.abspath(a) if os.path.isfile(a) else os.path.join(root, a)
    rest.append(a)
state = {}
CORE = os.environ.get("HEXN_SIM_CORE", "v2"); LAT = os.environ.get("HEXN_SIM_LAT", "16"); BANK = {"16": "17", "17": "18", "18": "19"}[LAT]
def Serial(port=None, baud=None, timeout=None):
    if sim:
        import hexn_jtag_check_v1 as C
        srcs = ["rtl/tb_hexn_jtag_v2.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/sim/bscane2_model.v", "rtl/hexn_core_%s.v" % CORE, "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v%s.v" % LAT, "rtl/hexn_bank_v%s.v" % BANK, "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v", "rtl/hexn_loader_v1.v"]
        cwd = os.getcwd(); os.chdir(root)
        state["ex"] = J.SimExec(C.build(["-DREALCORE", "-DCORE_MOD=hexn_core_%s" % CORE, "-DLATMOD=hexn_lattice_hex7_v%s" % LAT, "-DNBW=18", "-DAWB=7", "-DNCLS=7", "-DNCELL=%s" % os.environ.get("HEXN_SIM_NC", "1"), "-DACCMODE=0", "-DFSP=16"], srcs)); os.chdir(cwd)
    else:
        cands = [os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")]
        cfg = next((c for c in cands if c and os.path.isfile(c)), None)
        if cfg is None: sys.exit("openocd.cfg not found; set OPENOCD_CFG=<path to board/ypcb-00338-1p1/openocd.cfg> or run from ~/ypcb-00338-1p1")
        state["ex"] = J.OpenOCDExec(cfg)
    return J.JtagLink(state["ex"].scan)
sys.modules["serial"] = types.SimpleNamespace(Serial=Serial)
sys.argv = [target] + rest + ([] if "--port" in rest else ["--port", "jtag"])
sys.path.insert(0, os.path.dirname(target))
try: runpy.run_path(target, run_name="__main__")
finally:
    ex = state.get("ex")
    if ex is not None and hasattr(ex, "close"): ex.close()
