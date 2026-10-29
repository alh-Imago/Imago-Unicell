"""CLEAR (0x47) of the Kintex tier command layer v2: after PUTs that reach the DDR3 level, CLEAR empties every level, zeroes the 17 counters, makes earlier DDR3 lines read as not written, answers ready; the tier then behaves like a fresh Tier3 (same random stream compared with the Python reference) and a second CLEAR works too. Simulation only."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_hexn_tier7_cmd_v1 as T1
T1.SRCS = ["rtl/tb_hexn_tier7_cmd_v2.v", "rtl/hexn_tier7_cmd_v2.v", "rtl/hexn_tier_v8.v", "rtl/sim/wb_ddr_model_v1.v"]
_run = T1.run
def run(script, **params):
    import shutil, subprocess, tempfile
    d = tempfile.mkdtemp(); out = os.path.join(d, "t.vvp")
    subprocess.run(["iverilog", "-g2012", "-o", out] + ["-Ptb_hexn_tier7_cmd_v2.%s=%d" % (k, v) for k, v in params.items()] + [os.path.join(T1.ROOT, s) for s in T1.SRCS], check=True, capture_output=True)
    open(os.path.join(d, "script.hex"), "w").write("\n".join("%02x" % b for b in script) + "\n")
    o = subprocess.run(["vvp", out, "+n=%d" % len(script)], capture_output=True, text=True, timeout=3000, cwd=d).stdout
    assert "END ddr_err 0" in o, o[-800:]
    return bytes(int(l.split()[1], 16) for l in o.splitlines() if l.startswith("T "))
import hexn_tier7_host_v2 as H
from hexn_tier_ref_v3 import Tier3
def test_clear_empties_everything_and_the_tier_works_again():
    KW, VW, FB, BMB, RAMB, SB = 14, 14, 3, 6, 3, 3; MK = (1 << KW) - 1; MV = (1 << VW) - 1
    def stream(t, cmds, expect, base, n):
        for k in range(n):
            r = T1.h32(k + base); ki = (r >> 4) % 300; kk = ((ki + 1) * 0x2545F491 & 0xFFFFFFFF) & MK
            if ((r >> 20) % 10) < 4:
                v = T1.h32(k + base + 0x5151) & MV; t.put(kk, v); cmds.append(H.cmd_put(kk, v)); expect.append(("put", None))
            else:
                f, v = t.get(kk); cmds.append(H.cmd_get(kk)); expect.append(("get", (int(f), v if f else 0)))
    cmds, expect = [], []; t1 = Tier3(KW=KW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, SPS=8)
    stream(t1, cmds, expect, 0x1111, 400); assert t1.n["sd_blk_wr"] > 0 and t1.n["promote_sd"] > 0
    cmds.append(H.cmd_flush()); expect.append(("put", None)); written_before = sorted(t1.written)
    cmds.append(H.cmd_clear()); expect.append(("clear", None))
    cmds.append(H.cmd_counters()); expect.append(("zero", None))
    for i in range(1 << FB): cmds.append(H.cmd_level(0, i)); expect.append(("empty", None))
    for i in range(1 << RAMB): cmds.append(H.cmd_level(1, i)); expect.append(("empty", None))
    for i in written_before: cmds.append(H.cmd_line(i)); expect.append(("notwritten", None))
    t2 = Tier3(KW=KW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, SPS=8)
    stream(t2, cmds, expect, 0x4242, 400)
    cmds.append(H.cmd_counters()); expect.append(("counters", dict(t2.n)))
    cmds.append(H.cmd_clear()); expect.append(("clear", None)); cmds.append(H.cmd_counters()); expect.append(("zero", None))
    got = run(b"".join(cmds), KW=KW, VW=VW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, LAT=25, JIT=3, STALLP=9, SP=3)
    pos = 0
    for c, (kind, want) in zip(cmds, expect):
        ln = H.REPLY_LEN[c[0]]; r = got[pos:pos + ln]; pos += ln; assert len(r) == ln, (kind, pos, len(got))
        if kind == "get": p = H.parse_get(r); assert (p["found"], p["value"]) == want, (c.hex(), p, want)
        elif kind == "clear": s = H.status(r[0]); assert s["ready"] == 1 and s["ddr_err"] == 0, s
        elif kind == "zero": assert all(v == 0 for v in H.parse_counters(r).values()), H.parse_counters(r)
        elif kind == "empty": assert H.parse_level(r) == (0, 0)
        elif kind == "notwritten": p = H.parse_line(r); assert p["written"] == 0 and all(e == (0, 0) for e in p["entries"]), p
        elif kind == "counters": assert H.parse_counters(r) == want, (H.parse_counters(r), want)
        elif kind == "put": assert H.status(r[0])["ddr_err"] == 0
    assert pos == len(got)
