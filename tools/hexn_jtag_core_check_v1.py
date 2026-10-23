"""Simulation check of the whole chain: JTAG frames (rtl/hexn_jtag_bridge_v1.v) -> hexn_core_v1 (bank, cells, memory block) and back, running the suite of tools/hexn_mem_host_v1.py over tools/hexn_jtag_host_v1.py; every answer is compared with the Python rules by the suite. Slow (the JTAG clock is slow against the core clock): use a few tries.
Usage: python3 tools/hexn_jtag_core_check_v1.py [TRIES] [FLIP_PER_MILLE]"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_jtag_host_v1 as J, hexn_jtag_check_v1 as C, hexn_mem_host_v1 as H
def main():
    tries = int(sys.argv[1]) if len(sys.argv) > 1 else 3; flip = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    srcs = ["rtl/tb_hexn_jtag_v1.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/sim/bscane2_model.v", "rtl/hexn_core_v1.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v16.v", "rtl/hexn_bank_v17.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
    vvp = C.build(["-DREALCORE", "-DLATMOD=hexn_lattice_hex7_v16", "-DNBW=18", "-DAWB=7", "-DNCLS=7", "-DNCELL=1", "-DACCMODE=0", "-DFSP=128"], srcs)
    ex = J.SimExec(vvp, ["+flip=%d" % flip]); link = J.JtagLink(ex.scan)
    bad, checks, table, fb = H.suite(link, tries, rows=H.ROWS[:2]); ex.close(); H.show(table)
    print("through JTAG and the core: answers that differ from the Python rules: %d of %d (scans %d, bad captures %d, resends %d)" % (bad, checks, link.scans, link.bad, link.resends))
    for f in fb: print("  ", f)
    print("JTAG CORE SIM PASS" if bad == 0 else "JTAG CORE SIM FAIL"); sys.exit(0 if bad == 0 else 1)
if __name__ == "__main__": main()
