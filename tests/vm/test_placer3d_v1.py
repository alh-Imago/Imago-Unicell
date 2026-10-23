"""tests/vm/test_placer3d_v1.py -- ledger #1313: the automatic placer / router for the six-face toy grid (experimental/three_d/placer3d_v1.py). VM ONLY.
The placer's own claim is 'a returned layout equals its netlist by running it': these tests check the netlist refusals, the router and compaction pieces, that real layouts verify and the NOR adder is placed,
that the verification BITES (a broken layout is caught), and the composer hooks that use the placer."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ("../../experimental/three_d", "../../nano", "../../tools"):
    sys.path.insert(0, os.path.join(HERE, sub))
import composer3d_v1 as c3  # noqa: E402
import placer3d_v1 as pl  # noqa: E402

R = ("relay", None, 0, True)


def small():
    """A, B -> XOR -> shift-left 3 -> E ;  A also -> AND with B -> F  (a fan-out of A and of B, two exits)."""
    cells = {"A": R, "B": R, "X": ("gate", "XOR", 0, True), "S": ("relay", None, 3, True), "E": R, "N": ("gate", "AND", 0, True), "F": R}
    nets = [("A", "X"), ("B", "X"), ("X", "S"), ("S", "E"), ("A", "N"), ("B", "N"), ("N", "F")]
    return cells, nets


@pytest.mark.parametrize("mutate, word", [
    (lambda c, n: n.append(("A", "X")), "twice"),
    (lambda c, n: n.append(("A", "nope")), "does not exist"),
    (lambda c, n: n.append(("A", "A")), "itself"),
    (lambda c, n: n.remove(("B", "X")), "needs exactly two"),
    (lambda c, n: n.append(("E", "A")), "loop"),
    (lambda c, n: c.update(Z=R), "not joined"),
    (lambda c, n: n.append(("A", "S")), None),                      # a relay with two inputs is refused too
])
def test_netlist_refusals(mutate, word):
    c, n = small()
    mutate(c, n)
    with pytest.raises(pl.PlaceError) as e:
        pl.check_netlist(c, n)
    if word:
        assert word in str(e.value)


def test_more_than_six_connections_is_refused():
    c = {"H": R}
    n = []
    for i in range(7):
        c["o%d" % i] = R
        n.append(("H", "o%d" % i))
    with pytest.raises(pl.PlaceError, match="six faces"):
        pl.check_netlist(c, n)


def test_netlist_file_form_roundtrip_and_bad_files():
    c, n = small()
    c2, n2 = pl.parse_netlist(pl.netlist_doc(c, n))
    assert c2 == c and n2 == n
    for bad in ({}, {"format": pl.NETLIST_FORMAT, "version": 2}, {"format": pl.NETLIST_FORMAT, "version": 1, "cells": [{"name": "a"}, {"name": "a"}], "nets": []},
                {"format": pl.NETLIST_FORMAT, "version": 1, "cells": [{"name": "g", "kind": "gate", "gate": "AND", "shift": 2}], "nets": []},
                {"format": pl.NETLIST_FORMAT, "version": 1, "cells": [{"name": "a"}], "nets": [["a"]]}):
        with pytest.raises(pl.PlaceError):
            pl.parse_netlist(bad)


def test_small_netlist_is_placed_and_verified():
    c, n = small()
    d, rep = pl.place(c, n, layers=3, seed=1, keep=2)
    assert rep["verify"]["ok"] and rep["cells"] == 7 and d.layers <= 3
    assert {x["name"] for x in d.nodes.values()} >= set(c)
    assert not [p for p in d.problems() if p["level"] == "warn"]              # no dangling faces, gates have two inputs, no loop
    # and the composer's own stepper agrees with a direct sum of what was asked for
    t, v = c3.Sim(d, {d.pos_of("A"): 0xF0F0, d.pos_of("B"): 0x0FF0}, d.pos_of("E")).run_to_watch()
    assert v == ((0xF0F0 ^ 0x0FF0) << 3) & pl.M32


def test_deterministic_for_a_seed():
    c, n = small()
    a, _ = pl.place(c, n, 3, seed=4, keep=1)
    b, _ = pl.place(c, n, 3, seed=4, keep=1)
    assert a.export() == b.export()


def test_verification_bites():
    c, n = small()
    d, _ = pl.place(c, n, 3, seed=1, keep=1)
    nodes = {p: {**x, "down": set(x["down"])} for p, x in d.nodes.items()}
    assert pl.verify(nodes, c, n)["ok"]
    gate = next(p for p, x in nodes.items() if x["name"] == "X")
    nodes[gate]["gate"] = "OR"
    assert not pl.verify(nodes, c, n)["ok"]
    nodes[gate]["gate"] = "XOR"
    src = next(p for p, x in nodes.items() if x["name"] == "A")
    nodes[src]["down"] = set()                                               # cut the wire out of A
    assert not pl.verify(nodes, c, n)["ok"]


def test_compaction_removes_a_plane_of_straight_relays_and_nothing_else():
    def node(name, kind="relay", down=()):
        return {"name": name, "kind": kind, "gate": None, "shift": 0, "left": True, "down": set(down)}
    # a -> w -> b along the row axis: the relay's plane (row 1) holds only that straight relay
    nodes = {(0, 0, 0): node("a", down=[1]), (1, 0, 0): node("w_1", down=[1]), (2, 0, 0): node("b")}
    out, removed = pl.compact(nodes, {"a", "b"})
    assert removed == 1 and sorted(out) == [(0, 0, 0), (1, 0, 0)] and out[(0, 0, 0)]["down"] == {1}
    # a turning relay (it leaves sideways) must stay
    nodes = {(0, 0, 0): node("a", down=[1]), (1, 0, 0): node("w_1", down=[2]), (1, 1, 0): node("b")}
    out, removed = pl.compact(nodes, {"a", "b"})
    assert removed == 0 and len(out) == 3


def test_router_gives_every_net_its_own_squares():
    c, n = small()
    rng = pl.random.Random(1)
    pos = {"A": (1, 1, 0), "B": (1, 5, 0), "X": (3, 3, 0), "S": (5, 3, 0), "E": (7, 3, 0), "N": (3, 7, 0), "F": (5, 7, 0)}
    paths = pl.route_all(pos, n, (9, 9, 2), rng, False)
    assert paths is not None
    squares = [q for path in paths.values() for q in path]
    assert len(squares) == len(set(squares)) and not set(squares) & set(pos.values())
    for (a, b), path in paths.items():                                       # each chain starts beside a, ends beside b, one step at a time
        chain = [pos[a]] + path + [pos[b]]
        assert all(pl.manhattan(u, v) == 1 for u, v in zip(chain, chain[1:]))


def test_adder_is_placed_automatically_and_equals_addition():
    c, n = pl.adder_netlist()
    d, rep = pl.place(c, n, layers=3, seed=1, keep=1)
    assert rep["verify"]["ok"] and rep["layers_used"] <= 3 and d.layers <= 3 and rep["cells"] == 35
    assert rep["total"] == rep["cells"] + rep["relays_added"]
    res = c3.selfcheck(d)                                                    # composer check against the netlist
    assert res["ok"] and res["kind"] == "netlist"
    a, b, e = d.pos_of("A"), d.pos_of("B"), d.pos_of("E")
    for x, y in ((0xFFFFFFFF, 1), (0x12345678, 0x9ABCDEF0), (0x7FFFFFFF, 0x7FFFFFFF)):
        assert c3.Sim(d, {a: x, b: y}, e).run_to_watch()[1] == (x + y) & pl.M32


def test_one_layer_cannot_hold_the_adder_and_says_so():
    c, n = pl.adder_netlist()
    with pytest.raises(pl.PlaceError, match="no routable layout"):
        pl.place(c, n, layers=1, seed=1, keep=1, tries=3)


def test_composer_autoplace_action_and_netlist_check():
    c, n = small()
    comp = c3.Composer3D()
    st = comp.handle("autoplace", {"doc": pl.netlist_doc(c, n), "layers": 3, "keep": 1})
    assert st["ok"] and st["summary"]["cells"] >= 7 and st["meta"]["expect"] == "netlist"
    assert comp.handle("check", {})["check"]["ok"]
    with pytest.raises(c3.DesignError):
        comp.handle("autoplace", {"doc": {"format": "nope"}})
    with pytest.raises(c3.DesignError):
        comp.handle("autoplace", {"doc": pl.netlist_doc(c, n), "layers": 0})
    assert comp.design.nodes                                                  # a refused placement left the design alone
    comp.handle("undo", {})
    assert not comp.design.nodes
