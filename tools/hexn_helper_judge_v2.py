"""hexn_helper_judge_v2: THE JUDGE LEARNS FROM A DEEPER SEARCH INSTEAD OF THE GAME RESULT (Python + numpy only; no RTL, nothing on a card; imports hexn_helper_judge_v1.py unchanged).
Why (30 Oct 2026, 16:40): v1 trained on the final result of each game. Layer 4 wins 86 to 96 percent of those games, so the labels are almost all +1; the network reached a held-out correlation of about 0.2, no better than the hand score (0.26), and overfitted after 10 epochs (log row 16:45). Here each recorded position is relabelled with the value of a 4-ply minimax search of the hand score (tools/hexn_connect4_v1.py `search`, the same search the lookahead(2) opponent uses, from X's side), squashed as tanh(value/40). The judge then tries to be a one-look copy of a 4-ply search. Positions and games are those of v1.
Usage: python3 tools/hexn_helper_judge_v2.py relabel IN.npz OUT.npz DEPTH   |   (train with hexn_helper_judge_v1.py train on the relabelled files)
Limits: the teacher is a search of the hand score, so the judge can at best learn what that search knows; Connect Four only."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C
COLS, ROWS = C.COLS, C.ROWS
def board_from(f):
    b = [[0] * ROWS for _ in range(COLS)]
    for c in range(COLS):
        for r in range(ROWS):
            i = (c * ROWS + r) * 3; b[c][r] = int(np.argmax(f[i:i + 3]))
    return b
def relabel(src, dst, depth):
    d = np.load(src); F = d["F"]; Y = np.zeros(len(F), dtype=np.float32)
    for i, f in enumerate(F):
        b = board_from(f); n = sum(1 for c in range(COLS) for r in range(ROWS) if b[c][r]); turn = 1 if n % 2 == 0 else 2
        v = C.search(b, 1, turn, depth, -10 ** 9, 10 ** 9); Y[i] = np.tanh(v / 40.0)
    np.savez_compressed(dst, F=F, Y=Y, G=d["G"]); print("wrote", dst, len(Y), "positions; label mean %.3f, share above 0.9: %.2f, below -0.9: %.2f" % (Y.mean(), (Y > 0.9).mean(), (Y < -0.9).mean()))
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "relabel": a = a[1:]
    relabel(a[0], a[1], int(a[2]))
