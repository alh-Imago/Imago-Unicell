#!/usr/bin/env python3
"""tools/carrier_grid_v4.py -- ledger #1171: carrier_grid_v3.py (#1116, untouched) with the DIVISION core added to the cores the grid generator can configure (carrier slot 15, #1073).
Field map from div_cell_v4c / v4e (cfg_data[63:0]): downstream_mask [5:0], upstream_mask [11:6], rem_primary [12], second_output [33], second_downstream_mask [39:34], join_mode [40] (VIXeN).
The quotient bits per clock (STEPS) is a build-time parameter of the cell, not a config field here. Everything else is v3's.
Use: import carrier_grid_v4 as G; G.simulate(records, tap, clocks, keep=("ram","adder","div"))."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carrier_grid_v2 as _v2
import carrier_grid_v3 as _v3
from carrier_grid_v3 import *  # noqa: F401,F403

_v2.SEL["div"] = 15
_prev_core_word = _v2.core_word


def core_word(rec):
    if rec.core == "div":
        c = rec.core_config
        m = _v2.mask
        w = m(c.get("downstream_mask")) | (m(c.get("upstream_mask")) << 6) | ((c.get("remainder_primary", 0) & 1) << 12) | ((c.get("second_output", 0) & 1) << 33) | (m(c.get("second_downstream_mask")) << 34)
        if c.get("join_mode", 0):
            w |= 1 << 40
        return w
    return _prev_core_word(rec)


_v2.core_word = core_word
SEL = _v2.SEL
simulate, generate = _v2.simulate, _v2.generate
