"""hexn_store_rtl_check_v2: rtl/hexn_store_v3.v (store with reward values, goal read, REW) in iverilog against the bit-true model tools/hexn_store_v3.py, command by command (all outputs including gbest and gval) and the final tables slot by slot (key, seen, contra, VALUE) plus the counters. Clone of hexn_store_rtl_check_v1.py (untouched). Needs iverilog (exits with an error without it).
Cases: (1) host load of runs 1 and 2, real run 3 online, a retrieve before every event, a reward at every goal key; (2) the reward world: 500 random routines of the four real routines with random +64/-32 rewards and goal-read queries, N=2 W=400, step 2^-3, context 1; (3) heavy noise with tiny tables (known 16, candidate 8), rewards, step 2^-2, goal context 3, 16-bit clock wrapping; (4) random commands including REW with random rewards, N=2, 4 candidate slots, step 2^-5, goal context 2.
Usage: python3 tools/hexn_store_rtl_check_v2.py"""
import os, sys, random, subprocess, tempfile, shutil, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_store_v3 as M, hexn_layer2_v2 as V, hexn_host_promote_v1 as HP
from hexn_reward_v1 import TREE
RTL = "hexn_store_v3"
def run_case(name, cmds, N, W, KCAP, CCAP, vshift, glvl, work):
    ka, ca = max(1, math.ceil(math.log2(KCAP))), max(1, math.ceil(math.log2(CCAP)))
    exe = os.path.join(work, "tb_" + name); stim = os.path.join(work, name + ".hex"); log = os.path.join(work, name + ".log")
    subprocess.run(["iverilog", "-g2012", "-o", exe, "-Ptb_%s.KCAP=%d" % (RTL, KCAP), "-Ptb_%s.CCAP=%d" % (RTL, CCAP), "-Ptb_%s.KA=%d" % (RTL, ka), "-Ptb_%s.CA=%d" % (RTL, ca), os.path.join(ROOT, "rtl/%s.v" % RTL), os.path.join(ROOT, "rtl/tb_%s.v" % RTL)], check=True)
    open(stim, "w").write("\n".join("%08x" % ((c << 28) | (e << 24) | ((r & 0xFF) << 16) | (t & 0xFFFF)) for c, e, t, r in cmds) + "\n")
    out = subprocess.run(["vvp", "-n", exe, "+stim=" + stim, "+count=%d" % len(cmds), "+n=%d" % N, "+w=%d" % W, "+vshift=%d" % vshift, "+glvl=%d" % glvl, "+log=" + log], check=True, capture_output=True, text=True).stdout
    mc = [l for l in out.split("\n") if l.startswith("MAXCYC")]
    lines = open(log).read().split("\n"); mod = M.StoreV3(N=N, W=W, KCAP=KCAP, CCAP=CCAP, vshift=vshift, glvl=glvl); bad = []
    for i, (c, e, t, r) in enumerate(cmds):
        o = mod.step(c, e, t, r if r < 128 else r - 256); want = " ".join(str(o[k]) for k in ("verdict", "vlevel", "plevel", "pbest", "pbest_seen", "ptotal", "gbest")) + " %d" % (o["gval"] if o["gval"] < 128 else o["gval"] - 256)
        if lines[i] != want: bad.append((i, lines[i], want))
    rest = lines[len(cmds):]
    S = "S %d %d %d %d %d" % (mod.n_known, mod.n_cand, mod.promoted, mod.dropk, mod.dropc)
    if rest[0] != S: bad.append(("counters", rest[0], S))
    for i, e in enumerate(mod.k):
        w = "K %d %d %d %d %d %d" % ((i, 1, M.M2.key_bits(e[0]), e[1], e[2], mod.val[i]) if e else (i, 0, 0, 0, 0, 0))
        if rest[1 + i] != w: bad.append(("known slot", rest[1 + i], w))
    for i, e in enumerate(mod.c):
        w = "C %d %d %d %d %d" % ((i, 1, M.M2.key_bits(e[0]), e[1], e[2]) if e else (i, 0, 0, 0, 0))
        if rest[1 + KCAP + i] != w: bad.append(("cand slot", rest[1 + KCAP + i], w))
    mod.maxcyc = mc[0].replace("MAXCYC ", "").replace(" (cmd", " clocks (cmd") if mc else "?"
    return len(cmds), bad, mod
def seq(events, op, t0, rd=False, step=1, rew_at=None, rnd=None):
    out = [(M.CLR, 0, 0, 0)]
    for i, x in enumerate(events):
        if rd and i: out.append((M.RD, x, t0 + i * step, 0))
        out.append((op, x, t0 + i * step, 0))
        if rew_at is not None and x in rew_at: out.append((M.REW, 0, 0, rnd.choice((64, -32)) & 0xFF))
    return out
def main():
    if not (shutil.which("iverilog") and shutil.which("vvp")): print("iverilog/vvp missing: cannot run"); sys.exit(1)
    V.R = V.runs(); runs = [[k - 12 for k, _ in r] for r in V.R]; rb = HP.real_blocks(); pool = [tuple(k - 12 for k in b) for b in set(b for run in rb[:2] for b in run)]
    work = tempfile.mkdtemp(prefix="hexn_store3_"); res = []; rnd = random.Random(4)
    c1 = seq(runs[0], M.LOAD, 0) + seq(runs[1], M.LOAD, 0) + seq(runs[2], M.OBS, 1000, True, 1, (6, 7), rnd)
    c2 = [(M.CLR, 0, 0, 0)]; t = 0; first = True
    for _ in range(500):
        pref = ()
        while pref in TREE:
            e = rnd.choice(TREE[pref]); 
            if not first: c2.append((M.RD, 0, t, 0))
            first = False; c2.append((M.OBS, e - 1, t, 0)); t += 1; pref += (e,)
        c2.append((M.REW, 0, 0, rnd.choice((64, -32)) & 0xFF))
    base = [k - 12 for b in (rb[0] + rb[1]) for k in b]; sq = []
    for _ in range(800):
        b = list(rnd.choice(pool))
        if rnd.random() < 0.3: b.insert(rnd.randrange(len(b)), rnd.randrange(0, 6))
        sq += b
    c3 = seq(base, M.LOAD, 0) + seq(sq, M.OBS, 65400, True, 1, (5, 6), rnd)
    c4 = [(M.CLR, 0, 0, 0)]
    for i in range(1500): c4.append((rnd.choice([M.OBS, M.OBS, M.OBS, M.LOAD, M.RD, M.REW, M.REW if i % 97 else M.CLR]), rnd.randrange(0, 8), i * 3, rnd.randrange(-128, 128) & 0xFF))
    for name, cmds, N, W, KC, CC, vs, gl in (("real_loaded", c1, 3, 80, 128, 32, 3, 1), ("reward_world", c2, 2, 400, 128, 32, 3, 1), ("noise_tiny_tables", c3, 3, 80, 16, 8, 2, 3), ("random_stress", c4, 2, 40, 32, 4, 5, 2)):
        n, bad, mod = run_case(name, cmds, N, W, KC, CC, vs, gl, work)
        print("v3 %-18s %5d commands | mismatches %d | known %d cand %d promoted %d dropped known %d cand %d | slowest command %s" % (name, n, len(bad), mod.n_known, mod.n_cand, mod.promoted, mod.dropk, mod.dropc, mod.maxcyc))
        for b in bad[:3]: print("   first mismatch:", b)
        res.append(len(bad))
    shutil.rmtree(work, ignore_errors=True); sys.exit(1 if any(res) else 0)
if __name__ == "__main__": main()
