"""Simulation: does the reply to RUNCELLN (0x12) end after 2*NC + K bytes when NC is large? (hex7, K = 7, NCELL = NC; the end test of core v1 needs 2*NC + K <= 255.) Sends CLEAR, RUNCELLN, reads the 2*NC+K reply bytes, then CLEAR again: the next byte must be the 0xA5 acknowledgement and nothing may follow.
Usage: python3 tools/hexn_core_ncell_check_v1.py v1|v2 [NC]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_jtag_host_v1 as J, hexn_jtag_check_v1 as C
core = sys.argv[1]; NC = int(sys.argv[2]) if len(sys.argv) > 2 else 128; K = 7
srcs = ["rtl/tb_hexn_jtag_v2.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/sim/bscane2_model.v", "rtl/hexn_core_%s.v" % core, "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v16.v", "rtl/hexn_bank_v17.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
ex = J.SimExec(C.build(["-DREALCORE", "-DCORE_MOD=hexn_core_%s" % core, "-DLATMOD=hexn_lattice_hex7_v16", "-DNBW=18", "-DAWB=7", "-DNCLS=7", "-DNCELL=%d" % NC, "-DACCMODE=0", "-DFSP=16"], srcs)); link = J.JtagLink(ex.scan)
link.write(bytes([1])); print("CLEAR ->", hex(link.read(1)[0]))
link.write(bytes([0x12, 0, 0, 0])); body = link.read(2 * NC + K); print("RUNCELLN reply: %d bytes read (expected %d)" % (len(body), 2 * NC + K))
link.write(bytes([1])); x = link.read(1)[0]; print("next CLEAR -> 0x%02x (expected 0xa5)" % x)
for _ in range(40): link._poll()
extra = len(link.rxq); ok = x == 0xA5 and extra == 0
print("stray bytes still arriving after the acknowledgement:", extra); ex.close(); print("NCELL REPLY CHECK core %s NC %d: %s" % (core, NC, "PASS" if ok else "FAIL")); sys.exit(0 if ok else 1)
