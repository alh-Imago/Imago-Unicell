"""Region test programs shared by the simulation test (test_regions_sim.py) and the board script (run_regions_board.py)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sched_tests as st
rt = st.rt

DL = 4      # data limit used for the checked classes: words 0..3
K = [   # (name, source, expected a0 or None, expect trap, region trimmed by this many words at the end; None = no region for the class)
 ('sum10 in region',      st.k_sum(10),                                  55,     False, 0),
 ('store word 3 ok',      "li t0,4660\nsw t0,12(zero)\nmv a0,t0\nebreak", 4660,   False, 0),
 ('store word 20 wild',   "li t0,80\nli t1,21845\nsw t1,0(t0)\nebreak",  None,   True,  0),
 ('load word 20 wild',    "li t0,80\nlw a0,0(t0)\nebreak",              None,   True,  0),
 ('word 3 intact',        "lw a0,12(zero)\nebreak",                      4660,   False, 0),
 ('word 20 untouched',    "lw a0,80(zero)\nebreak",                      0,      False, None),
 ('fetch past end',       st.k_sum(10),                                  None,   True,  1),
 ('jump out of region',   "li a0,1\nj 40\nebreak",                       None,   True,  0),
 ('store word 4 (edge)',  "li t0,16\nsw t0,0(t0)\nebreak",              None,   True,  0),
 ('sum30 recover',        st.k_sum(30),                                  465,    False, 0),
 ('beyond physical, default class', "li t0,140\nsw t0,0(t0)\nebreak",  None,   True,  None),
 ('no region (default)',  st.k_sum(20),                                  210,    False, None),
]

def layout():
    """assemble every case; returns (words_all, [(base, length) per case])"""
    words_all, ents = [], []
    for name, src, exp, trap, trim in K:
        w = rt.assemble(src); ents.append((len(words_all), len(w))); words_all += w
    return words_all, ents
