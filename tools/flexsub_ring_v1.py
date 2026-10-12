"""tools/flexsub_ring_v1.py -- ledger #1109: closed rings (genuine feedback) for the flex family's generator.

Two small pieces the generator calls when rings are allowed:

add_host_entries(...)    A cell that is the ENTRY of a ring has two kinds of source: the ring's own feedback (an internal neighbour) and the host (an upstream face that leaves the grid, the
                         cell's io_name). The generator knows only one kind per cell, so the host side is turned into an ordinary entry cell: a synthetic ram `<cell>__in` placed on the face that
                         leaves the grid, carrying the io_name, sending into the cell. The cell then has two ordinary sources (the host and the feedback) which the flex family already builds as a
                         merge. Nothing else changes.
back_edges(order_seed, srcs_of)
                         The edges that close a cycle (found by a depth-first walk that starts at the entries). Timing / operand-order analysis is done on the graph WITHOUT them; the wiring keeps them.
"""
DELTA = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def _faces(v):
    if isinstance(v, (list, tuple, set)):
        return [str(x).upper() for x in v]
    return [str(v).upper()] if v else []


def add_host_entries(cells, edges, inputs, outputs, ext_out):
    """Graph-level. A RAM that carries an io_name, has at least one internal source and no face leaving the grid is a ring ENTRY whose host side is the VM's `inject` (the cordic's z_input on
    `s0.merge`). Hardware needs a port for it, so the host becomes an ordinary entry cell H (io_name moves to it) and the ring's feedback and the host meet in a new merge relay M placed in
    front of the entry: stream source x -> M <- H, M -> entry. The entry itself keeps its other sources (a constant reference stays where it was). One extra hop on the ring; the VALUES are
    unchanged (the handshake absorbs timing). Returns (cells, edges, inputs, outputs, added) with the dicts copied."""
    cells = dict(cells)
    edges = list(edges)
    inputs = {k: {r: list(v) for r, v in d.items()} for k, d in inputs.items()}
    outputs = {k: list(v) for k, v in outputs.items()}
    added = []
    for c in sorted(cells):
        r = cells[c]
        srcs = [(q, f) for lst in inputs.get(c, {}).values() for q, f in lst]
        if r.core != "ram" or not r.io_name or r.io_name == "result" or not srcs or ext_out.get(c):   # `result` marks where the ring is OBSERVED (the generator's own convention), not where it is entered
            continue
        const = {q for q, _ in srcs if (cells[q].preload_value is not None or (cells[q].core_config or {}).get("fixed_mode")) and not inputs.get(q)}
        stream = [(q, f) for q, f in srcs if q not in const]
        if len(stream) != 1:
            continue                                       # not a single-stream entry: leave it to the generator's own refusals
        x, face = stream[0]
        m_id, h_id = f"{c}__ringmerge", f"{c}__in"
        cfg_m = {"upstream_mask": ["N", "S"], "downstream_mask": ["E"], "fixed_mode": 0}
        cfg_h = {"downstream_mask": ["E"], "fixed_mode": 0}
        mk = lambda cid, core_config, io: type(r)(cell_id=cid, row=r.row, col=r.col, core="ram", core_config=core_config, addon_config={}, io_name=io, preload_value=None)
        cells[m_id], cells[h_id] = mk(m_id, cfg_m, None), mk(h_id, cfg_h, r.io_name)
        cells[c] = type(r)(cell_id=c, row=r.row, col=r.col, core=r.core, core_config=dict(r.core_config or {}), addon_config=r.addon_config, io_name=None, preload_value=r.preload_value)
        role = next(k for k, lst in inputs[c].items() if (x, face) in lst)
        inputs[c][role] = [(m_id, face) if q == x else (q, f) for q, f in inputs[c][role]]
        inputs[m_id] = {"in": [(h_id, "N"), (x, "S")]}
        inputs[h_id] = {}
        outputs[x] = [m_id if q == c else q for q in outputs.get(x, [])]
        outputs[h_id] = [m_id]
        outputs[m_id] = [c]
        edges = [((e[0], m_id) + tuple(e[2:])) if (e[0] == x and e[1] == c) else e for e in edges]
        edges.append((h_id, m_id, "E", "in", ()))
        edges.append((m_id, c, "E", role, ()))
        added.append((c, m_id, h_id))
    return cells, edges, inputs, outputs, added


def back_edges(entries, srcs_of):
    """Depth-first from `entries` along consumer edges; returns {(src, dst)} for every edge that points back at a cell on the current path."""
    cons = {}
    for dst, ss in srcs_of.items():
        for s in ss:
            cons.setdefault(s, []).append(dst)
    back, state = set(), {}
    def go(c):
        state[c] = 1
        for d in sorted(cons.get(c, [])):
            if state.get(d) == 1:
                back.add((c, d))
            elif d not in state:
                go(d)
        state[c] = 2
    for e in entries:                            # in the order given: the caller puts the host entries first
        if e not in state:
            go(e)
    for c in sorted(srcs_of):                    # anything not reachable from an entry (a pure ring): walk it too
        if c not in state:
            go(c)
    return back
