"""hexn_store_rtl_check_v3: rtl/hexn_store_v5.v (address index + dense heap, wide events) in iverilog against the bit-true model tools/hexn_store_v5.py, command by command (verdict, levels, best, totals, goal read) and then the whole memory slot by slot (index, row headers, entry words, candidates) and the counters.
Cases: (A) random commands with structured events, 16 classes; (B) tiny tables that force dropped entries (index 16 slots, probe 2, heap 8 rows of 2); (C) a tic-tac-toe move stream (random legal games, a retrieve before each move, a reward at the end); (D) small candidate table, N=3. Usage: python3 tools/hexn_store_rtl_check_v3.py"""
import os, sys, random, subprocess, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_store_v5 as M
import hexn_ttt_v1 as T
RTL = "hexn_store_v5"
def pack(ctx, EVB): return sum(x << (EVB * (len(ctx) - 1 - i)) for i, x in enumerate(ctx))
def tagbits(tag, EVB): j, ctx = tag; return (j << (3 * EVB)) | pack(ctx, EVB)
def run_case(name, cmds, work, EVB, IB, RB, RSB, P, CCAP, N, W, vshift, glvl):
    CA = max(1, (CCAP - 1).bit_length()); R = 1 << RSB
    exe = os.path.join(work, "tb_" + name); stim = os.path.join(work, name + ".hex"); log = os.path.join(work, name + ".log")
    ps = ["-Ptb_%s.%s=%d" % (RTL, k, v) for k, v in (("EVB", EVB), ("IB", IB), ("RB", RB), ("RSB", RSB), ("P", P), ("CCAP", CCAP), ("CA", CA))]
    subprocess.run(["iverilog", "-g2012", "-o", exe] + ps + [os.path.join(ROOT, "rtl/%s.v" % RTL), os.path.join(ROOT, "rtl/tb_%s.v" % RTL)], check=True, capture_output=True)
    open(stim, "w").write("\n".join("%08x" % ((c << 28) | (e << 24) | ((r & 0xFF) << 16) | (t & 0xFFFF)) for c, e, t, r in cmds) + "\n")
    out = subprocess.run(["vvp", "-n", exe, "+stim=" + stim, "+count=%d" % len(cmds), "+n=%d" % N, "+w=%d" % W, "+vshift=%d" % vshift, "+glvl=%d" % glvl, "+log=" + log], check=True, capture_output=True, text=True).stdout
    mc = [l for l in out.split("\n") if l.startswith("MAXCYC")]; lines = open(log).read().split("\n")
    mod = M.StoreV5(N=N, W=W, CCAP=CCAP, vshift=vshift, glvl=glvl, EVB=EVB, IB=IB, R=R, HROWS=1 << RB, P=P); bad = []
    for i, (c, e, t, r) in enumerate(cmds):
        o = mod.step(c, e, t, r if r < 128 else r - 256); want = " ".join(str(o[k]) for k in ("verdict", "vlevel", "plevel", "pbest", "pbest_seen", "ptotal", "gbest")) + " %d" % (o["gval"] if o["gval"] < 128 else o["gval"] - 256)
        if lines[i] != want: bad.append((i, lines[i], want))
    rest = lines[len(cmds):]; pos = 0
    S = "S %d %d %d %d %d" % (mod.n_known, mod.n_cand, mod.promoted, mod.dropk, mod.dropc)
    if rest[pos] != S: bad.append(("counters", rest[pos], S))
    pos += 1
    for i in range(1 << IB):
        e = mod.index[i]; w = "I %d %d %d %d" % ((i, 1, tagbits(e["tag"], EVB), e["row"]) if e else (i, 0, 0, 0))
        if rest[pos] != w: bad.append(("index", rest[pos], w))
        pos += 1
    for i in range(1 << RB):
        r = mod.heap[i] if i < len(mod.heap) else None; w = "H %d %d %d" % ((i, 1, r["next"]) if r and r["next"] is not None else (i, 0, 0))
        if rest[pos] != w: bad.append(("header", rest[pos], w))
        pos += 1
    for i in range(1 << (RB + RSB)):
        row, s = divmod(i, R); sl = mod.heap[row]["slots"][s] if row < len(mod.heap) and s < len(mod.heap[row]["slots"]) else None
        w = "E %d %d %d %d %d %d" % ((i, 1, sl[0], sl[1][0], sl[1][1], sl[1][2]) if sl else (i, 0, 0, 0, 0, 0))
        if rest[pos] != w: bad.append(("entry", rest[pos], w))
        pos += 1
    for i, e in enumerate(mod.c):
        w = "C %d %d %d %d %d" % ((i, 1, (e[0][0] << (4 * EVB)) | (pack(e[0][1], EVB) << EVB) | e[0][2], e[1], e[2]) if e else (i, 0, 0, 0, 0))
        if rest[pos] != w: bad.append(("cand", rest[pos], w))
        pos += 1
    mod.maxcyc = mc[0].replace("MAXCYC ", "").replace(" (cmd", " clocks (cmd") if mc else "?"
    return len(cmds), bad, mod
def workload(rnd, n, nev, small=5):
    cmds = [(M.CLR, 0, 0, 0)]; t = 0
    for i in range(n):
        t += rnd.randint(1, 5); c = rnd.random()
        if c < 0.02: cmds.append((M.CLR, 0, t, 0))
        elif c < 0.10: cmds.append((M.LOAD, rnd.randrange(nev), t, 0))
        elif c < 0.25: cmds.append((M.RD, 0, t, 0))
        elif c < 0.33: cmds.append((M.REW, 0, t, rnd.choice((64, -32, 16, 0, 100, -100)) & 0xFF))
        else: cmds.append((M.OBS, rnd.randrange(small) if rnd.random() < 0.75 else rnd.randrange(nev), t, 0))
    return cmds
def ttt(rnd, games):
    cmds = []; t = 0
    for g in range(games):
        b = [0] * 9; cmds.append((M.CLR, 0, t, 0)); t += 1; cmds.append((M.OBS, 9, t, 0)); turn = 1
        while True:
            t += 1
            if turn == 1: cmds.append((M.RD, 0, t, 0))
            c = rnd.choice(T.legal(b)); b[c] = turn; t += 1; cmds.append((M.OBS, c, t, 0)); w = T.winner(b)
            if w or not T.legal(b): break
            turn = 3 - turn
        cmds.append((M.REW, 0, 0, {1: 64, 2: -32, 0: 16}[w] & 0xFF))
    return cmds
def main():
    if not (shutil.which("iverilog") and shutil.which("vvp")): print("iverilog/vvp missing: cannot run"); sys.exit(1)
    work = tempfile.mkdtemp(prefix="hexn_store5_"); res = []; rnd = random.Random(11)
    cases = [("wide_random", workload(rnd, 2500, 16), dict(EVB=4, IB=10, RB=9, RSB=2, P=4, CCAP=32, N=2, W=80, vshift=3, glvl=2)),
             ("tiny_forced_drops", workload(rnd, 1500, 8, small=8), dict(EVB=3, IB=4, RB=3, RSB=1, P=2, CCAP=8, N=2, W=40, vshift=2, glvl=3)),
             ("tictactoe_stream", ttt(rnd, 120), dict(EVB=4, IB=10, RB=9, RSB=2, P=4, CCAP=32, N=2, W=1000, vshift=3, glvl=2)),
             ("small_cand_n3", workload(rnd, 2000, 16, small=6), dict(EVB=4, IB=9, RB=7, RSB=2, P=3, CCAP=4, N=3, W=200, vshift=4, glvl=1))]
    for name, cmds, kw in cases:
        n, bad, mod = run_case(name, cmds, work, **kw)
        print("v5 %-18s %5d commands | mismatches %d | known %d cand %d promoted %d dropped known %d cand %d | heap rows %d | slowest command %s" % (name, n, len(bad), mod.n_known, mod.n_cand, mod.promoted, mod.dropk, mod.dropc, len(mod.heap), mod.maxcyc))
        for b in bad[:3]: print("   first mismatch:", b)
        res.append(len(bad))
    shutil.rmtree(work, ignore_errors=True); sys.exit(1 if any(res) else 0)
if __name__ == "__main__": main()
