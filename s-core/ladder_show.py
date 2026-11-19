"""ladder_show.py - show what a job file should give, and compare it with a result file from the card.
   python3 ladder_show.py JOBS.json                 what the answers should be (computed on this computer, no card)
   python3 ladder_show.py JOBS.json RESULT.json     compare the card's results (made with scblocks.py ... --out RESULT.json) with the answers"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch
def main(argv):
    if not argv: print(__doc__); return 2
    tasks = scbatch.load_jobs(argv[0]); got = None
    if len(argv) > 1: got = {r['job']: r['result'] for r in json.load(open(argv[1]))}
    bad = 0
    for i, t in enumerate(tasks):
        want = t.expected(); ins = t.inputs
        shown = ('%s' % ins) if len(ins) <= 8 else ('%s ... %s (%d words)' % (ins[:4], ins[-2:], len(ins)))
        w = ('%s' % want) if len(want) <= 8 else ('%s ... (%d words)' % (want[:6], len(want)))
        line = 'job %d  %-8s inputs %s%s  ->  should be %s' % (i, t.kind, shown, ('  arg %d' % t.arg) if t.arg else '', w)
        if got is not None:
            ok = got.get(i) == want; bad += (not ok)
            line += '   card: %s   %s' % (('%s' % got.get(i)) if len(want) <= 8 else '(%d words)' % len(got.get(i, [])), 'MATCH' if ok else 'DIFFERENT')
        print(line)
    if got is not None: print('%d of %d jobs match' % (len(tasks) - bad, len(tasks)))
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
