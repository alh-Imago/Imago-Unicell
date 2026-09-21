"""
dsp_chain_placement_v1.py — points.md #816: PLACE `dsp_chain_v1.DspChain` objects onto a card's REAL DSP sites,
respecting the spine-region chain-length limit (#26).

WHY THE CASCADE NEEDS NO FABRIC ROUTING (the key fact this module rests on). Arria 10 DSP blocks cascade over
`chainin[63:0]`/`chainout[63:0]` -- a DEDICATED HARD-SILICON connection between physically adjacent blocks in the
same column (#26's "Bridge shape" section). This is unlike the mux/combiner trees (`#808`), whose adjacency the
fabric ROUTER must find: a DSP cascade's adjacency is fixed by the die layout before any placement happens. So
"placing a chain" is SITE SELECTION -- choosing a run of `max_length` (or fewer) physically consecutive DSP sites
in one column -- not a routing problem. What DOES still need the fabric (a bridge tile, per `#25`'s own "HARD_MUL
boundary tile", NOT yet built) is feeding the entry tap's operand in and reading the exit tap's result out.

THE SPINE-REGION CAVEAT, STATED PLAINLY. The MAN file records DSP sites as one per die y-unit in a column's
range, but NOT where the spine-region BOUNDARIES themselves fall within that range. This module's proxy --
group by column, then chunk the column's contiguous run into pieces of at most `max_length` -- assumes chain
breaks land exactly on `max_length`-multiples, which #26 does not confirm; the real boundaries could split a
column differently. Chunking is what's verifiable today; real spine geometry is an open item (see HONEST LIMITS).

WHAT THIS PRODUCES. `place_chains(target, chain_card)` returns one `PlacedChain` per column-chunk: its physical
block positions (die-column order, block 0 first) and a bound `dsp_chain_v1.DspChain` of that length. Taps and the
single-feed exclusivity are exactly `DspChain.tap()`/`.feed()` (`#815`) -- nothing new there; this module only
answers WHERE each block of a chain physically sits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import card_fit_v1 as C
import dsp_chain_v1 as DC

Pos = Tuple[int, int]


@dataclass
class PlacedChain:
    column: int
    positions: List[Pos]          # block 0 .. block N-1, in physical (die) order
    chain: DC.DspChain

    @property
    def length(self) -> int:
        return len(self.positions)

    def position_of(self, block: int) -> Pos:
        if not 0 <= block < self.length:
            raise ValueError(f"block {block} is outside this {self.length}-block chain")
        return self.positions[block]

    def tap_positions(self, entry: int, exit: int) -> List[Pos]:
        """The physical positions a tap [entry, exit] actually occupies -- for a fit report or a placer to consume."""
        self.chain.tap(entry, exit)                     # validates entry/exit; raises the same way DspChain does
        return self.positions[entry:exit + 1]


def group_by_column(sites: List[Pos]) -> Dict[int, List[Pos]]:
    """Sites are one per die y-unit within a column's y-range and already contiguous there (checked against the
    real Mustang MAN file: column x=26 gives 223 sites, rows 1..223, contiguous; the truncated column x=96 gives
    167, rows 1..167). Returns each column's sites sorted by row (physical, die-adjacent order)."""
    cols: Dict[int, List[Pos]] = {}
    for r, c in sites:
        cols.setdefault(c, []).append((r, c))
    for c in cols:
        cols[c].sort()
        rows = [r for r, _ in cols[c]]
        if rows != list(range(rows[0], rows[0] + len(rows))):
            raise ValueError(f"DSP sites in column {c} are not contiguous by row -- the column-grouping proxy for "
                             f"spine regions (points.md #816) assumes contiguity and does not hold here")
    return cols


def place_chains(target: C.CardTarget, chain_card: DC.DspChainCard) -> List[PlacedChain]:
    """One PlacedChain per `max_length`-sized (or shorter, for a column's remainder) contiguous run in each DSP
    column of `target`. `chain_card` normally comes from `card_fit_v1.dsp_chain_from_man` for the SAME card --
    passing one built from a different card's MAN file gives placements with no die-geometry meaning."""
    if "dsp" not in target.sites or not target.sites["dsp"]:
        raise ValueError(f"target {target.name!r} has no DSP sites to place chains on")
    if chain_card.max_length < 1:
        raise ValueError("max_length must be >= 1")
    placed: List[PlacedChain] = []
    for col, sites in sorted(group_by_column(target.sites["dsp"]).items()):
        for i in range(0, len(sites), chain_card.max_length):
            run = sites[i:i + chain_card.max_length]
            placed.append(PlacedChain(col, run, DC.DspChain(len(run), latency_per_block=chain_card.latency_per_block)))
    return placed


def chain_count(target: C.CardTarget, chain_card: DC.DspChainCard) -> int:
    """How many chains `place_chains` would actually produce -- the REAL count from real site geometry, to compare
    against `dsp_chain_v1.chains_available`'s optimistic `total_blocks // max_length` upper bound."""
    total = 0
    for sites in group_by_column(target.sites["dsp"]).values():
        total += -(-len(sites) // chain_card.max_length)          # ceil: a short final chunk still counts as a chain
    return total
