"""jobiss.py - runs ONE linked job class in Python, instruction by instruction (RV32I, word loads / stores), against its shared-RAM window, the way the board runs it.
It is the independent reference for programs that have no Python answer of their own, and an early bug catcher for programs written by hand:
  * a load / store outside the job's shared window (byte addresses from 0x10000) or outside its private data (words 0 .. dlen-1) is a TRAP, as the regions are on the board;
  * an instruction fetch outside the job's code region and the library window is a TRAP;
  * byte / halfword loads and stores and multiply / divide are not modelled (the pool core's support is not assumed): they raise ProgramError - use lw / sw;
  * a program that runs more than max_steps instructions is stopped (runaway loop).
It starts at the class entry with all registers zero and stops at ebreak (the start-up stub's last instruction after main returns).
It checks the program against the ISS, NOT against what the program should compute: a wrong program that the ISS and the board both run the same way passes."""
import runtests as rt
import jobio as J
M32 = 0xFFFFFFFF
WIN_BASE = 0x10000

class ProgramError(Exception): pass
class JobTrap(ProgramError): pass

def run_class(link, cid, image, max_steps=2_000_000):
    """image: {shared word index: value} (from jobio.prepare) -> (list of the window's words after the run, steps).  Raises JobTrap / ProgramError."""
    k = link.classes[cid]; words = link.words
    wbase, wlen = k['win'] if k['win'] else (0, 0)
    win = [image.get(wbase + i, 0) & M32 for i in range(wlen)]
    dm = [0] * k['dlen']
    lo, hi = k['cbase'], k['cbase'] + k['clen']; lib = link.lib[1]
    x = [0] * 32; pc = k['entry'] * 4; steps = 0
    def mem(a, write=None):
        a &= M32
        if WIN_BASE <= a < WIN_BASE + 4 * wlen:
            i = (a - WIN_BASE) >> 2
            if write is None: return win[i]
            win[i] = write & M32; return None
        if a < 4 * len(dm):
            i = a >> 2
            if write is None: return dm[i]
            dm[i] = write & M32; return None
        raise JobTrap('data access at byte address %#x outside the shared window [%#x,%#x) and the private data [0,%#x)' % (a, WIN_BASE, WIN_BASE + 4 * wlen, 4 * len(dm)))
    while True:
        w = pc >> 2
        if not (lo <= w < hi or w < lib): raise JobTrap('instruction fetch at word %d outside the job code [%d,%d) and the library [0,%d)' % (w, lo, hi, lib))
        if w >= len(words): raise JobTrap('pc ran off the program')
        ir = words[w]; steps += 1
        if steps > max_steps: raise ProgramError('more than %d instructions: runaway loop?' % max_steps)
        opc, rd, f3 = ir & 0x7F, (ir >> 7) & 31, (ir >> 12) & 7
        rs1, rs2, f7 = (ir >> 15) & 31, (ir >> 20) & 31, ir >> 25
        a, b = x[rs1], x[rs2]; npc = (pc + 4) & M32; wr = None
        if opc == 0x37: wr = ir & 0xFFFFF000
        elif opc == 0x17: wr = (pc + (ir & 0xFFFFF000)) & M32
        elif opc == 0x6F:
            imm = rt.sx(((ir >> 31) << 20) | (((ir >> 12) & 0xFF) << 12) | (((ir >> 20) & 1) << 11) | (((ir >> 21) & 0x3FF) << 1), 21)
            wr = npc; npc = (pc + imm) & M32
        elif opc == 0x67: wr = npc; npc = ((a + rt.sx(ir >> 20, 12)) & M32) & ~1
        elif opc == 0x63:
            imm = rt.sx(((ir >> 31) << 12) | (((ir >> 7) & 1) << 11) | (((ir >> 25) & 0x3F) << 5) | (((ir >> 8) & 0xF) << 1), 13)
            sa, sb = rt.sx(a, 32), rt.sx(b, 32)
            if {0: a == b, 1: a != b, 4: sa < sb, 5: sa >= sb, 6: a < b, 7: a >= b}[f3]: npc = (pc + imm) & M32
        elif opc == 0x03:
            if f3 != 2: raise ProgramError('byte / halfword loads are not modelled (use lw)')
            wr = mem(a + rt.sx(ir >> 20, 12))
        elif opc == 0x23:
            if f3 != 2: raise ProgramError('byte / halfword stores are not modelled (use sw)')
            mem(a + rt.sx(((ir >> 25) << 5) | ((ir >> 7) & 31), 12), b)
        elif opc in (0x13, 0x33):
            if opc == 0x33 and f7 == 1: raise ProgramError('multiply / divide are not modelled (the pool core has no RV32M)')
            if opc == 0x13: b = rt.sx(ir >> 20, 12) & M32; sh = (ir >> 20) & 31
            else: sh = b & 31
            sa, sb = rt.sx(a, 32), rt.sx(b, 32)
            if f3 == 0: wr = (a - b if (opc == 0x33 and f7 == 0x20) else a + b) & M32
            elif f3 == 1: wr = (a << sh) & M32
            elif f3 == 2: wr = int(sa < sb)
            elif f3 == 3: wr = int(a < b)
            elif f3 == 4: wr = a ^ b
            elif f3 == 5: wr = ((sa >> sh) & M32) if f7 == 0x20 else (a >> sh)
            elif f3 == 6: wr = a | b
            elif f3 == 7: wr = a & b
        elif opc == 0x73: return win, steps
        else: raise JobTrap('illegal instruction %08x' % ir)
        if wr is not None and rd: x[rd] = wr & M32
        pc = npc

def reference(link, job):
    """run a jobio.Job through the ISS: -> (status, n_out, output words).  The job must have been linked as class job.cid."""
    base = J.window_base(link, job)
    win, steps = run_class(link, job.cid, J.prepare(link, job))
    status, n = win[J.F_STATUS], win[J.F_NOUT]
    return status, n, win[job.out_off:job.out_off + min(n, job.out_len)], steps
