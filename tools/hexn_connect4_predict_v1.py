"""hexn_connect4_predict_v1: CAN LAYER 3 PREDICT THE OPPONENT'S NEXT MOVE in Connect Four? (Python only; no RTL, nothing on a card.)
Alan, 29 Oct 2026: layer 3 can build a predictive model from the moves played; when it meets a position it tries to predict ahead; layer 4 then varies the depth of each branch by the predicted branch confidence. This is the test of the first half: how good, and how well calibrated, is layer 3's prediction?
Method (prequential: every prediction is made BEFORE the move is learned): layer 3 = tools/hexn_layer3_v1.py Layer3 unchanged, set up as in tools/hexn_connect4_l23_v1.py (two channels, 0 = X's columns, 1 = O's columns, path memory up to 5 snapshots, masks (1,1) and (1,0), start marker 7 on channel 1). X plays at random so that all positions get explored; O is the opponent under test. After each X move, `channel_view(1)` gives the predicted columns for O with weights; the real O move is then compared. Scored: top-1 hit, top-3 hit, against chance (1 / number of legal columns), and calibration: top-1 hit rate by the weight layer 3 gave to its top guess.
Opponents: RANDOM (should be unpredictable: chance level is the best possible), BLOCKER (wins if it can, else blocks, else random: partly predictable), lookahead(2) (deterministic up to ties).
Limits: the layer 3 contexts are move histories, not boards; X plays randomly (a different X changes what is learned); one seed per row unless stated; windows of games are small samples."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1, hexn_connect4_v1 as C
START = 7
def run(opp, games=2000, seed=0, window=500):
    rnd = random.Random(seed); m = V1.Layer3(nch=2, L=5, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)]); t = 0
    rows = []; cur = dict(n=0, top1=0, top3=0, chance=0.0, hist=[0, 0, 0, 0, 0, 0], cal=[[0, 0] for _ in range(4)])
    def feed(ch, key):
        nonlocal t
        t += 5; m.feed(t, ch, key); m.flush()
    for g in range(1, games + 1):
        b = C.new(); m.hist = []; m.snap = [None, None]; t += 20; m.feed(t, 1, START); m.flush(); turn = 1
        while True:
            if turn == 1: c = random.Random(rnd.random()).choice(C.legal(b))
            else:
                view = m.channel_view(1, top=3); c = opp(b, 2, rnd)
                if view:
                    lg = C.legal(b); cur["n"] += 1; cur["chance"] += 1.0 / len(lg)
                    cols = [k for k, w in view if k in lg]
                    if cols and cols[0] == c: cur["top1"] += 1
                    if c in cols[:3]: cur["top3"] += 1
                    w0 = view[0][1]; bk = 0 if w0 < 0.25 else 1 if w0 < 0.5 else 2 if w0 < 0.75 else 3
                    cur["cal"][bk][0] += 1; cur["cal"][bk][1] += (cols[:1] == [c])
            C.drop(b, c, turn); feed(0 if turn == 1 else 1, c)
            if C.winner(b) or C.full(b): break
            turn = 3 - turn
        if g % window == 0: rows.append(cur); cur = dict(n=0, top1=0, top3=0, chance=0.0, hist=[], cal=[[0, 0] for _ in range(4)])
    return rows
def main(games=2000, window=500, seeds=2):
    for name, opp in (("RANDOM opponent", C.opp_random), ("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))):
        print("\n%s (X plays randomly; layer 3 predicts O's reply before it is learned; mean of %d seeds)" % (name, seeds))
        res = [run(opp, games, s, window) for s in range(seeds)]
        print("%-16s %8s %8s %8s %8s" % ("games", "n/seed", "top-1", "top-3", "chance"))
        for i in range(len(res[0])):
            n = sum(r[i]["n"] for r in res)
            print("%-16s %8d %8.2f %8.2f %8.2f" % ("%d-%d" % (i * window + 1, (i + 1) * window), n // seeds, sum(r[i]["top1"] for r in res) / max(n, 1), sum(r[i]["top3"] for r in res) / max(n, 1), sum(r[i]["chance"] for r in res) / max(n, 1)))
        last = [r[-1] for r in res]
        print("calibration, last window: top weight 0-.25 / .25-.5 / .5-.75 / .75-1 -> [predictions, top-1 hit rate]: " + "  ".join("[%d, %s]" % (sum(l["cal"][k][0] for l in last), ("%.2f" % (sum(l["cal"][k][1] for l in last) / sum(l["cal"][k][0] for l in last))) if sum(l["cal"][k][0] for l in last) else "-") for k in range(4)), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
