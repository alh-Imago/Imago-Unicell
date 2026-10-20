"""Hex-N ladder driver (new file): runs the steps of the one-change-at-a-time ladder in order, 25 seeds each (5 processes x 5 seeds), compares each with the best so far using
hexn_ladder_compare_v1.py (accept rule fixed in advance), keeps a change only if it is REAL, and writes a summary.  Usage: python3 tools/hexn_ladder_run_v1.py OUTDIR BASEFILE [--M m] [--steps fbpush,score,aim,decay,fweights]
BASEFILE = a file with the 25 per-seed lines of the current best arm.  Each arm's files are kept in OUTDIR/<name>_<first>.txt."""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, basefile = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
baseM = int(sys.argv[sys.argv.index("--M") + 1]) if "--M" in sys.argv else 2
steps = (sys.argv[sys.argv.index("--steps") + 1] if "--steps" in sys.argv else "fbpush,score,aim,decay,fweights").split(",")
accepted = []; best = basefile; log = open(os.path.join(out, "summary.txt"), "a")
def say(s): print(s, flush=True); log.write(s + "\n"); log.flush()
say(f"ladder start: base file {basefile}, M {baseM}, steps {steps}")
for st in steps:
    flags = accepted + [st]; name = "+".join(flags); procs = []
    for first in (0, 5, 10, 15, 20):
        cmd = [sys.executable, os.path.join(ROOT, "tools", "hexn_cluster_v19.py"), "--M", str(baseM), "--run", "3", "--first", str(first), "--runs", "5"] + ["--" + f for f in flags]
        procs.append(subprocess.Popen(cmd, stdout=open(os.path.join(out, f"{name}_{first}.txt"), "w"), stderr=subprocess.STDOUT))
    for p in procs: p.wait()
    files = [os.path.join(out, f"{name}_{f}.txt") for f in (0, 5, 10, 15, 20)]
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_ladder_compare_v1.py"), best, "--"] + files, capture_output=True, text=True).stdout
    say(f"STEP {st} (flags: {flags}) vs best so far:\n{r.strip()}")
    if "REAL" in r and "no difference" not in r:
        accepted.append(st)
        merged = os.path.join(out, f"best_after_{st}.txt")
        with open(merged, "w") as m:
            for f in files: m.write(open(f).read())
        best = merged
say(f"ladder end: accepted {accepted}")
