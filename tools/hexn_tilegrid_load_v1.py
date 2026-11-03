"""hexn_tilegrid_load_v1.py - load a Hex-N unit file (or a bare icm-hexn file) onto the tile grid sub/verilog/hexn_tilegrid_v1.v (2 Nov 2026).
unit -> program (header and checksums checked, weights never read) -> one config word per tile (routing cells as route tables, UN work cells as the unary core) -> chain bits -> optional run in iverilog.
Scope, stated plainly: the tile holds ONLY the unary core, so a program with any other work-cell type is refused by name (no guessing). Pads must be on the west edge (inputs, column 0) and the east edge (outputs, last column).
Faces: 0 N, 1 E, 2 S, 3 W. Unused outputs of a tile read index 7 (constant 0)."""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hexn_unit_file_v1 as U, hexn_icm_export_v2 as X, hexn_tile_cfg_v1 as C

SRC = [os.path.join(ROOT, "sub", "verilog", f) for f in ("hexn_tilegrid_v1.v", "hexn_tile_v2.v", "hexn_unary_core_v1.v")]
TB = os.path.join(ROOT, "tests", "hexn_tilegrid_tb.v")
UNARY = {"cp", "shl", "shr"}


def program_of(src):
    """src: unit dict or bare icm-hexn dict -> the program dict (X.from_icm form). Refuses a damaged unit; never reads the weights."""
    if isinstance(src, dict) and src.get("header", {}).get("format") == U.MAGIC:
        prog, rep = U.unicell_view(src)
        if prog is None:
            raise ValueError("unit file refused: header %s, program %s" % (rep["header"], rep["program"]))
        src = prog
    return X.from_icm(src)


def tile_words(program):
    """-> dict(rows, cols, words (row-major, chain order), in_rows {name: row}, out_rows {name: row})"""
    pts = [tuple(map(int, k.split(","))) for k in list(program["cells"]) + list(program["routing"])] + [tuple(v) for v in list(program["pads_in"].values()) + list(program["pads_out"].values())]
    rows, cols = max(p[0] for p in pts) + 1, max(p[1] for p in pts) + 1
    for n, (r, c) in program["pads_in"].items():
        if c != 0: raise ValueError("input pad %s is at column %d: only the west edge (column 0) is wired out" % (n, c))
    for n, (r, c) in program["pads_out"].items():
        if c != cols - 1: raise ValueError("output pad %s is at column %d: only the east edge (column %d) is wired out" % (n, c, cols - 1))
    words = []
    for r in range(rows):
        for c in range(cols):
            key = "%d,%d" % (r, c)
            if key in program["cells"]:
                cell = program["cells"][key]
                if cell["type"] != "UN" or cell["kind"] not in UNARY:
                    raise ValueError("cell %s is %s/%s: the tile has only the unary core (cp shl shr), not built for other cores yet" % (key, cell["type"], cell["kind"]))
                words.append(C.pack({o: 7 for o in "NESW"}, "W", ("E",), cell["kind"], cell["k"]))
            else:
                sel = dict(program["routing"].get(key, {}))
                words.append(C.pack({**{o: 7 for o in "NESW"}, **sel}, "W", (), "cp", 0))
    return dict(rows=rows, cols=cols, words=words, in_rows={n: v[0] for n, v in program["pads_in"].items()}, out_rows={n: v[0] for n, v in program["pads_out"].items()})


def rtl_run(tw, inputs, extra_clocks=140, gap=2, srcs=None):
    """load the chain, then put each input word (name -> int) on its row's west lane at the same clock; returns dict(loaded_at, start, out {name: [(line, word)]}). Needs iverilog."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    R, Cc = tw["rows"], tw["cols"]
    stim = [dict(cfg_en=1, cfg_in=b) for b in C.chain_bits(tw["words"])] + [dict() for _ in range(gap)]
    t0 = len(stim)
    while len(stim) < t0 + 32 + extra_clocks: stim.append(dict())
    for name, w in inputs.items():
        r = tw["in_rows"][name]
        for i in range(32): stim[t0 + i]["w%d" % r] = (1 if i == 0 else 0, (w >> i) & 1)
    lines = []
    for s in stim:
        v = s.get("cfg_in", 0) | (s.get("cfg_en", 0) << 1) | (s.get("clear", 0) << 2)
        for r in range(R):
            f, d = s.get("w%d" % r, (0, 0)); v |= (d << (3 + 2 * r)) | (f << (4 + 2 * r))
        lines.append("%08x" % v)
    d = tempfile.mkdtemp(prefix="tilegrid_")
    try:
        open(os.path.join(d, "stim.hex"), "w").write("\n".join(lines) + "\n"); o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.ROWS=%d" % R, "-P", "tb.COLS=%d" % Cc, "-o", o, TB] + (srcs or SRC), capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        out = subprocess.run(["vvp", o, "+stim=" + os.path.join(d, "stim.hex"), "+n=%d" % len(stim)], capture_output=True, text=True, timeout=600).stdout.split()
        out = [x for x in out if len(x) == 1 + 2 * R and set(x) <= {"0", "1"}]
        assert len(out) == len(stim), (len(out), len(stim))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    ef = [x[1:1 + R][::-1] for x in out]; ed = [x[1 + R:][::-1] for x in out]                     # printed row R-1 first; flip so index = row
    res = {}
    for name, r in tw["out_rows"].items():
        got = []
        for t in range(len(out)):
            if t >= t0 and ef[t][r] == "1":
                if t + 32 > len(out): raise AssertionError("word cut off")
                got.append((t - t0, sum(int(ed[t + i][r]) << i for i in range(32))))
        res[name] = got
    return dict(start=t0, out=res, chain_clocks=len(tw["words"]) * C.width())
