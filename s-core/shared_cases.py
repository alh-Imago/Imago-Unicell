"""Shared-data-RAM test programs and expectations, used by the simulation test (test_shared_sim.py) and the board script (run_shared_board.py).

Shared window: data word index 2^SHL (SHL=14) = byte address 0x10000, i.e. `lui t0,16` gives t0 = start of the window.
Physical map of the shared RAM used by the cases (DSH >= 256 words):
   0..16 17..  sum windows of classes 0..3 start at 0, 32, 64, 96 (17 words each: 16 inputs and the result)
   128..135    producer / consumer window
   144..147    'mixed' window (private + shared words in one program)
   160..163    load-beyond-length window
   199         guard word below the edge window       208  guard word above it
   200..207    edge window (classes 4 and 10)
   244..255    clamp window: asked for 100 words from 244, the hardware clamps it to the 12 that exist"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sched_tests as st
rt = st.rt

SUM16 = """lui t0,16
li t1,0
li t2,0
li t3,16
loop: lw t4,0(t0)
add t1,t1,t4
addi t0,t0,4
addi t2,t2,1
bne t2,t3,loop
sw t1,0(t0)
mv a0,t1
ebreak"""
EDGE_OK   = "lui t0,16\nli t1,77\nsw t1,28(t0)\nlw a0,28(t0)\nebreak"
EDGE_OVER = "lui t0,16\nli t1,99\nsw t1,32(t0)\nebreak"
NOWIN     = "lui t0,16\nlw a0,0(t0)\nebreak"
PRODUCER  = "lui t0,16\n" + "".join("li t1,%d\nsw t1,%d(t0)\n" % (k + 1, 4 * k) for k in range(8)) + "li a0,8\nebreak"
CONSUMER  = "lui t0,16\nli a0,0\n" + "".join("lw t1,%d(t0)\nadd a0,a0,t1\n" % (4 * k) for k in range(8)) + "ebreak"
MIXED     = "lui t0,16\nli t1,5\nsw t1,8(zero)\nli t2,7\nsw t2,12(t0)\nlw a0,8(zero)\nlw t3,12(t0)\nadd a0,a0,t3\nebreak"
CLAMP_OK  = "lui t0,16\nli t1,4660\nsw t1,44(t0)\nlw a0,44(t0)\nebreak"
CLAMP_OVER = "lui t0,16\nli t1,4660\nsw t1,48(t0)\nebreak"
LOAD_OVER = "lui t0,16\nlw a0,16(t0)\nebreak"

GUARD_LO, GUARD_HI = 0x1111EEEE, 0x5555AAAA
# kernel name -> (source, window (base, len) or None)
K = {
 'sum16':      (SUM16, None),          # window differs per class: see CLASSES
 'edge_ok':    (EDGE_OK, None), 'edge_over': (EDGE_OVER, None), 'nowin': (NOWIN, None),
 'producer':   (PRODUCER, None), 'consumer': (CONSUMER, None), 'mixed': (MIXED, None),
 'clamp_ok':   (CLAMP_OK, None), 'clamp_over': (CLAMP_OVER, None), 'load_over': (LOAD_OVER, None),
}
# class id -> (kernel, window or None)
CLASSES = {
 0: ('sum16', (0, 17)), 1: ('sum16', (32, 17)), 2: ('sum16', (64, 17)), 3: ('sum16', (96, 17)),
 4: ('edge_ok', (200, 8)), 10: ('edge_over', (200, 8)), 6: ('nowin', None),
 8: ('producer', (128, 8)), 9: ('consumer', (128, 8)), 11: ('mixed', (144, 4)),
 12: ('clamp_ok', (244, 100)), 13: ('clamp_over', (244, 100)), 14: ('load_over', (160, 4)),
}
def sum_of(k): return 16000 * k + 136

# (phase, class, expected a0 or None, expect trap)   one task each (15 in all: the build's default queue holds 16), except sum classes 0 and 1 which run twice
# (two tasks of one class share one window: here they only read it and write the same result word with the same value)
TASKS = [(1, k, sum_of(k), False) for k in range(4)] + [(1, 0, sum_of(0), False), (1, 1, sum_of(1), False)] + [
 (1, 4, 77, False), (1, 10, None, True), (1, 6, None, True), (1, 8, 8, False), (1, 11, 12, False),
 (1, 12, 4660, False), (1, 13, None, True), (1, 14, None, True),
 (2, 9, 36, False)]

def preload():
    """shared word -> value, written by the host before the run"""
    m = {}
    for k in range(4):
        for j in range(16): m[32 * k + j] = 1000 * k + j + 1
    m[199] = GUARD_LO; m[208] = GUARD_HI
    return m
def expect_mem():
    """shared word -> value, read back by the host after the run (None = not checked)"""
    m = dict(preload())
    for k in range(4): m[32 * k + 16] = sum_of(k)
    m[207] = 77; m[135 - 7 + 0] = 1                  # edge_ok stored word 7 of its window; producer word 0 (128)
    for k in range(8): m[128 + k] = k + 1
    m[147] = 7; m[255] = 4660
    return m

def layout():
    """assemble every kernel; returns (words_all, {kernel: base})"""
    words, base = [], {}
    for name, (src, _) in K.items():
        w = rt.assemble(src); base[name] = len(words); words += w
    return words, base
