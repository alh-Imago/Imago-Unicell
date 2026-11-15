"""sclink.py - a small linker for S-Core: one shared code LIBRARY, several program classes, and where each class keeps its stack.

What it does
  * puts the library at the start of the shared code store and gives every program class its own code window after it;
  * writes a start-up stub in front of each class (crt0):  li sp,<stack top> ; jal ra,main ; ebreak
    so the class's `main` is an ordinary function that ends with `ret` and leaves its result in a0;
  * gives class-local labels a prefix (c<id>_) so two classes may both have a label called `loop`; library labels stay global
    (call them from any class: `call lib_sum`);
  * adds the pseudo-instructions the S-Core assembler lacks:  ret, call f, push r, pop r;
  * lays out the shared data RAM: each class gets a window (data words, then its stack if the stack lives there); windows are
    disjoint unless two classes are told to share one;
  * produces the host commands: code words (W), library window (Y), code/private-data regions (B), shared windows (X).

Where the stack goes (per class)
  stack='private'  the top of the class's private data memory (sp = 4 * private limit); grows down; hardware stops it at word 0 (trap).
  stack='shared'   the top of the class's shared window (sp = shared base address + 4 * window words); the window is [data | stack];
                   the hardware stops a stack that grows below the window's start (trap); it does NOT detect a stack that grows into
                   the class's own data words inside the window (keep the stack size generous, or put data in a separate window).

A class's `main` is an ordinary function: if it calls anything it must save ra first (`push ra` ... `pop ra`), exactly as in C.

Calling convention (RISC-V standard names): a0..a7 arguments / results, ra return address, sp stack pointer (word aligned),
t0..t6 scratch (library functions may use any t register and a0..a7), s0..s11 callee-saved.
Library code runs under the CALLER's limits, so a library function can only reach what the calling task may reach."""
import os, re, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import runtests as rt
import host_sc as hs

SHL_DEFAULT = 14

def _split(line):
    """-> (labels, op, args-string) of one source line"""
    line = line.split('#')[0].strip()
    labels = []
    while True:
        m = re.match(r'([A-Za-z_]\w*)\s*:\s*(.*)$', line)
        if not m: break
        labels.append(m.group(1)); line = m.group(2)
    op, _, rest = line.partition(' ')
    return labels, op.strip(), rest.strip()

def _expand(op, args):
    """pseudo-instructions -> list of (op, args)"""
    a = [x.strip() for x in args.split(',')] if args else []
    if op == 'ret':  return [('jalr', 'zero, ra, 0')]
    if op == 'call': return [('jal', 'ra, ' + a[0])]
    if op == 'push': return [('addi', 'sp, sp, -4'), ('sw', '%s, 0(sp)' % a[0])]
    if op == 'pop':  return [('lw', '%s, 0(sp)' % a[0]), ('addi', 'sp, sp, 4')]
    return [(op, args)] if op else []

def _unit(text, prefix, glob_ok):
    """rename the labels of one source unit (prefix=None: keep them); returns assembler lines"""
    items = [_split(l) for l in text.splitlines()]
    local = {lab for labs, _, _ in items for lab in labs}
    for lab in local:
        if lab in rt.ABI: raise ValueError('label %r is a register name' % lab)
        if prefix and lab.startswith('lib_'): raise ValueError('class label %r starts with lib_ (reserved for the library)' % lab)
    ren = (lambda n: prefix + n) if prefix else (lambda n: n)
    out = []
    for labs, op, args in items:
        pend = [ren(l) + ':' for l in labs]
        exp = _expand(op, args)
        if not exp: out += pend; continue
        for k, (o, a) in enumerate(exp):
            if prefix and local: a = re.sub(r'\b(%s)\b' % '|'.join(map(re.escape, sorted(local, key=len, reverse=True))), lambda m: ren(m.group(1)), a)
            out.append(' '.join(pend if k == 0 else []) + ' ' + o + (' ' + a if a else ''))
    return out

class Link:
    """Result of a link: .words, .lib (base, len), .classes {id: dict}, and helpers to produce / send the host commands."""
    def __init__(self): self.words = []; self.lib = (0, 0); self.classes = {}; self.shared_preload = {}
    def commands(self, with_code=True):
        """host command bytes in the order they must be sent (the array must be idle)"""
        c = []
        if with_code: c += [hs.cmd_W(i, w) for i, w in enumerate(self.words)]
        if self.lib[1]: c.append(hs.cmd_Y(*self.lib))
        for cid, k in sorted(self.classes.items()):
            c.append(hs.cmd_B(cid, k['cbase'], k['clen'], k['dlen']))
            if k['win'] and k['win'][1]: c.append(hs.cmd_X(cid, *k['win']))
        for a, v in sorted(self.shared_preload.items()): c.append(hs.cmd_M(a, v))
        return c
    def apply(self, board, with_code=True):
        """send everything to a host_sc.Board"""
        if with_code: board.load(0, self.words)
        if self.lib[1]: board.s.write(hs.cmd_Y(*self.lib))
        for cid, k in sorted(self.classes.items()):
            board.region(cid, k['cbase'], k['clen'], k['dlen'])
            if k['win'] and k['win'][1]: board.shared_region(cid, *k['win'])
        if self.shared_preload: board.shared_write_map(self.shared_preload)
        board.s.flush()
    def report(self):
        lines = ['code words %d: library at %d (%d words)' % (len(self.words), self.lib[0], self.lib[1])]
        for cid, k in sorted(self.classes.items()):
            lines.append('class %2d: entry word %3d, code [%d,%d), private limit %d words, shared window %s, stack in %s, sp=0x%x' % (
                cid, k['entry'], k['cbase'], k['cbase'] + k['clen'], k['dlen'], ('[%d,%d)' % (k['win'][0], k['win'][0] + k['win'][1])) if k['win'] else 'none', k['stack'], k['sp']))
        return '\n'.join(lines)

class Linker:
    def __init__(self, shared_words=256, private_words=32, shl=SHL_DEFAULT, code_words=None):
        self.shared_words, self.private_words, self.shl, self.code_words = shared_words, private_words, shl, code_words
        self.lib_src = ''; self.cls = {}; self.preload = {}
    @property
    def shared_base_addr(self): return 4 << self.shl          # byte address of shared word 0
    def library(self, src): self.lib_src += '\n' + src
    def add_class(self, cid, src, stack='private', stack_words=0, data_words=0, win_base=None, dlen=None, share_window_of=None):
        """cid: program class id (0..63).  src: assembly with a `main:` label ending in `ret`.
        stack: 'private' or 'shared' (then stack_words are reserved at the top of the window).
        data_words: shared data words before the stack.  win_base: place the window here (else automatic).
        dlen: private data limit in words (default: all of the private memory).  share_window_of: use the same window as another class."""
        if cid in self.cls: raise ValueError('class %d defined twice' % cid)
        if stack not in ('private', 'shared'): raise ValueError("stack must be 'private' or 'shared'")
        if stack == 'shared' and stack_words <= 0: raise ValueError('a shared stack needs stack_words > 0')
        self.cls[cid] = dict(src=src, stack=stack, stack_words=stack_words if stack == 'shared' else 0, data_words=data_words,
                             win_base=win_base, dlen=self.private_words if dlen is None else dlen, share=share_window_of)
    def clone_class(self, cid, of, win_base=None):
        """A second class id with the SAME code as class `of` but its OWN shared window (same size).  Use it for tasks of one program that run
        at the same time and each need their own stack / data in the shared RAM: a window belongs to a class id, not to a task, so two tasks
        with one id would share one stack."""
        if of not in self.cls or self.cls[of].get('clone') is not None: raise ValueError('class %d is not a plain class' % of)
        if cid in self.cls: raise ValueError('class %d defined twice' % cid)
        k = dict(self.cls[of]); k.update(clone=of, win_base=win_base, share=None); self.cls[cid] = k
    def preload_shared(self, addr, words):
        for i, w in enumerate(words): self.preload[addr + i] = w & 0xFFFFFFFF
    def link(self):
        # shared windows first (the stack tops are needed for the start-up stubs)
        win, nxt = {}, 0
        for cid, k in sorted(self.cls.items()):
            if k['share'] is not None: continue
            n = k['data_words'] + k['stack_words']
            base = k['win_base'] if k['win_base'] is not None else nxt
            win[cid] = (base, n); nxt = max(nxt, base + n)
        for cid, k in self.cls.items():
            if k['share'] is not None:
                if k['share'] not in win: raise ValueError('class %d shares the window of class %d, which has none (or shares itself)' % (cid, k['share']))
                b, n = win[k['share']]; need = k['data_words'] + k['stack_words']
                if need > n: raise ValueError('class %d needs a window of %d words but shares one of %d' % (cid, need, n))
                win[cid] = (b, n)
        spans = sorted((b, b + n, cid) for cid, (b, n) in win.items() if n and self.cls[cid]['share'] is None)
        for (b1, e1, c1), (b2, e2, c2) in zip(spans, spans[1:]):
            if b2 < e1: raise ValueError('shared windows of classes %d and %d overlap (use share_window_of to share on purpose)' % (c1, c2))
        if nxt > self.shared_words: raise ValueError('shared windows need %d words, the shared RAM has %d' % (nxt, self.shared_words))
        # source: library, then each class (stub + code)
        lines = _unit(self.lib_src, None, True)
        lib_words = len(rt.assemble('\n'.join(lines))) if lines else 0
        starts = {}
        text = list(lines)
        sp = {}
        for cid, k in sorted(self.cls.items()):
            if k.get('clone') is not None:
                sp[cid] = sp[k['clone']] if k['clone'] in sp else None; continue
            top = 4 * k['dlen'] if k['stack'] == 'private' else self.shared_base_addr + 4 * win[cid][1]      # a class sees its window starting at logical word 0, wherever it sits in the RAM
            if k['stack'] == 'private' and k['dlen'] <= 0: raise ValueError('class %d has no private data for its stack' % cid)
            sp[cid] = top
            starts[cid] = len(text)
            text += ['c%d_start:' % cid, ' li sp, %d' % top, ' jal ra, c%d_main' % cid, ' ebreak']
            body = _unit(k['src'], 'c%d_' % cid, False)
            if not any(l.strip().startswith('c%d_main:' % cid) or ' c%d_main:' % cid in l for l in body): raise ValueError("class %d has no label 'main:'" % cid)
            text += body
            starts[cid] = (starts[cid], len(text))
        full = '\n'.join(text)
        # find word addresses: assemble the prefix up to each class start
        words = rt.assemble(full)
        def words_upto(n): return len(rt.assemble('\n'.join(text[:n]))) if n else 0
        L = Link(); L.words = words; L.lib = (0, lib_words); L.shared_preload = dict(self.preload)
        for cid, k in self.cls.items():
            if k.get('clone') is not None: continue
            s, e = starts[cid]; cb, ce = words_upto(s), words_upto(e)
            L.classes[cid] = dict(entry=cb, cbase=cb, clen=ce - cb, dlen=k['dlen'], win=win[cid] if win[cid][1] else None, stack=k['stack'], sp=sp[cid])
        for cid, k in self.cls.items():
            if k.get('clone') is not None:
                base = L.classes[k['clone']]; sp[cid] = sp[k['clone']]
                L.classes[cid] = dict(base, win=win[cid] if win[cid][1] else None)
        if self.code_words and len(words) > self.code_words: raise ValueError('code needs %d words, the store has %d' % (len(words), self.code_words))
        return L
