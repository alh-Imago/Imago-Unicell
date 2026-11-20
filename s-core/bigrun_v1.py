"""bigrun_v1: write a long test run for the window (ledger #1439) and size it.  HOST ONLY, no board needed.

The 41-job demo runs for 12.6 ms on the card, shorter than one status read of the window (4.8 ms, #1437), so the live cores panel has nothing to show.  This makes a job set
that keeps the card busy for a long time: every job is the made kind `wb_heavy7` (seven `mul arg` steps then a sum: about 700 instructions per data word, against about 7
for a plain sum), 40 words per job, so five jobs fill the 256 shared words of a batch.  The widths of the jobs repeat 0, 0, 1, 2, 0 so the panel shows single slices and fused groups.
Every job has a different arg and different data; every answer is computed here (by the made kind's Python reference) and compared on the card as usual.

  python3 bigrun_v1.py --batches 25 -o window_run_medium_v1.score     (writes the file and prints the size estimate)

The estimate is the host's length model (lengthest_v1: instructions counted on the reference interpreter x clocks per instruction fitted from crc32 runs, with the speed-ups
of the profile) summed over the batches.  It is an ESTIMATE: other kinds were never fitted, and the model has no cost for starting a batch.  The loading time is the rate of the 19 Nov
runs (4,281 words in 1.1 s)."""
import sys, os, io, argparse, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
WIDTHS = [0, 0, 1, 2, 0]; WORDS = 40; PER_BATCH = 5; MULS = 7
def lines(batches, name='wb_heavy7'):
    out = ['make %s %s then sum' % (name, ' '.join(['mul arg'] * MULS))]
    for k in range(batches * PER_BATCH):
        arg = 3 + 2 * (k % 50)                                   # odd args 3..101, different from job to job
        out.append('add %s seq %d %d %d arg=%d lw=%d' % (name, 1 + 7 * k, WORDS, 1 + (k % 4), arg, WIDTHS[k % len(WIDTHS)]))
    return out
def size(text_lines, profile_name='example_2x8_nu3_v2', say=print):
    import score_shell_v1 as S, lengthest_v1 as E, sc_calibrate_v1 as K, jobcomp_v2 as C
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sh = S.Shell()
        for ln in text_lines: sh.execute(ln)
        sh.execute('plan')
        tasks = sh.tasks()
    plan = buf.getvalue()
    bad = [l for l in plan.splitlines() if l.startswith('error') or 'does not fit' in l]
    if bad: raise SystemExit('the shell reports a problem:\n' + '\n'.join(bad[:5]))
    prof = K.load_profile(profile_name); m = E.fit_model(prof, 128, 256).with_units(prof['card'].get('units') or 3)
    tot = 0.0; nb = 0
    for b in C.pack(tasks, 128, 256, 16):
        kinds = [tasks[i].kind for i in b]; widths = [tasks[i].lw for i in b]
        works = [m.work(tasks[i].kind, E.task_steps(tasks[i], 128, 256)) for i in b]
        tot += E.batch_time(m, kinds, works, widths); nb += 1
    import re
    fr = re.search(r'far RAM (0x[0-9a-f]+) to (0x[0-9a-f]+)', plan)
    words = (int(fr.group(2), 16) - int(fr.group(1), 16)) if fr else None
    return dict(jobs=len(tasks), batches=nb, clocks=tot, ms=1000.0 * tot / 50e6, words=words, plan=plan)
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('--batches', type=int, required=True); ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--title', default='')
    a = ap.parse_args(argv)
    ls = lines(a.batches); r = size(ls)
    head = ['# %s' % (a.title or 'Long test run for the window (ledger #1439): %d heavy jobs in %d batches' % (r['jobs'], r['batches'])),
            '# Made by bigrun_v1.py.  Estimate (host model, NOT measured): about %.2f s of card time for the run itself, plus about %.0f s to load %s words (the 19 Nov rate).' % (r['ms'] / 1000.0, (r['words'] or 0) / 3900.0, r['words']),
            '# Open it in the window and watch the cores panel:   nix shell nixpkgs#openocd --command python3 scwin_v2.py -f %s' % os.path.basename(a.out)]
    open(a.out, 'w').write('\n'.join(head + ls + ['plan']) + '\n')
    print('wrote %s: %d jobs, %d batches, far RAM %s words; estimated card time %.2f s (%d clocks); estimated load %.0f s' % (a.out, r['jobs'], r['batches'], r['words'], r['ms'] / 1000.0, r['clocks'], (r['words'] or 0) / 3900.0))
if __name__ == '__main__': main()
