#!/usr/bin/env python3
"""test_card_label_v1.py (ledger #1556): the label record and the block probe, on a FAKE card that obeys the rule read from host_bridge_v13.v ("O k with k >= NB is ignored").
It proves the program logic, not the card: whether the real card does what the fake does is the thing to measure (card_label_v1.py test / read).  python3 test_card_label_v1.py"""
import os, sys, io, contextlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import card_label_v1 as L
bad = 0
def check(name, cond):
    global bad
    print('%-120s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)

class FakeLink:
    def __init__(self, nb, S=8, imem=128, shared=256, far_works=True):
        self.nb, self.S, self.imem, self.shared = nb, S, imem, shared; self.sel = 0
        self.sh = [dict() for _ in range(16)]; self.far = {}; self.far_works = far_works
    def info(self): return dict(version=12, S=self.S, imem_words=self.imem, dmem_words=16, shared_words=self.shared)
    def shared_words(self): return self.shared
    def select(self, k):
        if k < self.nb: self.sel = k          # the rule read from the RTL: a value at or above the block count is ignored
    def shared_put(self, w, v): self.sh[self.sel][w] = v
    def shared_get(self, w): return self.sh[self.sel].get(w, 0)
    def far_put(self, a, v):
        if self.far_works: self.far[a] = v & 0xFFFFFFFF
    def far_flush(self): pass
    def far_get(self, a): return self.far.get(a, 0)

def run_main(args, link):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): rc = L.main(args, link=link)
    return rc, buf.getvalue()

w = L.encode('hk8s32u32n1i1024', 8, 32, 32, 1, 1024, 256, when=1732712345)
check('encode: 19 words, marker first, checksum last', len(w) == L.LABEL_WORDS == 19 and w[0] == L.MAGIC and w[-1] == L._check(w[:-1]))
lab, why = L.decode(w)
check('decode: round trip gives the name and every number back', lab == dict(name='hk8s32u32n1i1024', blocks=8, slices=32, lanes=32, units=1, imem=1024, shared=256, time=1732712345) and why == '')
check('decode: all zeros is "empty" (what a reload is expected to leave)', L.decode([0] * 19) == (None, 'empty'))
x = list(w); x[0] = 0x12345678; check('decode: other data at the address is "no label marker"', L.decode(x)[0] is None and 'no label marker' in L.decode(x)[1])
x = list(w); x[11] ^= 1; check('decode: one changed number is "damaged" (checksum)', L.decode(x)[0] is None and 'damaged' in L.decode(x)[1])
x = list(w); x[1] = 9; check('decode: an unknown format number is refused, not guessed', L.decode(x)[0] is None and 'format 9' in L.decode(x)[1])
check('decode: wrong length is refused', L.decode(w[:5])[0] is None)
long = L.encode('x' * 50, 1, 1, 0, 0, 0, 0); check('encode: a name longer than 32 characters is cut to 32, not corrupting the other fields', L.decode(long)[0]['name'] == 'x' * 32 and L.decode(long)[0]['blocks'] == 1)
for nb in (1, 2, 3, 5, 8, 12, 15, 16):
    f = FakeLink(nb); check('probe: a fake card with %d blocks is counted as %d' % (nb, nb), L.probe_blocks(f) == nb)
f = FakeLink(8, shared=64); L.probe_blocks(f); check('probe: uses a word inside a small shared RAM (61 for 64 words), not 253', any(61 in d for d in f.sh) and not any(253 in d for d in f.sh))
f = FakeLink(8); L.write_label(f, w); check('write then read the label back through the link', L.decode(L.read_label(f))[0]['name'] == 'hk8s32u32n1i1024')
rc, o = run_main(['read'], FakeLink(8, S=32, imem=1024))
check('read on a card with no label: BOARD, PROBE blocks=8 and "LABEL none: empty" lines', rc == 0 and 'BOARD version=12 S=32 imem=1024 shared=256' in o and 'PROBE blocks=8' in o and 'LABEL none: empty' in o)
f = FakeLink(8, S=32, imem=1024); rc, o = run_main(['write', 'hk8s32u32n1i1024', '8', '32', '32', '1', '1024', '256'], f)
check('write: prints BOARD, PROBE blocks=8 and "LABEL written ok name=hk8s32u32n1i1024", rc 0', rc == 0 and 'PROBE blocks=8' in o and 'LABEL written ok name=hk8s32u32n1i1024 blocks=8 slices=32 lanes=32 units=1 imem=1024 shared=256' in o)
rc, o = run_main(['read'], f); check('read after write: "LABEL ok name=hk8s32u32n1i1024 ..."', 'LABEL ok name=hk8s32u32n1i1024 blocks=8' in o)
f.far = {}; rc, o = run_main(['read'], f); check('read after the far RAM was cleared (a reload): "LABEL none: empty"', 'LABEL none: empty' in o)
f = FakeLink(8, far_works=False); rc, o = run_main(['write', 'hk8s32u32n1i1024', '8', '32', '32', '1', '1024', '256'], f)
check('write when the far RAM does not return what was written: LABEL write FAILED and rc 1 (the shell can then say so)', rc == 1 and 'LABEL write FAILED' in o)
rc, o = run_main(['write', 'only', 'three'], FakeLink(8)); check('write with the wrong number of arguments says the usage, rc 2', rc == 2 and 'usage: write' in o)
rc, o = run_main(['test'], FakeLink(8)); check('test on a working fake: both patterns 0 bad words, TEST label read back, rc 0, and the step-2 instruction is printed', rc == 0 and o.count('0 bad words') == 2 and 'TEST written and read back: ok' in o and 'STEP 2' in o)
rc, o = run_main(['test'], FakeLink(8, far_works=False)); check('test on a fake whose far RAM drops data: bad words reported, rc 1', rc == 1 and 'bad words' in o and '0 bad words' not in o)
r = subprocess.run([sys.executable, os.path.join(HERE, 'card_label_v1.py')], capture_output=True, text=True, cwd=HERE); check('run with no command prints the usage (rc 2)', r.returncode == 2 and 'Usage' in r.stdout)
r = subprocess.run([sys.executable, os.path.join(HERE, 'card_label_v1.py'), 'read'], capture_output=True, text=True, cwd=HERE, timeout=120)
print('   (no card here: `read` ended with rc %d; its last words: %s)' % (r.returncode, ((r.stderr or r.stdout).strip().splitlines() or [''])[-1][:140]))
check('read with no card link fails with a non-zero return code and no LABEL line (the shell treats that as "could not read the card")', r.returncode != 0 and 'LABEL' not in r.stdout)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
