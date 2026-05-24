"""
test_workspace_pond.py — Tests WorkspacePond PondManager-backed API.

Verifies:
1. Legacy path still works (no PondManager)
2. launch_program creates a connected program pond
3. run_program routes inputs and captures outputs
4. Multiple programs on one workspace simultaneously
5. disconnect_program cleans up correctly
6. status() reports active programs and PTT state
7. Bridge registry wired in UniCellArray after connect
"""

import os, sys, json
os.chdir(os.path.dirname(os.path.realpath(os.path.abspath('test_workspace_pond.py')))
         if os.path.exists('composer/examples') else os.getcwd())
# Ensure we are in repo root
if not os.path.exists('composer/examples/not_gate.icm'):
    # Try to find the repo root
    for p in ['.', '..', '/home/claude/Imago-Unicell']:
        if os.path.exists(os.path.join(p, 'composer/examples/not_gate.icm')):
            os.chdir(p)
            break
os.environ['IMAGO_VERBOSE'] = '0'

from controller import ImagoController
from unicell_array import UniCellArray
from pond import PondManager
from workspace import WorkspacePond

results = []

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    suffix = f" — {detail}" if detail and not condition else ""
    print(f"  [{status}] {label}{suffix}")

def load_icm(name):
    with open(f'composer/examples/{name}.icm') as f:
        return json.load(f)


print("\n── legacy path ──")
ctrl = ImagoController(cell_count=512)
ws_leg = WorkspacePond(ctrl, name='legacy')
r = ws_leg.load_icm('composer/examples/not_gate.icm')
check("Legacy load_icm works", r['ok'])
ws_leg.set('a', 0)
r = ws_leg.run()
check("Legacy run: not(0)=1", r['ok'] and r['outputs'].get('result') == 0xFFFFFFFF)
ws_leg.set('a', 1)
r = ws_leg.run()
check("Legacy run: not(1)=0", r['ok'] and r['outputs'].get('result') == 0xFFFFFFFE)
st = ws_leg.status()
check("Legacy status no active_programs", st['active_programs'] == {})
check("Legacy status pond_manager=False", not st['pond_manager'])


print("\n── PondManager path ──")
array = UniCellArray(cell_count=8192)
mgr   = PondManager(array)
ctrl2 = ImagoController(cell_count=8192)
ws    = WorkspacePond(ctrl2, name='ws', pond_manager=mgr, owner_id='alice')
check("Workspace pond created", ws._ws_pond is not None)
check("Workspace pond is PRIVATE", ws._ws_pond.security_level == 'PRIVATE')

icm_ng = load_icm('not_gate')
h = ws.launch_program(icm_ng)
check("launch_program returns ok", h.get('ok'), str(h.get('error', '')))
check("handle_id assigned",    h.get('handle_id') == 'prog_0001')
check("program_name correct",  h.get('program_name') == 'not_gate')

r0 = ws.run_program('prog_0001', a=0)
check("run_program not_gate(0)=1",
      r0.get('ok') and r0.get('outputs', {}).get('result') == 0xFFFFFFFF, str(r0))
r1 = ws.run_program('prog_0001', a=1)
check("run_program not_gate(1)=0",
      r1.get('ok') and r1.get('outputs', {}).get('result') == 0xFFFFFFFE, str(r1))


print("\n── multiple programs ──")
icm_mux = load_icm('mux')
h2 = ws.launch_program(icm_mux)
check("launch_program mux", h2.get('ok'))
check("second handle_id",   h2.get('handle_id') == 'prog_0002')
check("two active programs", len(ws._active_programs) == 2)
r_ng = ws.run_program('prog_0001', a=0)
check("both programs independently runnable", r_ng.get('ok'))


print("\n── status with active programs ──")
st = ws.status()
check("status pond_manager=True", st['pond_manager'])
check("status shows 2 active programs", len(st['active_programs']) == 2)
ng_st = st['active_programs']['prog_0001']
check("prog_0001 shows in status", ng_st['program'] == 'not_gate')
check("prog_0001 has PTT entries", len(ng_st['ptt']) >= 1)
ptt_vals = list(ng_st['ptt'].values())
check("PTT entry WAITING or IDLE", any(v in ('WAITING', 'IDLE') for v in ptt_vals))


print("\n── bridge registry ──")
check("array has bridge registry", hasattr(array, '_bridge_registry'))
check("bridge registry has entries after connect",
      len(array._bridge_registry) > 0,
      f"keys: {list(array._bridge_registry.keys())}")


print("\n── disconnect ──")
r_disc = ws.disconnect_program('prog_0001')
check("disconnect returns ok", r_disc.get('ok'))
check("prog_0001 removed from active_programs",
      'prog_0001' not in ws._active_programs)
check("prog_0002 still active", 'prog_0002' in ws._active_programs)
r_bad = ws.disconnect_program('prog_0001')
check("unknown handle returns error", not r_bad.get('ok'))


print()
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  [FAIL] {n}")
