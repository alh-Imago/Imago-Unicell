#!/usr/bin/env python3
"""hexn_ir_decode_v1: decode the IR receiver's edge file (hexn_esp_log_v2.py: <name>_edges.csv, columns esp_us,level,host_s; level = pin level AFTER the edge, 1 = idle, 0 = burst) into NEC-style remote frames.
NEC as recorded by this receiver module: header = a 9 ms burst then a 4.5 ms space (data frame) or a 2.2 ms space (repeat frame, sent about every 108 ms while a key is held); a data frame is 32 bits, each a burst of about 0.56 to 0.65 ms (this module stretches them by about 70 to 90 us) followed by a space of about 0.5 ms (bit 0) or about 1.6 ms (bit 1), least significant bit first: address, address (inverted or an extension), command, command inverted. Thresholds here: space under 1100 us = 0, 1100 to 2200 us = 1.
Prints one line per key press: time of the first frame, address bytes, command, whether the command's inverse check passes, and how many repeat frames followed.
Usage: python3 tools/hexn_ir_decode_v1.py file_edges.csv"""
import sys, csv
def load(fn): return [(int(r[0]), int(r[1])) for r in csv.reader(open(fn)) if r and r[0].isdigit()]
def states(E): return [(E[i][1], E[i + 1][0] - E[i][0], E[i][0]) for i in range(len(E) - 1)]
def decode(E):
    st = states(E); out = []; i = 0
    while i < len(st) - 1:
        lv, d, t = st[i]
        if lv == 0 and 8000 <= d <= 10500:
            sp = st[i + 1][1]
            if 4000 <= sp <= 5000 and i + 66 < len(st):
                bits = []; ok = True
                for k in range(32):
                    mk = st[i + 2 + 2 * k]; sc = st[i + 3 + 2 * k]
                    if mk[0] != 0 or not 350 <= mk[1] <= 1000 or sc[0] != 1: ok = False; break
                    bits.append(1 if 1100 <= sc[1] <= 2200 else 0 if sc[1] < 1100 else None)
                if ok and None not in bits:
                    by = [sum(b << j for j, b in enumerate(bits[8 * n:8 * n + 8])) for n in range(4)]
                    out.append(dict(t=t, kind="data", bytes=by, repeats=0)); i += 66; continue
                out.append(dict(t=t, kind="bad", bytes=None, repeats=0)); i += 2; continue
            if 1800 <= sp <= 2700: out.append(dict(t=t, kind="repeat", bytes=None, repeats=0)); i += 3; continue
        i += 1
    return out
def presses(fr):
    ps = []
    for f in fr:
        if f["kind"] == "data": ps.append(dict(f)); 
        elif f["kind"] == "repeat":
            if ps: ps[-1]["repeats"] += 1
            else: ps.append(dict(f, note="started on a repeat frame (the first code of this hold was before the recording)"))
        else: ps.append(dict(f))
    return ps
def main():
    E = load(sys.argv[1]); fr = decode(E); ps = presses(fr); t0 = E[0][0]
    print("%d edges, %d frames (%d data, %d repeat, %d undecodable), %d key presses" % (len(E), len(fr), sum(f["kind"] == "data" for f in fr), sum(f["kind"] == "repeat" for f in fr), sum(f["kind"] == "bad" for f in fr), len(ps)))
    print(" #   t(s)  | address bytes | command | inverse ok | repeats")
    for n, p in enumerate(ps, 1):
        if p["kind"] == "data":
            a0, a1, c, ci = p["bytes"]; print("%2d  %6.2f |  0x%02X  0x%02X  |  0x%02X   |    %s     |  %d" % (n, (p["t"] - t0) / 1e6, a0, a1, c, "yes" if c ^ ci == 255 else "NO ", p["repeats"]))
        else: print("%2d  %6.2f | %s" % (n, (p["t"] - t0) / 1e6, p.get("note", p["kind"])))
if __name__ == "__main__": main()
