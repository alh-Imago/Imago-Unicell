"""tests/vm/test_corner_tile_v1.py -- ledger #1035: the CORNER tile (core "corner", number 11, Alan 8 Oct 2026: "not just E to W and N to S but a corner type, so E can be sent N while W is sent S, and vice
versa"): two independent turns in one square. `turn` 0 pairs E-N and W-S, `turn` 1 pairs E-S and W-N; each pairing carries words in both directions, one register slice per direction of travel, ONE TICK per tile.
Proven in the generated RTL (the netlist step turns each slice into an ordinary ram relay: plain and random stalls), in FlexGrid (the VM), and in the ICM v3 codec. Requires iverilog."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
from fp_block_runner_v1 import run_rtl, run_vm  # noqa: E402
from flex_layout_v1 import Grid  # noqa: E402
import icm_v3  # noqa: E402

ARM = {"W": [(2, 0), (2, 1)], "E": [(2, 4), (2, 3)], "N": [(0, 2), (1, 2)], "S": [(4, 2), (3, 2)]}      # outer cell first, inner (next to the tile) second
PAIRS = {0: {"E": "N", "N": "E", "W": "S", "S": "W"}, 1: {"E": "S", "S": "E", "W": "N", "N": "W"}}


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    d = tempfile.mkdtemp(prefix="cornertile_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def tile(turn, ins):
    """A corner tile at (2,2); `ins` = the arms that carry words IN (their partner arms carry them OUT)."""
    g = Grid(rows=5, cols=5)
    g.add("X", 2, 2, "corner", {"turn": turn})
    outs = [PAIRS[turn][a] for a in ins]
    for arm in list(ins) + outs:
        for k, (r, c) in enumerate(ARM[arm]):
            g.add(f"{arm}{k}", r, c)
    for arm in ins:
        g.link(f"{arm}0", f"{arm}1")
        g.link(f"{arm}1", "X")
    for arm in outs:
        g.link("X", f"{arm}1")
        g.link(f"{arm}1", f"{arm}0")
    return g, outs


def streams(n, seed):
    r = random.Random(seed)
    return [[r.getrandbits(32) for _ in range(n)] for _ in range(2)]


SCENARIOS = [(0, ("W", "E")), (0, ("S", "N")), (0, ("W", "N")), (1, ("W", "E")), (1, ("N", "S")), (1, ("E", "N"))]


@pytest.mark.parametrize("turn,ins", SCENARIOS)
@pytest.mark.parametrize("mode", ["plain", "stall"])
def test_two_words_turn_independently_in_rtl(tmp, turn, ins, mode):
    g, outs = tile(turn, ins)
    S = streams(16, 3)
    ent = {f"{a}0": S[i] for i, a in enumerate(ins)}
    ex = {f"o{i}": f"{a}0" for i, a in enumerate(outs)}
    got = run_rtl(tmp, f"corner_{turn}_{''.join(ins)}_{mode}", g.records(), ent, ex, mode, settle=500)
    assert [got[f"o{i}"] for i in range(2)] == S


@pytest.mark.parametrize("turn,ins", SCENARIOS)
def test_two_words_turn_independently_in_vm(turn, ins):
    g, outs = tile(turn, ins)
    S = streams(12, 4)
    vm = run_vm(g.records(), {f"{a}0": S[i] for i, a in enumerate(ins)}, {f"o{i}": f"{a}0" for i, a in enumerate(outs)}, {}, ticks=80)
    assert [vm[f"o{i}"] for i in range(2)] == S


def test_bite_the_other_turn_sends_the_words_elsewhere(tmp):
    """The same inputs W and E: with turn 0 they leave S and N, with turn 1 they leave N and S -- so a tile built with the wrong turn delivers the two streams swapped."""
    S = streams(10, 5)
    res = {}
    for turn in (0, 1):
        g = Grid(rows=5, cols=5)
        g.add("X", 2, 2, "corner", {"turn": turn})
        for arm, ins_ in (("W", True), ("E", True), ("N", False), ("S", False)):
            for k, (r, c) in enumerate(ARM[arm]):
                g.add(f"{arm}{k}", r, c)
            if ins_:
                g.link(f"{arm}0", f"{arm}1")
                g.link(f"{arm}1", "X")
            else:
                g.link("X", f"{arm}1")
                g.link(f"{arm}1", f"{arm}0")
        res[turn] = run_rtl(tmp, f"cornerbite{turn}", g.records(), {"W0": S[0], "E0": S[1]}, {"N": "N0", "S": "S0"}, "plain", settle=500)
    assert res[0]["S"] == S[0] and res[0]["N"] == S[1]          # turn 0: W -> S, E -> N
    assert res[1]["N"] == S[0] and res[1]["S"] == S[1]          # turn 1: W -> N, E -> S


def test_one_tick_per_tile_like_a_relay():
    import flex_grid_v1 as fg

    def first_tick(turn):
        g, outs = tile(turn, ("W",))
        fgm = fg.FlexGrid(g.records(), width=32)
        fgm.inject(2, 0, 7)
        cell = fgm.cells[ARM[outs[0]][0]]
        for t in range(1, 60):
            fgm.tick()
            if cell.ram_data_valid:
                return t
    straight = Grid(rows=5, cols=5)
    for n, (r, c) in (("a0", (2, 0)), ("a1", (2, 1)), ("X", (2, 2)), ("a2", (2, 3)), ("a3", (2, 4))):
        straight.add(n, r, c, "ram")
    for a, b in (("a0", "a1"), ("a1", "X"), ("X", "a2"), ("a2", "a3")):
        straight.link(a, b)
    fgm = fg.FlexGrid(straight.records(), width=32)
    fgm.inject(2, 0, 7)
    ref = None
    for t in range(1, 60):
        fgm.tick()
        if fgm.cells[(2, 4)].ram_data_valid:
            ref = t
            break
    assert first_tick(0) == first_tick(1) == ref is not None


def test_icm_v3_codec_round_trips_the_turn_field():
    assert icm_v3.CORE_NAMES[icm_v3.SEL_CORNER] == "corner" == icm_v3.CORE_NAMES[11]
    for turn in (0, 1):
        packed = icm_v3.pack_core_config(icm_v3.SEL_CORNER, {"downstream_mask": ["s", "n"], "upstream_mask": ["w", "e"], "turn": turn})
        back = icm_v3.unpack_core_config(icm_v3.SEL_CORNER, packed)
        assert back["turn"] == turn and set(back["downstream_mask"]) == {"s", "n"} and set(back["upstream_mask"]) == {"w", "e"}
    assert icm_v3.wiring_tile_partner("corner", {"turn": 0}) == PAIRS[0] and icm_v3.wiring_tile_partner("corner", {"turn": 1}) == PAIRS[1]
    assert icm_v3.wiring_tile_partner("cross") == {"N": "S", "S": "N", "E": "W", "W": "E"}
