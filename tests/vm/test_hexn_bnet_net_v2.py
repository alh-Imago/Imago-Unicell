"""Cross-check of the MERGED network netlist sub/verilog/hexn_bnet_net_v2.v (iverilog) against the Python merger model (tools/hexn_busnet_hw_v1.py HWNet, PORTS=1): 3 layers of 2 buses of 4 cells, 8 input lines, feedback layer 3 to layer 1, sub-queue depth 4, per-cell thresholds, 240 clocks. Every clock the fire vector of every layer must match, and the lost-packet count at the end.
Needs iverilog: FAILS (does not skip) without it."""
import os, sys, random, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", ".."); V = os.path.join(ROOT, "sub", "verilog")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_busnet_hw_v2 as W

G, PER, NIN = 2, 4, 8


def srow(n, l, r):
    ncell = G * PER
    if l == 1: return r if r < NIN else NIN + 2 * ncell + (r - NIN)
    if l == 2: return NIN + r
    return NIN + ncell + r


def test_merged_network_matches_python_model(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    total_fire = 0; total_lost = 0
    for seed in (1, 2, 3, 4):
        n = W.HWNetP(seed, th=3, leak_every=4, refr=3, sq=4, k=3, fb_k=2, fb_w=2, nin=NIN, layers=3, groups=G, per=PER)
        r = random.Random(seed); dense = seed > 2
        for g in n.th_cell: n.th_cell[g] = r.choice((1, 2) if dense else (2, 3, 4))
        words = []
        for l in (1, 2, 3):
            for b in range(G):
                for row in range(NIN + G * PER if l == 1 else G * PER):
                    s = srow(n, l, row); w = 0
                    for i in range(PER): w |= (n.table[n.gid(l, b * PER + i)].get(s, 0) & 0xF) << (4 * i)
                    words.append(w)
        inp = []; ev = {}
        for t in range(240):
            lines = [x for x in range(NIN) if r.random() < (0.5 if dense else 0.15)]; ev[t] = lines; inp.append(sum(1 << x for x in lines))
        d = tmp_path / ("s%d" % seed); d.mkdir()
        (d / "tab.hex").write_text("\n".join("%04x" % w for w in words) + "\n")
        (d / "th.hex").write_text("\n".join("%x" % n.th_cell[n.gid(l, c)] for l in (1, 2, 3) for c in range(G * PER)) + "\n")
        (d / "inp.hex").write_text("\n".join("%02x" % x for x in inp) + "\n")
        srcs = [os.path.join(V, f) for f in ("hexn_bnet_bus_v2.v", "hexn_bnet_ser_v2.v", "hexn_bnet_tbus_v2.v", "hexn_bnet_net_v2.v")]
        subprocess.run(["iverilog", "-g2012", "-s", "tbn", "-o", str(d / "sim"), os.path.join(HERE, "hexn_bnet_net_v2_tb.v")] + srcs, check=True)
        out = subprocess.run(["vvp", str(d / "sim")], cwd=d, capture_output=True, text=True, check=True).stdout
        hw = {}
        for line in out.splitlines():
            if line.startswith("F "): _, t, a, b_, c = line.split(); hw[int(t)] = (int(a, 16), int(b_, 16), int(c, 16))
        py = {}
        for t in range(240):
            f = n.step(t, ev[t])
            if t == 238: d238 = n.dropped          # the loss counters are four clocks late: after the two quiet clocks they have counted through clock 238
            v = [0, 0, 0]
            for g in f: l = n.layer_of(g); v[l - 1] |= 1 << (g - n.nin - (l - 1) * G * PER)
            py[t] = tuple(v)
        bad = [t for t in range(240) if hw[t] != py[t]]
        assert not bad, "seed %d: first difference at clock %d: hw %s python %s" % (seed, bad[0], hw[bad[0]], py[bad[0]])
        total_fire += sum(bin(x).count("1") for v in py.values() for x in v)
        lost = int([l for l in out.splitlines() if l.startswith("L ")][0].split()[1]); assert lost == d238, "lost %d vs python %d" % (lost, d238); total_lost += lost
    assert total_fire > 100          # real activity through all layers
    assert total_lost > 0            # the merge / drop paths were exercised
