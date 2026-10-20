"""experimental_3d_nor_v2.py -- the 3D toy grid (experimental_3d_grid_v1.py, left as it is) given the two behaviours a NOR-built adder needs: a GATE cell and a SHIFT add-on. VM ONLY.

REAL, HONEST SCOPE. This is a thought experiment in software, like its parent: nothing here is grounded in RTL, no 6-port cell exists, and no claim is made about what an FPGA could hold (the nano's routing
mask is six bits wide in the RTL, but only four directions are implemented). The model is deliberately the simplest one that can carry a word-level adder:

  * six neighbours: N, S, E, W, U, D (U/D = the stacked layer). Cells have no addresses; a cell sends to its `down` faces and receives from any neighbour whose `down` points at it.
  * one tick per cell, like the standard-mode VM: what arrives in tick t is processed in tick t and offered to the neighbours for tick t+1.
  * RELAY: passes its word on, through an optional SHIFT add-on (the same left/right shift by n bits as the real add-on, zero fill, 32-bit).
  * GATE: holds the first operand, fires when the second has arrived; AND / OR / XOR / NOR / NAND / XNOR (the nano topologies 0x007 / 0x024 / 0x0BC / 0x004 / 0x027 / 0x03C). DIFFERENCE FROM THE REAL
    NANO, stated once: the real nano takes the held operand first and the flowing one a tick later, and the generator refuses two operands in the same hop. Here two operands in the SAME tick are
    accepted, because every gate used is commutative. Anything non-commutative would need the real ordering rule added.
  * No flow control (no ack): one item at a time. That is the standard-mode VM's regime too.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

N, S, E, W, U, D = range(6)
DELTA = {N: (-1, 0, 0), S: (1, 0, 0), E: (0, 1, 0), W: (0, -1, 0), U: (0, 0, 1), D: (0, 0, -1)}
OPP = {N: S, S: N, E: W, W: E, U: D, D: U}
M32 = 0xFFFFFFFF
GATES = {"AND": lambda a, b: a & b, "OR": lambda a, b: a | b, "XOR": lambda a, b: a ^ b, "NOR": lambda a, b: ~(a | b) & M32, "NAND": lambda a, b: ~(a & b) & M32, "XNOR": lambda a, b: ~(a ^ b) & M32}
TOPOLOGY = {0x007: "AND", 0x024: "OR", 0x0BC: "XOR", 0x004: "NOR", 0x027: "NAND", 0x03C: "XNOR"}

Pos = Tuple[int, int, int]      # (row, col, layer)


class Cell3:
    def __init__(self, kind="relay", gate=None, shift=0, left=True):
        self.kind, self.gate, self.shift, self.left = kind, gate, shift, left
        self.down: List[int] = []
        self.held: Optional[int] = None
        self.out: Optional[int] = None

    def shifted(self, v: int) -> int:
        if not self.shift:
            return v & M32
        return (v << self.shift) & M32 if self.left else (v >> self.shift) & M32


class Grid3:
    def __init__(self):
        self.cells: Dict[Pos, Cell3] = {}

    def add(self, pos: Pos, cell: Cell3) -> Cell3:
        if pos in self.cells:
            raise ValueError(f"square {pos} already used")
        self.cells[pos] = cell
        return cell

    def link(self, a: Pos, b: Pos) -> None:
        d = next((k for k, (dr, dc, dl) in DELTA.items() if (a[0] + dr, a[1] + dc, a[2] + dl) == b), None)
        if d is None:
            raise ValueError(f"{a} and {b} are not neighbours")
        if d not in self.cells[a].down:
            self.cells[a].down.append(d)

    def run(self, injections: Dict[Pos, int], watch: Pos, max_ticks: int = 2000):
        """Inject words at entry cells in tick 1; return (tick the watched cell first holds a word, that word). Fresh state each call."""
        for c in self.cells.values():
            c.held, c.out = None, None
        arrivals: Dict[Pos, List[int]] = {p: [v & M32] for p, v in injections.items()}
        for t in range(1, max_ticks):
            nxt: Dict[Pos, List[int]] = {}
            for pos, vals in arrivals.items():
                c = self.cells[pos]
                if c.kind == "relay":
                    for v in vals:
                        c.out = c.shifted(v)
                        self._send(pos, c, nxt)
                else:
                    for v in vals:
                        if c.held is None:
                            c.held = v
                        else:
                            c.out = GATES[c.gate](c.held, v)
                            c.held = None
                            self._send(pos, c, nxt)
            if self.cells[watch].out is not None and watch not in nxt:
                return t, self.cells[watch].out
            arrivals = nxt
            if not arrivals:
                break
        return None, None

    def _send(self, pos: Pos, c: Cell3, nxt) -> None:
        for d in c.down:
            dr, dc, dl = DELTA[d]
            nb = (pos[0] + dr, pos[1] + dc, pos[2] + dl)
            if nb in self.cells:
                nxt.setdefault(nb, []).append(c.out)
