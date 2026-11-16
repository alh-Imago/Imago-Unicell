"""board_diag.py - when a job does not finish, say what the scheduler is doing (used by the board runners)."""
import host_sc as hs

def diagnose(b, tid, out=print):
    try:
        S = b.slices(); t = b.status(); c = b.counters(); q = b.task(tid)
    except Exception as e:
        out('  (could not read the board status: %s)' % e); return
    out('  --- board status when task %d did not finish ---' % tid)
    out('  hold flag: %s   waiting critical %d, waiting bulk %d, slices allocated %d, tasks running %d' % (t['hold'], t['waiting_critical'], t['waiting_bulk'], t['allocated'], t['running']))
    out('  task %d: state %d (0 empty, 1 waiting, 2 running, 3 done), trap %s, start %d, end %d, slot %d' % (tid, q['state'], q['trap'], q['start'], q['end'], q.get('slot', -1)))
    out('  counters: cycles %d, tasks done %d, launch errors %d, dispatches %d' % (c['cyc'], c['done'], c['launch_err'], c['dispatches']))
    if t['hold']: out('  -> the scheduler is ON HOLD (an earlier session left it so): send G, or rerun the runner (it now sends G).')
    elif q['state'] == 1: out('  -> the task is queued but never started.')
    elif q['state'] == 2: out('  -> the task started and has not ended: the program is probably not what was expected (wrong or damaged code in the store).')
    elif q['state'] == 0: out('  -> the board has no such task: the submit command did not arrive, or the board was reset after it.')
    try:
        e = b.trap_info(tid); out('  trap cause for this task: %s at %#x' % (e['why'], e['addr']))
    except Exception: pass
