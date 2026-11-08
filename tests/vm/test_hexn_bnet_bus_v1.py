"""Cross-check of sub/verilog/hexn_bnet_bus_v1.v (iverilog) against the Python bus network model, one bus, one external input per clock, 160 clocks.
Needs iverilog: the test FAILS (does not skip) without it, so a missing toolchain cannot look like a pass."""
import os, sys, random, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_busnet_homeo_v1 as H


def test_bus_matches_python_model(tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required"
    refires = 0
    for seed in (1, 2, 3, 4, 5, 6):
        dense = seed > 3
        n = H.AdaptNet(seed, th=4, leak_every=4, refr=3, qdepth=8, k=10, nin=48, layers=1, groups=1, per=16)
        r = random.Random(seed); cells = [n.gid(1, i) for i in range(16)]
        for g in cells: n.th_cell[g] = r.choice((1, 2) if dense else (3, 4, 5, 6))
        tab = []
        for s in range(48):
            word = 0
            for i, g in enumerate(cells): word |= (n.table[g].get(s, 0) & 0xF) << (4 * i)
            tab.append(word)
        inp = []; ev = {}
        for t in range(160):
            if r.random() < (1.0 if dense else 0.7): s = r.randrange(8 if dense else 48); inp.append(0x40 | s); ev[t] = [s]
            else: inp.append(0)
        d = tmp_path / ("s%d" % seed); d.mkdir()
        (d / "tab.hex").write_text("\n".join("%016x" % w for w in tab) + "\n"); (d / "th.hex").write_text("\n".join("%x" % n.th_cell[g] for g in cells) + "\n"); (d / "inp.hex").write_text("\n".join("%02x" % x for x in inp) + "\n")
        subprocess.run(["iverilog", "-g2012", "-o", str(d / "sim"), os.path.join(HERE, "hexn_bnet_bus_v1_tb.v"), os.path.join(ROOT, "sub", "verilog", "hexn_bnet_bus_v1.v")], check=True)
        out = subprocess.run(["vvp", str(d / "sim")], cwd=d, capture_output=True, text=True, check=True).stdout
        hw = {}
        for line in out.splitlines():
            if line.startswith("F "): _, t, m = line.split(); hw[int(t)] = int(m, 16)
        fired = n.run(ev, 160) if False else None
        py = {}
        for t in range(160):
            f = n.step(t, ev.get(t, ())); py[t] = sum(1 << cells.index(g) for g in f)
        assert hw == py, "seed %d: first difference at clock %s" % (seed, next(t for t in range(160) if hw[t] != py[t]))
        assert sum(1 for v in py.values() if v) > 5
        last = {}
        for t in range(160):
            for i in range(16):
                if py[t] >> i & 1:
                    if i in last and t - last[i] <= 4: refires += 1
                    last[i] = t          # the test must actually have fired
        dr = [l for l in out.splitlines() if l.startswith("D ")][0].split()[1]; assert int(dr) == n.dropped
    assert refires > 10          # the refractory period (3 clocks) must really have been exercised
