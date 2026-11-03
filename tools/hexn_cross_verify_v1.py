"""hexn_cross_verify_v1.py - run a pattern program through hexn_xtop_v1 (the serial<->parallel crossing on every row; sub/verilog/hexn_cross_v1.v) with iverilog (3 Nov 2026, Alan 10:07).
xrun(ref, program, inputs, ...) -> {"out": {name: [(tick, word)]}, "serial_in_tick": t}. The inputs are PARALLEL words (one per input pad row, presented with a one-clock valid); the outputs are the parallel words with the tick of their one-clock valid.
Ticks are counted so that a word whose valid is given at tick -1 is on the west pad (flag) at tick 0, the same zero as hexn_pattern_verify's sim_run: an output's tick here is (the tick sim_run gives for its flag on the east pad) + 33 (measured)."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hexn_pattern_gen_v8 as P

TB = os.path.join(ROOT, "tests", "hexn_xtop_tb.v")
EXTRA = [os.path.join(ROOT, "sub", "verilog", f) for f in ("hexn_cross_v1.v", "hexn_xtop_v1.v")]


def xrun(ref, program, inputs, extra_clocks=200, gap=2):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    words, widths = P.load_words(ref, program); rows = ref["rows"]
    in_rows = {n: v[0] for n, v in program["pads_in"].items()}; out_rows = {n: v[0] for n, v in program["pads_out"].items()}
    stim = [dict(cfg_en=1, cfg_in=b) for b in P.chain_bits(words, widths)] + [dict() for _ in range(gap)]
    t0 = len(stim)
    stim.append({"v": sum(1 << in_rows[n] for n in inputs)})                       # valid in the clock before tick 0
    while len(stim) < t0 + 32 + 40 + extra_clocks: stim.append(dict())
    lines = ["%08x" % (s.get("cfg_in", 0) | (s.get("cfg_en", 0) << 1) | (s.get("clear", 0) << 2) | (s.get("v", 0) << 3)) for s in stim]
    data = ["%08x" % (inputs[next(n for n in inputs if in_rows[n] == r)] if any(in_rows[n] == r for n in inputs) else 0) for r in range(rows)]
    d = tempfile.mkdtemp(prefix="xtop_")
    try:
        open(os.path.join(d, "top.v"), "w").write(P.generate(ref)); open(os.path.join(d, "stim.hex"), "w").write("\n".join(lines) + "\n"); open(os.path.join(d, "data.hex"), "w").write("\n".join(data) + "\n")
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.ROWS=%d" % rows, "-P", "tb.COLS=%d" % ref["cols"], "-o", o, TB, os.path.join(d, "top.v")] + P.FILES + EXTRA, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        out = subprocess.run(["vvp", o, "+stim=" + os.path.join(d, "stim.hex"), "+data=" + os.path.join(d, "data.hex"), "+n=%d" % len(stim)], capture_output=True, text=True, timeout=600).stdout.splitlines()
        out = [x.split() for x in out if x and set(x.split()[0]) <= {"0", "1"} and len(x.split()) == rows + 1]
        assert len(out) == len(stim), (len(out), len(stim))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    res = {}
    for name, r in out_rows.items():
        res[name] = [(t - t0, int(x[1 + r], 16)) for t, x in enumerate(out) if t >= t0 and x[0][::-1][r] == "1"]
    return dict(out=res)
