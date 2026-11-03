"""hexn_pattern_verify_v12 = verify_v11 on ref_v8 (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v11 = verify_v10 on pattern generator v6: program_for also returns the plan's RAM holds as program["holds"] (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v10 = verify_v9 on ref_v7 / wrgrid_v18 (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v9 = verify_v8 on pattern generator v5 (UN, AL, JN, BR, MG tiles; 3 Nov 2026); nothing else changed.
hexn_pattern_verify_v8 = verify_v7 on ref_v6 / wrgrid_v17 (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v7 = verify_v6 on pattern generator v4 (UN, AL, JN, BR tiles; 3 Nov 2026); nothing else changed.
hexn_pattern_verify_v6 = verify_v5 on ref_v5 / wrgrid_v16 (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v5 = verify_v4 on ref_v4 / wrgrid_v15 (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v3 = verify_v2 on ref_v3 / wrgrid_v14 (3 Nov 2026); nothing else changed.
hexn_pattern_verify_v2.py - (v2: uses pattern generator v2, UN + AL tiles; v1 untouched) VERIFY A PATTERN BY SIMULATION AND BY PLACE AND ROUTE (3 Nov 2026, Alan 08:53: 'if the details are fed back from the place and route into the design, that gives verification of the pattern').
  sim_run(ref, program, inputs)  generate the pattern top, load a program (from a unit file) through the chain, run it in iverilog -> output words and ticks.
  pnr_run(ref)                   generate the top, synthesise it ALONE (yosys synth_gowin -nowidelut: slots = LUT + ALU), wrap it (LFSR in, XOR-reduced out, clk + led only) and place and route it for the Tang Nano 20K
                                 (GW2AR-LV18QN88C8/I7, 27 MHz target) with yowasp-nextpnr-himbaechel-gowin -> a RECORD (format hexn-pnr-v1) tied to the pattern's ID and content hash.
  verified(ref, record)          True only if the record is for THIS reference (same ID and hash) and its verdict is PASS.
The reference file is never edited (its hash would break); the record is a separate file next to it. VERDICT PASS needs: place and route completed, Fmax >= the target, the PLACED pattern (placed total minus the wrapper's own slots) within +-10% of the planner's estimate (the yosys count and the packing overhead are recorded too), utilisation <= 100%.
CAVEATS: one run, no seed sweep; Fmax is nextpnr's estimator against a modest target; wrapper adds ~65 flip-flops and a few LUTs (reported); not silicon, not a board run."""
import datetime, json, os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hexn_pattern_gen_v6 as P
import hexn_pattern_ref_v8 as R

TB = os.path.join(ROOT, "tests", "hexn_pattern_tb.v")
DEVICE, FAMILY, FREQ = "GW2AR-LV18QN88C8/I7", "GW2A-18C", 27
CST = 'IO_LOC "clk" 4;\nIO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;\nIO_LOC "led" 15;\nIO_PORT "led" IO_TYPE=LVCMOS33 DRIVE=8;\n'
TOL = 0.10


def sim_run(ref, program, inputs, extra_clocks=140, gap=2):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    words, widths = P.load_words(ref, program)
    rows, cols = ref["rows"], ref["cols"]
    in_rows = {n: v[0] for n, v in program["pads_in"].items()}; out_rows = {n: v[0] for n, v in program["pads_out"].items()}
    stim = [dict(cfg_en=1, cfg_in=b) for b in P.chain_bits(words, widths)] + [dict() for _ in range(gap)]
    t0 = len(stim)
    while len(stim) < t0 + 32 + extra_clocks: stim.append(dict())
    for name, w in inputs.items():
        for i in range(32): stim[t0 + i]["w%d" % in_rows[name]] = (1 if i == 0 else 0, (w >> i) & 1)
    lines = []
    for s in stim:
        v = s.get("cfg_in", 0) | (s.get("cfg_en", 0) << 1) | (s.get("clear", 0) << 2)
        for r in range(rows):
            f, d = s.get("w%d" % r, (0, 0)); v |= (d << (3 + 2 * r)) | (f << (4 + 2 * r))
        lines.append("%08x" % v)
    d = tempfile.mkdtemp(prefix="pattern_")
    try:
        open(os.path.join(d, "top.v"), "w").write(P.generate(ref)); open(os.path.join(d, "stim.hex"), "w").write("\n".join(lines) + "\n"); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.ROWS=%d" % rows, "-P", "tb.COLS=%d" % cols, "-o", o, TB, os.path.join(d, "top.v")] + P.FILES, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        out = subprocess.run(["vvp", o, "+stim=" + os.path.join(d, "stim.hex"), "+n=%d" % len(stim)], capture_output=True, text=True, timeout=600).stdout.split()
        out = [x for x in out if len(x) == 1 + 2 * rows and set(x) <= {"0", "1"}]
        assert len(out) == len(stim), (len(out), len(stim))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    ef = [x[1:1 + rows][::-1] for x in out]; ed = [x[1 + rows:][::-1] for x in out]
    res = {}
    for name, r in out_rows.items():
        got = []
        for t in range(t0, len(out)):
            if ef[t][r] == "1":
                if t + 32 > len(out): raise AssertionError("word cut off")
                got.append((t - t0, sum(int(ed[t + i][r]) << i for i in range(32))))
        res[name] = got
    return dict(start=t0, out=res, chain_clocks=len(P.chain_bits(words, widths)), chain_bits=sum(widths))


def program_for(base, plan):
    """the program (hexn_bases_v2.program_of's form) of a plan made by the v13 planner on a pattern's base - the same dict, built with the v13 grid"""
    import hexn_wrgrid_v18 as G
    g = G.configure9(plan); cells = {}
    for w, i in g.work.items():
        cells["%d,%d" % w] = dict(type=base.type[w], kind=i["op"], mode=i["mode"], k=i["k"], cfg={k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in i["cfg"].items()}, ins=i["ins"], outs=i["outs"])
    holds = {}
    for ((r_, c_), face), h in (getattr(g, "holds", None) or {}).items():
        if "%d,%d" % (r_, c_) in holds: raise ValueError("two holds in cell (%d,%d): the RAM cell has one delay line" % (r_, c_))
        holds["%d,%d" % (r_, c_)] = dict(out=face, dly=h)
    return dict(bitstream=base.name, cells=cells, routing={"%d,%d" % c: dict(sel) for c, sel in g.route.items()},
                pads_in={k: list(v) for k, v in g.pads_in.items()}, pads_out={k: list(v) for k, v in g.pads_out.items()}, holds=holds)


def _counts(text):
    g = lambda k: sum(int(m.group(1)) for m in re.finditer(r"^\s+(\d+)\s+" + k + r"\s*$", text, re.M))
    lut = sum(g("LUT%d" % i) for i in (1, 2, 3, 4)); alu = g("ALU")
    dff = sum(g(k) for k in ("DFF", "DFFE", "DFFR", "DFFS", "DFFRE", "DFFSE", "DFFP", "DFFC", "DFFCE", "DFFNE"))
    return dict(lut=lut, alu=alu, dff=dff, mux2=sum(g("MUX2_LUT%d" % i) for i in (5, 6, 7, 8)), slots=lut + alu)


def _wrapper(rows):
    return ("module pnr_wrap (input wire clk, output reg led);\n    reg [63:0] l = 64'h1ACE_B00C_DEAD_BEEF; always @(posedge clk) l <= {l[62:0], l[63] ^ l[62] ^ l[60] ^ l[59]};\n"
            "    wire [%d:0] ed, ef; wire co;\n    hexn_pattern_top t (.clk(clk), .clear(l[0]), .w_d(l[%d:1]), .w_f(l[%d:%d]), .e_d(ed), .e_f(ef), .cfg_en(l[40]), .cfg_in(l[41]), .cfg_out(co));\n"
            "    always @(posedge clk) led <= ^{ed, ef, co};\nendmodule\n") % (rows - 1, rows, 2 * rows, rows + 1)


def _ver(cmd):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0]
    except Exception: return "unknown"


def pnr_run(ref, keep=None):
    for tool in ("yosys", "yowasp-nextpnr-himbaechel-gowin"):
        assert shutil.which(tool), tool + " is REQUIRED"
    top = P.generate(ref); rows = ref["rows"]
    d = keep or tempfile.mkdtemp(prefix="pnr_pattern_")
    os.makedirs(d, exist_ok=True)
    try:
        open(os.path.join(d, "top.v"), "w").write(top); open(os.path.join(d, "wrap.v"), "w").write(_wrapper(rows)); open(os.path.join(d, "pnr.cst"), "w").write(CST)
        files = " ".join(P.FILES)
        subprocess.run(["yosys", "-q", "-l", "alone.log", "-p", "read_verilog -sv top.v %s; hierarchy -top hexn_pattern_top; synth_gowin -top hexn_pattern_top -nowidelut; tee -q -o alone.txt stat" % files], cwd=d, capture_output=True, text=True)
        synth = _counts(open(os.path.join(d, "alone.txt")).read()) if os.path.exists(os.path.join(d, "alone.txt")) else None
        subprocess.run(["yosys", "-q", "-p", "read_verilog -sv wrap.v top.v %s; hierarchy -top pnr_wrap; synth_gowin -top pnr_wrap -nowidelut -json w.json; tee -q -o wrapstat.txt stat" % files], cwd=d, capture_output=True, text=True)
        wsynth = _counts(open(os.path.join(d, "wrapstat.txt")).read()) if os.path.exists(os.path.join(d, "wrapstat.txt")) else None
        placed, fmax, log = None, None, ""
        if os.path.exists(os.path.join(d, "w.json")):
            t = subprocess.run(["yowasp-nextpnr-himbaechel-gowin", "--device", DEVICE, "--vopt", "family=" + FAMILY, "--vopt", "cst=pnr.cst", "--json", "w.json", "--write", "w_r.json", "--freq", str(FREQ), "--timing-allow-fail"],
                               cwd=d, capture_output=True, text=True, timeout=3000)
            log = t.stdout + t.stderr
            util = {m.group(1): (int(m.group(2)), int(m.group(3))) for m in re.finditer(r"^\s*Info:\s+(LUT4|MUX2_LUT5|MUX2_LUT6|MUX2_LUT7|MUX2_LUT8|ALU|DFF):\s+(\d+)/\s*(\d+)", log, re.M)}
            fm = re.findall(r"Max frequency for clock\s+'[^']*':\s+([\d.]+) MHz", log)
            if fm and util:
                fmax = float(fm[-1]); placed = dict(lut4=util.get("LUT4", (0, 0))[0], alu=util.get("ALU", (0, 0))[0], dff=util.get("DFF", (0, 0))[0], lut4_available=util.get("LUT4", (0, 0))[1],
                                                    slots=util.get("LUT4", (0, 0))[0] + util.get("ALU", (0, 0))[0])
    finally:
        if not keep: shutil.rmtree(d, ignore_errors=True)
    est = ref["slots_estimate"]; reasons = []
    wrap_syn = (wsynth["slots"] - synth["slots"]) if (synth and wsynth) else None                 # what the LFSR / XOR wrapper adds in yosys, measured by difference
    pat_placed = (placed["slots"] - wrap_syn) if (placed and wrap_syn is not None) else None      # placed slots of the pattern itself (placed total minus the wrapper's own)
    if synth is None: reasons.append("yosys did not finish on the pattern alone")
    if placed is None: reasons.append("place and route did not complete")
    dev = (synth["slots"] - est) / est if synth else None                                          # yosys count against the planner (informational)
    devp = (pat_placed - est) / est if pat_placed is not None else None                              # PLACED count against the planner: this is the verification
    if devp is not None and abs(devp) > TOL: reasons.append("placed pattern is %+.1f%% from the planner estimate (limit %.0f%%)" % (100 * devp, 100 * TOL))
    if fmax is not None and fmax < FREQ: reasons.append("Fmax %.1f MHz is below the %d MHz target" % (fmax, FREQ))
    if placed and placed["lut4"] > placed["lut4_available"]: reasons.append("does not fit the device")
    return dict(format="hexn-pnr-v1", pattern_name=ref["name"], pattern_id=ref["pattern_id"], pattern_id_hex=ref["pattern_id_hex"], content_hash=ref["content_hash"],
                device=DEVICE, family=FAMILY, freq_target_mhz=FREQ, tools=dict(yosys=_ver(["yosys", "-V"]), nextpnr=_ver(["yowasp-nextpnr-himbaechel-gowin", "--version"])),
                synth_alone=synth, placed_with_wrapper=placed, fmax_mhz=fmax, wrapper_synth_slots=wrap_syn, placed_pattern_slots=pat_placed,
                packing_overhead_pct=None if (pat_placed is None or not synth) else round(100 * (pat_placed - synth["slots"]) / synth["slots"], 2),
                planner_estimate_slots=est, deviation_synth_pct=None if dev is None else round(100 * dev, 2), deviation_pct=None if devp is None else round(100 * devp, 2), verdict="PASS" if not reasons else "FAIL", reasons=reasons,
                date=datetime.date.today().isoformat(), caveats="one run, no seed sweep; Fmax is nextpnr's estimator; wrapped with an LFSR; not a board run")


def verified(ref, record):
    return (record.get("format") == "hexn-pnr-v1" and record.get("pattern_id") == ref.get("pattern_id") and record.get("content_hash") == ref.get("content_hash") and record.get("verdict") == "PASS"
            and not R.check_reference(ref))


if __name__ == "__main__":
    ref = json.load(open(sys.argv[1])); rec = pnr_run(ref, keep=sys.argv[3] if len(sys.argv) > 3 else None)
    json.dump(rec, open(sys.argv[2], "w"), indent=1, sort_keys=True); print(rec["verdict"], rec["reasons"])
