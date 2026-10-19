"""flex_grid_v2.py -- FlexGrid v2: HELD CONSTANTS (ledger #1271). A subclass of FlexGrid (flex_grid_v1.py is untouched and stays the proven reference).

The difference it fixes (ledger #1266-#1270): the flex generator builds every ram with nothing feeding it and a preload_value as a CONSTANT, a fixed-mode ram that is offered all the time
and never used up, and a two-operand cell (adder, multiplier) that has one simply waits for its live operand. FlexGrid v1 reads the same ICM cell as the standard family does:
fixed_mode 0 plus a preload is a ONE-SHOT, offered once and then empty. In a streaming design that is wrong for the flex hardware: the CORDIC's per-stage constants are used up by the first word, so
the second word waits for ever for an operand that the hardware keeps offering. (The standard hardware is a one-shot there, and SuperGrid models that correctly; this class changes only the flex mirror.)

RULE (deliberately narrow; everything else behaves exactly as in v1): a ram cell that has a preload_value, is NOT fixed_mode, has NOTHING feeding it, and whose consumers are ALL two-operand
adders or multipliers is a held constant: whenever it has been used up it is offered again (re-armed after the tick in which it drained), so the consumer finds it again for the next word.
A constant that feeds anything else (a relay, a merge, a branch's reference) stays a one-shot as in v1: the branch's reference is already HELD by the VM's branch (first arrival is kept), and a
repeated reference would be taken as stream data (measured, ledger #1268). Divide is not included (its operand order is by arrival and the VM refuses a same-tick pair).

Use: `from flex_grid_v2 import FlexGrid2`. Same constructor as FlexGrid.
"""
from flex_grid_v1 import FlexGrid, _DIRS_ALL
from unicell_super_automaton_v1 import _DIR_BIT


class FlexGrid2(FlexGrid):
    family = "flex"

    def __init__(self, records, *a, **kw):
        super().__init__(records, *a, **kw)
        preload = {(r.row, r.col): r.preload_value for r in records if r.core == "ram" and r.preload_value is not None}
        fed = set()
        for pos, c in self.cells.items():
            for d in _DIRS_ALL:
                if self._out_mask(c) >> _DIR_BIT[d] & 1:
                    nb = self.neighbor_pos(pos[0], pos[1], d, upstream=False)
                    if nb is not None:
                        fed.add(nb)
        self._held = {}
        for pos, v in preload.items():
            c = self.cells.get(pos)
            if c is None or c.core != "ram" or c.ram_fixed_mode or pos in fed:
                continue
            consumers = []
            for d in _DIRS_ALL:
                if c.ram_downstream_mask >> _DIR_BIT[d] & 1:
                    nb = self.neighbor_pos(pos[0], pos[1], d, upstream=False)
                    consumers.append(self.cells[nb].core if nb is not None and nb in self.cells else None)
            if consumers and all(k in ("adder", "mul") for k in consumers):
                self._held[pos] = int(v) & c.mask

    @staticmethod
    def _out_mask(c):
        return {"ram": c.ram_downstream_mask, "adder": c.adder_downstream_mask}.get(c.core, 0) if c.core in ("ram", "adder") else getattr(c, c.core + "_downstream_mask", 0)

    def tick(self):
        out = super().tick()
        for pos, v in self._held.items():
            c = self.cells[pos]
            if not c.ram_data_valid:
                c.ram_data_reg, c.ram_data_valid = v, True
        return out
