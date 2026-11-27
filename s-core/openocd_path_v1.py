#!/usr/bin/env python3
"""openocd_path_v1.py - make the shell use ONE named openocd (ledger #1568).

Why: on this machine more than one openocd exists.  jtagport.py starts whichever `openocd` comes first on PATH, and outside (or ahead of) `nix shell nixpkgs#openocd`
that is a different version from the one proven on this card (Alan, 14:58: "defaulted to another version ... it needs a specific path for this machine").
The proven JTAG code is not edited: this module puts the chosen openocd's folder FIRST on this process's PATH, so jtagport's shutil.which, the helper programs the
shell starts (card_label_v1.py, link_check_v1.py) and everything below them find that one.

Order of choice: the user's setting (`set openocd PATH`, or "openocd" in ~/.score_shell.json), the environment variable SCORE_OPENOCD, the nix build that ran on this card
(NIX_OPENOCD, seen in `pgrep` on 27 Nov: openocd 0.12.0), then whatever is on PATH.  The nix path is a store path of THIS machine's current nixpkgs: if nix updates it,
the file is gone and the next choice is used, and the shell says which one it took.
"""
import os, shutil, subprocess

NIX_OPENOCD = '/nix/store/zi88f99wi0fbaa9992jzwb8jykvnpaa5-openocd-0.12.0/bin/openocd'

def find_openocd(user=None, env=None):
    """-> (path, why) of the openocd to use, or (None, why not)"""
    env = os.environ if env is None else env
    for label, c in (('your setting', user), ('SCORE_OPENOCD', env.get('SCORE_OPENOCD')), ('the nix build proven on this card', NIX_OPENOCD)):
        if c:
            c = os.path.expanduser(c)
            if os.path.isfile(c) and os.access(c, os.X_OK): return c, label
    w = shutil.which('openocd')
    if w: return w, 'the first openocd on PATH'
    return None, 'no openocd found (not in your setting, SCORE_OPENOCD, the nix path or PATH)'

def version(path, runner=subprocess.run):
    """the version line of that openocd ('Open On-Chip Debugger 0.12.0 ...'), or '' when it cannot be asked"""
    try:
        r = runner([path, '--version'], capture_output=True, text=True, timeout=10)
        t = (r.stdout or '') + (r.stderr or '')
        return t.strip().split('\n')[0][:100]
    except Exception: return ''

def apply(path):
    """put path's folder first on PATH (this process and the programs it starts) -> True when it was changed"""
    d = os.path.dirname(os.path.abspath(path)); parts = [p for p in os.environ.get('PATH', '').split(os.pathsep) if p]
    if parts and parts[0] == d: return False
    os.environ['PATH'] = os.pathsep.join([d] + [p for p in parts if p != d]); return True

def choose(user=None, env=None, runner=subprocess.run):
    """find, apply and describe -> (path or None, one line for the person)"""
    p, why = find_openocd(user, env)
    if not p: return None, why
    apply(p)
    v = version(p, runner)
    return p, 'openocd: %s%s (%s)' % (p, (' - ' + v) if v else '', why)
