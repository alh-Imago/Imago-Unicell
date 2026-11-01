"""tests/vm/test_hexn_open13_v1.py -- Hex-N open unit stage 9 (1 Nov 2026): a CHAIN of four gated units with a BYPASS switch per unit, programmed from the pattern bank (hexn_open_top_v13 = hexn_unit_v2 + hexn_stage_v1 + arith_block_v10), in simulation through the whole unit over SPI. Alan, 19:19.
Programs (four consecutive bank slots = four units): A = add const 5 -> shift left by const 2 -> xor with the side operand -> subtract the side operand; B = bypass, add side, bypass, ge-compare; C = all four bypassed (the word passes straight through); D = only the last unit active; E = only the first. Each program is applied with PROGRAM (status words all 0) and 24 random pairs are run; every result equals an independent model (one block model per unit, bypassed units skipped). Then: one unit re-applied alone (unit 2 from bypass to a shift right), the bank saved, CLEARED and program A applied (now four plain adds), the bank loaded back and program A applied again; commands that are out of range (PROGRAM past slot 63, unit index 4) are ignored. Mutants are caught. Requires iverilog."""
import os, random, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); V = os.path.join(ROOT, "fpga", "verilog"); S = os.path.join(ROOT, "sub", "verilog"); R = os.path.join(ROOT, "rtl")
sys.path.insert(0, HERE)
from test_spi_bridge_v1 import MASTER  # noqa: E402
from test_arith_block_v10_v1 import Model  # noqa: E402
FILES = [V + "/" + f for f in ("hexn_open_top_v13.v", "hexn_unit_v2.v", "hexn_pins_v1.v", "hexn_presets_v1.v", "spi_bridge_v2.v", "hexn_tabs_v5.v", "hexn_react_core_v2.v", "hexn_morse_core_v2.v", "hexn_raw_engine_v4.v", "hexn_demo_rom_v1.v", "hexn_morse_gen_v1.v", "hexn_scorer_v1.v", "hexn_scorer_v3.v", "hw262_shield_v2.v")] + \
        [S + "/config_gate_v3.v", S + "/arith_block_v10.v", S + "/flex_sub_bridge_v1.v", R + "/hexn_neural_v1.v", R + "/hexn_tanh512_v1.v"]
N = 4; W = 18; M = (1 << W) - 1; BYP = 1 << 31
def cfg(mode, step=0, topo=0, held=0, bsrc=0, byp=0): return mode | (step << 8) | (topo << 16) | (held << 26) | (bsrc << 27) | (byp << 31)
BYPASS = cfg(0, byp=1)
PROGS = {
    "A": [cfg(0, step=5, bsrc=1), cfg(5, step=2, bsrc=1), cfg(7, topo=0x0BC), cfg(1)],
    "B": [BYPASS, cfg(0), BYPASS, cfg(2)],
    "C": [BYPASS] * 4,
    "D": [BYPASS, BYPASS, BYPASS, cfg(0, step=9, bsrc=1)],
    "E": [cfg(1, step=3, bsrc=1), BYPASS, BYPASS, BYPASS],
}
SLOT = {"A": 0, "B": 4, "C": 8, "D": 12, "E": 16}


def hexfile(d, name, words): open(os.path.join(d, name), "w").write("\n".join("%08x" % (int(w) & 0xFFFFFFFF) for w in words) + "\n")


def chain_model(cfgs):
    ms = []
    for c in cfgs: m = Model(W); m.clock(1, c, 0, 0, 0); ms.append(m)
    def run(a, x):
        for c, m in zip(cfgs, ms):
            if c & BYP: continue
            m.clock(0, 0, a, x, 1); a = m.out
        return a
    return run


def batch(d, bid, cfgs, rnd, n=24):
    f = chain_model(cfgs); ops, ex = [], []
    for _ in range(n):
        a = rnd.getrandbits(W) if rnd.random() < 0.8 else rnd.choice([0, 1, 2, 3, M, 1 << (W - 1)]); x = rnd.getrandbits(W) if rnd.random() < 0.5 else rnd.choice([0, 1, 2, 5, 17, 18, 19, 31])
        ops += [a, x]; ex.append(f(a, x))
    hexfile(d, "op%d.hex" % bid, ops); hexfile(d, "ex%d.hex" % bid, ex)


def script(d):
    rnd = random.Random(13); L = []; bid = 0; bank = [0] * 64
    for k, p in PROGS.items():
        for u, c in enumerate(p): bank[SLOT[k] + u] = c
    bank[20] = cfg(6, step=1, bsrc=1)                               # slot 20: shift right by const 1
    L.append("for (i = 0; i < 64; i = i + 1) wbuf[i] = 32'd0;")
    for i, c in enumerate(bank):
        if c: L.append("wbuf[%d] = 32'h%08x;" % (i, c))
    L.append("wr_words(16'd0, 64); load(4'd7, 0, 64);")
    for k in "ABCDE":
        L.append('chainprog(6\'d%d, 4\'d4, 10\'d400, 4, "program %s: four status words 0");' % (SLOT[k], k)); batch(d, bid, PROGS[k], rnd)
        L.append('run_batch(%d, 10\'d24, "program %s: 24 chain results equal the model");' % (bid, k)); bid += 1
    # program fewer units: n = 2 from slot 0 -> units 0,1 get A's first two words, units 2,3 keep program E's bypass
    cur = [PROGS["A"][0], PROGS["A"][1], PROGS["E"][2], PROGS["E"][3]]
    L.append('chainprog(6\'d0, 4\'d2, 10\'d400, 2, "PROGRAM of two units: two status words 0, the rest untouched");'); batch(d, bid, cur, rnd)
    L.append('run_batch(%d, 10\'d24, "two units programmed: results equal the model");' % bid); bid += 1
    # one unit alone: unit 2 from bypass to shift right by 1 (slot 20)
    cur[2] = bank[20]
    L.append('apply1(4\'d2, 6\'d20, 10\'d400, "unit 2 alone set to slot 20 (shift right)");'); batch(d, bid, cur, rnd)
    L.append('run_batch(%d, 10\'d24, "one unit re-applied: chain results equal the model");' % bid); bid += 1
    # save, clear, program A, load back, program A
    L.append("sentinel(16'd700, 70); save(4'd7, 700, 0); rd_words(16'd700, 66); bad = 0;")
    for i, c in enumerate(bank):
        if c: L.append("if (rbuf[%d] !== 32'h%08x) bad = bad + 1;" % (i, c))
    L.append("check(bad == 0 && rbuf[64] === SENT, \"the saved bank equals what was loaded\");")
    L.append("for (i = 0; i < 64; i = i + 1) bank[i] = rbuf[i]; for (i = 0; i < 64; i = i + 1) wbuf[i] = 32'd0; wr_words(16'd0, 64); load(4'd7, 0, 64);")
    L.append('chainprog(6\'d0, 4\'d4, 10\'d400, 4, "after clearing the bank: program A applied");'); batch(d, bid, [0, 0, 0, 0], rnd)
    L.append('run_batch(%d, 10\'d24, "cleared bank: the four units are plain adds (a + 4x)");' % bid); bid += 1
    L.append("for (i = 0; i < 64; i = i + 1) wbuf[i] = bank[i]; wr_words(16'd0, 64); load(4'd7, 0, 64);")
    L.append('chainprog(6\'d0, 4\'d4, 10\'d400, 4, "after loading the bank back: program A applied");'); batch(d, bid, PROGS["A"], rnd)
    L.append('run_batch(%d, 10\'d24, "restored bank: program A again");' % bid); bid += 1
    # out of range commands are ignored
    L.append("sentinel(16'd900, 8); ucmd(4'd3, 10'd900, 10'd0, 4'd4, 6'd62); repeat (40) @(negedge clk); rd_reg(8'd10); check(!rv[4], \"PROGRAM of 4 units from slot 62 is ignored (busy low)\"); rd_words(16'd900, 8); check(rbuf[0] === SENT && rbuf[3] === SENT, \"and no status word was written\");")
    L.append("sentinel(16'd900, 8); ucmd(4'd1, 10'd900, 10'd0, 4'd5, 6'd0); repeat (40) @(negedge clk); rd_reg(8'd10); check(!rv[4], \"APPLY to unit 5 (there are 4) is ignored\");")
    return "\n        ".join(L)


def run(d, mutate=None):
    for t in ("hexn_demo_rom_v1.py", "hexn_morse_gen_v1.py"): subprocess.run([sys.executable, os.path.join(ROOT, "tools", t)], check=True, capture_output=True)
    sc = script(d)
    tb = open(os.path.join(ROOT, "tests", "hexn_open13", "tb_hexn_open13_v1.v")).read().replace("//MASTER//", MASTER.replace("wire miso;", "wire miso = SPI_MISO;").replace("[0:15]", "[0:255]")).replace("//SCRIPT//", sc)
    open(os.path.join(d, "tb.v"), "w").write(tb); o = os.path.join(d, "o.vvp"); files = list(FILES)
    if mutate:
        name, a, b = mutate; dirs = {"hexn_unit_v2.v": V}; src = open(os.path.join(dirs.get(name, S), name)).read(); assert a in src, a
        p = os.path.join(d, "mut_" + name); open(p, "w").write(src.replace(a, b)); files[[os.path.basename(f) for f in files].index(name)] = p
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True); assert c.returncode == 0, c.stderr[:1500]
    return subprocess.run(["vvp", o, "+dir=" + d], capture_output=True, text=True, timeout=3000).stdout


def test_chain_with_bypass_from_the_bank():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnopen13_")
    try: res = run(d)
    finally: shutil.rmtree(d, ignore_errors=True)
    assert "PASS" in res and "FAIL" not in res and "TIMEOUT" not in res, res[-2500:]
    assert res.count("ok ") == 5 * 2 + 2 + 2 + 1 + 2 + 2 + 3, res[-2500:]


MUTS = [("hexn_unit_v2.v", "assign out_data  = byp ? in_data  : bd;", "assign out_data  = bd;"),                                   # bypass does not pass the data
        ("hexn_unit_v2.v", "assign in_ack    = byp ? out_ack : g_ack;", "assign in_ack    = g_ack;"),                                 # bypass does not pass the ack back
        ("hexn_unit_v2.v", "else if (cfg_v) byp <= cfg_d[31];", "else if (cfg_v) byp <= 1'b0;"),                                         # bypass bit ignored
        ("hexn_unit_v2.v", "E_PA: begin pat_addr <= slot + {2'b00, u}; st <= E_PB; end", "E_PA: begin pat_addr <= slot; st <= E_PB; end"),   # every unit gets the same slot
        ("hexn_unit_v2.v", "{2'b00, c_base} + {1'b0, c_cnt, 1'b0} + {2'b00, c_cnt} <= 12'd1024)", "1'b1)"),                              # no end-of-scratch guard
        ("hexn_unit_v2.v", "({1'b0, c_slot} + n_eff <= 7'd64)", "1'b1"),                                                               # PROGRAM past slot 63 not refused
        ("hexn_unit_v2.v", "sub_to_flex_v1 #(.WIDTH(2*W)) O (.clk(clk), .rst(rr), .sub_data({bo, region_data[W-1:0]})", "sub_to_flex_v1 #(.WIDTH(2*W)) O (.clk(clk), .rst(rr), .sub_data({bo, bo})")]   # the side operand is lost after a stage


def test_mutations_caught():
    for m in MUTS:
        d = tempfile.mkdtemp(prefix="hexnopen13m_")
        try: res = run(d, m)
        finally: shutil.rmtree(d, ignore_errors=True)
        assert ("FAIL" in res and "PASS" not in res) or "TIMEOUT" in res, (m[1], res[-800:])
