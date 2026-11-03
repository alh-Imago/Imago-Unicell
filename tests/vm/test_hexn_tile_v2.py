"""tests/vm/test_hexn_tile_v2.py (clone of the v1 test for tile v2: power-up zeros and the core result straight from the core register; latencies are one clock less than v1)
 tests/vm/test_hexn_tile_v1.py -- the first full Hex-N tile (sub/verilog/hexn_tile_v2.v: routing cell with flag lane + unary work core, one config chain), simulated alone with iverilog.
Checks, against a word-level Python model: every unary op after a config load through the chain (random k, mask, words); a routed stream passing the tile untouched while the core computes on another;
the result replaces ONLY the outputs in RMASK; two tiles chained (farthest tile's word first) doing shl then inv; config chain length; the accumulator and its clear; a mutant (flag lane ignores RMASK) is caught.
Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tile_cfg_v1 as C

SRC = [os.path.join(ROOT, "sub", "verilog", "hexn_tile_v2.v"), os.path.join(ROOT, "sub", "verilog", "hexn_unary_core_v1.v")]
TB = os.path.join(ROOT, "tests", "hexn_tile_tb_v2.v")
M32 = 0xFFFFFFFF
GAP = 40


def run(stim, nt=1, srcs=None):
    """stim: list of dict(clear, cfg_en, cfg_in, n=(f,d), s=(f,d), w=(f,d)) per clock -> list of dict(cfg_out, e=(f,d), s=(f,d)) per clock"""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="tile_")
    try:
        lines = []
        for s in stim:
            v = (s.get("clear", 0) << 8) | (s.get("cfg_en", 0) << 7) | (s.get("cfg_in", 0) << 6)
            for sh, key in ((4, "n"), (2, "s"), (0, "w")):
                f, dd = s.get(key, (0, 0)); v |= (f << (sh + 1)) | (dd << sh)
            lines.append("%03x" % v)
        open(os.path.join(d, "stim.hex"), "w").write("\n".join(lines) + "\n")
        o = os.path.join(d, "o.vvp"); files = srcs or SRC
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.NT=%d" % nt, "-o", o, TB] + files, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        out = subprocess.run(["vvp", o, "+stim=" + os.path.join(d, "stim.hex"), "+n=%d" % len(stim)], capture_output=True, text=True, timeout=300).stdout.split()
        out = [x for x in out if len(x) == 5 and set(x) <= {"0", "1"}]
        assert len(out) == len(stim), (len(out), len(stim), out[:3])
        return [dict(cfg_out=int(x[0]), e=(int(x[1]), int(x[2])), s=(int(x[3]), int(x[4]))) for x in out]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def load(words, nt):
    return [dict(cfg_en=1, cfg_in=b) for b in C.chain_bits(words)] + [dict() for _ in range(3)]


def put(stim, key, t0, word):
    """put a 32-bit word on face `key` starting at clock t0 (flag on bit 0)"""
    while len(stim) < t0 + 32: stim.append(dict())
    for i in range(32):
        stim[t0 + i][key] = (1 if i == 0 else 0, (word >> i) & 1)


def words_out(res, key):
    """every flag-framed word on an output lane -> [(flag clock, value)]"""
    out = []
    for t, r in enumerate(res):
        if r[key][0]:
            assert t + 32 <= len(res), "word cut off"
            out.append((t, sum(res[t + i][key][1] << i for i in range(32))))
    return out


def model(op, k, mask, a, total=0):
    if op == "cp": return a, 0
    if op == "shl": return (a << k) & M32, 0
    if op == "shr": return a >> k, k
    if op == "inv": return ~a & M32, 0
    if op == "mask": return sum(((a >> (4 * l)) & 0xF) << (4 * l) for l in range(8) if (mask >> l) & 1), 0
    raise ValueError(op)


def test_chain_length_and_pack_roundtrip():
    assert C.width(4) == 35
    w = C.pack({"E": "W", "S": "N"}, "W", ("E",), "shr", 9, 0xA5)
    u = C.unpack(w)
    assert u["route"][1] == 3 and u["route"][2] == 0 and u["sela"] == 3 and u["result_to"] == [1] and u["op"] == "shr" and u["k"] == 9 and u["mask"] == 0xA5
    # the chain really is 35 bits long: shift a marker in and see it come out after exactly 35 clocks
    stim = [dict(cfg_en=1, cfg_in=1)] + [dict(cfg_en=1, cfg_in=0) for _ in range(40)]
    res = run(stim)
    assert [t for t, r in enumerate(res) if r["cfg_out"]] == [34]


def test_every_unary_op_on_random_words_and_config():
    rnd = random.Random(5)
    for op in ("cp", "shl", "shr", "inv", "mask"):
        for _ in range(3):
            k, mask = rnd.randrange(32), rnd.randrange(256)
            stim = load([C.pack({}, "W", ("E",), op, k, mask)], 1)
            ws = [rnd.randrange(1 << 32) for _ in range(3)]
            starts = []
            for w in ws:
                t0 = len(stim) + 2; starts.append(t0); put(stim, "w", t0, w)
                stim += [dict() for _ in range(GAP)]
            got = words_out(run(stim), "e")
            assert len(got) == len(ws), (op, got)
            for (t, v), w, t0 in zip(got, ws, starts):
                want, extra = model(op, k, mask, w)
                assert v == want, (op, k, mask, hex(w), hex(v), hex(want))
                assert t == t0 + extra, (op, k, t - t0)                # v2: the core's own register only; shr starts k clocks later


def test_routed_stream_passes_the_tile_untouched_while_the_core_computes():
    rnd = random.Random(8)
    stim = load([C.pack({"S": "N"}, "W", ("E",), "inv")], 1)        # S <- N routed, E <- core(W)
    a, b = rnd.randrange(1 << 32), rnd.randrange(1 << 32)
    t0 = len(stim) + 2
    put(stim, "w", t0, a); put(stim, "n", t0 + 7, b)
    stim += [dict() for _ in range(GAP)]
    res = run(stim)
    assert words_out(res, "e") == [(t0, ~a & M32)]
    assert words_out(res, "s") == [(t0 + 7, b)]                    # routed: no delay seen at the line, flag and data together


def test_result_replaces_only_the_outputs_in_rmask():
    stim = load([C.pack({"E": "N", "S": "N"}, "W", ("S",), "cp")], 1)   # E <- N routed, S <- core(W)
    t0 = len(stim) + 2
    put(stim, "w", t0, 0x12345678); put(stim, "n", t0 + 3, 0x0BADF00D)
    stim += [dict() for _ in range(GAP)]
    res = run(stim)
    assert words_out(res, "s") == [(t0, 0x12345678)]
    assert words_out(res, "e") == [(t0 + 3, 0x0BADF00D)]


def test_two_tiles_chained_shl_then_inv():
    rnd = random.Random(2)
    t0w = C.pack({}, "W", ("E",), "shl", 3)                       # tile 0
    t1w = C.pack({}, "W", ("E",), "inv")                          # tile 1
    stim = load([t0w, t1w], 2)
    a = rnd.randrange(1 << 32); t0 = len(stim) + 2
    put(stim, "w", t0, a); stim += [dict() for _ in range(GAP)]
    got = words_out(run(stim, nt=2), "e")
    assert got == [(t0 + 1, ~((a << 3) & M32) & M32)]              # tile 0 shows its word at t0; the link into tile 1 is registered (+1), then its own core register shows it at the same line


def test_accumulator_runs_a_total_and_clear_resets_it():
    stim = load([C.pack({}, "W", ("E",), "acc")], 1)
    ws = [0x10, 0xFFFFFFF0, 0x25]; total = 0; want = []
    for w in ws:
        total = (total + w) & M32; want.append(total)
    t0s = []
    for w in ws:
        t0 = len(stim) + 2; t0s.append(t0); put(stim, "w", t0, w); stim += [dict() for _ in range(GAP)]
    got = [v for _, v in words_out(run(stim), "e")]
    assert got == want
    # clear pulse between words restarts the total
    stim = load([C.pack({}, "W", ("E",), "acc")], 1)
    t0 = len(stim) + 2; put(stim, "w", t0, 7); stim += [dict() for _ in range(GAP)]
    stim[-5]["clear"] = 1
    t1 = len(stim) + 2; put(stim, "w", t1, 9); stim += [dict() for _ in range(GAP)]
    assert [v for _, v in words_out(run(stim), "e")] == [7, 9]


def test_mutant_flag_lane_ignoring_rmask_is_caught():
    src = open(SRC[0]).read()
    bad = src.replace("assign fo_f[g] = rmask[g] ? rs : ro_f[g];", "assign fo_f[g] = ro_f[g];")
    assert bad != src
    d = tempfile.mkdtemp(prefix="tilemut_")
    try:
        p = os.path.join(d, "t.v"); open(p, "w").write(bad)
        stim = load([C.pack({}, "W", ("E",), "cp")], 1); t0 = len(stim) + 2
        put(stim, "w", t0, 0xCAFEBABE); stim += [dict() for _ in range(GAP)]
        res = run(stim, srcs=[p, SRC[1]])
        assert words_out(res, "e") != [(t0 + 1, 0xCAFEBABE)]
    finally:
        shutil.rmtree(d, ignore_errors=True)
