"""hexn_promote_v1: HOW MANY SIGHTINGS BEFORE A CANDIDATE IS PROMOTED TO A KNOWN SEQUENCE (the promotion level N), and how the right N depends on the data (Alan, 27 Oct 2026: the level is set by the host at the start but must be variable, depending on the data analysed, i.e. part of the training set-up; the counts add real value). Python only; no RTL; new file; uses hexn_layer2_v2's routines through the plan file, no other tool.
Model: the stream is blocks (keys up to a goal key 7 or 8). Known blocks = the four routines A to D. Each block that is not known is an ANOMALY and is held as a CANDIDATE with a count of sightings; a candidate reaching N sightings becomes a known block (promoted). Two kinds of anomaly are mixed into a random-order stream of routines: (1) NOISE: with probability r per block, one extra random digit key (1 to 9) is inserted at a random place (a different block almost every time, but repeats happen by chance); (2) a REAL NEW ROUTINE E = 1 5 3 7 that Alan starts using: it makes up 1 block in 6 from block 200 on.
Per N and noise rate r (5000 blocks, 200 streams): false promotions per 1000 blocks (a noise block promoted), blocks of E that were alarmed before E was promoted (the cost of waiting, N-1 alarms if E is seen N times), and the block number at which E is promoted. 
What the host can measure from training data: the anomaly REPEAT RATE (how often an anomaly block recurs as the same block). The table's last column is the smallest N giving fewer than 1 false promotion per 1000 blocks.
Limits: synthetic stream built from the known routine design, not recorded; noise is one inserted digit; blocks compared whole (an exact repeat); counts do not decay.
Usage: python3 tools/hexn_promote_v1.py"""
import random
ROUT = {"A": (1, 2, 3, 7), "B": (4, 2, 3, 8), "C": (1, 5, 6, 8), "D": (4, 5, 6, 7)}; E = (1, 5, 3, 7)
def stream(rnd, r, nblk, new_from=200):
    out = []
    for b in range(nblk):
        if b >= new_from and rnd.random() < 1 / 6: blk = E; kind = "E"
        else: blk = ROUT[rnd.choice("ABCD")]; kind = "R"
        if kind == "R" and rnd.random() < r:
            pos = rnd.randrange(0, len(blk)); blk = blk[:pos] + (rnd.randrange(1, 10),) + blk[pos:]; kind = "N"
        out.append((blk, kind))
    return out
def run(N, r, seeds=200, nblk=5000):
    fp = alarmE = 0.0; when = []; norm = 0
    for s in range(seeds):
        rnd = random.Random(s * 7 + 1); known = set(ROUT.values()); cand = {}; prom_E = None; al = 0
        for i, (blk, kind) in enumerate(stream(rnd, r, nblk)):
            if blk in known: continue
            cand[blk] = cand.get(blk, 0) + 1
            if kind == "E" and prom_E is None: al += 1
            if cand[blk] >= N:
                known.add(blk)
                if kind == "N": fp += 1
                if kind == "E" and prom_E is None: prom_E = i
        alarmE += al; when.append(prom_E if prom_E is not None else nblk)
    return fp / seeds / nblk * 1000, alarmE / seeds, sum(when) / len(when)
def run_w(N, W, r, seeds=100, nblk=5000):
    """Promotion on N sightings inside the last W blocks (a rate, counts forgotten after W blocks)."""
    fp = alarmE = 0.0; when = []
    for s in range(seeds):
        rnd = random.Random(s * 7 + 1); known = set(ROUT.values()); seen = {}; prom_E = None; al = 0
        for i, (blk, kind) in enumerate(stream(rnd, r, nblk)):
            if blk in known: continue
            L = [t for t in seen.get(blk, []) if i - t < W] + [i]; seen[blk] = L
            if kind == "E" and prom_E is None: al += 1
            if len(L) >= N:
                known.add(blk)
                if kind == "N": fp += 1
                if kind == "E" and prom_E is None: prom_E = i
        alarmE += al; when.append(prom_E if prom_E is not None else nblk)
    return fp / seeds / nblk * 1000, alarmE / seeds, sum(when) / len(when)
def main_w():
    print("\nRATE RULE: promote on N=3 sightings inside the last W blocks (counts older than W are forgotten)\n")
    print(" noise r | W  | false per 1000 | E alarms | E promoted at block")
    for r in (0.02, 0.1, 0.3, 0.6):
        for W in (10, 20, 40, 80, 5000):
            fp, al, w = run_w(3, W, r); print(" %.2f    | %4d | %14.3f | %8.2f | %8.0f" % (r, W, fp, al, w))
def main():
    print("N = sightings before promotion; false = noise blocks wrongly promoted per 1000 blocks; E alarms = blocks of the new routine flagged before it became known; E block = block number at which the new routine was promoted (it starts at block 200)\n")
    best = {}
    for r in (0.02, 0.1, 0.3, 0.6):
        print("noise rate r = %.2f (share of blocks with an inserted digit)" % r); print(" N | false per 1000 | E alarms | E promoted at block")
        for N in (1, 2, 3, 4, 5):
            fp, al, w = run(N, r, 100); print(" %d | %14.3f | %8.2f | %8.0f" % (N, fp, al, w)); 
            if fp < 1 and r not in best: best[r] = N
        print()
    print("smallest N with under 1 false promotion per 1000 blocks:", {("%.2f" % r): best.get(r, ">5") for r in (0.02, 0.1, 0.3, 0.6)})
if __name__ == "__main__": main(); main_w()
