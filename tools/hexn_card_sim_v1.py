"""hexn_card_sim_v1.py - drive an ASSEMBLED Hex-N card design (hexn_card_top: hexn_frame_v1 + pattern + crossing) in iverilog through its UART, as a PC would (3 Nov 2026, Alan 10:07).
CardSim(outdir, clkdiv).run([...commands...]) -> list of replies. Commands: ("I",) ("W",) ("B", bytes) ("D", row, word) ("G", mask) ("L",) ("wait", clocks). One simulation of the whole sequence: after each command the driver waits long enough
for the frame's reply (the frame ignores a byte that arrives while it is still answering), so the sequence is fixed in advance.
Replies: I -> dict(pattern_id, rows); L -> list of (row, word, tick); the others -> b'K'. Same wire protocol as a real serial port, so tools/hexn_host_v1.py (later) can reuse the byte layouts."""
import os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TB = os.path.join(ROOT, "tests", "hexn_card_tb.v")


def encode(cmds, clkdiv):
    """-> (list of rx levels, list of (command, expected reply bytes))"""
    bit = clkdiv; lv = [1] * (4 * bit); plan = []
    def byte(b):
        for x in [0] + [(b >> i) & 1 for i in range(8)] + [1]: lv.extend([x] * bit)
    def idle(n): lv.extend([1] * n)
    for c in cmds:
        k = c[0]
        if k == "wait": idle(c[1]); continue
        if k == "I": byte(ord("I")); idle(10 * bit * 5 + 400); plan.append(("I", 5))
        elif k == "W": byte(ord("W")); idle(400 + 10 * bit * 2); plan.append(("K", 1))
        elif k == "B":
            byte(ord("B"))
            for x in c[1]: byte(x); idle(0)
            idle(10 * bit * 2 + 300); plan.append(("K", 1))
        elif k == "D":
            byte(ord("D")); byte(c[1])
            for i in range(4): byte((c[2] >> (8 * i)) & 255)
            idle(10 * bit * 2 + 100); plan.append(("K", 1))
        elif k == "G": byte(ord("G")); byte(c[1]); idle(10 * bit * 2 + 100); plan.append(("K", 1))
        elif k == "L": byte(ord("L")); idle(10 * bit * 113 + 800); plan.append(("L", None))
        else: raise ValueError(k)
    idle(10 * bit * 3)
    return lv, plan


def decode(changes, clkdiv, total):
    """tx transitions [(cycle, level)] -> list of (cycle of start bit, byte)"""
    lvl = [1] * total; cur = 1; last = 0
    for cyc, v in changes:
        for i in range(last, min(cyc, total)): lvl[i] = cur
        cur = v; last = cyc
    for i in range(last, total): lvl[i] = cur
    out = []; i = 0
    while i < total - 10 * clkdiv:
        if lvl[i] == 0 and (i == 0 or lvl[i - 1] == 1):
            b = 0
            for k in range(8): b |= lvl[i + clkdiv + clkdiv // 2 + k * clkdiv] << k
            out.append((i, b)); i += 10 * clkdiv
        else: i += 1
    return out


class CardSim:
    def __init__(self, outdir, clkdiv=8):
        self.dir, self.clkdiv = outdir, clkdiv

    def run(self, cmds):
        assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
        lv, plan = encode(cmds, self.clkdiv); d = tempfile.mkdtemp(prefix="card_")
        try:
            open(os.path.join(d, "rx.mem"), "w").write("\n".join(str(x) for x in lv) + "\n"); o = os.path.join(d, "o.vvp")
            src = os.path.join(self.dir, "src"); files = [os.path.join(src, f) for f in sorted(os.listdir(src))]
            c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-P", "tb.CLKDIV=%d" % self.clkdiv, "-o", o, TB] + files, capture_output=True, text=True)
            assert c.returncode == 0, c.stderr[:1500]
            out = subprocess.run(["vvp", o, "+rx=" + os.path.join(d, "rx.mem"), "+n=%d" % len(lv)], capture_output=True, text=True, timeout=1800).stdout.splitlines()
        finally:
            shutil.rmtree(d, ignore_errors=True)
        ch = [(int(a), int(b)) for a, b in (x.split() for x in out if x and x[0].isdigit() and len(x.split()) == 2 and x.split()[1] in "01")]
        by = [b for _, b in decode(ch, self.clkdiv, len(lv))]
        res = []; p = 0
        for kind, n in plan:
            if kind == "K": res.append(bytes(by[p:p + 1])); p += 1
            elif kind == "I": r = by[p:p + 5]; res.append(dict(pattern_id=int.from_bytes(bytes(r[:4]), "little"), rows=r[4])); p += 5
            else:
                cnt = by[p]; p += 1; ents = []
                for _ in range(cnt):
                    e = by[p:p + 7]; p += 7; ents.append((e[0], int.from_bytes(bytes(e[1:5]), "little"), int.from_bytes(bytes(e[5:7]), "little")))
                res.append(ents)
        return res
