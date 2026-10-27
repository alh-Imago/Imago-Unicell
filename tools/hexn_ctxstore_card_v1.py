"""hexn_ctxstore_card_v1: drives the context store on the Tang Nano 20K (bitstream hexn_tang_ctxstore_v1.fs) over the USB serial port with a stream of operations, checks EVERY RD answer and all nine counters against the bit-true model (tools/hexn_ctxstore_v1.py, table size BB=17 CB=8 as built), and reports the speed.
Streams: mixed / full / sat (random, as in the RTL check), or world = the operations the layer 3 predictor itself issues on the synthetic coupled world (steady, 3000 routines: about 200,000 operations; takes minutes at 115200 baud; use --routines to shorten).
Usage:  python3 tools/hexn_ctxstore_card_v1.py --port /dev/ttyUSB1 --stream mixed --n 20000
        python3 tools/hexn_ctxstore_card_v1.py --port /dev/ttyUSB1 --stream world --routines 300
        python3 tools/hexn_ctxstore_card_v1.py --port model --stream mixed --n 2000        (dry run against the model itself: tests this script)
Load the bitstream first with `openFPGALoader -b tangnano20k hexn_tang_ctxstore_v1.fs` and do not reset the board: every run needs a freshly loaded store (the counters and table start empty). Protocol: see the header of rtl/hexn_tang_ctxstore_v1.v."""
import os, sys, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_ctxstore_v1 as C, hexn_ctxstore_rtl_check_v1 as K
NAMES = K.NAMES
class ModelPort:
    """a stand-in serial port that speaks the board protocol using the model (for testing this script)"""
    def __init__(s, bb, cb): s.st = C.CtxStore(bb, cb, 14); s.buf = bytearray(); s.out = bytearray()
    def write(s, b):
        s.buf += b
        while s.buf:
            c = chr(s.buf[0])
            need = {"W": 6, "R": 5, "S": 2, "I": 1}.get(c)
            if need is None: s.buf.pop(0); continue
            if len(s.buf) < need: return
            a = bytes(s.buf[:need]); del s.buf[:need]
            if c == "W": s.st.obs(int.from_bytes(a[1:5], "little") & 0x7FFFFFFF, a[5]); s.out += b"k"
            elif c == "R":
                f, sl = s.st.rd(int.from_bytes(a[1:5], "little") & 0x7FFFFFFF); v = 0
                for j, (ff, w) in enumerate(sl): v |= ((ff << 8) | w) << (16 * j)
                s.out += b"r" + bytes([f]) + v.to_bytes(28, "little")
            elif c == "S": s.out += b"s" + s.st.c[NAMES[a[1]]].to_bytes(4, "little")
            else: s.out += b"i\x01"
    def read(s, n): r = bytes(s.out[:n]); del s.out[:n]; return r
class Rec(C.CtxStore):
    def __init__(s, *a): super().__init__(*a); s.ops = []
    def obs(s, key, fid): s.ops.append((1, key, fid, None)); super().obs(key, fid)
    def rd(s, key):
        f, sl = super().rd(key); v = 0
        for j, (ff, w) in enumerate(sl): v |= ((ff << 8) | w) << (16 * j)
        s.ops.append((0, key, 0, (f, v))); return f, sl
def world_ops(routines, bb, cb):
    import hexn_layer3_tiers_acc_v1 as A, hexn_ctxstore_acc_v1 as X
    rec = Rec(bb, cb, 14); A.make = lambda rule, cap: X.HW(rec, nch=3, L=4, align=2)
    ev, ph = A.world(routines, False); A.run(ev, ph, "hw", 0); return rec.ops, rec.c
def stream_ops(stream, n, seed, bb, cb):
    ops = K.gen(stream, n, seed); m = Rec(bb, cb, 14)
    for obs, k, f in ops: m.obs(k, f) if obs else m.rd(k)
    return m.ops, m.c
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", required=True); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--stream", default="mixed"); ap.add_argument("--n", type=int, default=5000); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--routines", type=int, default=300)
    ap.add_argument("--bb", type=int, default=17); ap.add_argument("--cb", type=int, default=8); a = ap.parse_args()
    ops, expc = world_ops(a.routines, a.bb, a.cb) if a.stream == "world" else stream_ops(a.stream, a.n, a.seed, a.bb, a.cb)
    if a.port == "model": ser = ModelPort(a.bb, a.cb)
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5)
    def rx(n):
        b = ser.read(n)
        if len(b) != n: raise SystemExit("timeout: wanted %d bytes, got %d (is the bitstream loaded and the board not reset?)" % (n, len(b)))
        return b
    ser.write(b"I"); r = rx(2)
    if r[0:1] != b"i": raise SystemExit("no answer to the status request: %r" % r)
    print("status byte %d (bit 0 ready, bit 1 error)" % r[1]);
    if not r[1] & 1: raise SystemExit("store not ready yet (it clears its table for about 40 ms after load): run again")
    t0 = time.time(); bad = 0; nrd = 0
    for i, (obs, key, fid, exp) in enumerate(ops):
        if obs: ser.write(b"W" + key.to_bytes(4, "little") + bytes([fid])); r = rx(1); assert r == b"k", r
        else:
            ser.write(b"R" + key.to_bytes(4, "little")); r = rx(30); nrd += 1
            got = (r[1], int.from_bytes(r[2:30], "little"))
            if r[0:1] != b"r" or got != exp:
                bad += 1
                if bad <= 5: print("op %d: RD key %d: board %s, model %s" % (i, key, got, exp))
        if i and i % 20000 == 0: print("  %d / %d ops, %.0f s" % (i, len(ops), time.time() - t0))
    dt = time.time() - t0; cbad = 0
    for i, nm in enumerate(NAMES):
        ser.write(b"S" + bytes([i])); r = rx(5); v = int.from_bytes(r[1:5], "little")
        if v != expc[nm]: cbad += 1; print("counter %s: board %d, model %d" % (nm, v, expc[nm]))
    print("%d ops (%d RD) in %.1f s (%.0f ops/s over the serial link); counters %s" % (len(ops), nrd, dt, len(ops) / dt, expc))
    ok = bad == 0 and cbad == 0; print("CTXSTORE CARD CHECK PASS" if ok else "CTXSTORE CARD CHECK FAIL (%d wrong RD answers, %d wrong counters)" % (bad, cbad)); sys.exit(0 if ok else 1)
if __name__ == "__main__": main()
