"""points.md #740: a real, small prototype loader for the hierarchical
ICM format designed in #737-#739 -- built specifically to try the
design against an actual VM run, not to be a finished, production
loader. Flattens patterns + a design map into real IcmV3Record
objects, runs the advisory connection cross-check (#739's own real
clarification: this checks placement against actual core_config bits,
it does not drive the connection), then hands the flattened records to
the real, existing VixCarrierGrid to actually execute.
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import icm_v3 as v3
from vix_carrier_automaton_v1 import VixCarrierGrid

_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def load_hierarchical(path):
    with open(path) as f:
        return json.load(f)


def flatten(doc):
    """Real, direct flattening -- no solving, no placement inference,
    matching #739's own real clarification: the design_map's own
    'at' coordinates are direct, given anchors, not derived. Returns
    (records, instance_index) where instance_index maps
    (instance_name, rel_row, rel_col) -> real (row, col), used by the
    advisory check below."""
    patterns = doc["patterns"]
    records = []
    instance_index = {}
    for placement in doc["design_map"]["placements"]:
        inst = placement["instance"]
        pat = patterns[placement["pattern"]]
        anchor_row, anchor_col = placement["at"]
        for cell in pat["cells"]:
            row = anchor_row + cell["rel_row"]
            col = anchor_col + cell["rel_col"]
            global_id = f"{inst}.{cell['cell_id']}"
            instance_index[(inst, cell["rel_row"], cell["rel_col"])] = (row, col)
            records.append(v3.IcmV3Record(
                cell_id=global_id, row=row, col=col, core=cell["core"],
                core_config=dict(cell.get("core_config", {})),
                addon_config=dict(cell.get("addon_config", {})),
                io_name=cell.get("io_name"),
            ))
    return records, instance_index


def check_connections(doc, records, instance_index):
    """points.md #739's own real, advisory cross-check -- confirms each
    declared connection's own two endpoints are (a) actually grid-
    adjacent in the stated direction, and (b) the source cell's own
    real downstream_mask and the destination's own real upstream_mask
    actually agree with the declared link. Returns a list of real,
    human-readable warning strings -- never raises, matching #590's
    own established advisory-check shape (discover_instantiated_
    modules()/check_dependency_compatibility()) directly."""
    by_pos = {(r.row, r.col): r for r in records}
    warnings = []
    for conn in doc["design_map"]["connections"]:
        f_inst, f_row, f_col, f_face = conn["from"]
        t_inst, t_row, t_col, t_face = conn["to"]
        f_pos = instance_index.get((f_inst, f_row, f_col))
        t_pos = instance_index.get((t_inst, t_row, t_col))
        if f_pos is None or t_pos is None:
            warnings.append(f"connection {conn}: real cell not found at declared position")
            continue
        if _OPPOSITE.get(f_face) != t_face:
            warnings.append(f"connection {conn}: real face mismatch -- {f_face} should pair with {_OPPOSITE.get(f_face)}, not {t_face}")
        dr = t_pos[0] - f_pos[0]
        dc = t_pos[1] - f_pos[1]
        expected = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}[f_face]
        if (dr, dc) != expected:
            warnings.append(f"connection {conn}: real placement doesn't match the declared face -- "
                             f"{f_pos} to {t_pos} is offset {(dr, dc)}, not the real {f_face}-direction offset {expected}")
        f_rec = by_pos.get(f_pos)
        t_rec = by_pos.get(t_pos)
        if f_rec is not None:
            dmask = f_rec.core_config.get("downstream_mask", [])
            if f_face not in dmask:
                warnings.append(f"connection {conn}: source cell at {f_pos} declares a link {f_face}, "
                                 f"but its own real downstream_mask is {dmask} -- doesn't actually offer that way")
        if t_rec is not None:
            umask = t_rec.core_config.get("upstream_mask", [])
            if t_face not in umask:
                warnings.append(f"connection {conn}: destination cell at {t_pos} declares a link {t_face}, "
                                 f"but its own real upstream_mask is {umask} -- doesn't actually listen that way")
    return warnings


if __name__ == "__main__":
    doc = load_hierarchical(sys.argv[1] if len(sys.argv) > 1 else
                             os.path.join(os.path.dirname(__file__), "small_relay_chain.icm-hier.json"))
    records, index = flatten(doc)
    print(f"Flattened {len(records)} real cells from {len(doc['patterns'])} patterns "
          f"({len(doc['design_map']['placements'])} placements).")

    warnings = check_connections(doc, records, index)
    if warnings:
        print(f"\n{len(warnings)} real, advisory warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("\nAdvisory connection check: all declared connections agree with the real, configured core_config bits.")

    grid = VixCarrierGrid(records)
    print(f"\nReal VM grid built: {len(grid.cells)} cells at {sorted(grid.cells.keys())}")

    input_cell = next(r for r in records if r.io_name == "input")
    output_cell = next(r for r in records if r.io_name == "output")
    print(f"\nInjecting 0x2A at the real 'input' cell ({input_cell.row},{input_cell.col})...")
    grid.inject(input_cell.row, input_cell.col, 0x2A)

    for i in range(20):
        grid.tick()
        out = grid.cells[(output_cell.row, output_cell.col)]
        if getattr(out, "ram_data_valid", False):
            print(f"Tick {i+1}: real 'output' cell now holds 0x{out.ram_data_reg:X} (valid={out.ram_data_valid})")
            break
    else:
        print("Value never reached the real output cell within 20 ticks.")

    # A real, small diff-section snapshot, per #737's own design --
    # cell_id -> current latch value, for whichever real cells hold a
    # meaningful value right now.
    diff = {}
    for r in records:
        cell = grid.cells[(r.row, r.col)]
        if r.core == "ram" and getattr(cell, "ram_data_valid", False):
            diff[r.cell_id] = f"0x{cell.ram_data_reg:X}"
    print(f"\nReal diff-section snapshot (cell_id -> current value): {diff}")
