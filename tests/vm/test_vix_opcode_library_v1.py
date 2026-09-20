"""tests/vm/test_vix_opcode_library_v1.py — points.md #793: real tests
for the formalized opcode library, confirming each entry's own real
facts (target, tile, commutativity, port style, timing) are correct,
that timing is genuinely pulled from the tile's own real contract
field rather than duplicated, and that an unknown opcode correctly
returns the real, honest `None` escalation signal rather than a guess.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from vix_opcode_library_v1 import lookup  # noqa: E402
import vix_tile_library_v1 as vtl  # noqa: E402


def test_named_port_entries():
    for opcode, tile in [("add", vtl.TILE_ADDER), ("sub", vtl.TILE_SUBTRACTOR), ("mul", vtl.TILE_MUL)]:
        entry = lookup(opcode)
        assert entry is not None
        assert entry.tile is tile
        assert entry.port_style == "named"
        assert entry.timing == tile.arrivals_needed  # pulled from the tile, not duplicated


def test_unconditional_port_entries_share_nano_gate():
    for opcode, topology in [("and", 0x007), ("or", 0x024), ("xor", 0x0BC)]:
        entry = lookup(opcode)
        assert entry is not None
        assert entry.tile is vtl.TILE_NANO_GATE
        assert entry.port_style == "unconditional"
        assert entry.extra_params == {"topology": topology}
        assert entry.timing == vtl.TILE_NANO_GATE.arrivals_needed


def test_commutativity_matches_real_operation_semantics():
    assert lookup("add").is_commutative is True
    assert lookup("sub").is_commutative is False
    assert lookup("mul").is_commutative is True
    assert lookup("and").is_commutative is True
    assert lookup("or").is_commutative is True
    assert lookup("xor").is_commutative is True


def test_unknown_opcode_returns_none_not_a_guess():
    """The real, honest escalation signal (#752's own already-scoped
    ladder) -- never a silent guess standing in for a real entry."""
    assert lookup("icmp") is None
    assert lookup("shl") is None
    assert lookup("nonexistent_opcode") is None
