"""tests/vm/test_hexn_open12_v1.py -- Hex-N open unit stage 8 (1 Nov 2026): ONE GATED MUTABLE UNIT (hexn_unit_v1 = config_gate_v3 -> arith_block_v9 W18 -> sub_to_flex_v1) driven from the PATTERN BANK (table space 7), in simulation through the whole unit over SPI (hexn_open_top_v12). Alan, 18:35.
Script: (1) load nine config words into the bank, for every slot: APPLY it through the gate (status word 0) and RUN 30 random operand pairs; every result equals the independent Python model of the block (add, sub, >=, 3-way compare, accumulate, shift left, shift right, nano XOR, nano AND with config mask); (2) SAVE the bank, CLEAR it, apply slot 5 (now an all-zero config = add) and run: the results are the ADD results, so the bank content really drives the unit; LOAD the saved words back, apply slot 5: shift left again; the saved words equal what was loaded; (3) a RUN that would run past the scratch RAM is ignored (busy low, nothing written). Mutants are caught. Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog"); S = os.path.join(ROOT, "sub", "verilog"); R = os.path.join(ROOT, "rtl")
sys.path.insert(0, HERE)
from test_spi_bridge_v1 import MASTER  # noqa: E402
from test_arith_block_v9_v1 import Model  # noqa: E402
FILES = [V + "/hexn_open_top_v12.v", V + "/hexn_unit_v1.v", V + "/hexn_pins_v1.v", V + "/hexn_presets_v1.v", V + "/spi_bridge_v2.v", V + "/hexn_tabs_v5.v", V + "/hexn_react_core_v2.v", V + "/hexn_morse_core_v2.v", V + "/hexn_raw_engine_v4.v", V + "/hexn_demo_rom_v1.v", V + "/hexn_morse_gen_v1.v", V + "/hexn_scorer_v1.v", V + "/hexn_scorer_v3.v", V + "/hw262_shield_v2.v",
         S + "/config_gate_v3.v", S + "/arith_block_v9.v", S + "/flex_sub_bridge_v1.v", R + "/hexn_neural_v1.v", R + "/hexn_tanh512_v1.v"]
CFG = [0, 1, 2, 3, 4 | (5 << 8), 5, 6, 7 | (0x0BC << 16), 7 | (0x35 << 8) | (0x007 << 16) | (1 << 26)]      # add, sub, >=, cmp3, accumulate step 5, shl, shr, nano XOR, nano AND with the config mask
W = 18; M = (1 << W) - 1


def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (int(w) & 0xFFFFFFFF) for w in words) + "\n")


def batch(d, bid, cfgword, rnd, n=30):
    m = Model(W); m.clock(1, cfgword, 0, 0, 0); ops, ex = [], []
    for _ in range(n):
        a = rnd.getrandbits(W) if rnd.random() < 0.8 else rnd.choice([0, 1, 2, 3, M, 1 << (W - 1)]); b = rnd.getrandbits(W) if rnd.random() < 0.6 else rnd.choice([0, 1, 2, 5, 17, 18, 19, 31])
        m.clock(0, 0, a, b, 1); ops += [a, b]; ex.append(m.out)
    hexfile(d, "op%d.hex" % bid, ops); hexfile(d, "ex%d.hex" % bid, ex)


def script(d):
    rnd = random.Random(12); L = []; bid = 0
    L.append("for (i = 0; i < 64; i = i + 1) wbuf[i] = 32'd0;")
    for i, c in enumerate(CFG): L.append("wbuf[%d] = 32'h%08x;" % (i, c))
    L.append("wr_words(16'd0, 64); load(4'd7, 0, 64);")
    for s, c in enumerate(CFG):
        L.append('apply(6\'d%d, 10\'d400, 32\'d0, "slot %d applied, status word 0");' % (s, s)); batch(d, bid, c, rnd); L.append('run_batch(%d, 10\'d30, "slot %d: 30 results equal the model");' % (bid, s)); bid += 1
    # save, clear, apply, run; load back, apply, run
    L.append("sentinel(16'd700, 70); save(4'd7, 700, 0); rd_words(16'd700, 66); bad = 0;")
    for i, c in enumerate(CFG): L.append("if (rbuf[%d] !== 32'h%08x) bad = bad + 1;" % (i, c))
    L.append("for (i = %d; i < 64; i = i + 1) if (rbuf[i] !== 32'd0) bad = bad + 1; check(bad == 0 && rbuf[64] === SENT, \"the saved bank equals what was loaded\");" % len(CFG))
    L.append("for (i = 0; i < 64; i = i + 1) bank[i] = rbuf[i]; for (i = 0; i < 64; i = i + 1) wbuf[i] = 32'd0; wr_words(16'd0, 64); load(4'd7, 0, 64);")
    L.append('apply(6\'d5, 10\'d400, 32\'d0, "after clearing the bank: slot 5 applied");'); batch(d, bid, 0, rnd, 20); L.append('run_batch(%d, 10\'d20, "cleared bank: slot 5 is now an all-zero config = add");' % bid); bid += 1
    L.append("for (i = 0; i < 64; i = i + 1) wbuf[i] = bank[i]; wr_words(16'd0, 64); load(4'd7, 0, 64);")
    L.append('apply(6\'d5, 10\'d400, 32\'d0, "after loading the saved bank back: slot 5 applied");'); batch(d, bid, CFG[5], rnd, 20); L.append('run_batch(%d, 10\'d20, "restored bank: slot 5 is shift left again");' % bid); bid += 1
    # a run that would run past the scratch RAM is ignored
    L.append("sentinel(16'd1000, 24); ucmd(4'd2, 10'd900, 10'd100, 6'd0); repeat (40) @(negedge clk); rd_reg(8'd10); check(!rv[4], \"an oversized RUN is ignored: busy stays low\"); rd_words(16'd1000, 24); check(rbuf[0] === SENT && rbuf[23] === SENT, \"and nothing was written\");")
    return "\n        ".join(L)


def run(d, mutate=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    sc = script(d)
    tb = open(os.path.join(ROOT, "tests", "hexn_open12", "tb_hexn_open12_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]")).replace("//SCRIPT//", sc)
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp"); files = list(FILES)
    if mutate:
        name, a, b = mutate; src = open(os.path.join(V if name.startswith("hexn_unit") else S, name)).read(); assert a in src, a
        p = os.path.join(d, "mut_" + name); open(p, "w").write(src.replace(a, b)); files[[os.path.basename(f) for f in files].index(name)] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+dir=" + d], capture_output=True, text=True, timeout=3000).stdout


def test_gated_unit_from_the_pattern_bank():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen12_")
    try: res = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-2500:]
    assert res.count("ok ") == 9 * 2 + 1 + 4 + 2, res[-2500:]


MUTS = [("hexn_unit_v1.v", "E_PA: begin pat_addr <= slot;", "E_PA: begin pat_addr <= slot + 6'd1;"),                         # applies the wrong slot
        ("hexn_unit_v1.v", "E_PC: begin cfg_word <= pat_data;", "E_PC: begin cfg_word <= 32'd0;"),                             # applies an empty config
        ("hexn_unit_v1.v", "assign wa = (st == E_SW) ? base : base + {cnt[8:0], 1'b0} + k;", "assign wa = (st == E_SW) ? base : base + {cnt[8:0], 1'b0} + k + 10'd1;"),   # result written one word late
        ("hexn_unit_v1.v", "E_RC: begin a <= rd[W-1:0];", "E_RC: begin a <= rd[W-1:0] ^ 18'd1;"),                             # operand a corrupted
        ("hexn_unit_v1.v", "({2'b00, c_base} + {1'b0, c_cnt, 1'b0} + {2'b00, c_cnt} <= 12'd1024)", "1'b1"),                    # no end-of-scratch guard
        ("config_gate_v3.v", "assign in_ack     = in_valid & ~busy & ~closed & ~rst;", "assign in_ack     = in_valid & ~busy & ~rst;")]   # the gate lets words in while closed


def test_mutations_caught():
    for m in MUTS:
        d = tempfile.mkdtemp(prefix="hexnopen12m_")
        try: res = run(d, m)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert "FAIL" in res and "PASS" not in res or "TIMEOUT" in res, (m[1], res[-800:])
