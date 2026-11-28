"""jobio_ext_v2.py (ledger #1598, cloned from jobio_ext_v1.py which stays as it is): install(level, narrow=False): level = the multiply LEVEL (0 none, 1 low half, 2 + high half lib_mulhu32, 3 + byte stores sb/sh); narrow = byte/half loads exist.  Header word 7 = the level.  lib_mulhu32 (software or unit version by level >= 2) is linked ONLY when a job source mentions it.  The assembler extension asm_ext_v1 is installed with it.  Original text of v1:
jobio_ext_v1.py - adds the multiply library (jobio/lib_mul.s: lib_mul32) and the multiply-unit count (job header word 7) to jobio WITHOUT editing jobio.py (ledger #1582).
`install(mul_units)` replaces jobio.build_link and jobio.prepare with these versions (every other file calls them as J.build_link / J.prepare, so they all see the new ones);
`uninstall()` puts the originals back.  The header word 7 (jobio.F_SPARE, 0 in the original) is set to the number of multiply units of the build that is loaded (0 = none:
lib_mul32 then multiplies by shift and add).  With units > 0 the unit version of lib_mul32 (jobio/lib_mul_unit.s) is linked and the interpreter models the unit (jobiss_v2.py); with 0 the software version is linked.
Nothing here talks to hardware (ledger #1582, #1584)."""
import os
import jobio as J, sclink, jobiss, jobiss_v3 as jobiss_v2, asm_ext_v1
HERE = os.path.dirname(os.path.abspath(__file__))
_orig = {}
state = {'units': 0}

def build_link_mul(jobs, shared_words=256, private_words=16, code_words=128):
    """jobio.build_link with the multiply library added after lib_io.s (same arguments, same result otherwise)"""
    L = sclink.Linker(shared_words=shared_words, private_words=private_words, code_words=code_words)
    L.library(open(os.path.join(HERE, 'jobio', 'lib_io.s')).read())
    L.library(open(os.path.join(HERE, 'jobio', 'lib_mul_unit.s' if state['units'] > 0 else 'lib_mul.s')).read())     # ledger #1584: the unit version when the build has multiply units
    if any('lib_mulhu32' in open(os.path.join(HERE, J.KINDS[j.kind])).read() for j in jobs if j.clone_of is None):
        L.library(open(os.path.join(HERE, 'jobio', 'lib_mulhu_unit.s' if state['units'] >= 2 else 'lib_mulhu.s')).read())
    by = {j.cid: j for j in jobs}
    for j in jobs:
        if j.clone_of is None: L.add_class(j.cid, open(os.path.join(HERE, J.KINDS[j.kind])).read(), data_words=j.window_words)
    for j in jobs:
        if j.clone_of is not None:
            if by[j.clone_of].window_words != j.window_words or by[j.clone_of].kind != j.kind: raise ValueError('a clone needs the same program and window size as class %d' % j.clone_of)
            L.clone_class(j.cid, j.clone_of)
    return L.link()

def prepare_mul(link, job):
    m = _orig['prepare'](link, job)
    m[J.window_base(link, job) + J.F_SPARE] = state['units'] & J.M32
    return m

def install(mul_units=0, narrow=False):
    """use the multiply library and write `mul_units` into header word 7 of every job; safe to call again (it only changes the unit count)"""
    state['units'] = int(mul_units); jobiss_v2.UNITS[0] = state['units']; jobiss_v2.NARROW[0] = bool(narrow)
    asm_ext_v1.install(state['units'], narrow)
    if _orig: return
    _orig['build_link'], _orig['prepare'], _orig['run_class'] = J.build_link, J.prepare, jobiss.run_class
    jobiss.run_class = jobiss_v2.run_class      # the interpreter that models the unit
    J.build_link, J.prepare = build_link_mul, prepare_mul

def uninstall():
    if not _orig: return
    J.build_link, J.prepare, jobiss.run_class = _orig.pop('build_link'), _orig.pop('prepare'), _orig.pop('run_class')
    _orig.clear(); state['units'] = 0; jobiss_v2.UNITS[0] = 0; jobiss_v2.NARROW[0] = False; asm_ext_v1.uninstall()

def installed(): return bool(_orig)
