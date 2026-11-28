"""asm_ext_v1.py - the assembler extension for the byte and halfword instructions (ledger #1598), installed by jobio_ext_v2.install WITHOUT editing runtests.py or sclink.py.
  lb lh lbu lhu  rd, off(rs)   assembled as real RV32I loads (needs a build with the v26+ core: manifest narrow_loads; on others they trap).
  sb sh          rs2, off(rs1) expanded INLINE into the byte-store unit sequence (needs multiply level 3, line hp; else a link error), 5 instructions:
                     addi t1, rs1, off      # the byte address
                     lui  t0, 0x20          # device window
                     sw   t1, 16(t0)        # stage the address
                     sw   rs2, 20(t0)       # sh: 24(t0) - the store starts here
                     lw   zero, 16(t0)      # wait until the unit has finished
                 It CLOBBERS t0 and t1; rs2 must not be t0 or t1 (error).  The byte or halfword is the low 8 or 16 bits of rs2; a halfword address is used aligned down.
install(level, narrow): level = multiply level of the build (0 to 3), narrow = the build has byte/half loads.  uninstall() puts the originals back."""
import re
import runtests as rt
import sclink
_orig = {}
state = {'level': 0, 'narrow': False}
NARROW = {'lb': 0, 'lh': 1, 'lbu': 4, 'lhu': 5}
_REG = re.compile(r'^\s*(\w+)\s*,\s*(-?\w+)\s*\(\s*(\w+)\s*\)\s*$')

def _expand_ext(op, args):
    if op in ('sb', 'sh'):
        if state['level'] < 3: raise ValueError('%s needs a build with the byte-store unit (multiply level 3, line hp); this build has level %d' % (op, state['level']))
        m = _REG.match(args)
        if not m: raise ValueError('bad %s operands: %r' % (op, args))
        rs2, off, rs1 = m.group(1), m.group(2), m.group(3)
        if rs2 in ('t0', 't1', 'x5', 'x6'): raise ValueError('%s: the value register must not be t0 or t1 (they are used by the expansion)' % op)
        return [('addi', 't1, %s, %s' % (rs1, off)), ('lui', 't0, 0x20'), ('sw', 't1, 16(t0)'), ('sw', '%s, %d(t0)' % (rs2, 20 if op == 'sb' else 24)), ('lw', 'zero, 16(t0)')]
    if op in NARROW and not state['narrow']:
        raise ValueError('%s needs a build with byte and halfword loads (line hp); this build has none' % op)
    return _orig['expand'](op, args)

def _assemble_ext(text):
    kinds = []; out = []
    for line in text.splitlines():
        m = re.match(r'\s*(?:[A-Za-z_]\w*\s*:\s*)*(lb|lh|lbu|lhu)\s', line)
        if m: kinds.append(NARROW[m.group(1)]); line = re.sub(r'\b(lb|lh|lbu|lhu)\b', 'lw', line, count=1)
        elif re.match(r'\s*(?:[A-Za-z_]\w*\s*:\s*)*lw\s', line): kinds.append(2)
        out.append(line)
    words = _orig['assemble']('\n'.join(out)); k = 0
    for i, w in enumerate(words):
        if (w & 0x7F) == 0x03: words[i] = (w & ~(7 << 12)) | (kinds[k] << 12); k += 1
    return words

def install(level=0, narrow=False):
    state['level'] = int(level); state['narrow'] = bool(narrow)
    if _orig: return
    _orig['expand'], _orig['assemble'] = sclink._expand, rt.assemble
    sclink._expand, rt.assemble = _expand_ext, _assemble_ext

def uninstall():
    if not _orig: return
    sclink._expand, rt.assemble = _orig.pop('expand'), _orig.pop('assemble'); _orig.clear(); state['level'] = 0; state['narrow'] = False
