#!/usr/bin/env python3
"""score_store_v1.py - the build store of the S-Core front end (ledger #1534): finds the builds in a folder (manifests, bitstreams, timing reports),
says what fits on which board, checks timing before a load, loads a bitstream and checks that the loaded design is the one that was asked for.
Used by score_shell_v2.py (commands store, builds, target, fit, use, load); everything here works without a card (the card steps take the
functions that talk to it as arguments, so the tests use fakes).
Rules kept here: SRAM load only (the loader is never given a flash option); a build whose timing failed is never loaded; a build whose timing is not known
is loaded only when the user says `confirm`."""
import os, re, json, glob, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_manifest_v2 as M

NIX_LOADER = '/nix/store/77r1cv86zjls4xix4kijr1sv9vn9a5yq-openfpgaloader-1.1.1/bin/openFPGALoader'
NAME_RE = re.compile(r'^h([a-z])(\d+)s(\d+)u(\d+)n(\d+)(?:i(\d+))?$')

# ---------------------------------------------------------------- config (one small file in the user's home)
def config_path(): return os.environ.get('SCORE_SHELL_CONFIG') or os.path.join(os.path.expanduser('~'), '.score_shell.json')
def load_config():
    try: return json.load(open(config_path()))
    except (OSError, ValueError): return {}
def save_config(cfg): json.dump(cfg, open(config_path(), 'w'), indent=1)

def search_dirs(store=None):
    """the folders searched for builds: the user's store, then the k7 folder of this checkout"""
    d = []
    if store: d.append(os.path.abspath(os.path.expanduser(store)))
    k7 = os.path.join(HERE, 'k7')
    if os.path.isdir(k7) and k7 not in d: d.append(k7)
    return d

# ---------------------------------------------------------------- timing
def parse_timing(path):
    """Vivado timing_summary.txt -> {'setup': WNS, 'hold': WHS, 'fail': failing endpoints} or None"""
    try: lines = open(path, errors='replace').read().split('\n')
    except OSError: return None
    for i, ln in enumerate(lines):
        if 'WNS(ns)' in ln:
            for nxt in lines[i + 1:i + 6]:
                tok = nxt.split()
                if len(tok) >= 8:
                    try: v = [float(x) for x in tok[:8]]
                    except ValueError: continue
                    return {'setup': v[0], 'hold': v[4], 'fail': int(v[2]) + int(v[6])}
    return None

# ---------------------------------------------------------------- the builds
def _bit_for(name, dirs):
    for d in dirs:
        for p in (os.path.join(d, 'vivado_out_%s' % name, '%s.bit' % name), os.path.join(d, name, '%s.bit' % name), os.path.join(d, '%s.bit' % name)):
            if os.path.isfile(p): return p
    return None

def _timing_for(name, dirs, measured):
    for d in dirs:
        for p in (os.path.join(d, 'vivado_out_%s' % name, 'timing_summary.txt'), os.path.join(d, name, 'timing_summary.txt')):
            t = parse_timing(p)
            if t: t['source'] = 'timing_summary.txt'; return t
    m = measured.get(name)
    if m and 'setup_ns' in m: return {'setup': m['setup_ns'], 'hold': m['hold_ns'], 'fail': 0, 'source': 'builds_measured_v1.json'}
    return None

def fit_for(nb, s, ulw, nu, imem, luts=None, targets=None):
    """-> {board: {'fit', 'lut_fraction', 'why'}} (a measured LUT count replaces the model)"""
    m = M.manifest(nb, s, ulw, nu, imem, targets)
    out = m['targets']
    if luts:
        tg = targets or json.load(open(os.path.join(HERE, 'targets_v1.json')))
        for k, r in out.items():
            t = tg[k]
            if not t.get('s_core_builds_measured'): continue
            f = luts / t['luts']; r['lut_fraction'] = [round(f, 3), round(f, 3)]
            r['fit'] = 'recommended' if f <= t['target_fraction'] else ('tight' if f <= 1.0 else 'no'); r['why'] = 'measured %d LUTs' % luts
    return out, m

def find_builds(store=None):
    """all builds known in the search folders: manifests, plus the names in builds_measured_v1.json -> list of dicts, sorted by name"""
    dirs = search_dirs(store)
    try: measured = {k: v for k, v in json.load(open(os.path.join(HERE, 'builds_measured_v1.json'))).items() if not k.startswith('_')}
    except (OSError, ValueError): measured = {}
    found = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, 'sc_k7_*.manifest.json'))):
            try: m = json.load(open(f))
            except ValueError: continue
            found.setdefault(m['build'], {'manifest': m, 'manifest_file': f})
    for name in measured:
        if name in found: continue
        g = NAME_RE.match(name)
        if g:
            nb, s, w, nu = int(g.group(2)), int(g.group(3)), int(g.group(4)), int(g.group(5)); imem = int(g.group(6) or 128)
            ulw = 0 if w == 1 else w.bit_length() - 1
            found[name] = {'manifest': {'build': name, 'line': 'h' + g.group(1), 'blocks': nb, 'slices_per_block': s, 'unit_lanes': 0 if ulw == 0 else w,
                                        'units_per_block': 0 if ulw == 0 else nu, 'unit_lw': ulw, 'imem_words': imem}, 'manifest_file': None}
    out = []
    for name, r in found.items():
        m = r['manifest']; mm = measured.get(name)
        luts = mm['luts'] if mm else None
        fits, _ = fit_for(m['blocks'], m['slices_per_block'], m['unit_lw'], max(m['units_per_block'], 1), m['imem_words'], luts)
        low = m.get('predicted_luts', {}).get('low') if 'predicted_luts' in m else None
        out.append({'name': name, 'line': m.get('line', ''), 'blocks': m['blocks'], 'slices': m['slices_per_block'], 'lanes': m['unit_lanes'],
                    'units': m['units_per_block'], 'unit_lw': m['unit_lw'], 'imem': m['imem_words'], 'luts': luts, 'predicted': low,
                    'timing': _timing_for(name, dirs, measured), 'bit': _bit_for(name, dirs), 'card': (mm or {}).get('card'),
                    'fits': fits, 'manifest_file': r['manifest_file']})
    return sorted(out, key=lambda b: b['name'])

def get_build(store, name):
    for b in find_builds(store):
        if b['name'] == name: return b
    near = [b['name'] for b in find_builds(store) if name in b['name']][:5]
    raise KeyError('no build %r%s' % (name, ('; similar: ' + ', '.join(near)) if near else ''))

def timing_verdict(b):
    """-> (ok: True / False / None, text)"""
    t = b['timing']
    if t is None: return None, 'timing not known (no timing_summary.txt and no measured figures)'
    ok = t['setup'] > 0 and t['hold'] > 0 and t.get('fail', 0) == 0
    return ok, 'setup %+.3f ns, hold %+.3f ns, failing endpoints %d (%s)' % (t['setup'], t['hold'], t.get('fail', 0), t['source'])

# ---------------------------------------------------------------- loading and checking
def find_loader(cfg=None):
    cfg = cfg or {}
    # order: the user's own setting, the nix build proven on this card (knows the XC7K480T chip id), then whatever is on PATH (#1535)
    for c in (cfg.get('loader'), NIX_LOADER, shutil.which('openFPGALoader')):
        if c and os.path.isfile(c): return c
    return None

def load_bitstream(b, confirm=False, loader=None, runner=subprocess.run):
    """load build b into the card's SRAM. -> (ok, message). Never loads a failed or missing build."""
    if not b['bit']: return False, 'no bitstream found for %s (looked for vivado_out_%s/%s.bit in %s)' % (b['name'], b['name'], b['name'], ', '.join(search_dirs(None)))
    ok, text = timing_verdict(b)
    if ok is False: return False, 'refused: timing failed for %s: %s' % (b['name'], text)
    if ok is None and not confirm: return False, 'timing for %s is not known; add the word confirm to load it anyway (load %s confirm)' % (b['name'], b['name'])
    if not loader: return False, 'no openFPGALoader found (set it with: set loader PATH)'
    r = runner([loader, '-c', 'ft232', b['bit']], capture_output=True, text=True)
    out = (r.stdout or '') + (r.stderr or '')
    if r.returncode == 0 and re.search(r'\bdone\s+1\b', out): return True, 'loaded %s (%s)' % (b['name'], text)
    tail = '\n'.join(out.strip().split('\n')[-4:])
    hint = ''
    if 'Unknown device with IDCODE' in out: hint = ' This loader does not know the chip: set loader to the nix one (set loader %s).' % NIX_LOADER
    elif 'bulk write failed' in out or 'usb' in out.lower(): hint = ' If it says "usb bulk write failed", reconnect the adapter and try again.'
    return False, 'the load did not finish (exit %s, loader %s).%s\n%s' % (r.returncode, loader, hint, tail)

BOARD_RE = re.compile(r"board version (\{.*?\})")
def parse_first_read(text):
    """output of shared_ram_first_v1.py -> {'healthy': bool, 'S': n, 'imem_words': n} (missing keys when not printed)"""
    d = {'healthy': ('healthy B C A B A' in text) and ('read order 5 7 0 5 0 gave: B C A B A' in text)}
    m = BOARD_RE.search(text)
    if m:
        try:
            v = eval(m.group(1), {'__builtins__': {}}, {}) if re.fullmatch(r"\{[\w'\": ,]*\}", m.group(1)) else {}
            d['S'] = v.get('S'); d['imem_words'] = v.get('imem_words'); d['version'] = v.get('version')
        except Exception: pass
    return d

def first_read(runner=subprocess.run):
    r = runner([sys.executable, os.path.join(HERE, 'shared_ram_first_v1.py'), 'jtag', '0'], capture_output=True, text=True, cwd=HERE)
    return parse_first_read((r.stdout or '') + (r.stderr or '')), (r.stdout or '') + (r.stderr or '')

def compare_board(b, info):
    """-> list of mismatch messages between the build and what the board reported (empty = the board matches)"""
    bad = []
    if not info.get('healthy'): bad.append('the first-read test is not healthy (B C A B A expected)')
    if info.get('S') is not None and info['S'] != b['slices']: bad.append('the board has %s slices per block, the build %s has %d' % (info['S'], b['name'], b['slices']))
    if info.get('imem_words') is not None and info['imem_words'] != b['imem']: bad.append('the board has %s code words, the build %s has %d' % (info['imem_words'], b['name'], b['imem']))
    return bad

def host_settings(b):
    """what the shell's settings become when this build is chosen"""
    return {'blocks': b['blocks'], 'slices': b['slices'], 'unit-lw': (b['unit_lw'] if b['lanes'] else None), 'imem': b['imem']}
