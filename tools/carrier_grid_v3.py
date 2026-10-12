#!/usr/bin/env python3
"""tools/carrier_grid_v3.py -- ledger #1116: carrier_grid_v2.py (#1105, untouched) with the ACCUMULATOR added to the cores the grid generator can configure (the std-line ring control counts with it).
Field map from accumulator_cell_v4c (cfg_data[63:0]): inc_dir [5:0], dec_dir [11:6], downstream_mask [17:12], step_amount [25:18], pulse_mode [26], threshold [42:27]. Everything else is v2's.
Use: import carrier_grid_v3 as G; G.simulate(records, tap, clocks, keep=("ram","adder","branch","accumulator"))."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carrier_grid_v2 as _v2
from carrier_grid_v2 import *  # noqa: F401,F403

_v2.SEL["accumulator"] = 5
_orig_core_word = _v2.core_word


def core_word(rec):
    if rec.core == "accumulator":
        c = rec.core_config
        m = _v2.mask
        return (m(c.get("inc_dir")) | (m(c.get("dec_dir")) << 6) | (m(c.get("downstream_mask")) << 12) | ((c.get("step_amount", 1) & 0xFF) << 18)
                | ((c.get("pulse_mode", 0) & 1) << 26) | ((c.get("threshold", 0) & 0xFFFF) << 27))
    return _orig_core_word(rec)


_v2.core_word = core_word
SEL = _v2.SEL
simulate, generate = _v2.simulate, _v2.generate
