"""tests/vm/test_hexn_open8_v1.py -- Hex-N open unit stage 5b (1 Nov 2026): DUMP and GUARDED RESTORE of the judges' weights (hexn_raw_engine_v4, hexn_scorer_v3, hexn_open_top_v8), in simulation through the whole unit over SPI. Alan, 13:01.
Phases: (0) load two different tables into judges A and B, dump both: each 260-word record equals the Python reference, and the scores after the dump are unchanged; (1) clear both, restore both from the records: every A and B answer equals the reference; (2) a record of A restored into B (the judge number in the header is ignored); (3) refusals: bad checksum 3, bad magic 1, wrong array size 2, class/address out of order 4, truncated 4 - the judge is NOT touched (still cleared, answers all zero) and the record is skipped; (4) restore replaces EVERY entry: a different table is in A, a record is restored over it, a dump of A afterwards equals the record exactly. Mutations are caught. Requires iverilog."""
import os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog")
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_scorer_ref_v1 as R  # noqa: E402
FILES = ["hexn_open_top_v8.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v3.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v4.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hexn_scorer_v3.v", "hw262_shield_v2.v"]
CTRL = lambda jc: (14 << 28) | jc
CLEAR_BOTH = (14 << 28) | 0xC
DUMP_A, DUMP_B, REST_A, REST_B = 0xF0000000, 0xF0000002, 0xF0000008, 0xF000000A


def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (int(w) & 0xFFFFFFFF) for w in words) + "\n")


def ld(W): return [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12)] + [R.w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(8) for b in range(12, 16) if W[c][s][b]]      # the usual 192 loads (bins 0..11) plus any entry in bins 12..15 (scoring never reads those)


def rec(W, bias, judge, geom=(8, 16, 256), magic=0x48571):
    h0 = (magic << 12) | (judge << 8) | 2; h1 = (geom[0] << 24) | (geom[1] << 16) | geom[2]
    body = [R.w_load(c, k >> 4, k & 15, W[c][k >> 4][k & 15]) for k in range(128) for c in range(2)]
    w = [h0, h1] + body + [R.w_bias(bias)]
    return w + [sum(w) & 0xFFFFFFFF]


def rows(WA, ba, WB, bb, rng, n, two=True):
    s, e = [], []
    for _ in range(n):
        v = [int(x) for x in rng.integers(0, 12, size=8)]; s.append(R.w_score(v)); e += [R.score(WA, ba, v)[0], R.score(WB, bb, v)[0]]
    return s, e


def make(d):
    rng = np.random.default_rng(21)
    WA = np.zeros((2, 8, 16), dtype=int); WB = np.zeros((2, 8, 16), dtype=int); Z = np.zeros((2, 8, 16), dtype=int)
    WA[:, :, :12] = rng.integers(-60, 61, size=(2, 8, 12)); WB[:, :, :12] = rng.integers(-60, 61, size=(2, 8, 12))
    WA[:, 3, 13] = 9; WB[1, 5, 14] = -7                      # entries the scoring never reads (bins 12..15): only a complete dump and restore carries them
    recA, recB = rec(WA, 25, 0), rec(WB, -17, 1); assert len(recA) == 260
    ph = []
    # 0: load A and B, dump both, then two-judge rows
    r0, e0 = rows(WA, 25, WB, -17, rng, 5)
    ph.append((ld(WA) + [R.w_bias(25), CTRL(2)] + ld(WB) + [R.w_bias(-17), CTRL(1), DUMP_A, DUMP_B] + r0, recA + recB + e0, 480))
    # 1: clear both, restore both, rows
    r1, e1 = rows(WA, 25, WB, -17, rng, 5)
    ph.append(([CLEAR_BOTH, REST_A] + recA + [REST_B] + recB + [CTRL(1)] + r1, [0, 0] + e1, 600))
    # 2: a record of A restored into B; A stays cleared
    r2, e2 = rows(Z, 0, WA, 25, rng, 5)
    ph.append(([CLEAR_BOTH, REST_B] + recA + [CTRL(1)] + r2, [0] + e2, 600))
    # 3a/3b/3c: refusals; the judges stay cleared
    bad_ck = list(recA); bad_ck[259] ^= 1
    bad_mg = rec(WA, 25, 0, magic=0x48581)
    r3, e3 = rows(Z, 0, Z, 0, rng, 3)
    ph.append(([CLEAR_BOTH, REST_A] + bad_ck + [REST_A] + bad_mg + [CTRL(1)] + r3, [3, 1] + e3, 600))
    bad_geo = rec(WA, 25, 0, geom=(7, 16, 256))
    swp = list(recA); swp[2], swp[3] = swp[3], swp[2]; swp[259] = sum(swp[:259]) & 0xFFFFFFFF            # a valid checksum, but class/address out of order
    ph.append(([CLEAR_BOTH, REST_A] + bad_geo + [REST_A] + swp + [CTRL(1)] + r3, [2, 4] + e3, 600))
    ph.append(([CLEAR_BOTH, REST_A] + recA[:100], [4], 600))                                          # truncated record: nothing touched, stream ends
    # 4: A holds table B, a record of A is restored over it, a dump of A afterwards equals the record
    ph.append((ld(WB) + [R.w_bias(7), REST_A] + recA + [DUMP_A], [0] + recA, 480))
    hexfile(d, "meta.hex", [x for s, e, ob in ph for x in (len(s), len(e), ob)])
    for p, (s, e, ob) in enumerate(ph): hexfile(d, "s%d.hex" % p, s); hexfile(d, "e%d.hex" % p, e); assert len(s) + 0 < 480 or ob >= len(s) + 1, (p, len(s)); assert ob + len(e) <= 1024, (p, ob + len(e))
    return len(ph)


def run(d, mutate=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    np_ = make(d)
    tb = open(os.path.join(ROOT, "tests", "hexn_open8", "tb_hexn_open8_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]"))
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp")
    files = [os.path.join(V, f) for f in FILES]
    if mutate:
        name, a, b = mutate; src = open(os.path.join(V, name)).read(); assert a in src, a
        p = os.path.join(d, "mut_" + name); open(p, "w").write(src.replace(a, b)); files[FILES.index(name)] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+dir=" + d, "+np=%d" % np_], capture_output=True, text=True, timeout=3400).stdout


def test_dump_and_guarded_restore():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen8_")
    try: res = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-2500:]
    assert res.count("ok phase") == 7, res[-2500:]


MUTS = [("hexn_raw_engine_v4.v", "if (j == 9'd259 && rd != rck && rcode == 0) rcode <= 3'd3;", "if (j == 9'd259 && 1'b0) rcode <= 3'd3;"),                  # checksum not checked
        ("hexn_raw_engine_v4.v", "if (j == 9'd1 && rd != H1 && rcode == 0) rcode <= 3'd2;", "if (j == 9'd1 && 1'b0) rcode <= 3'd2;"),                      # array size not checked
        ("hexn_raw_engine_v4.v", "(rd[24] == m[0])", "1'b1"),                                                                                              # class order not checked
        ("hexn_raw_engine_v4.v", "else begin i <= i + 16'd260; st <= S_N; end", "else begin i <= i + 16'd1; st <= S_N; end"),                                 # a refused record is not skipped
        ("hexn_scorer_v3.v", "dm_data <= {4'd12, 3'd0, 1'b1, 1'b0, dm_k, 8'd0, rd1};", "dm_data <= {4'd12, 3'd0, 1'b1, 1'b0, dm_k, 8'd0, rd0};")]          # class 1 dumped from the wrong table


def test_mutations_caught():
    for m in MUTS:
        d = tempfile.mkdtemp(prefix="hexnopen8m_")
        try: res = run(d, m)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in res and "PASS" not in res, (m[1], res[-800:])
