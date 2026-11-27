#!/usr/bin/env python3
"""card_label_v1.py - a LABEL in the card's far RAM that says which build the shell loaded, and a PROBE that counts the card's blocks (ledger #1556).

Why: the card reports only version, slices per block, code words and shared RAM size (the V and Z replies). It does not report how many blocks it has, the fusion unit's
lanes, or which build it is. This file adds two things that need NO new build:
  LABEL  the shell writes a short record into far RAM words 0x0100 to 0x0112 right after a successful `load`: a marker word, the build name, blocks, slices, lanes, units,
         code words, shared words, the time, and a checksum. Far RAM is block RAM; loading a bitstream is expected to reset it to zeros (NOT yet measured on the card: run
         `test` below), so the label lasts as long as the design it describes and a reload by hand wipes it (then the label reads "empty": not known).
         It is the HOST's record that it loaded this build, not something the hardware asserts.
  PROBE  counts the blocks: the host command `O k` selects block k and a k at or above the real block count is IGNORED (read from host_bridge_v13.v line 217, not yet
         measured on the card). So: write a different marker (0x5C000000 + k) into one shared RAM word of "block k" for k = 0..15 in order, then read them back in order; the
         first block that does not hold its own marker is the last real block (the later writes all landed there), so blocks = that index + 1; all 16 matching means 16.
         It overwrites one shared RAM word (default 253) of each block, so never run it while a job runs.

Usage (card loaded, openOCD on the path), from s-core:
  nix shell nixpkgs#openocd --command python3 card_label_v1.py read              board report, block probe, and the label (nothing is written except the probe words)
  nix shell nixpkgs#openocd --command python3 card_label_v1.py write NAME BLOCKS SLICES LANES UNITS IMEM SHARED     write the label, read it back, probe
  nix shell nixpkgs#openocd --command python3 card_label_v1.py probe             only the block count
  nix shell nixpkgs#openocd --command python3 card_label_v1.py test              step 1 of the reload test: far RAM words 0x0000 to 0x01FF store and return two patterns, then
                                                                                 a label named TEST is written; step 2 is yours: load a build by hand, then run `read`: expect LABEL none (empty)
Output lines (the shell reads these):  BOARD version=12 S=32 imem=1024 shared=256 | PROBE blocks=8 | LABEL ok name=... blocks=... | LABEL none: reason"""
import sys, time, struct

MAGIC = 0x53434C42            # 'SCLB'
FORMAT = 1
LABEL_BASE = 0x0100           # far RAM word address; the planner starts its work at 0x2000
NAME_WORDS = 8                # 32 characters
LABEL_WORDS = 19              # magic, format, name length, 8 name words, blocks, slices, lanes, units, imem, shared, time, checksum
PROBE_WORD = 253              # shared RAM word used by the block probe (fallback: shared words - 3)
M32 = 0xFFFFFFFF

def _check(words): return ((sum(words) & M32) ^ 0xA5A5A5A5) & M32

def encode(name, blocks, slices, lanes, units, imem, shared, when=None):
    """-> the 19 words of the label"""
    nb = name.encode('ascii', 'replace')[:NAME_WORDS * 4]
    nb = nb + bytes(NAME_WORDS * 4 - len(nb))
    w = [MAGIC, FORMAT, len(name.encode('ascii', 'replace')[:NAME_WORDS * 4])] + list(struct.unpack('<%dI' % NAME_WORDS, nb))
    w += [blocks & M32, slices & M32, lanes & M32, units & M32, imem & M32, shared & M32, int(time.time() if when is None else when) & M32]
    return w + [_check(w)]

def decode(words):
    """-> (label dict or None, reason).  reason is '' for a good label"""
    if len(words) != LABEL_WORDS: return None, 'wrong length'
    if all(x == 0 for x in words): return None, 'empty'
    if words[0] != MAGIC: return None, 'no label marker (the far RAM there holds other data)'
    if words[1] != FORMAT: return None, 'label format %d is not known to this program' % words[1]
    if _check(words[:-1]) != words[-1]: return None, 'damaged (checksum does not match)'
    n = words[2]
    if n > NAME_WORDS * 4: return None, 'damaged (name length)'
    name = struct.pack('<%dI' % NAME_WORDS, *words[3:3 + NAME_WORDS])[:n].decode('ascii', 'replace')
    return dict(name=name, blocks=words[11], slices=words[12], lanes=words[13], units=words[14], imem=words[15], shared=words[16], time=words[17]), ''

def probe_blocks(link, maxb=16, pause=0.03):
    """count the blocks with the `O k` ignore rule (see the top of this file).  link: select(k), shared_put(word, value), shared_get(word), shared_words()"""
    w = min(PROBE_WORD, max(0, link.shared_words() - 3))
    for k in range(maxb):
        link.select(k); link.shared_put(w, 0x5C000000 + k)
    for k in range(maxb):
        link.select(k)
        if link.shared_get(w) != 0x5C000000 + k: return k + 1
    return maxb

def write_label(link, words):
    for i, x in enumerate(words): link.far_put(LABEL_BASE + i, x)
    link.far_flush()

def read_label(link): return [link.far_get(LABEL_BASE + i) for i in range(LABEL_WORDS)]

class CardLink:
    """the real card: the same host commands scblocks.py and far_ram_check_v1.py use"""
    def __init__(self, port='jtag', pause=0.03):
        import host_sc as hs, sdt_host as H
        self.hs, self.H, self.pause = hs, H, pause; self.b = hs.Board(port)
    def info(self):
        v = self.b.version(); v['shared_words'] = self.b.shared_info()['shared_words']; return v
    def shared_words(self): return self.b.shared_info()['shared_words']
    def select(self, k): self.b.s.write(self.hs.cmd_O(k)); self.b.s.flush(); time.sleep(self.pause)
    def shared_put(self, w, v): self.b.shared_write(w, [v]); time.sleep(self.pause)
    def shared_get(self, w): g = self.b.shared_read(w, 1)[0]; time.sleep(self.pause); return g
    def far_put(self, a, v): self.b.s.write(self.hs.cmd_O(0)); self.b.s.write(self.H.c_w(a, v))      # the far RAM is reached through block 0, as far_ram_check_v1.py does
    def far_flush(self): self.b.s.flush()
    def far_get(self, a):
        self.b.s.write(self.hs.cmd_O(0)); self.b.s.write(self.H.c_r(a)); self.b.s.flush()
        return self.H.dec_r(self.b._rd(4))

def report(link):
    """the lines the shell reads, for `read`"""
    i = link.info(); out = ['BOARD version=%d S=%d imem=%d shared=%d' % (i['version'], i['S'], i['imem_words'], i['shared_words'])]
    out.append('PROBE blocks=%d' % probe_blocks(link))
    lab, why = decode(read_label(link))
    if lab: out.append('LABEL ok name=%s blocks=%d slices=%d lanes=%d units=%d imem=%d shared=%d time=%d' % (lab['name'], lab['blocks'], lab['slices'], lab['lanes'], lab['units'], lab['imem'], lab['shared'], lab['time']))
    else: out.append('LABEL none: ' + why)
    return out

def low_area_test(link, count=0x200):
    """far RAM words 0x0000..count-1 store and return two patterns -> list of (pattern, bad words)"""
    res = []
    for name, f in (('address', lambda a: a), ('complement', lambda a: (~a) & M32)):
        for a in range(count): link.far_put(a, f(a))
        link.far_flush()
        bad = [(a, f(a), link.far_get(a)) for a in range(count) if link.far_get(a) != f(a)]
        res.append((name, bad))
    return res

def parse_report(text):
    """the output of `read` or `write` -> dict(board={version,S,imem,shared}|None, blocks=int|None, label={...}|None, why=str|None, written=bool, failed=str|None)"""
    import re
    d = dict(board=None, blocks=None, label=None, why=None, written=False, failed=None)
    m = re.search(r'BOARD version=(\d+) S=(\d+) imem=(\d+) shared=(\d+)', text)
    if m: d['board'] = dict(version=int(m.group(1)), S=int(m.group(2)), imem=int(m.group(3)), shared=int(m.group(4)))
    m = re.search(r'PROBE blocks=(\d+)', text)
    if m: d['blocks'] = int(m.group(1))
    m = re.search(r'LABEL (written )?ok name=(\S+) blocks=(\d+) slices=(\d+) lanes=(\d+) units=(\d+) imem=(\d+) shared=(\d+) time=(\d+)', text)
    if m: d['written'] = bool(m.group(1)); d['label'] = dict(name=m.group(2), blocks=int(m.group(3)), slices=int(m.group(4)), lanes=int(m.group(5)), units=int(m.group(6)), imem=int(m.group(7)), shared=int(m.group(8)), time=int(m.group(9)))
    m = re.search(r'LABEL none: (.*)', text)
    if m: d['why'] = m.group(1).strip()
    m = re.search(r'LABEL write FAILED: (.*)', text)
    if m: d['failed'] = m.group(1).strip()
    return d

def main(argv=None, link=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or a[0] not in ('read', 'write', 'probe', 'test'): print(__doc__); return 2
    link = link or CardLink('jtag')
    if a[0] == 'read':
        for ln in report(link): print(ln)
    elif a[0] == 'probe': print('PROBE blocks=%d' % probe_blocks(link))
    elif a[0] == 'write':
        if len(a) != 8: print('usage: write NAME BLOCKS SLICES LANES UNITS IMEM SHARED'); return 2
        name = a[1]; nums = [int(x, 0) for x in a[2:]]
        if nums[-1] == 0: nums[-1] = link.info()['shared_words']          # SHARED 0 = take the board's own figure
        words = encode(name, *nums); write_label(link, words)
        lab, why = decode(read_label(link))
        i = link.info(); print('BOARD version=%d S=%d imem=%d shared=%d' % (i['version'], i['S'], i['imem_words'], i['shared_words']))
        print('PROBE blocks=%d' % probe_blocks(link))
        if lab and lab['name'] == name[:32]: print('LABEL written ok name=%s blocks=%d slices=%d lanes=%d units=%d imem=%d shared=%d time=%d' % (lab['name'], lab['blocks'], lab['slices'], lab['lanes'], lab['units'], lab['imem'], lab['shared'], lab['time']))
        else: print('LABEL write FAILED: read back as ' + (why or 'a different name')); return 1
    elif a[0] == 'test':
        bad_any = False
        for name, bad in low_area_test(link):
            print('low far RAM 0x0000-0x01FF, pattern %s: %d bad words%s' % (name, len(bad), (' first: addr 0x%04x wrote 0x%08x got 0x%08x' % bad[0]) if bad else '')); bad_any |= bool(bad)
        write_label(link, encode('TEST', 1, 1, 0, 0, 0, 0)); lab, why = decode(read_label(link))
        print('label TEST written and read back: %s' % ('ok' if lab and lab['name'] == 'TEST' else 'FAILED (' + why + ')'))
        print('STEP 2 (yours): load any build by hand, then `read`: expect "LABEL none: empty". If it still says TEST the reload does NOT clear far RAM and the label is not trustworthy.')
        return 1 if bad_any or not lab else 0
    return 0

if __name__ == '__main__': sys.exit(main())
