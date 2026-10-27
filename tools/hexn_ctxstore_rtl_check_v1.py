"""hexn_ctxstore_rtl_check_v1: co-simulation of rtl/hexn_ctxstore_v1.v (with our SDRAM controller and the SDRAM model) against the bit-true model tools/hexn_ctxstore_v1.py. Generates a random operation stream, runs both, and compares EVERY RD answer (found + all 14 slots) and ALL nine counters. Needs iverilog (fails, not skips, without it).
Streams: 'mixed' (random keys from a pool, RD/OBS mix, many followers per key so slots are replaced), 'sat' (one key/follower observed 600 times so the weight saturates and halves), 'full' (more keys than buckets so probes overflow).
Usage: python3 tools/hexn_ctxstore_rtl_check_v1.py [stream] [n_ops] [seed] [BB] [CB]"""
import os, sys, random, subprocess, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_ctxstore_v1 as C
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = ["rtl/tb_hexn_ctxstore_v1.v", "rtl/hexn_ctxstore_v1.v", "rtl/hexn_sdram_v1.v", "rtl/sim/sdram_model_v1.v"]
def gen(stream, n, seed):
    r = random.Random(seed); ops = []
    if stream == "sat":
        for i in range(n):
            ops.append((1, 12345, 7) if i % 3 else (0, 12345, 0))
        return ops
    pool = [r.getrandbits(31) for _ in range({"mixed": 40, "full": 400}[stream])]
    hot = pool[:3]
    for i in range(n):
        k = r.choice(hot) if r.random() < 0.3 else r.choice(pool)
        if r.random() < 0.55: ops.append((1, k, r.randint(1, 30 if k in hot else 6)))
        else: ops.append((0, k, 0))
    return ops
def model(ops, bb, cb):
    m = C.CtxStore(bb, cb, 14); out = []
    for obs, k, f in ops:
        if obs: m.obs(k, f)
        else:
            fd, sl = m.rd(k); v = 0
            for j, (ff, w) in enumerate(sl): v |= ((ff << 8) | w) << (16 * j)
            out.append((fd, v))
    return out, m.c
def rtl(ops, bb, cb):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    d = tempfile.mkdtemp(); f = os.path.join(d, "ops.hex"); out = os.path.join(d, "t.vvp")
    with open(f, "w") as fh:
        for obs, k, fid in ops: fh.write("%016x\n" % ((obs << 40) | (fid << 31) | k))
    subprocess.run(["iverilog", "-g2012", "-P", "tb_hexn_ctxstore_v1.BB=%d" % bb, "-P", "tb_hexn_ctxstore_v1.CB=%d" % cb, "-o", out] + [os.path.join(ROOT, s) for s in SRC], check=True, capture_output=True)
    o = subprocess.run(["vvp", out, "+OPS=" + f, "+N=%d" % len(ops)], capture_output=True, text=True, timeout=3000).stdout
    res = []; cnt = {}; err = None
    for line in o.splitlines():
        p = line.split()
        if p and p[0] == "R": res.append((int(p[2]), int(p[3], 16)))
        elif p and p[0] == "C": cnt[int(p[1])] = int(p[2])
        elif p and p[0] == "ERR": err = int(p[1])
        elif "TIMEOUT" in line: raise AssertionError(line)
    return res, cnt, err, o
NAMES = ["ops", "cache_hit", "filter_skip", "sd_probe", "sd_rd", "sd_wr", "created", "slot_evict", "overflow"]
def check(stream="mixed", n=3000, seed=1, bb=8, cb=4):
    ops = gen(stream, n, seed); me, mc = model(ops, bb, cb); re_, rc, err, o = rtl(ops, bb, cb)
    bad = []
    if len(me) != len(re_): bad.append("RD answers: model %d, rtl %d" % (len(me), len(re_)))
    else:
        for i, (a, b) in enumerate(zip(me, re_)):
            if a != b: bad.append("RD answer %d differs: model %s rtl %s" % (i, a, b)); break
    for i, nme in enumerate(NAMES):
        if mc[nme] != rc.get(i): bad.append("counter %s: model %d rtl %s" % (nme, mc[nme], rc.get(i)))
    if err: bad.append("rtl err flag set")
    return bad, mc
if __name__ == "__main__":
    a = sys.argv[1:]; stream = a[0] if a else "mixed"; n = int(a[1]) if len(a) > 1 else 3000; seed = int(a[2]) if len(a) > 2 else 1
    bb = int(a[3]) if len(a) > 3 else 8; cb = int(a[4]) if len(a) > 4 else 4
    bad, mc = check(stream, n, seed, bb, cb); print(stream, n, seed, "BB=%d CB=%d" % (bb, cb), "counters", mc)
    print("CTXSTORE CHECK PASS" if not bad else "CTXSTORE CHECK FAIL\n" + "\n".join(bad))
    sys.exit(1 if bad else 0)
