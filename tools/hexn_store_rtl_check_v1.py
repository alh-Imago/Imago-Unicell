"""hexn_store_rtl_check_v1: runs rtl/hexn_store_v1.v in iverilog against the bit-true model tools/hexn_store_v2.py on the same command streams and compares EVERY command's outputs and the final tables slot by slot (and the counters). Needs iverilog (refuses to run without it; a SKIP would look like a pass).
Cases: (1) host load of runs 1 and 2, real run 3 online with a retrieve before every event; (2) cold start by the promotion rule, runs 1, 2 then 3; (3) heavy noise in real blocks with tiny tables (KNOWN 16, CANDIDATE 8: constant eviction) and the 16-bit clock wrapping; (4) random event stress with N=2 and 4 candidate slots.
Usage: python3 tools/hexn_store_rtl_check_v1.py [hexn_store_v1 | hexn_store_v2]   (default: both)"""
import os, sys, random, subprocess, tempfile, shutil, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_store_v2 as M, hexn_layer2_v2 as V, hexn_host_promote_v1 as HP
def run_case(name, cmds, N, W, KCAP, CCAP, work, rtl="hexn_store_v1"):
    ka, ca = max(1, math.ceil(math.log2(KCAP))), max(1, math.ceil(math.log2(CCAP)))
    exe = os.path.join(work, "tb_%s_%s" % (rtl, name)); stim = os.path.join(work, rtl + name + ".hex"); log = os.path.join(work, rtl + name + ".log")
    subprocess.run(["iverilog", "-g2012", "-o", exe, "-Ptb_%s.KCAP=%d" % (rtl, KCAP), "-Ptb_%s.CCAP=%d" % (rtl, CCAP), "-Ptb_%s.KA=%d" % (rtl, ka), "-Ptb_%s.CA=%d" % (rtl, ca),
                    os.path.join(ROOT, "rtl/%s.v" % rtl), os.path.join(ROOT, "rtl/tb_%s.v" % rtl)], check=True)
    open(stim, "w").write("\n".join("%06x" % ((c << 20) | (e << 16) | (t & 0xFFFF)) for c, e, t in cmds) + "\n")
    r = subprocess.run(["vvp", "-n", exe, "+stim=" + stim, "+count=%d" % len(cmds), "+n=%d" % N, "+w=%d" % W, "+log=" + log], check=True, capture_output=True, text=True).stdout
    mc = [l for l in r.split("\n") if l.startswith("MAXCYC")]
    lines = open(log).read().split("\n"); mod = M.StoreV2(N=N, W=W, KCAP=KCAP, CCAP=CCAP); bad = []
    for i, (c, e, t) in enumerate(cmds):
        o = mod.step(c, e, t); want = " ".join(str(o[k]) for k in ("verdict", "vlevel", "plevel", "pbest", "pbest_seen", "ptotal"))
        if lines[i] != want: bad.append((i, lines[i], want))
    rest = lines[len(cmds):]
    S = "S %d %d %d %d %d" % (mod.n_known, mod.n_cand, mod.promoted, mod.dropk, mod.dropc)
    if rest[0] != S: bad.append(("counters", rest[0], S))
    for i, e in enumerate(mod.k):
        w = "K %d %d %d %d %d" % ((i, 1, M.key_bits(e[0]), e[1], e[2]) if e else (i, 0, 0, 0, 0))
        if rest[1 + i] != w: bad.append(("known slot", rest[1 + i], w))
    for i, e in enumerate(mod.c):
        w = "C %d %d %d %d %d" % ((i, 1, M.key_bits(e[0]), e[1], e[2]) if e else (i, 0, 0, 0, 0))
        if rest[1 + KCAP + i] != w: bad.append(("cand slot", rest[1 + KCAP + i], w))
    mod.maxcyc = mc[0].replace("MAXCYC ", "").replace(" (cmd", " clocks (cmd") if mc else "?"
    return len(cmds), bad, mod
def seq_cmds(seq, op, t0, step=1, first_rd=False):
    out = [(M.CLR, 0, 0)]
    for i, x in enumerate(seq):
        if first_rd and i: out.append((M.RD, x, t0 + i * step))
        out.append((op, x, t0 + i * step))
    return out
def main():
    if not (shutil.which("iverilog") and shutil.which("vvp")): print("iverilog/vvp missing: cannot run"); sys.exit(1)
    V.R = V.runs(); runs = [[k - 12 for k, _ in r] for r in V.R]; rb = HP.real_blocks(); pool = [tuple(k - 12 for k in b) for b in set(b for run in rb[:2] for b in run)]
    work = tempfile.mkdtemp(prefix="hexn_store_"); results = []
    c1 = seq_cmds(runs[0], M.LOAD, 0) + seq_cmds(runs[1], M.LOAD, 0) + seq_cmds(runs[2], M.OBS, 1000, 1, True)
    c2 = []; t = 0
    for r in runs: c2 += seq_cmds(r, M.OBS, t); t += 100
    rnd = random.Random(5); base = [x for b in (rb[0] + rb[1]) for x in [k - 12 for k in b]]; seq = []
    for _ in range(1500):
        b = list(rnd.choice(pool))
        if rnd.random() < 0.3: b.insert(rnd.randrange(len(b)), rnd.randrange(0, 6))
        seq += b
    c3 = seq_cmds(base, M.LOAD, 0) + seq_cmds(seq, M.OBS, 65400, 1, True)
    rnd = random.Random(8); c4 = [(M.CLR, 0, 0)]
    for i in range(1500): c4.append((rnd.choice([M.OBS, M.OBS, M.OBS, M.LOAD, M.RD, M.CLR if i % 97 == 0 else M.OBS]), rnd.randrange(0, 8), i * 3))
    rtls = [a for a in sys.argv[1:]] or ["hexn_store_v1", "hexn_store_v2"]
    for rtl in rtls:
      for name, cmds, N, W, KC, CC in (("real_loaded", c1, 3, 80, 128, 32), ("cold_start", c2, 3, 80, 128, 32), ("noise_tiny_tables", c3, 3, 80, 16, 8), ("random_stress", c4, 2, 40, 32, 4)):
        n, bad, mod = run_case(name, cmds, N, W, KC, CC, work, rtl)
        print(rtl[-2:], "%-18s %5d commands | mismatches %d | known %d cand %d promoted %d dropped known %d cand %d | slowest command %s" % (name, n, len(bad), mod.n_known, mod.n_cand, mod.promoted, mod.dropk, mod.dropc, mod.maxcyc))
        for b in bad[:3]: print("   first mismatch:", b)
        results.append(len(bad))
    shutil.rmtree(work, ignore_errors=True); sys.exit(1 if any(results) else 0)
if __name__ == "__main__": main()
