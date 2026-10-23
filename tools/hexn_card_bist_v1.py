#!/usr/bin/env python3
"""Hex-N BIST (the proven tools/hexn_tang_bist_v1.py, unchanged) over the JTAG link of the Kintex card design (fpga/ypcb/hexn). The BIST asks for a serial port; this wrapper hands it the JTAG frame link instead, so the same battery runs on the card.
Usage (from ~/ypcb-00338-1p1):  nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/Imago-Unicell/tools/hexn_card_bist_v1.py [--cells 7 --wires 18 --aw 7 --sets N]    (--sim: against the iverilog simulation, hex7 1 cell)
Load the design first; run this right after the load (the BIST clears and then uses the trainer)."""
import os, sys, types
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import hexn_jtag_host_v1 as J
sim = "--sim" in sys.argv
if sim: sys.argv.remove("--sim")
state = {}
def Serial(port=None, baud=None, timeout=None):
    if sim:
        import hexn_jtag_check_v1 as C
        srcs = ["rtl/tb_hexn_jtag_v1.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/sim/bscane2_model.v", "rtl/hexn_core_v1.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v16.v", "rtl/hexn_bank_v17.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
        os.chdir(os.path.join(here, ".."))
        state["ex"] = J.SimExec(C.build(["-DREALCORE", "-DLATMOD=hexn_lattice_hex7_v16", "-DNBW=18", "-DAWB=7", "-DNCLS=7", "-DNCELL=1", "-DACCMODE=0", "-DFSP=128"], srcs))
    else:
        cands = [os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")]
        cfg = next((c for c in cands if c and os.path.isfile(c)), None)
        if cfg is None: sys.exit("openocd.cfg not found; set OPENOCD_CFG=<path to board/ypcb-00338-1p1/openocd.cfg> or run from ~/ypcb-00338-1p1")
        state["ex"] = J.OpenOCDExec(cfg)
    return J.JtagLink(state["ex"].scan)
sys.modules["serial"] = types.SimpleNamespace(Serial=Serial)
import hexn_tang_bist_v1 as B
try: B.main()
finally:
    ex = state.get("ex")
    if ex is not None and hasattr(ex, "close"): ex.close()
