"""Byte-level test of the JTAG command layer of the Kintex tier (rtl/hexn_tier7_cmd_v1.v + hexn_tier_v8.v): a script of PUT / GET / COUNTERS / INFO / FLUSH / LEVEL / LINE commands is sent byte by byte (transmit side busy at random, slow DDR3 stand-in) and every answer is compared with tools/hexn_tier_ref_v3.py (Tier3, SPS = 8): replies of PUT and GET, the counters, every entry of both upper levels and every DDR3 line."""
import os, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tier7_host_v1 as H
from hexn_tier_ref_v3 import Tier3
SRCS = ["rtl/tb_hexn_tier7_cmd_v1.v", "rtl/hexn_tier7_cmd_v1.v", "rtl/hexn_tier_v8.v", "rtl/sim/wb_ddr_model_v1.v"]
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def run(script, **params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    d = tempfile.mkdtemp(); out = os.path.join(d, "t.vvp")
    subprocess.run(["iverilog", "-g2012", "-o", out] + ["-Ptb_hexn_tier7_cmd_v1.%s=%d" % (k, v) for k, v in params.items()] + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    open(os.path.join(d, "script.hex"), "w").write("\n".join("%02x" % b for b in script) + "\n")
    o = subprocess.run(["vvp", out, "+n=%d" % len(script)], capture_output=True, text=True, timeout=3000, cwd=d).stdout
    assert "END ddr_err 0" in o, o[-800:]
    return bytes(int(l.split()[1], 16) for l in o.splitlines() if l.startswith("T "))
def check(KW=12, VW=12, FB=4, BMB=8, RAMB=6, SB=5, NK=120, STEPS=200, **sim):
    t = Tier3(KW=KW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, SPS=8); MK = (1 << KW) - 1; MV = (1 << VW) - 1
    cmds = [H.cmd_info()]; expect = []   # expect: (kind, payload)
    expect.append(("info", None))
    for n in range(STEPS):
        r = h32(n + 0x1111); ki = (r >> 4) % NK; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
        if ((r >> 20) % 10) < 4:
            v = h32(n + 0x5151) & MV; t.put(kk, v); cmds.append(H.cmd_put(kk, v)); expect.append(("put", None))
        else:
            f, v = t.get(kk); cmds.append(H.cmd_get(kk)); expect.append(("get", (int(f), v if f else 0)))
    cmds.append(H.cmd_counters()); expect.append(("counters", dict(t.n)))
    t.flush(); cmds.append(H.cmd_flush()); expect.append(("flush", None))
    for i in range(1 << FB): cmds.append(H.cmd_level(0, i)); e = t.fast.get(i); expect.append(("level", (((1 << 31) | e[0], e[1]) if e else (0, 0))))
    for i in range(1 << RAMB): cmds.append(H.cmd_level(1, i)); e = t.sdram.get(i); expect.append(("level", (((1 << 31) | e[0], e[1]) if e else (0, 0))))
    for i in range(1 << SB):
        cmds.append(H.cmd_line(i)); w = i in t.written
        ents = [((((1 << 31) | e[0]), e[1]) if e else (0, 0)) for e in (t.sec[i] if w else [None] * 8)]
        expect.append(("line", (int(w), ents)))
    cmds.append(H.cmd_counters()); expect.append(("counters", dict(t.n)))
    cmds.append(bytes([0x7F])); expect.append(("bad", None))
    cmds.append(H.cmd_info()); expect.append(("info", None))
    got = run(b"".join(cmds), KW=KW, VW=VW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, **sim)
    pos = 0
    for c, (kind, want) in zip(cmds, expect):
        ln = 1 if kind == "bad" else H.REPLY_LEN[c[0]]; r = got[pos:pos + ln]; pos += ln
        assert len(r) == ln, ("short answer", kind, pos, len(got))
        if kind == "info": p = H.parse_info(r); assert (p["KW"], p["VW"], p["FB"], p["BMB"], p["RAMB"], p["SB"], p["bucket"], p["ready"], p["ddr_err"]) == (KW, VW, FB, BMB, RAMB, SB, 8, 1, 0), p
        elif kind == "get": p = H.parse_get(r); assert (p["found"], p["value"]) == want and p["ddr_err"] == 0, (c, p, want)
        elif kind in ("put", "flush"): assert H.status(r[0])["ddr_err"] == 0 and H.status(r[0])["ready"] == 1
        elif kind == "counters": assert H.parse_counters(r) == want, (H.parse_counters(r), want)
        elif kind == "level": assert H.parse_level(r) == want, (c.hex(), H.parse_level(r), want)
        elif kind == "line": p = H.parse_line(r); assert (p["written"], p["entries"]) == want and p["ddr_err"] == 0, (c.hex(), p, want)
        elif kind == "bad": assert r == b"\xee"
    assert pos == len(got), ("extra bytes", pos, len(got))
    return t
def test_commands_answer_like_the_reference():
    t = check(); n = t.n
    assert n["promote_sd"] > 0 and n["demote_sd"] > 0 and n["sd_blk_wr"] > 0 and len(t.fast) > 0 and len(t.sdram) > 0
def test_slow_ddr_and_full_lines():
    check(KW=14, FB=3, RAMB=3, SB=3, BMB=6, NK=300, STEPS=400, LAT=25, JIT=3, STALLP=9, SP=3)
class FakeLink:
    """a link that runs a recorded script through the simulation lazily, to try Tier7Dev and dump_all"""
    def __init__(self, **p): self.p = p; self.buf = bytearray(); self.out = None
    def write(self, b): self.buf += b
    def read(self, n):
        if self.out is None:
            self.out = run(bytes(self.buf), **self.p); self.pos = 0
        r = self.out[self.pos:self.pos + n]; self.pos += n; return r
def test_dump_all_roundtrip(tmp_path):
    # record the command sequence of dump_all with a recording link, then replay it through the simulation
    class Rec:
        def __init__(s): s.w = bytearray(); s.n = 0
        def write(s, b): s.w += b; s.last = b[0]
        def read(s, n):
            if s.last == H.OP_INFO: return bytes([4, 12, 12, 4, 8, 6, 5, 8])
            if s.last == H.OP_LEVEL or s.last == H.OP_COUNTERS or s.last == H.OP_LINE: return bytes(n)
            return bytes(n)
    rec = Rec(); H.Tier7Dev(rec).dump_all()
    pre = H.cmd_put(5, 77) + H.cmd_put(900, 5) + H.cmd_get(5)
    out = run(pre + bytes(rec.w), KW=12, VW=12, FB=4, BMB=8, RAMB=6, SB=5)
    class Rep:
        def __init__(s): s.o = out[REPLEN:]; s.p = 0
        def write(s, b): pass
        def read(s, n): r = s.o[s.p:s.p + n]; s.p += n; return r
    REPLEN = 1 + 1 + 5
    class Pair:
        def __init__(s): s.rep = Rep()
        def write(s, b): pass
        def read(s, n): return s.rep.read(n)
    path = str(tmp_path / "dump.json"); d = H.Tier7Dev(Pair()).dump_all(path)
    assert d["info"]["SB"] == 5 and os.path.getsize(path) > 100
    keys = {v[0] & 0xFFF for v in list(d["level0"].values()) + list(d["level1"].values())}
    assert len(d["level0"]) + len(d["level1"]) + sum(len([e for e in l if e[0] >> 31]) for l in d["lines"].values()) == 2
