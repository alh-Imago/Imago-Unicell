"""tests/vm/fp_block_runner_v1.py -- run a Grid of flex cells (built by tools/fp_assembler_v1.py) in the generated RTL (plain + random stalls) and in FlexGrid, return what each exit produced (ledger #989)."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
import flex_rtl_harness_v1 as h  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402


def port(cell):
    return re.sub(r"\W", "_", cell)


def run_rtl(tmp, name, recs, entries, exits, mode, settle=6000, cycles=3000):
    """entries: {cell: [values]}; exits: {label: cell}. Returns {label: [values]}."""
    d, r = h.build(tmp, f"{name}_{mode}", recs)
    assert r.returncode == 0, r.stderr[:1500]
    _, got = h.run_level(d, {port(c): v for c, v in entries.items()}, mode, 4, settle=settle, cycles=cycles)
    return {k: got[port(c)] for k, c in exits.items()}


def run_vm(recs, entries, exits, consts, ticks=2500):
    """The VM offers a PRELOADED constant once; the RTL's constants are always valid -> here every constant is an ordinary entry injected with each item."""
    recs = [type(r)(cell_id=r.cell_id, row=r.row, col=r.col, core=r.core, core_config=r.core_config, addon_config=r.addon_config, io_name=r.io_name, preload_value=None) if r.cell_id in consts else r for r in recs]
    g = fg.FlexGrid(recs, width=32)
    pos = {r.cell_id: (r.row, r.col) for r in recs}
    seen = {k: [] for k in exits}
    n = len(next(iter(entries.values())))
    for i in range(n):
        for c, vals in entries.items():
            g.inject(*pos[c], vals[i])
        for c, v in consts.items():
            g.inject(*pos[c], v)
        for _ in range(ticks):
            g.tick()
            for k, c in exits.items():
                cell = g.cells[pos[c]]
                if cell.ram_data_valid:
                    seen[k].append(cell.ram_data_reg)
                    cell.ram_data_valid = False
    return seen
