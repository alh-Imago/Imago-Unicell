"""progs.py - register your own programs as job kinds for the job compiler.

    import progs
    progs.register('vmax', 'programs/vmax.s', expect='programs.examples:vmax_ref', out=1)     # expect: Python function(inputs, arg, out_len) -> list of words
    progs.register('mine', 'programs/mine.s', expect='iss', out='same')                       # expect 'iss': the reference interpreter (jobiss.py) gives the answer
    tasks = [jobcomp.Task('vmax', [5, 9, 2]), jobcomp.Task('mine', [...])]

A program is assembly with a `main:` label that follows the job I/O convention (programs/template.s explains it).  out = how many output words the window
reserves: a number, or 'same' (as many as there are inputs).  What register() checks at once, before any board is involved: the file assembles and links as a job, the
code fits the store, a small trial run under the reference interpreter finishes with status 1 (and, if you gave a Python answer, agrees with it).
expect='iss' only compares the board with the interpreter: it proves the board ran the program as RV32I says, not that the program computes what you meant."""
import os, re, importlib, sys
import jobio as J, jobiss
HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN = ('vsum', 'vscale', 'vstress')
_user = {}
class ProgramRegistryError(Exception): pass

def _resolve(expect, base):
    if expect == 'iss' or callable(expect): return expect
    if not isinstance(expect, str) or ':' not in expect: raise ProgramRegistryError("expect must be 'iss', a function, or 'module:function' (got %r)" % (expect,))
    for d in (base, HERE):
        if d and d not in sys.path: sys.path.insert(0, d)
    mod, fn = expect.split(':', 1)
    try: return getattr(importlib.import_module(mod), fn)
    except (ImportError, AttributeError) as e: raise ProgramRegistryError('cannot load the Python answer %r: %s' % (expect, e))

def unregister(name):
    J.KINDS.pop(name, None); _user.pop(name, None)

def register(name, source, expect='iss', out=1, base_dir=None, imem=128, dsh=256, check=True, replace=False):
    """source: path to an assembly file (relative to base_dir), or the assembly text itself"""
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name): raise ProgramRegistryError('program name %r: letters, digits and _ only, starting with a letter' % name)
    if name in BUILTIN or (name in _user and not replace): raise ProgramRegistryError('program name %r is already taken' % name)
    if replace: unregister(name)
    if out != 'same' and not (isinstance(out, int) and out >= 1): raise ProgramRegistryError("out must be a number >= 1 or 'same'")
    if '\n' in source: 
        import tempfile
        d = tempfile.mkdtemp(prefix='scprog_'); path = os.path.join(d, name + '.s'); open(path, 'w').write(source)
    else:
        path = source if os.path.isabs(source) else os.path.join(base_dir or os.getcwd(), source)
        if not os.path.exists(path): raise ProgramRegistryError('program %r: file not found: %s' % (name, path))
    fn = _resolve(expect, base_dir)
    J.KINDS[name] = path
    _user[name] = dict(path=path, expect=fn, out=out)
    try:
        if check: _selfcheck(name, imem, dsh)
    except Exception:
        J.KINDS.pop(name, None); _user.pop(name, None); raise

def _selfcheck(name, imem, dsh):
    n_in = 4
    job = J.Job(0, name, [3, 1, 4, 1][:n_in], default_out_len(name, n_in))
    try: lk = J.build_link([job], shared_words=dsh, code_words=imem)
    except Exception as e: raise ProgramRegistryError('program %r does not assemble / link as a job: %s' % (name, e))
    try: status, n, out, steps = jobiss.reference(lk, job)
    except jobiss.ProgramError as e: raise ProgramRegistryError('program %r failed its trial run under the reference interpreter: %s' % (name, e))
    if status != 1: raise ProgramRegistryError('program %r finished with status %d on a trial run with 4 inputs (1 = ok): it refused or failed' % (name, status))
    f = _user[name]['expect']
    if callable(f):
        want = [w & J.M32 for w in f(list(job.inputs), 0, job.out_len)]
        if want != out: raise ProgramRegistryError('program %r disagrees with its Python answer on a trial run: program gave %s, Python gave %s' % (name, out, want))

def known(name): return name in BUILTIN or name in _user
def kinds(): return list(BUILTIN) + sorted(_user)
def default_out_len(kind, n_in):
    if kind in _user: o = _user[kind]['out']; return n_in if o == 'same' else o
    return n_in if kind == 'vscale' else 1

_ref_link = {}
def expected(kind, inputs, out_len, arg):
    """the answer for one job: built-in kinds from jobio, user kinds from their Python function or the reference interpreter"""
    if kind not in _user: return J.Job(0, kind, inputs, out_len, arg=arg).expected()
    f = _user[kind]['expect']
    if callable(f): return [w & J.M32 for w in f(list(inputs), arg, out_len)]
    job = J.Job(0, kind, inputs, out_len, arg=arg)
    key = (kind, job.window_words)
    if key not in _ref_link: _ref_link[key] = J.build_link([job])
    status, n, out, steps = jobiss.reference(_ref_link[key], job)
    if status != 1: raise jobiss.ProgramError('reference run of %r finished with status %d (not 1)' % (kind, status))
    return out
