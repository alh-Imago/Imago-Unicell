"""tools/flex_layout_sim_v2.py -- ledger #1065: the step simulator can now read a RESULT that sits in a nano (logic) cell.

v1's `_collect` asks each output cell for `_offer_state()`; the nano has none (it is delegated to the standalone nano model), so v1 raised "unsupported core 'nano'", skipped
the cell, and a design whose last cell is an and/or/xor/not/... showed NO output although the cell had computed the right value. The design was fine; the observer was blind.

A nano that ends a chain (no output faces) marks its result `_needs_confirm` until something outside reads it -- the model's chain-end rule (#77). v2 reads it then, records it,
and confirms the read, the same way v1 treats an adder or multiplier result. Everything else is v1 unchanged (this class subclasses it; v1 is untouched)."""
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
import flex_layout_sim_v1 as _v1  # noqa: E402

MAX_TICKS = _v1.MAX_TICKS


class StepSim(_v1.StepSim):
    def _collect(self):
        got = super()._collect()
        for k in self.outputs:
            cell = self.grid.cells[self.pos[k]]
            if cell.core != "nano":
                continue
            n = cell._nano
            if getattr(n, "_needs_confirm", False) and n.out_buffer is not None:
                v = int(n.out_buffer)
                self.seen[k].append(v)
                got.append((k, v))
                self.log.append(f"tick {self.ticks}: out {self.io.get(k) or k} = {v}")
                n.pending_ack = 0
                n._needs_confirm = False
        return got
