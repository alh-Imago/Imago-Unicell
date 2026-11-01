"""tests/vm/test_hexn_open9_v1.py -- Hex-N open unit stage 6, HEAVY route (1 Nov 2026): the NEURAL JUDGE inside the raw stream engine (hexn_raw_engine_v5, hexn_open_top_v9): its own 11-word guarded record (dump 0xF0000004, restore 0xF000000C with refusal codes 1 to 4 checked BEFORE any weight is written) and eval / learn words (0xF0000006 / 0xF000000E), in simulation through the whole unit over SPI. Alan, 17:39 ('carry on'); 16:49/17:26 (cover most of the data, do not trim).
Checks against the integer model tools/hexn_layer1_int_v4.py (OnlineInt4), the judge state carried across phases: (0) restore a record, 40 eval / learn commands, every y equals the model, dump equals the model's weights as a record; (1) restore zeros: probe equals zero-weight model; restore the dumped record back: probe equals the learned model; (2) refusals - bad magic 1, wrong geometry 2, bad checksum 3, a value word with upper bits set 4, truncated 4 - the judge is NOT touched (probe unchanged) and the record is skipped; (3) a dump after the refusals equals the same record. Mutants are caught. Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog"); RT = os.path.join(ROOT, "rtl")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_layer1_int_v4 as I4  # noqa: E402
FILES = ["hexn_open_top_v9.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v3.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v5.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hexn_scorer_v3.v", "hw262_shield_v2.v"]
RTL = [RT + "/hexn_neural_v1.v", RT + "/hexn_tanh512_v1.v"]
WB = 14; NJ_DUMP, NJ_REST, NJ_EVAL, NJ_LEARN = 0xF0000004, 0xF000000C, 0xF0000006, 0xF000000E
MAGIC = (0x4E4A << 16) | (1 << 12) | 8; GEO = (7 << 24) | (6 << 16) | (14 << 8) | 16


def pack(x): return sum(v << (6 * i) for i, v in enumerate(x))
def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (int(w) & 0xFFFFFFFF) for w in words) + "\n")


def record(W, B, magic=MAGIC, geo=GEO):
    w = [magic, geo] + [v & 0xFFFF for v in list(W) + [B]]
    return w + [sum(w) & 0xFFFFFFFF]


def opwords(kind, x, t=0, m=1):
    xp = pack(x)
    if kind == "eval": return [NJ_EVAL, xp & 0xFFFFFFFF, xp >> 32]
    return [NJ_LEARN, xp & 0xFFFFFFFF, (xp >> 32) | ((t & 0x3FF) << 10) | ((1 if m == 2 else 0) << 20)]


class Model:
    def __init__(s): s.j = I4.OnlineInt4("blank", "TD", WB); s.j.W = [0] * 7; s.j.Bq = 0
    def set(s, W, B): s.j.W = list(W); s.j.Bq = B
    def snap(s): return list(s.j.W), s.j.Bq
    def ev(s, x): return s.j.out(x)
    def learn(s, x, t, m):
        j = s.j; o = j.out(x); err = o - t; gain = 256 - ((o * o) >> 8); sh = 29 - WB; rr = 1 << (sh - 1)
        for i in range(7): j.W[i] -= (5 * err * gain * x[i] * m + rr) >> sh
        j.Bq -= (5 * err * gain * 64 * m + rr) >> sh
        return o


def make(d):
    rnd = random.Random(11); M = Model(); ph = []
    W0 = [rnd.randint(-3000, 3000) for _ in range(7)]; B0 = rnd.randint(-3000, 3000)
    # 0: restore, 40 evals / learns, dump
    s, e = [NJ_REST] + record(W0, B0), [0]; M.set(W0, B0)
    for _ in range(40):
        x = [rnd.randint(0, 40) for _ in range(7)]
        if rnd.random() < 0.4: s += opwords("eval", x); e.append(M.ev(x))
        else:
            t = rnd.randint(-256, 256); m = 2 if rnd.random() < 0.25 else 1; s += opwords("learn", x, t, m); e.append(M.learn(x, t, m))
    W1, B1 = M.snap(); rec1 = record(W1, B1); s += [NJ_DUMP]; e += rec1; ph.append((s, e))
    # 1: zeros, probe, restore the learned record, probe
    px = [rnd.randint(0, 40) for _ in range(7)]
    z = Model(); z.set([0] * 7, 0)
    ph.append(([NJ_REST] + record([0] * 7, 0) + opwords("eval", px) + [NJ_REST] + rec1 + opwords("eval", px), [0, z.ev(px), 0, M.ev(px)]))
    # 2: refusals, each followed by a probe (judge must be unchanged: the learned weights)
    bad_ck = list(rec1); bad_ck[10] ^= 1
    bad_mg = record(W1, B1, magic=(0x4E4B << 16) | (1 << 12) | 8)
    bad_geo = record(W1, B1, geo=(6 << 24) | (6 << 16) | (14 << 8) | 16)
    up = list(rec1); up[3] |= 0x10000; up[10] = sum(up[:10]) & 0xFFFFFFFF                      # valid checksum, but a value word with upper bits set
    p = M.ev(px); ph2s, ph2e = [], []
    for code, rc in ((3, bad_ck), (1, bad_mg), (2, bad_geo), (4, up)): ph2s += [NJ_REST] + rc + opwords("eval", px); ph2e += [code, p]
    ph.append((ph2s, ph2e))
    ph.append(([NJ_REST] + rec1[:5], [4]))                                                       # truncated: nothing touched, stream ends
    # 3: probe after the truncated record, then dump: equals the same record
    ph.append((opwords("eval", px) + [NJ_DUMP], [p] + rec1))
    meta = []
    for k, (s, e) in enumerate(ph):
        assert len(s) < 480 and len(e) <= 500, (k, len(s), len(e)); hexfile(d, "s%d.hex" % k, s); hexfile(d, "e%d.hex" % k, e); meta += [len(s), len(e), 520]
    hexfile(d, "meta.hex", meta)
    return len(ph)


def run(d, mutate=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    np_ = make(d)
    tb = open(os.path.join(ROOT, "tests", "hexn_open9", "tb_hexn_open9_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
    files = [os.path.join(V, f) for f in FILES]
    if mutate:
        a, b = mutate; name = "hexn_raw_engine_v5.v"; src = open(os.path.join(V, name)).read(); assert a in src, a
        p = os.path.join(d, "mut_" + name); open(p, "w").write(src.replace(a, b)); files[FILES.index(name)] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files + RTL, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+dir=" + d, "+np=%d" % np_], capture_output=True, text=True, timeout=3400).stdout


def test_neural_record_eval_learn_and_refusals():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen9_")
    try: res = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-2500:]
    assert res.count("ok phase") == 5, res[-2500:]


MUTS = [("if (jn == 4'd10 && rd != rck && rcode == 0) rcode <= 3'd3;", "if (jn == 4'd10 && 1'b0) rcode <= 3'd3;"),                    # checksum not checked
        ("if (jn == 4'd1 && rd != H1N && rcode == 0) rcode <= 3'd2;", "if (jn == 4'd1 && 1'b0) rcode <= 3'd2;"),                          # geometry not checked
        ("(rd[31:12] != MAGICN || rd[7:0] != 8'd8)", "1'b0"),                                                                                 # magic not checked
        ("rd[31:16] != 16'd0 && rcode == 0) rcode <= 3'd4;", "1'b0 && rcode == 0) rcode <= 3'd4;"),                                           # upper bits not checked
        ("i <= i + 16'd11; st <= S_N; end\n            end\n            S_PA", "i <= i + 16'd1; st <= S_N; end\n            end\n            S_PA"),   # a refused record is not skipped
        ("n_wa <= pk;", "n_wa <= pk + 4'd1;"),                                                                                                # restore writes the wrong address
        ("wire [15:0] wsel = nw[{jm, 4'd0} +: 16];", "wire [15:0] wsel = nw[{jm + 4'd1, 4'd0} +: 16];")]                                      # dump reads the wrong value


def test_mutations_caught():
    for m in MUTS:
        d = tempfile.mkdtemp(prefix="hexnopen9m_")
        try: res = run(d, m)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in res and "PASS" not in res, (m[0], res[-800:])
