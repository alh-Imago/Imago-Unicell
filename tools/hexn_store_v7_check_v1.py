"""Check of tools/hexn_store_v7.py (reference) against rtl/hexn_store_v6.v (needs iverilog): random command streams (CLR, OBS, LOAD, RD, REW, with promotion N and small sizes so that the heap fills and evictions happen), every command's eight outputs and the final counters must be equal. Uses rtl/tb_hexn_store_v6.v (-P sets sizes). Also checks the variable look-back in the reference alone: lookback 1..LMAX must give the same answers as a build whose LMAX equals that value."""
import os, random, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_store_v7 as M
def stream(seed, n, A=6, mix=(0.01, 0.7, 0.05, 0.2, 0.04)):
    rnd = random.Random(seed); T = [[rnd.randrange(A) for _ in range(A)] for _ in range(A)]; ev = [rnd.randrange(A), rnd.randrange(A)]; cmds = []; t = 0
    for i in range(n):
        c = rnd.choices([M.CLR, M.OBS, M.LOAD, M.RD, M.REW], mix)[0]
        e = T[ev[-2]][ev[-1]] if rnd.random() < 0.8 else rnd.randrange(A)
        if c in (M.OBS, M.LOAD): ev.append(e)
        if i == n // 2: T = [[rnd.randrange(A) for _ in range(A)] for _ in range(A)]
        t += rnd.choice((1, 1, 3, 9, 40)); cmds.append((c, e if c in (M.OBS, M.LOAD, M.RD) else 0, rnd.randrange(256) if c == M.REW else 0, t))
    return cmds
def rtl(cmds, N, params, d):
    f = os.path.join(d, "stim.hex"); open(f, "w").write("\n".join("%08x" % ((c << 28) | (e << 24) | (r << 16) | (t & 0xFFFF)) for c, e, r, t in cmds) + "\n"); exe = os.path.join(d, "sim")
    subprocess.run(["iverilog", "-g2005-sv", "-o", exe, "-s", "tb_hexn_store_v6"] + ["-Ptb_hexn_store_v6.%s=%s" % kv for kv in params.items()] + [os.path.join(ROOT, "rtl/tb_hexn_store_v6.v"), os.path.join(ROOT, "rtl/hexn_store_v6.v")], check=True)
    lg = os.path.join(d, "log.txt"); subprocess.run(["vvp", exe, "+stim=" + f, "+count=%d" % len(cmds), "+log=" + lg, "+n=%d" % N], capture_output=True, text=True)
    L = open(lg).read().split("\n")[:-1]; return L[:-1], L[-1]
def model(cmds, N, params, **kw):
    m = M.StoreV7(N=N, IB=params["IB"], RB=params["RB"], RSB=params.get("RSB", 2), P=params.get("P", 4), CCAP=params.get("CCAP", 32), **kw); lines = []
    for c, e, r, t in cmds:
        o = m.step(c, e, t, r)
        lines.append("%d %d %d %d %d %d %d %d" % (o["verdict"], o["vlevel"], o["plevel"], o["pbest"], o["pbest_seen"], o["ptotal"], o["gbest"], o["gval"]))
    return lines, "S %d %d %d %d %d %d" % (m.n_known, m.n_cand, m.n_promoted, m.n_dropk, m.n_dropc, m.n_evict)
def main():
    d = tempfile.mkdtemp(); fails = 0
    for seed, N, params in ((1, 1, dict(IB=7, RB=4)), (2, 3, dict(IB=7, RB=4)), (3, 1, dict(IB=10, RB=9)), (4, 2, dict(IB=6, RB=3)), (5, 1, dict(IB=5, RB=3))):
        cmds = stream(seed, 1500); a, sa = rtl(cmds, N, params, d); b, sb = model(cmds, N, params)
        bad = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]; ok = (not bad) and sa == sb and len(a) == len(b)
        print(f"seed {seed} N={N} {params}: RTL v6 against reference: {'EQUAL' if ok else 'DIFFERENT'} | {sa} | first difference at command {bad[0] if bad else '-'}" + ("" if ok else f"\n   RTL {a[bad[0]] if bad else ''} / {sa}\n   REF {b[bad[0]] if bad else ''} / {sb}")); fails += (not ok)
    # variable look-back inside the reference: a build with LMAX = k and lookback = k equals LMAX = 8 with lookback = k, except that history beyond k is kept
    cmds = stream(9, 1500); params = dict(IB=10, RB=9)
    for k in (1, 2, 3, 5):
        x, sx = model(cmds, 1, params, LMAX=k, lookback=k); y, sy = model(cmds, 1, params, LMAX=8, lookback=k); same = (x == y and sx == sy); print(f"look-back {k}: LMAX={k} build equals LMAX=8 build set to {k}: {same}"); fails += (not same)
    return fails
if __name__ == "__main__": sys.exit(1 if main() else 0)
