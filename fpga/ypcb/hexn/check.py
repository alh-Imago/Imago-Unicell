#!/usr/bin/env python3
"""Check for designs/hexn on the YPCB-00338-1P1 (run with `fpga check designs/hexn` after `fpga load designs/hexn/build/hexn.bit`; extra arguments: --tries N, --seeds N, --skip-write, --sim).
Talks to the card through OpenOCD (the repo's board openocd.cfg) with the frame link of tools/hexn_jtag_host_v1.py from the Imago-Unicell checkout (HEXN_REPO, default ~/Imago-Unicell, branch Hex-N):
  1 link: the card answers frames and every capture's CRC is good;
  2 memory: the save/recall suite of hexn_mem_host_v1.py (saved slots read back, every recall: best slot, matches, known wires, second best, cue, recalled pattern, deviation) - every answer compared with the Python copy of the block's rules;
  3 write rules: the four write policies of hexn_mem_write_v2.py on a stream of events, every answer compared with the Python rules (skipped with --skip-write).
PASS needs 0 answers that differ. --sim runs the same stages against the iverilog simulation of the bridge and core (hex7, 1 cell) instead of the card."""
import os, sys, argparse
repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/Imago-Unicell")); sys.path.insert(0, os.path.join(repo, "tools"))
import hexn_jtag_host_v1 as J, hexn_mem_host_v1 as H, hexn_mem_write_v2 as W
ap = argparse.ArgumentParser(); ap.add_argument("--tries", type=int, default=20); ap.add_argument("--seeds", type=int, default=1); ap.add_argument("--skip-write", action="store_true"); ap.add_argument("--sim", action="store_true"); a = ap.parse_args()
if a.sim:
    import hexn_jtag_check_v1 as C
    srcs = ["rtl/tb_hexn_jtag_v1.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/sim/bscane2_model.v", "rtl/hexn_core_v1.v", "rtl/hexn_mem_v1.v", "rtl/gen/hexn_lattice_hex7_w18_v16.v", "rtl/hexn_bank_v17.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
    ex = J.SimExec(C.build(["-DREALCORE", "-DLATMOD=hexn_lattice_hex7_v16", "-DNBW=18", "-DAWB=7", "-DNCLS=7", "-DNCELL=1", "-DACCMODE=0", "-DFSP=128"], srcs))
else:
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../board/ypcb-00338-1p1/openocd.cfg")
    ex = J.OpenOCDExec(cfg)
link = J.JtagLink(ex.scan); ok = True
try:
    c = link._poll(); print("  link: the card answers (rx_free %d, %d bytes waiting)        ok" % (c["rxfree"], c["nvalid"]))
    bad, checks, table, fb = H.suite(link, a.tries); H.show(table)
    print("  memory: answers that differ from the Python rules: %d of %d" % (bad, checks)); ok &= bad == 0
    for f in fb: print("     ", f)
    if not a.skip_write:
        bw = cw = 0; rows = []
        for name, pol in W.POLICIES.items():
            acc = None
            for sd in range(1, a.seeds + 1):
                r = W.run(link, pol, sd); bw += r["bad"]; cw += r["checks"]; acc = {k: (acc[k] if acc else 0) + r[k] for k in W.KEYS}
            rows.append((name, {k: v / a.seeds for k, v in acc.items()}))
        W.show(rows); print("  write rules: answers that differ from the Python rules: %d of %d" % (bw, cw)); ok &= bw == 0
    print("  frames: %d scans, %d bad captures (CRC), %d resent frames" % (link.scans, link.bad, link.resends))
finally:
    ex.close() if hasattr(ex, "close") else None
print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
