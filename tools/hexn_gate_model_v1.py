"""Mechanism check of the cell's FEEDBACK AGREEMENT GATE with two real cell models (tools/hexn_cell_v2_model.py MixCell, the Python twin of hexn_cell_v2/v3/v4), no RTL. FINDING: with ONE output lane gated by ALL THREE and feedback coming only from the cell it feeds, the gate DEADLOCKS (case 0 below): feedback exists only after the output was sent, and the output is sent only after feedback agreed. So A has TWO output routes. Cell A takes the input token on lane 0 (receive, direction 0); lane 1 (direction 3: forward out, feedback in) sends UNGATED (code 1: pass when the total reached the threshold) to B and receives B's feedback; lane 2 (direction 1, forward out) is the GATED output, code 0 (ALL THREE: input arrived, total reached threshold, feedback agreed). Cell B receives A's output on lane 0 (direction 2: forward in, feedback out, code 1 = pass when it reached its threshold). Wiring: A.lane1 -> B.lane0 in the forward phase, B.lane0 -> A.lane1 in the feedback phase.
NOTE (found while writing this): the window-start pulse (ph_start) must be given at the start of the FEEDBACK phase too; the burst counter bc restarts only on ph_start and saturates at 7, so without it a cell transmits nothing in the feedback phase (as the bank v15 wiring does now: cph_start is pulsed only at the start of the two forward windows). Here it is pulsed at both phase starts.
Windows = a forward phase of PL clocks then a feedback phase of PL clocks (win_end at the last clock). The token (a burst of LEN clocks, lane 0 high) arrives in the forward phase of every window listed. Prints per window: A's forward total, whether A's gate was open, the clocks A sent, B's total and the clocks B sent feedback.
Usage: python3 tools/hexn_gate_model_v1.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_cell_v2_model as M
N, PL = M.N, M._m.PL
def cfg(lanes):
    act = [0] * N; dr = [0] * N; code = [0] * N
    for i, (d, c) in lanes.items(): act[i] = 1; dr[i] = d; code[i] = c
    return act, dr, code
def run(thrA, thrB, tokens, LEN=5, windows=7, deadlock=False):
    A = M.MixCell(*cfg({0: (0, 0), 1: (3, 0)} if deadlock else {0: (0, 0), 1: (3, 1), 2: (1, 0)}), [thrA], 0); B = M.MixCell(*cfg({0: (2, 1)}), [thrB], 0); rows = []
    for w in range(windows):
        sentA = sentB = gated = 0
        for phase in (0, 1):
            for t in range(PL):
                txA = A.tx(phase); txB = B.tx(phase)
                rxA = [0] * N; rxB = [0] * N
                if phase == 0:
                    rxA[0] = int(tokens[w] and 1 <= t <= LEN)      # burst of LEN clocks (as the glue buffer replays it)
                    rxB[0] = txA[1]; sentA += txA[1]; gated += txA[2]
                else:
                    rxA[1] = txB[0]; sentB += txB[0]
                ps = (t == 0); we = (phase == 1 and t == PL - 1)
                A.clock(rxA, phase, ps, we); B.clock(rxB, phase, ps, we)
        rows.append((w + 1, int(tokens[w]), A.fwd, A.reach_r, A.fbok_r, sentA, gated, B.fwd, B.reach_r, sentB))
    return rows
def show(title, rows):
    print(title); print("window token | A: total reached fb-agreed | A ungated out (clocks) | A GATED out (clocks) | B: total reached | B feedback sent (clocks)")
    for w, tk, fa, ra, fo, sa, ga, fb, rb, sb in rows: print("  %d     %d    |    %3d     %d       %d        |         %2d             |         %2d           |   %3d     %d        |        %2d" % (w, tk, fa, ra, fo, sa, ga, fb, rb, sb))
if __name__ == "__main__":
    show("CASE 0: ONE gated output lane, feedback from the cell it feeds: deadlock, nothing is ever sent", run(3, 2, [1] * 7, deadlock=True))
    show("CASE 1: B's threshold is low (2): B reaches it when A's output arrives, so it sends feedback and A's gate opens", run(3, 2, [1] * 7))
    show("CASE 2: B's threshold is high (40): B never reaches it, no feedback comes, A's gate stays shut although A itself reached its threshold", run(3, 40, [1] * 7))
    show("CASE 3: as case 1, the token stops after window 3", run(3, 2, [1, 1, 1, 0, 0, 0, 0]))
