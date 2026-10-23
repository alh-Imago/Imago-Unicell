"""Simulation check of the JTAG bridge (rtl/hexn_jtag_bridge_v1.v) with the emulated core (every byte comes back +1; byte 0xFF = 60 bytes of burst): random writes and reads, with and without injected bit errors (+flip).
Usage: python3 tools/hexn_jtag_check_v1.py [BYTES] [FLIP_PER_MILLE]"""
import sys, os, random, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_jtag_host_v1 as J
def build(defs=(), srcs=None):
    dd = tempfile.mkdtemp(); out = os.path.join(dd, "s.vvp")
    srcs = srcs or ["rtl/tb_hexn_jtag_v1.v", "rtl/hexn_jtag_bridge_v1.v", "rtl/sim/bscane2_model.v"]
    subprocess.run(["iverilog", "-g2012", "-o", out, "-DFSP=16"] + list(defs) + [os.path.join(ROOT, x) for x in srcs], check=True, capture_output=True); return out
def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400; flip = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    ex = J.SimExec(build(), ["+flip=%d" % flip]); link = J.JtagLink(ex.scan); r = random.Random(5); bad = 0; sent = 0
    while sent < n:
        k = r.randint(1, 20); data = bytes(r.choice([x for x in range(255)]) for _ in range(k))
        link.write(data); got = link.read(k); sent += k
        if got != bytes((x + 1) & 255 for x in data): bad += 1; print("MISMATCH", data.hex(), got.hex())
    link.write(bytes([0xFF])); b = link.read(60); ok = b == bytes(range(60, 0, -1)); bad += not ok
    ex.close()
    print("bytes %d, mismatches %d, burst of 60 %s, scans %d, bad captures %d, resends %d (flip %d per mille)" % (sent, bad, "ok" if ok else "WRONG", link.scans, link.bad, link.resends, flip))
    print("JTAG BRIDGE SIM PASS" if bad == 0 else "JTAG BRIDGE SIM FAIL"); sys.exit(0 if bad == 0 else 1)
if __name__ == "__main__": main()
