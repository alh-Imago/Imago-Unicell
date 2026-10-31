"""Check of rtl/hexn_store_v6.v (LRU eviction of whole contexts) against rtl/hexn_store_v5.v with the small testbench rtl/tb_hexn_store_v6.v (needs iverilog).
(1) When the heap never fills, v6 must give EXACTLY the same answers as v5 (the stamp, dead bit and eviction FSM must be invisible).
(2) When the heap is small and fills (sizes set by -P), v5 drops new entries and stops learning; v6 evicts and keeps learning: next-event accuracy over a stream whose function changes half way.
Stream: alphabet 6; next event = fixed function of the last two events with probability 0.9, else random; for every step the store is asked to predict (RD) and then told the event (OBS). Promotion N=1. Prints accuracy (prediction made and right / all steps) in windows, counters, and the longest command in clocks."""
import os, random, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); A = 6
def stim(seed, n, switch=None):
    rnd = random.Random(seed); T1 = [[rnd.randrange(A) for _ in range(A)] for _ in range(A)]; T2 = [[rnd.randrange(A) for _ in range(A)] for _ in range(A)]
    ev = [rnd.randrange(A), rnd.randrange(A)]
    while len(ev) < n: T = T2 if (switch and len(ev) >= switch) else T1; ev.append(T[ev[-2]][ev[-1]] if rnd.random() < 0.9 else rnd.randrange(A))
    words = []; t = 0
    for e in ev: words.append((3 << 28) | (0 << 24) | t); words.append((1 << 28) | (e << 24) | t); t += 1
    return ev, words
def run(v5, words, params, d):
    f = os.path.join(d, "stim.hex"); open(f, "w").write("\n".join("%08x" % w for w in words) + "\n"); exe = os.path.join(d, "sim_v5" if v5 else "sim_v6")
    cmd = ["iverilog", "-g2005-sv", "-o", exe, "-s", "tb_hexn_store_v6"] + (["-DV5"] if v5 else []) + ["-P%s=%s" % ("tb_hexn_store_v6." + k, v) for k, v in params.items()] + [os.path.join(ROOT, "rtl/tb_hexn_store_v6.v"), os.path.join(ROOT, "rtl/hexn_store_v5.v" if v5 else "rtl/hexn_store_v6.v")]
    subprocess.run(cmd, check=True); lg = os.path.join(d, "log.txt")
    out = subprocess.run(["vvp", exe, "+stim=" + f, "+count=%d" % len(words), "+log=" + lg], capture_output=True, text=True).stdout
    return open(lg).read().split("\n")[:-1], out
def score(ev, lines, spans):
    # lines: one per command, in pairs (RD, OBS); RD line gives plevel/pbest for the NEXT event ev[i]
    res = []
    for a, b in spans:
        ok = 0
        for i in range(a, b):
            v, vl, pl, pb = map(int, lines[2 * i].split()); ok += (pl > 0 and pb == ev[i])
        res.append(ok / (b - a))
    return res
def main():
    d = tempfile.mkdtemp(); fails = 0
    ev, w = stim(1, 400); big = {"IB": 10, "RB": 9}
    l5, o5 = run(True, w, big, d); l6, o6 = run(False, w, big, d)
    same = l5[:-1] == l6[:-1]; print("(1) big heap, 400 events: answers identical to v5:", same, "| v5 counters:", l5[-1], "| v6 counters:", l6[-1]); fails += (not same)
    ev, w = stim(2, 2400, switch=1200); small = {"IB": 7, "RB": 4}
    l5, o5 = run(True, w, small, d); l6, o6 = run(False, w, small, d)
    spans = [(600, 1200), (1200, 1400), (1400, 2400)]
    print("(2) small heap (16 rows x 4 slots, 128 index slots), function changes at event 1200; windows 600-1200 | 1200-1400 | 1400-2400")
    print("    v5 (drops when full):", " ".join("%.3f" % x for x in score(ev, l5, spans)), "|", l5[-1], "|", [x for x in o5.split("\n") if x.startswith("MAXCYC")][0])
    print("    v6 (LRU eviction)   :", " ".join("%.3f" % x for x in score(ev, l6, spans)), "|", l6[-1], "|", [x for x in o6.split("\n") if x.startswith("MAXCYC")][0])
    print("    (S known cand promoted dropk dropc evict)")
    return fails
if __name__ == "__main__": sys.exit(1 if main() else 0)
