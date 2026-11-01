"""tests/vm/test_hexn_open10_v1.py -- Hex-N open unit stage 6 (modest, 1 Nov 2026): SAVE AND LOAD OF THE NEURAL JUDGE'S WEIGHTS as table space 6 in the generic save/load path (hexn_open_top_v10 + hexn_tabs_v4 + hexn_neural_v1), in simulation through the whole unit over SPI. Alan, 16:47/16:49: save and restore of the weights, kept modest.
Checks against the integer model tools/hexn_layer1_int_v4.py (OnlineInt4): starting values loaded through space 6, then 40 evals and learning steps, every y equals the model; the 8 values saved equal the model's weights and bias; after loading zeros the probe equals the model with zero weights; after loading the saved words back the probe equals the model with the learned weights and a second save equals the first; while the judge is busy a save writes nothing and a load changes nothing. Mutations are caught. Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog"); R = os.path.join(ROOT, "rtl")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_layer1_int_v4 as I4  # noqa: E402
FILES = [V + "/hexn_open_top_v10.v", V + "/hexn_pins_v1.v", V + "/hexn_presets_v1.v", V + "/spi_bridge_v2.v", V + "/hexn_tabs_v4.v", V + "/hexn_react_core_v2.v", V + "/hexn_morse_core_v2.v", V + "/hexn_raw_engine_v4.v", V + "/hexn_demo_rom_v1.v", V + "/hexn_morse_gen_v1.v", V + "/hexn_scorer_v1.v", V + "/hexn_scorer_v3.v", V + "/hw262_shield_v2.v", R + "/hexn_neural_v1.v", R + "/hexn_tanh512_v1.v"]
WB = 14


def s16(v): v &= 0xFFFF; return v - 65536 if v & 0x8000 else v
def pack(x): return sum(v << (6 * i) for i, v in enumerate(x))


def model(rnd, n=40):
    j = I4.OnlineInt4("blank", "TD", WB); W = [rnd.randint(-3000, 3000) for _ in range(7)]; B = rnd.randint(-3000, 3000); j.W = list(W); j.Bq = B
    words, ys = [], []
    for _ in range(n):
        x = [rnd.randint(0, 40) for _ in range(7)]; xp = pack(x); o = j.out(x)
        if rnd.random() < 0.4: words.append((xp << 9)); ys.append(o)
        else:
            tq = rnd.randint(-256, 256); m = 2 if rnd.random() < 0.25 else 1; words.append((1 << 62) | ((1 if m == 2 else 0) << 61) | ((tq & 0x3FF) << 51) | (xp << 9)); ys.append(o)
            err = o - tq; gain = 256 - ((o * o) >> 8); sh = 29 - WB; rr = 1 << (sh - 1)
            for i in range(7): j.W[i] -= (5 * err * gain * x[i] * m + rr) >> sh
            j.Bq -= (5 * err * gain * 64 * m + rr) >> sh
    return j, W, B, words, ys


def run(d, tabs_text=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    rnd = random.Random(7); j, W, B, words, ys = model(rnd)
    probe_x = [rnd.randint(0, 40) for _ in range(7)]
    open(os.path.join(d, "w0.hex"), "w").write("\n".join("%08x" % (w & 0xFFFF) for w in W + [B]) + "\n")
    open(os.path.join(d, "ops.hex"), "w").write("\n".join("%016x" % w for w in words) + "\n"); open(os.path.join(d, "probe.hex"), "w").write("%016x\n" % (pack(probe_x) << 9))
    tb = open(os.path.join(ROOT, "tests", "hexn_open10", "tb_hexn_open10_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp"); files = list(FILES)
    if tabs_text is not None:
        p = os.path.join(d, "tabs_mut.v"); open(p, "w").write(tabs_text); files[files.index(V + "/hexn_tabs_v4.v")] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    out = subprocess.run(["vvp", o, "+dir=" + d, "+nops=%d" % len(words)], capture_output=True, text=True, timeout=3000).stdout
    return out, (j, ys, probe_x)


def parse(out):
    r = {"Y": [], "Z": [], "P": [], "P2": [], "W": {}, "W2": {}, "S": {}, "G": {}}
    for l in out.splitlines():
        t = l.split()
        if not t: continue
        if t[0] in ("Y", "Z", "P", "P2"): r[t[0]].append(int(t[1]))
        elif t[0] in ("W", "W2", "S", "G"): r[t[0]][int(t[1])] = int(t[2], 16)
    return r


def check(out, ref):
    j, ys, px = ref; r = parse(out)
    assert "DONE" in out and "TIMEOUT" not in out and "FAIL" not in out, out[-1500:]
    assert r["Y"] == ys, ("op outputs differ", r["Y"][:6], ys[:6])
    final = list(j.W) + [j.Bq]
    assert [s16(r["W"][k]) for k in range(8)] == final, ("saved values differ from the model", [s16(r["W"][k]) for k in range(8)], final)
    assert all(r["W"][k] >> 16 == 0 for k in range(8)), "upper half of a saved word is not 0"
    z = I4.OnlineInt4("blank", "TD", WB); z.W = [0] * 7; z.Bq = 0; assert r["Z"] == [z.out(px)], (r["Z"], z.out(px))
    assert r["P"] == [j.out(px)], (r["P"], j.out(px))
    assert [r["W2"][k] for k in range(8)] == [r["W"][k] for k in range(8)], "second save differs from the first"
    assert all(r["S"][k] == 0xDEADBEEF for k in range(8)), ("a save while busy wrote words", r["S"])
    assert r["P2"] == [j.out(px)], ("a load while busy changed the judge", r["P2"])
    assert [r["G"][k] for k in range(8)] == [r["W"][k] for k in range(8)], "values changed by the refused load"


def test_neural_weights_save_and_load():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen10_")
    try: out, ref = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    check(out, ref)


MUTS = [("nw[{i[2:0], 4'd0} +: 16]", "nw[{i[2:0] + 3'd1, 4'd0} +: 16]"),                                                              # save reads the wrong value
        ("assign nj_wa = i[3:0];", "assign nj_wa = i[3:0] + 4'd1;"),                                                                     # load writes the wrong address
        ("(sctl[31:28] != 4'd6 || nj_idle) &&", ""),                                                                                     # no guard on save
        ("if (ctl[15:0] != 0 && (ctl[31:28] != 4'd6 || nj_idle)) st <= S_CA;", "if (ctl[15:0] != 0) st <= S_CA;")]                      # no guard on load


def test_mutations_caught():
    src = open(os.path.join(V, "hexn_tabs_v4.v")).read()
    for a, b in MUTS:
        assert a in src, a
        d = tempfile.mkdtemp(prefix="hexnopen10m_")
        try: out, ref = run(d, src.replace(a, b))
        finally: shutil.rmtree(d, ignore_errors=True)
        try: check(out, ref)
        except AssertionError: continue
        raise AssertionError("mutant not caught: " + a)
