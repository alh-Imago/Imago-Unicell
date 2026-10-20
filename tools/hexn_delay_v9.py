"""Hex-N delay test v9 (new file; v1-v8 untouched). VM only. Single cell.

Question (Alan, 20 Oct): when the right output depends on an input that arrived EARLIER, is changing the wire settings enough?
Task: a hidden 'teacher' cell is fed the input stream DELAYED by d windows (it sees window t-d's input at window t; nothing before that).
The learner cell is fed the real stream, so to match the teacher it has to carry information about older input forward.
d = 0 is the ordinary task (reachable by the learner exactly). The cell's only memory is what it registers at the end of a window
(reach/margin/any-input/feedback-agrees), i.e. about one window; the accumulators clear every phase.  8 windows per run.
Learner = v6 (LFSR, 4-bit reward, warm start, keep-or-undo with 1-3 changes).  Control = best of the same number of random cells.
Usage: python3 tools/hexn_delay_v9.py --delay D [--first S] [--runs N] [--tries T]"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v3, v6 = load("hexn_mutation_v3"), load("hexn_learner_v6")
v1, PL, N = v3.v1, v3.PL, v3.N
WIN = 8


def shifted(stim, d):
    """the stream the teacher sees: window t gets window t-d's inputs (zeros before that); phase/start flags unchanged"""
    L = 2 * PL; out = []
    for i, (rx, ph, ps, we) in enumerate(stim):
        w, off = divmod(i, L)
        out.append((stim[(w - d) * L + off][0] if w >= d else [0] * N, ph, ps, we))
    return out


def one(seed, d, tries, w, warm, bits, min_goal=20):
    rnd = random.Random(seed); stim = v1.make_stimuli(rnd, windows=WIN)
    for _ in range(500):
        gb = v3.bursts(v1.rand_cfg(rnd), shifted(stim, d))
        if sum(map(sum, gb[0])) + sum(map(sum, gb[1])) >= min_goal: break
    cfg = v6.learn(v6.Teacher(stim, gb, w, bits), v6.Lfsr(seed + 77), tries, warm)
    rr = random.Random(seed + 1); rb = max(v3.score(v1.rand_cfg(rr), stim, gb, w) for _ in range(tries))
    return v3.score(cfg, stim, gb, w), rb


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--delay", type=int, default=0); ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--runs", type=int, default=30); ap.add_argument("--tries", type=int, default=1500); ap.add_argument("--warm", type=int, default=100)
    ap.add_argument("--bits", type=int, default=4); ap.add_argument("--fb", type=float, default=0.5); a = ap.parse_args()
    print(f"delay {a.delay} windows, {WIN} windows per run, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11}")
    for s in range(a.first, a.first + a.runs):
        l, rb = one(s, a.delay, a.tries, a.fb, a.warm, a.bits); print(f"{s:>4} {l:>8} {rb:>11}", flush=True)
