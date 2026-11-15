"""Violation test for every slice, with simultaneous traps (v10 / v11 designs).

The plan is a list of operations that two executors run: the whole-board simulation (test_violations_sim.py) and the real board
(run_violations_board.py).  Each ROUND resets the array, sets the regions/windows, then submits S tasks together so that every slice
runs one at the same time (a busy loop first keeps every task alive until all slices have started; the report shows how many different
slices were used).  Rounds:
   1..6  one violation kind on all S slices at once: wild private store, wild private load, shared store past the window, shared load
         past the window, a class with no window, a jump out of the code region.  All tasks must end with the trap flag.
   mixed trapping and good tasks side by side: good tasks must give the right answer and trappers must trap;
   all   all six kinds at once across the slices (several different violations in the same clocks);
   after the private memory of every slice is checked for the wild store (word 20 must still be 0), a good program runs on every slice,
         and the host checks the guard words next to the shared windows are untouched.
Designed for a board with the shared RAM (version >= 7)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import runtests as rt

BUSY = "li t0,150\nbusy:\naddi t0,t0,-1\nbnez t0,busy\n"
PROGS = {   # class -> (name, source)
 0: ('good sum30',          BUSY + "li a0,0\nli t1,30\nsl:\nadd a0,a0,t1\naddi t1,t1,-1\nbnez t1,sl\nebreak"),
 1: ('wild private store',  BUSY + "li t0,80\nli t1,21845\nsw t1,0(t0)\nebreak"),
 2: ('wild private load',   BUSY + "li t0,80\nlw a0,0(t0)\nebreak"),
 3: ('shared store past end', BUSY + "lui t0,16\nli t1,43690\nsw t1,16(t0)\nebreak"),
 4: ('shared load past end',  BUSY + "lui t0,16\nlw a0,16(t0)\nebreak"),
 5: ('shared, no window',   BUSY + "lui t0,16\nlw a0,0(t0)\nebreak"),
 6: ('jump out of region',  BUSY + "li a0,1\nli t0,0\njalr zero,t0,0\nebreak"),   # absolute byte address 0 = the first program (class 0), outside this class's code window (a plain `j 0` is relative to the program and would only restart it)
 7: ('private word 20 check', BUSY + "lw a0,80(zero)\nebreak"),
}
KINDS = [1, 2, 3, 4, 5, 6]
GUARD = {0: 0x11110000, 1: 0x11110001, 2: 0x11110002, 3: 0x11110003, 4: 0x5555AAAA, 5: 0x5555AAAB, 6: 0x5555AAAC, 7: 0x5555AAAD}

def layout():
    words, base = [], {}
    for c, (name, src) in PROGS.items():
        w = rt.assemble(src); base[c] = (len(words), len(w)); words += w
    return words, base

def plan(S):
    """-> ops list.  ops: ('send', bytes) | ('wait_done', n) | ('wait_clocks', n) | ('read', 'Q', tid, tag) | ('read', 'L', addr, tag) | ('round', title)
    expectations: dict tag -> ('task', trap, a0 or None) | ('word', value) ; coverage: dict round-title -> tag list of Q reads"""
    import host_sc as hs
    words, base = layout()
    ops, exp, cover = [], {}, {}
    send = lambda b: ops.append(('send', b))
    loaded = []
    def setup():
        send(hs.cmd_R()); ops.append(('wait_clocks', 3000))
        if not loaded:                              # the code store survives a reset: load it once
            loaded.append(1)
            for i, w in enumerate(words): send(hs.cmd_W(i, w))
        for c in range(1, 7):                       # exact code region per class; private limit 4 words
            send(hs.cmd_B(c, base[c][0], base[c][1], 4))
        send(hs.cmd_B(0, base[0][0], base[0][1], 32)); send(hs.cmd_B(7, base[7][0], base[7][1], 32))
        send(hs.cmd_X(3, 0, 4)); send(hs.cmd_X(4, 0, 4))      # classes 3 and 4 may use shared words 0..3; class 5 has no window
        for a, v in GUARD.items(): send(hs.cmd_M(a, v))
    def round_(title, kinds):
        ops.append(('round', title)); setup()
        send(hs.cmd_H())
        for t, c in enumerate(kinds): send(hs.cmd_P(t, base[c][0], 0, 0, c))
        send(hs.cmd_G()); ops.append(('wait_done', len(kinds)))
        tags = []
        for t, c in enumerate(kinds):
            tag = '%s/t%d' % (title, t); tags.append(tag)
            ops.append(('read', 'Q', t, tag))
            exp[tag] = ('task', c not in (0, 7), {0: 465, 7: 0}.get(c), c)
        cover[title] = tags
        for a, v in GUARD.items():
            tag = '%s/guard%d' % (title, a); ops.append(('read', 'L', a, tag)); exp[tag] = ('word', v)
    for k in KINDS: round_('kind %d: %s' % (k, PROGS[k][0]), [k] * S)
    h = max(1, S // 2)
    round_('mixed: %d trapping + %d good' % (h, S - h), [1] * h + [0] * (S - h))
    round_('all six kinds at once', [KINDS[i % 6] for i in range(S)])
    round_('private word 20 check on every slice', [7] * S)
    round_('good program on every slice', [0] * S)
    return ops, exp, cover


def evaluate(results, exp, cover, S, out=print):
    """results: dict tag -> decoded reply (Q dict or L int).  Returns True if everything is as expected."""
    bad = 0
    for title, tags in cover.items():
        slots = set(); fails = []
        for tag in tags:
            r = results[tag]; _, trap, a0, c = exp[tag]
            ok = r['state'] == 3 and bool(r['trap']) == trap and (a0 is None or r['a0'] == a0)
            slots.add(r['slot'])
            if not ok: fails.append('%s: state %d trap %d a0 %d, expected trap %d%s' % (tag.rsplit('/', 1)[1], r['state'], r['trap'], r['a0'], trap, '' if a0 is None else ' a0 %d' % a0))
        gfail = [t for t in results if t.startswith(title + '/guard') and results[t] != exp[t][1]]
        out('%-44s tasks %2d  slices used %2d of %d  %s' % (title, len(tags), len(slots), S, 'ok' if not fails and not gfail else 'FAIL'))
        for f in fails: out('     ' + f)
        for t in gfail: out('     %s = %08x, expected %08x' % (t, results[t], exp[t][1]))
        bad += bool(fails) + bool(gfail)
        if len(tags) >= S and len(slots) < S: out('     note: only %d different slices ran this round' % len(slots)); bad += 1
    out('RESULT', 'PASS' if not bad else 'FAIL')
    return not bad
