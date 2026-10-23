"""A stand-in for ypcb tools/jtagdr.py that reaches the card through OpenOCD instead of xsdb (Alan's machine has no Xilinx tools).
Same calls the uberddr3 scripts use: read_dr(bits, ir, count, gap_ms) -> [(ms, int)], xfer_dr(words, bits), words(int, 32), gray_to_bin(g).
The int has bit 0 = the first bit shifted out (the design's LSB), as in jtagdr.py. Only the USER registers of the xc7k480t tap are used.
Use it through run_with_openocd.py, which puts it in place of `jtagdr` and then runs an unchanged ypcb script (check.py) or memlat.py.
Needs the same things as the other card tools: OPENOCD (the program, default: openocd on PATH), OPENOCD_CFG or running from ~/ypcb-00338-1p1."""
import os, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "tools"))
_ex = None
_ir = None

def _cfg():
    for c in (os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"),
              os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")):
        if c and os.path.exists(c): return c
    sys.exit("openocd.cfg not found; set OPENOCD_CFG=<path to board/ypcb-00338-1p1/openocd.cfg> or run from ~/ypcb-00338-1p1")

def _open(ir):
    global _ex, _ir
    if _ex is None:
        import hexn_jtag_host_v1 as J
        _ex = J.OpenOCDExec(_cfg(), ir=ir, bits=1024); _ir = ir
    elif ir != _ir:
        _ex.cmd("irscan %s 0x%x" % (_ex.tap, ir)); _ir = ir
    return _ex

def read_dr(bits, ir=0x02, count=1, gap_ms=1000):
    ex = _open(ir); ex.bits = bits; out = []; t0 = time.time()
    for i in range(count):
        if i: time.sleep(gap_ms / 1000.0)
        out.append((int((time.time() - t0) * 1000), ex.scan(0)))
    return out

def xfer_dr(ws, bits, ir=0x02):
    ex = _open(ir); ex.bits = bits
    v = 0
    for i, w in enumerate(ws): v |= (w & 0xFFFFFFFF) << (32 * i)
    return ex.scan(v)

def words(v, w=32, n=None):
    """Split an int into w-bit words, lowest first. n words (default: enough for 1024 bits, so indexes up to 31 always exist)."""
    n = n or max(1024 // w, (v.bit_length() + w - 1) // w)
    return [(v >> (i * w)) & ((1 << w) - 1) for i in range(n)]

def gray_to_bin(g):
    b = g; m = g >> 1
    while m: b ^= m; m >>= 1
    return b
