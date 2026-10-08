"""tools/flex_layout_sim_v1.py -- the Composer's step-through: inject values into a design's inputs, step it tick by tick (or run it until it settles) in FlexGrid, the flex
VM mirror (nano/flex_grid_v1.py), and watch every value move, so the flow and the result of a design can be checked before any RTL is built.

  * INPUTS are the io-named cells nothing joins into (any cell can also be injected by name); OUTPUTS are the io-named cells that join nowhere. An output's value is taken
    when it becomes valid and the cell is read (cleared), as tests/vm/fp_block_runner_v1.run_vm does.
  * A CONSTANT (a ram with a preload) is offered again with every injected item, as the RTL's constants are always valid (the VM would offer a preload once).
  * `state()` is every cell's (value, valid) after the last tick, keyed by cell name, so a page can draw values on the board, relays included.
Test/design-support tooling: the RTL generator stays the oracle."""
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TOOLS_DIR, "..", "nano"))
sys.path.insert(0, TOOLS_DIR)
from icm_v3 import IcmV3Record  # noqa: E402

MAX_TICKS = 20000


class StepSim:
    def __init__(self, layout, width=None):
        import flex_grid_v1 as fg
        recs = layout.records(file_coords=False)
        self.pos = {r.cell_id: (r.row, r.col) for r in recs}
        self.consts = {r.cell_id: r.preload_value for r in recs if r.preload_value is not None}
        recs = [IcmV3Record(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config, io_name=r.io_name,
                            preload_value=None) if r.cell_id in self.consts else r for r in recs]
        self.width = width or layout.min_bit_width or 32
        self.grid = fg.FlexGrid(recs, width=self.width)
        g = layout.grid
        has_in = {b for a, b, _ in g.links}
        has_out = {a for a, b, _ in g.links}
        io = layout.io
        self.inputs = [k for k in g.nodes if k in io and k not in has_in]
        self.outputs = [k for k in g.nodes if k in io and k not in has_out]
        if not self.inputs:                                        # no io names: every logic cell nothing feeds that is not a constant
            self.inputs = [k for k in g.nodes if layout.is_logic(k) and k not in has_in and k not in self.consts]
        if not self.outputs:
            self.outputs = [k for k in g.nodes if layout.is_logic(k) and k not in has_out]
        self.io = {k: io.get(k) for k in self.inputs + self.outputs}
        self.seen = {k: [] for k in self.outputs}
        self.ticks, self.items, self.log = 0, 0, []
        self.fed = []                                              # what each injected item gave each input (a saved model's reference inputs)

    # ---- driving -------------------------------------------------------------------------------------------------------------------------
    def inject(self, values):
        """values: {cell name: int}. The constants are offered again with each injected item."""
        for k, v in values.items():
            if k not in self.pos:
                raise ValueError(f"no cell {k}")
            self.grid.inject(*self.pos[k], int(v) & ((1 << self.width) - 1))
        for k, v in self.consts.items():
            self.grid.inject(*self.pos[k], v)
        self.items += 1
        self.fed.append({k: int(v) for k, v in values.items()})
        self.log.append(f"tick {self.ticks}: item {self.items} in: " + ", ".join(f"{self.io.get(k) or k}={v}" for k, v in values.items()))

    def _collect(self):
        got = []
        for k in self.outputs:
            cell = self.grid.cells[self.pos[k]]
            if getattr(cell, "ram_data_valid", False):
                self.seen[k].append(cell.ram_data_reg)
                got.append((k, cell.ram_data_reg))
                cell.ram_data_valid = False
            elif cell.core != "ram":
                try:
                    v, ok, _ = cell._offer_state()
                except Exception:
                    continue
                if not ok:
                    continue
                if cell.is_continuously_live():               # a live value (accumulator, latch): recorded when it changes
                    if not self.seen[k] or self.seen[k][-1] != v:
                        self.seen[k].append(v)
                        got.append((k, v))
                else:                                         # a one-shot result (adder, mul, comparator, ...): read it, and the read frees the cell, as an ack would
                    self.seen[k].append(v)
                    got.append((k, v))
                    cell.clear_valid_on_drain()
        for k, v in got:
            self.log.append(f"tick {self.ticks}: out {self.io.get(k) or k} = {v}")
        return got

    def step(self, n=1):
        for _ in range(max(1, min(int(n), MAX_TICKS))):
            self.grid.tick()
            self.ticks += 1
            self._collect()

    def _fingerprint(self):
        return tuple(sorted((k, v["v"], v["valid"]) for k, v in self.state().items()))   # positions never change during a run

    def run(self, max_ticks=2000):
        """Tick until nothing is pending and the cells' values stop changing (or max_ticks). Returns the ticks used."""
        start, last, same = self.ticks, None, 0
        for _ in range(max(1, min(int(max_ticks), MAX_TICKS))):
            self.step(1)
            fp = (bool(self.grid._pending), self._fingerprint())
            same = same + 1 if fp == last and not fp[0] else 0
            last = fp
            if same >= 3:
                break
        return self.ticks - start

    def run_items(self, items, max_ticks=2000):
        """items: {cell: [v0, v1, ...]}: from the next item not yet injected, inject item i on every listed input, run until settled, then the next item."""
        n = max((len(v) for v in items.values()), default=0)
        for i in range(self.items, n):
            self.inject({k: v[i] for k, v in items.items() if i < len(v)})
            self.run(max_ticks)
        return max(0, n - self.items)

    # ---- the view --------------------------------------------------------------------------------------------------------------------------
    def state(self):
        out = {}
        for k, p in self.pos.items():
            cell = self.grid.cells.get(p)
            if cell is None:
                continue
            try:
                v, ok, _ = cell._offer_state()
            except Exception:
                v, ok = getattr(cell, "ram_data_reg", 0), bool(getattr(cell, "ram_data_valid", False))
            out[k] = {"v": int(v or 0), "valid": bool(ok), "r": p[0], "c": p[1]}
        return out

    def view(self):
        return {"ticks": self.ticks, "items": self.items, "width": self.width, "inputs": [{"cell": k, "io": self.io.get(k)} for k in self.inputs],
                "outputs": [{"cell": k, "io": self.io.get(k), "values": self.seen[k]} for k in self.outputs],
                "pending": sum(len(v) for v in self.grid._pending.values()), "state": self.state(), "log": self.log[-60:]}
