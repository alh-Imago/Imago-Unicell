"""cell_face_budget_v1.py -- what would SIX faces cost each core's ICM v3 config? (VM/paper analysis only; no RTL is touched.)

Reads nano/icm_v3.py's CORE_FIELD_TABLES (the code that was cross-checked against the RTL, #336/#355) and, for every direction-carrying field, works out how many bits it would need if a cell had six faces
(N, S, E, W + U, D) instead of four. The new faces take the HIGH bits (bit 4 = U, bit 5 = D), so an existing four-face design keeps its meaning unchanged.

Field kinds (decided by hand from the field names and the RTL, see CELL_AUDIT_6_FACE.md):
  mask      one-hot face mask, 4 bits today        -> 6 bits   (+2)
  enc       a single face as a number, 2 bits      -> 3 bits   (+1)
  rank      one 2-bit rank PER FACE                -> two more faces, +2 bits each (+4 in all)
  already6  already 6 bits wide in the table       -> no growth

    python3 experimental/three_d/cell_face_budget_v1.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
import icm_v3 as m  # noqa: E402

LIMIT = m.CORE_CONFIG_WIDTH        # 42: the union that every core shares in the 80-bit SUPER_LATCH

# field name -> kind, per core (anything not listed carries no direction)
KIND = {
    "nano":        {"routing_mask": "already6", "cardinal_edge": "already6", "pattern_low": "mask", "pattern_equal": "mask", "pattern_high": "mask"},
    "ram":         {"downstream_mask": "mask", "upstream_mask": "mask"},
    "adder":       {"downstream_mask": "mask", "upstream_mask": "mask", "second_downstream_mask": "mask"},
    "accumulator": {"inc_dir": "mask", "dec_dir": "mask", "downstream_mask": "mask"},
    "comparator":  {"downstream_mask": "mask", "upstream_mask": "mask"},
    "latch":       {"set_dir": "mask", "clear_dir": "mask", "downstream_mask": "mask", "toggle_dir": "mask"},
    "sequencer":   {"downstream_mask": "mask"},
    "branch":      {"upstream_dir": "enc", "route_low": "mask", "route_equal": "mask", "route_high": "mask"},
    "mul":         {"downstream_mask": "mask", "upstream_mask": "mask", "second_downstream_mask": "mask"},
    "priority":    {"upstream_mask": "mask", "downstream_mask": "mask", "priority_rank_n": "rank", "priority_rank_s": "rank", "priority_rank_e": "rank", "priority_rank_w": "rank",
                    "sequence_0": "enc", "sequence_1": "enc", "sequence_2": "enc", "sequence_3": "enc"},
    "cross":       {"downstream_mask": "mask", "upstream_mask": "mask"},
    "corner":      {"downstream_mask": "mask", "upstream_mask": "mask"},
    "merge":       {"downstream_mask": "mask", "upstream_mask": "mask"},
    "div":         {"downstream_mask": "mask", "upstream_mask": "mask", "second_downstream_mask": "mask"},
}
GROWTH = {"mask": 2, "enc": 1, "already6": 0}
# priority is special: its four ranks are one 2-bit rank per face, so two more faces add two more ranks (4 bits); a sequence of up to six turns needs two more 3-bit entries
PRIORITY_RANKS_EXTRA = 4
PRIORITY_FULL_SEQUENCE_EXTRA = 6


def rows():
    out = []
    for cid, fields in m.CORE_FIELD_TABLES.items():
        name = m.CORE_NAMES[cid]
        used = max(hi for (_lo, hi) in fields.values()) + 1
        grow, notes = 0, []
        for fname, kind in KIND.get(name, {}).items():
            if kind == "rank":
                continue
            grow += GROWTH[kind]
        if name == "priority":
            grow += PRIORITY_RANKS_EXTRA
        extra_note = ""
        if name == "priority":
            extra_note = f"(+{PRIORITY_FULL_SEQUENCE_EXTRA} more if the sequenced order may run all six turns: {used + grow + PRIORITY_FULL_SEQUENCE_EXTRA} bits)"
        need = used + grow
        out.append((cid, name, used, grow, need, need - LIMIT, extra_note))
    return out


def main():
    print(f"ICM v3 core_config union = {LIMIT} bits. Bits each core uses today, the growth for six faces, and what is left over (negative = does not fit):\n")
    print(f"{'core':12s} {'uses':>5s} {'+6face':>7s} {'needs':>6s} {'spare':>6s}  verdict")
    over = []
    for cid, name, used, grow, need, over_by, note in rows():
        ok = over_by <= 0
        if not ok:
            over.append((name, over_by))
        print(f"{name:12s} {used:5d} {grow:7d} {need:6d} {LIMIT - need:6d}  {'fits' if ok else 'DOES NOT FIT by %d' % over_by} {note}")
    print()
    print("cores that do not fit the 42-bit union:", ", ".join(f"{n} ({b} over)" for n, b in over) or "none")
    worst = max(b for _n, b in over) if over else 0
    print(f"largest overflow: {worst} bits (the 80-bit SUPER_LATCH has 11 reserved bits [79:69]; the VIX carrier's core_config is 128 bits; standalone v4c cores have 64/80/128-bit words)")


if __name__ == "__main__":
    main()
