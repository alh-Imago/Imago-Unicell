"""
unicell_gate_core.py — the genuinely shared gate-computation core, extracted
from unicell_v3.py (2026-08-04) as the first concrete step toward the
shared-core-plus-cell-specific-shells split (Alan's own framing).

WHY THIS EXISTS: docs/shared/SYSTEM_MECHANICS.md verified directly against
both fpga/verilog/unicell64_v3.v (FULL cell) and
fpga/verilog/unicell_stripped_v1.v (STRIPPED/nano cell) that the NOR-tree
gate computation and the topology decode table are BYTE-IDENTICAL, gate for
gate, in both RTL files — this is not an approximation, it's the same logic.
Everything else about how a cell decides WHAT becomes A and B (addressing,
cardinal wires, ready/ack, freeze) genuinely differs between the two cells
and stays in their own separate VM modules — only the part proven identical
lives here.

Moved unchanged from unicell_v3.py, not rewritten — same discipline as
moving Verilog: mechanical extraction, not a reimplementation, so there is
nothing new to get wrong. unicell_v3.py re-exports these names so every
existing caller and the full 216-test regression suite keeps working
unchanged (verified after the move, not just assumed).
"""

from __future__ import annotations

# ── Topology decode table (cmd_latch[9:0] on both cells — verified
# identical bit position in docs/shared/SYSTEM_MECHANICS.md §1) ──────────────
# Verified against unicell64_v3.v lines ~724-753 (the g0..g9 NOR-decomposition
# and the case(topology) table), NOT reconstructed from memory. Every gate is
# built from repeated NOR — this is the actual thesis of the project
# ("topology is computation"), so the VM computes it the SAME way the
# silicon does rather than shortcutting with Python's native ~/&/|/^ on the
# final result. Test vectors A=0xDEADBEEF, B=0xCAFEBABE match the RTL's own
# verification comment (line 736).

TOPO_PASS_A = 0x000   # identity(A) — default/fallback
TOPO_NOT_A  = 0x001
TOPO_NOT_B  = 0x002   # real, decoded, but no dedicated preset opcode (points.md #56)
TOPO_NOR    = 0x004
TOPO_AND    = 0x007
TOPO_ZERO   = 0x030
TOPO_XNOR   = 0x03C
TOPO_OR     = 0x024
TOPO_NAND   = 0x027
TOPO_PASS_B = 0x02C
TOPO_ONE    = 0x0B0
TOPO_XOR    = 0x0BC

_MASK32 = 0xFFFFFFFF


def _gate_tree(a: int, b: int) -> dict:
    """The exact NOR-decomposition from unicell64_v3.v lines 724-733, and
    (byte-identical, verified) unicell_stripped_v1.v lines ~482-491."""
    g0 = (~(a | a)) & _MASK32                    # NOT(A)
    g1 = (~(b | b)) & _MASK32                    # NOT(B)
    g2 = (~(g0 | g1)) & _MASK32                  # AND(A,B) = NOR(NOT A, NOT B)
    g3 = (~(g2 | g2)) & _MASK32                  # NAND(A,B)
    g4 = (~(a | b)) & _MASK32                    # NOR(A,B)
    g5 = (~(g4 | g4)) & _MASK32                  # OR(A,B)
    g6 = (~(a | g4)) & _MASK32                   # NOR(A, NOR(A,B))
    g7 = (~(b | g4)) & _MASK32                   # NOR(B, NOR(A,B))
    g8 = (~(g6 | g7)) & _MASK32                  # XNOR(A,B)
    g9 = (~(g8 | g8)) & _MASK32                  # XOR(A,B)
    return {"g0": g0, "g1": g1, "g2": g2, "g3": g3, "g4": g4,
            "g5": g5, "g6": g6, "g7": g7, "g8": g8, "g9": g9}


def compute_gate(topology: int, a: int, b: int) -> int:
    """
    computed_output — matches the case(topology) table at unicell64_v3.v
    lines 740-753 exactly (and unicell_stripped_v1.v lines ~493-511, byte-
    identical), including its fallback-to-PASS_A default for any topology
    code not in the table (same as the RTL's `default:` arm on both cells).
    a = input_val (A, the stored/first-arrival operand)
    b = second_val (B, the live/second-arrival trigger operand)
    """
    a &= _MASK32
    b &= _MASK32
    g = _gate_tree(a, b)
    return {
        TOPO_PASS_A: a,
        TOPO_PASS_B: b,
        TOPO_NOT_A:  g["g0"],
        TOPO_NOT_B:  g["g1"],
        TOPO_NOR:    g["g4"],
        TOPO_AND:    g["g2"],
        TOPO_OR:     g["g5"],
        TOPO_NAND:   g["g3"],
        TOPO_XOR:    g["g9"],
        TOPO_XNOR:   g["g8"],
        TOPO_ZERO:   0,
        TOPO_ONE:    _MASK32,
    }.get(topology, a)  # default: fallback PASS(A), matches RTL exactly
