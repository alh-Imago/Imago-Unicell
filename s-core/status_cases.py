"""Shared by test_status_sim.py (simulation) and run_status_board.py (real board): the programs and the checks for the v12 read-out."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import host_sc as hs, sclink

WANT = {2: (1, 2), 3: (2, 250), 4: (3, 0x4004), 5: (4, 0x4000), 6: (0, 0)}      # class -> (trap cause, word address)

def link(spin=1500):
    L = sclink.Linker(shared_words=256, private_words=16, code_words=128)
    L.add_class(1, "main:\n li a0,0\n li t0,%d\nl:\n addi a0,a0,1\n bne a0,t0,l\n ret\n" % spin)
    L.add_class(2, "main:\n li t0,8\n jalr zero,t0,0\n ret\n")                         # jump to byte 8 = word 2, inside class 1's code: outside this class's window
    L.add_class(3, "main:\n li t0,1000\n sw t0,0(t0)\n li a0,1\n ret\n")                # private word 250, limit 16
    L.add_class(4, "main:\n li t0,0x10000\n sw t0,16(t0)\n li a0,1\n ret\n", data_words=4)   # shared word 4 of a 4-word window
    L.add_class(5, "main:\n li t0,0x10000\n lw a0,0(t0)\n ret\n")                        # shared access, class has no window
    L.add_class(6, "main:\n li a0,7\n ret\n")
    return L.link()

def evaluate(res, S, n_crit, spin, out=print):
    """res: tag -> decoded reply.  Tags: T_hold T_run U_run T_idle U_end C_end Q<t> and E<c> / P2Q<c> for the classes in WANT."""
    bad = []
    def chk(c, m):
        if not c: bad.append(m)
    short = lambda t: {k: t[k] for k in t if k != 'slices'}
    h = res['T_hold']; chk(h['hold'] and h['waiting_critical'] == n_crit and h['waiting_bulk'] == 3 and h['running'] == 0, 'on hold: %s' % short(h))
    r = res['T_run']
    chk(r['running'] == S and r['allocated'] == S, 'running: %s' % short(r))
    chk(r['waiting_critical'] == 2 and r['waiting_bulk'] == 3, 'queues while running: crit %d bulk %d, expected 2 and 3' % (r['waiting_critical'], r['waiting_bulk']))
    chk(sorted(x['tid'] for x in r['slices'] if x['leader']) == list(range(S)), 'tids on the slices: %s' % [x['tid'] for x in r['slices']])
    chk(all(x['cls'] == 1 for x in r['slices'] if x['leader']), 'class on the slices')
    chk(all(b > 0 for b in res['U_run']['busy']), 'every slice must show usage while running: %s' % res['U_run']['busy'])
    i = res['T_idle']; chk(i['running'] == 0 and i['allocated'] == 0 and i['waiting_critical'] == 0 and i['waiting_bulk'] == 0 and not i['hold'], 'idle: %s' % short(i))
    ue, ce = res['U_end'], res['C_end']
    chk(sum(ue['busy']) == ce['busy_slice_cycles'], 'sum of per-slice usage %d != board busy counter %d' % (sum(ue['busy']), ce['busy_slice_cycles']))
    chk(all(b >= a for a, b in zip(res['U_run']['busy'], ue['busy'])), 'usage went backwards')
    for t in range(n_crit + 3): chk(res['Q%d' % t]['state'] == 3 and res['Q%d' % t]['a0'] == spin, 'phase 1 job %d' % t)
    for c, (cause, addr) in WANT.items():
        e, q = res['E%d' % c], res['P2Q%d' % c]
        chk(q['state'] == 3 and bool(q['trap']) == (cause != 0), 'class %d: state %d trap %d' % (c, q['state'], q['trap']))
        chk(e['cause'] == cause, 'class %d: cause %d, expected %d' % (c, e['cause'], cause))
        if cause: chk(e['addr'] == addr, 'class %d: addr 0x%x, expected 0x%x' % (c, e['addr'], addr))
        out('class %d: cause %d (%s) addr 0x%x' % (c, e['cause'], e['why'], e['addr']))
    out('T on hold:', short(h)); out('T running:', short(r), [(x['cls'], x['tid']) for x in r['slices']])
    out('usage while running:', res['U_run']['busy'], ' at end:', ue['busy'], ' sum', sum(ue['busy']), 'board busy', ce['busy_slice_cycles'])
    out('RESULT', 'PASS' if not bad else 'FAIL'); [out('  ' + m) for m in bad]
    return not bad
