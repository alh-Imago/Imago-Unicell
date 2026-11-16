"""batch_demo.py - a two-phase batch used by test_batch_sim.py and run_batch_board.py.
Phase 1 runs a vsum and a vscale job; phase 2 REPLACES the code store with different programs (a vstress and a vscale with other class numbers, window
sizes and addresses) and runs two more jobs.  Everything the card needs sits in far RAM: two scripts, two code images, four window images (header + inputs
+ zeroed output area).  The results of all four jobs are gathered into one block."""
import jobio as J, batch as B

SCRIPT1, SCRIPT2, IMAGES, RESULTS = 0x2000, 0x2100, 0x2200, 0x3000
COPY_WINDOW = (0x2200, 0x1000)               # far words the copy engine may touch: images and results (the scripts are read directly)
TAG = 0x600D

def phase(sc, lay, link, jobs, tids, res):
    assert not link.shared_preload, 'shared-RAM preload is not carried by a batch (jobs bring their data in window images)'
    """append one phase to script sc.  res = next free word of the results block.  -> new res"""
    if link.lib[1]: sc.library(*link.lib)
    for cid, k in sorted(link.classes.items()):
        sc.region(cid, k['cbase'], k['clen'], k['dlen'])
        if k['win'] and k['win'][1]: sc.window(cid, *k['win'])
    sc.load_code(0, lay.put(link.words), len(link.words))
    for j in jobs:
        base = J.window_base(link, j); img = [0] * j.window_words
        for a, v in J.prepare(link, j).items(): img[a - base] = v
        sc.load_data(base, lay.put(img), j.window_words)
    for tid, j in zip(tids, jobs): sc.submit(tid, link.classes[j.cid]['entry'], j.cid)
    sc.wait(300)
    for j in jobs:
        n = len(j.expected()); sc.save(J.window_base(link, j) + j.out_off, res, n); res += n
    return res

def build():
    A = J.Job(0, 'vsum', [3 * i + 1 for i in range(12)], 1)
    Bj = J.Job(1, 'vscale', [100 + 7 * i for i in range(10)], 10)
    E = J.Job(0, 'vstress', [4, 5, 6, 7, 8, 9], 1, arg=9)
    F = J.Job(1, 'vscale', [0xFFFFFFF0 + i for i in range(8)], 8)
    link1, link2 = J.build_link([A, Bj]), J.build_link([E, F])
    lay = B.Layout(IMAGES)
    s1, s2 = B.Script(), B.Script()
    res = phase(s1, lay, link1, [A, Bj], [0, 1], RESULTS)
    s1.jump(SCRIPT2)
    res = phase(s2, lay, link2, [E, F], [2, 3], res)
    s2.end(TAG)
    lay.put(s1.words(), at=SCRIPT1); lay.put(s2.words(), at=SCRIPT2)
    assert len(s1) <= SCRIPT2 - SCRIPT1 and SCRIPT2 + len(s2) <= IMAGES and lay.next <= RESULTS and res - RESULTS < 0x200
    expected = A.expected() + Bj.expected() + E.expected() + F.expected()
    return dict(layout=lay, entry=SCRIPT1, results=RESULTS, expected=expected, scripts=(s1, s2), links=(link1, link2), jobs=(A, Bj, E, F))

if __name__ == '__main__':
    d = build()
    print('far RAM image: %d words in %d places; scripts %d + %d steps; code %d and %d words' % (len(d['layout'].image), 1, len(d['scripts'][0].steps), len(d['scripts'][1].steps), len(d['links'][0].words), len(d['links'][1].words)))
    print('expected results (%d words):' % len(d['expected']), ' '.join('%x' % x for x in d['expected']))
    for sc in d['scripts']:
        for st in sc.steps: print('  ', B.decode(st))
