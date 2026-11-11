"""hexn_bytecard_sim_v2.py (11 Nov 2026: clone of hexn_bytecard_sim_v1.py; ADDED the command ("rawgap", bytes, reply bytes, gap, idle): raw bytes with a chosen gap between them instead of the bridge's 128 clocks, and the test bench memory is no longer the limit check: at most 65,536 bytes per run is asserted. Earlier text:) - drive hexn_arr_core (frame v4 + pattern) in iverilog through its BYTE PORT, as the Kintex JTAG bridge does (4 Nov 2026).
ByteSim(src_dir).run([...commands...]) -> list of replies; same commands and replies as tools/hexn_card_sim_v1.CardSim: ("I",) ("W",) ("B", bytes) ("D", row, word) ("G", mask) ("L",) ("wait", clocks).
Bytes are handed over FSPACING (128) clocks apart, as the bridge does; after each command a fixed idle covers the reply. src_dir = the `src` folder written by `hexn_kxarr_v1.py sim`."""
import os, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TB = os.path.join(ROOT, "tests", "hexn_bytecard_tb.v")
FSP = 128


def encode(cmds):
    """-> (list of (gap, byte), tail clocks, plan [(kind, nbytes)])"""
    seq = []; plan = []; pending_gap = 40
    def put(b, extra=0):
        nonlocal pending_gap
        seq.append((pending_gap + extra, b)); pending_gap = FSP - 1
    def idle(n):
        nonlocal pending_gap
        pending_gap += n
    for c in cmds:
        k = c[0]
        if k == "wait": idle(c[1]); continue
        if k == "I": put(ord("I")); idle(1200); plan.append(("I", 5))
        elif k == "W": put(ord("W")); idle(1500); plan.append(("K", 1))
        elif k == "B":
            put(ord("B"))
            for x in c[1]: put(x)
            idle(1500); plan.append(("K", 1))
        elif k == "D":
            put(ord("D")); put(c[1])
            for i in range(4): put((c[2] >> (8 * i)) & 255)
            idle(1200); plan.append(("K", 1))
        elif k == "raw": [put(x) for x in c[1]]; idle(c[3] if len(c) > 3 else 1500); plan.append(("N", c[2]))
        elif k == "rawgap":                                   # ("rawgap", bytes, reply bytes, gap clocks between bytes, idle after): bytes closer together than the bridge sends them (to shorten long loads in simulation)
            for i, x in enumerate(c[1]):
                put(x)
                if i < len(c[1]) - 1: pending_gap = c[3]
            idle(c[4] if len(c) > 4 else 1500); plan.append(("N", c[2]))
        elif k == "S": put(ord("S")); idle(1200); plan.append(("S", 13))
        elif k == "G": put(ord("G")); put(c[1]); idle(1200); plan.append(("K", 1))
        elif k == "L": put(ord("L")); idle(113 * 40 + 3000); plan.append(("L", None))
        else: raise ValueError(k)
    return seq, pending_gap + 2000, plan


class ByteSim:
    def __init__(self, src_dir): self.src = src_dir

    def run(self, cmds):
        assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
        seq, tail, plan = encode(cmds); assert len(seq) <= 65536, "the test bench holds 65,536 bytes"; d = tempfile.mkdtemp(prefix="bytecard_")
        try:
            open(os.path.join(d, "rx.mem"), "w").write("\n".join("%08x" % ((g << 8) | b) for g, b in seq) + "\n"); o = os.path.join(d, "o.vvp")
            files = [os.path.join(self.src, f) for f in sorted(os.listdir(self.src))]
            c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, TB] + files, capture_output=True, text=True)
            assert c.returncode == 0, c.stderr[:1500]
            out = subprocess.run(["vvp", o, "+rx=" + os.path.join(d, "rx.mem"), "+n=%d" % len(seq), "+tail=%d" % tail], capture_output=True, text=True, timeout=3600).stdout.splitlines()
        finally:
            shutil.rmtree(d, ignore_errors=True)
        by = [int(x.split()[2]) for x in out if x.startswith("T ")]; self.by = by
        res = []; p = 0
        for kind, n in plan:
            if kind == "K": res.append(bytes(by[p:p + 1])); p += 1
            elif kind == "N": res.append(bytes(by[p:p + n])); p += n
            elif kind == "S": res.append(list(by[p:p + 13])); p += 13
            elif kind == "I": r = by[p:p + 5]; res.append(dict(pattern_id=int.from_bytes(bytes(r[:4]), "little"), rows=r[4])); p += 5
            else:
                cnt = by[p]; p += 1; ents = []
                for _ in range(cnt):
                    e = by[p:p + 7]; p += 7; ents.append((e[0], int.from_bytes(bytes(e[1:5]), "little"), int.from_bytes(bytes(e[5:7]), "little")))
                res.append(ents)
        return res
