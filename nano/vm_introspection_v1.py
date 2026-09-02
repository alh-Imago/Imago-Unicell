"""
vm_introspection_v1.py — JSON introspection for the Unicell-S VM
(`unicell_super_automaton_v1.SuperGrid`/`SuperCell`), the first real
piece of `points.md #216`'s VM-core architecture, per Alan's own
explicit choice: do #216's work before the workbench, starting with
"JSON introspection, etc." as the named first piece.

SCOPE, stated honestly against #216's own full 8-item list: this file
answers ONLY item 5 ("full contents of any cell or the whole grid
exposed via a JSON API"), applied to the VM that already exists
(`unicell_super_automaton_v1.py`, built this session for Unicell-S).
It does NOT attempt items 1/3/4 (a mechanically-derived "root
definition" driving a genuinely generic, cell-design-agnostic engine --
today's `SuperCell` still hand-codes each of the 6 cores' behavior in
Python, the opposite of "parameterized against whatever root definition
got loaded"), item 6 (AI-interaction port), or item 8's specific
`core/` folder migration (though `nano/` already satisfies that item's
own underlying goal -- a clean, fresh, non-legacy folder, just under a
different name than originally proposed in `#216`). Those remain real,
separate, unstarted pieces of #216, not assumed solved by this file.

DESIGN CHOICE: a separate module, not methods added to `SuperCell`/
`SuperGrid` themselves -- keeps serialization concerns decoupled from
the VM's own tested tick/deliver logic (`#337`), so this file can never
risk regressing anything already proven there.

Deliberately omits `CACell`'s many legacy/Phase-2/3/4 fields
(`invert_out`, `latch_in`, `hold_in`, `fb_internal_in`, etc.) from the
nano JSON block -- every one of them is permanently unreachable through
Unicell-S's own restricted nano exposure (`icm_v3.py`'s own documented
scope: topology/ready/routing_mask/cardinal_edge only), so including
them would just be a wall of always-default noise, not real
information about the running cell.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def cell_to_dict(cell) -> Dict[str, Any]:
    """Full state of one `SuperCell`, as a plain dict -- common fields
    every core shares, plus a core-specific block with exactly that
    core's own real registers (field names checked directly against
    `unicell_super_automaton_v1.SuperCell`'s own dataclass fields, not
    guessed)."""
    base: Dict[str, Any] = {
        "row": cell.row,
        "col": cell.col,
        "core": cell.core,
        "pending_ack": cell.pending_ack,
        "downstream_mask": cell.downstream_mask,
        "addon_config": dict(cell.addon_config),
    }

    if cell.core == "nano":
        n = cell._nano
        base["nano"] = {
            "topology": n.topology,
            "ready_config": n.start_flag,
            "routing_mask": n.routing_mask,
            "cardinal_edge": n.cardinal_edge,
            "a_data": n.a_data,
            "a_arrived": n.a_arrived,
            "data_reg": n.data_reg,
            "out_buffer": n.out_buffer,
            "is_ready": n.ready,
        }
    elif cell.core == "ram":
        base["ram"] = {
            "downstream_mask": cell.ram_downstream_mask,
            "upstream_mask": cell.ram_upstream_mask,
            "fixed_mode": cell.ram_fixed_mode,
            "data_reg": cell.ram_data_reg,
            "data_valid": cell.ram_data_valid,
        }
    elif cell.core == "adder":
        base["adder"] = {
            "downstream_mask": cell.adder_downstream_mask,
            "upstream_mask": cell.adder_upstream_mask,
            "a_reg": cell.adder_a_reg,
            "a_arrived": cell.adder_a_arrived,
            "out_buffer": cell.adder_out_buffer,
            "data_valid": cell.adder_data_valid,
        }
    elif cell.core == "accumulator":
        base["accumulator"] = {
            "downstream_mask": cell.acc_downstream_mask,
            "inc_dir": cell.acc_inc_dir,
            "dec_dir": cell.acc_dec_dir,
            "total": cell.acc_total,
            "out_buffer": cell.acc_out_buffer,
            "step_amount": cell.acc_step_amount,
            "pulse_mode": cell.acc_pulse_mode,
            "threshold": cell.acc_threshold,
            "pulse_pending": cell.acc_pulse_pending,
        }
    elif cell.core == "comparator":
        base["comparator"] = {
            "downstream_mask": cell.cmp_downstream_mask,
            "upstream_mask": cell.cmp_upstream_mask,
            "threshold": cell.cmp_threshold,
            "out_buffer": cell.cmp_out_buffer,
            "data_valid": cell.cmp_data_valid,
        }
    elif cell.core == "latch":
        base["latch"] = {
            "downstream_mask": cell.latch_downstream_mask,
            "set_dir": cell.latch_set_dir,
            "clear_dir": cell.latch_clear_dir,
            "state": cell.latch_state,
        }
    elif cell.core == "sequencer":
        base["sequencer"] = {
            "downstream_mask": cell.seq_downstream_mask,
            "value_0": cell.seq_value_0,
            "value_1": cell.seq_value_1,
            "value_2": cell.seq_value_2,
            "value_3": cell.seq_value_3,
            "sequence_len_m1": cell.seq_sequence_len_m1,
            "index": cell.seq_index,
            "out_buffer": cell.seq_out_buffer,
            "data_valid": cell.seq_data_valid,
        }
    elif cell.core == "branch":
        base["branch"] = {
            "upstream_dir": cell.br_upstream_dir,
            "ref_value": cell.br_ref_value,
            "ref_valid": cell.br_ref_valid,
            "out_buffer": cell.br_out_buffer,
            "data_valid": cell.br_data_valid,
            "active_route": cell.br_active_route,
            "rolling_mode": cell.br_rolling_mode,
        }
    else:
        raise ValueError(f"unrecognized core {cell.core!r} -- introspection doesn't "
                          f"know this core's own field names yet")

    return base


def grid_to_dict(grid) -> Dict[str, Any]:
    """Full state of an entire `SuperGrid` -- every cell, keyed by
    `"row,col"` (JSON object keys must be strings; tuples aren't
    valid), plus the grid's own tick counter."""
    return {
        "tick_count": grid.tick_count,
        "cell_count": len(grid.cells),
        "cells": {
            f"{row},{col}": cell_to_dict(cell)
            for (row, col), cell in sorted(grid.cells.items())
        },
    }


def cell_at(grid, row: int, col: int) -> Dict[str, Any]:
    """Convenience: introspect a single cell by position, with a real,
    clear error if nothing's placed there -- rather than a bare
    `KeyError` with no context."""
    key = (row, col)
    if key not in grid.cells:
        raise KeyError(f"no cell placed at ({row},{col}) -- known positions: "
                        f"{sorted(grid.cells.keys())}")
    return cell_to_dict(grid.cells[key])


def grid_to_json(grid, **json_kwargs) -> str:
    return json.dumps(grid_to_dict(grid), **json_kwargs)


def cell_to_json(cell, **json_kwargs) -> str:
    return json.dumps(cell_to_dict(cell), **json_kwargs)
