"""nano/corner_cell_automaton_v1.py -- ledger #1035: the CORNER wiring core in the VIX / super-cell VM (the model of fpga/verilog/corner_cell_v4.v / corner_cell_v4c.v and of core_select 11 in the carriers).

A pure-wiring tile: `turn` 0 pairs E-N and W-S, `turn` 1 pairs E-S and W-N; every pairing carries words in BOTH directions, so the cell holds four independent one-word slices, one per face a word can enter by.
A word that arrives on face X is held in slice X and offered on partner(X); when the neighbour acknowledges, the slice empties. It transforms nothing (no addon chain), costs one tick per tile.

It is a duck-typed cell in the same sense as `DspWrapperCell`: `SuperGrid` builds it for a record whose core is "corner" and gives it its own offer/drain pass (a normal SuperCell has ONE value and ONE offer
per tick; a corner has up to four, each to its own face)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from unicell_automaton_v1 import N, S, E, W, _DIRS, _DIR_BIT, _MASK4

# in-face -> out-face, per turn
PARTNER = {0: {E: N, N: E, W: S, S: W}, 1: {E: S, S: E, W: N, N: W}}


@dataclass
class CornerCell:
    row: int
    col: int
    turn: int = 0
    cell_id: int = 0
    core: str = field(default="corner", init=False)
    addon_config: dict = field(default_factory=dict)
    freeze_in: bool = False
    width: int = 32
    mask: int = 0xFFFFFFFF
    slice_value: Dict[int, int] = field(default_factory=dict)       # in-face -> held word
    pending_ack: int = 0                                            # bit per OUT face with an offer awaiting its acknowledgement

    @classmethod
    def from_record(cls, rec, width: int = 32) -> "CornerCell":
        cfg = rec.core_config or {}
        c = cls(row=rec.row, col=rec.col, turn=int(cfg.get("turn", 0)) & 1, cell_id=rec.cell_id)
        c.width, c.mask = width, (1 << width) - 1
        return c

    def partner(self, face: int) -> int:
        return PARTNER[self.turn][face]

    # ---- the interface SuperGrid.tick() uses ----
    def deliver(self, arrivals: Dict[int, int], injected: Optional[int] = None):
        """Accept the arrivals whose slice is empty (returns the SET of accepted faces, like the priority core); a full slice leaves the sender's offer standing."""
        if self.freeze_in:
            return False, None
        taken = set()
        for d, v in arrivals.items():
            if d not in self.slice_value:
                self.slice_value[d] = v & self.mask
                taken.add(d)
        return taken, None

    def is_continuously_live(self) -> bool:
        return True                      # SuperGrid's generic drain/offer passes skip it; corner_pass() below does its own

    def clear_valid_on_drain(self) -> None:
        pass

    def _offer_state(self) -> Tuple[int, bool, int]:
        return 0, False, 0

    @property
    def downstream_mask(self) -> int:
        return 0

    @property
    def data_valid(self) -> bool:
        return bool(self.slice_value)

    # ---- the corner's own pass (called by SuperGrid.tick) ----
    def drain(self, pre_pending: int) -> None:
        """Empty the slice of every offer whose acknowledgement arrived this tick."""
        for o in _DIRS:
            if (pre_pending >> _DIR_BIT[o]) & 1 and not (self.pending_ack >> _DIR_BIT[o]) & 1:
                self.slice_value.pop(self.partner(o), None)     # partner is an involution: the slice that feeds out-face o is the one entered by partner(o)

    def offers(self):
        """[(out_face, value)] for every full slice not already waiting on an acknowledgement; marks them pending."""
        out = []
        if self.freeze_in:
            return out
        for i, v in sorted(self.slice_value.items()):
            o = self.partner(i)
            if not (self.pending_ack >> _DIR_BIT[o]) & 1:
                self.pending_ack = (self.pending_ack | (1 << _DIR_BIT[o])) & _MASK4
                out.append((o, v))
        return out

    def checkpoint(self) -> dict:
        return {"row": self.row, "col": self.col, "core": "corner", "turn": self.turn, "cell_id": self.cell_id, "slice_value": dict(self.slice_value), "pending_ack": self.pending_ack}
