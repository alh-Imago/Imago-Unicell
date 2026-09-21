"""
shared_bus_v1.py — points.md #814: ONE bus, TWO chain ends. Alan's side thought (2026-09-21): for the single-bus
units, place a PRIORITY CELL instead, so both chain ends are kept moving at the rate of the RAM.

The two ends of a chain on a shared port are the FEED-IN end (data coming from the BRAM: the read requests) and the
RETURN end (the return values written back: feed out). One transaction at a time; `service` rounds each.

WHAT THE REAL CELL DOES (measured on the VM, then read from `unicell_super_automaton_v1.py` and replicated here):
  * scheduling_mode 0 = STRICT rank. Under saturation (both ends always ready) the winner takes EVERY slot and the other
    end gets NONE -- 199 of 199, at equal ranks (the fixed N>S>E>W tie-break decides) and at unequal ranks. A priority
    cell in its default mode does NOT keep both ends moving.
  * scheduling_mode 1 = WEIGHTED round-robin -- Surplus Round Robin: every side's credit grows by its weight at each
    arbitration, the highest credit wins (ties N>S), and the winner pays the total weight of the candidates. Equal weights
    alternate ABAB; 3:1 gives exactly 75%/25%; a side that offers only occasionally is served whenever it does.
  * THE WEIGHT FIELD IS 2 BITS (0-3) and the real cell MASKS larger values silently (`& 0x3`): 5 behaves as 1, 7 as 3.
    So the achievable shares run from 1:1 up to 3:1 (75%/25%) at most, and this replica REFUSES anything larger.
  * scheduling_mode 2 = sequenced channel: fair only while BOTH ends always have something (head-of-line blocking otherwise).
The `shared_bram_arbiter_v1.v` policy -- WRITE priority, a blocked read queued -- is a strict policy: it starves the read
end whenever returns saturate, which is the opposite failure to a strict read-priority.

So the side thought holds, with one condition: the cell must be in WEIGHTED mode (1), not the default strict mode (0).

REAL, HONEST LIMITS. Rounds, not clock cycles; one queued offer per end; no RTL arbiter is simulated except by this
policy model; the weighted mode is verified against the real VM cell only under saturation (both ends always ready);
the credit accumulation of an ABSENT side (the real cell adds its weight at every arbitration whether or not it offered)
is replicated but its long-idle burst behaviour was not separately measured on the VM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# the two ends, in the cell's fixed tie-break order (N before S)
FEED_IN, RETURN = "A", "B"
_ORDER = (FEED_IN, RETURN)


class SurplusRoundRobin:
    """The priority core's arbitration, replicated line for line (unicell_super_automaton_v1.py, `_arbitrate_priority`):
    strict scores (3 - rank); weighted scores are the live credit; a fixed N>S tie-break; and in weighted mode every side's
    credit gains its weight at each arbitration while the winner pays the total weight of the CANDIDATES (floored at 0)."""

    def __init__(self, weights: Dict[str, int], mode: int = 1):
        if mode not in (0, 1):
            raise ValueError("mode is 0 (strict) or 1 (weighted round-robin)")
        for d in _ORDER:
            if not 0 <= int(weights.get(d, 0)) <= 3:
                raise ValueError(f"weight/rank {weights.get(d)} for end {d} does not fit the cell's 2-bit field (0-3); the real "
                                 f"cell MASKS it silently (5 behaves as 1, 7 as 3) -- so the largest share ratio is 3:1")
        self.rank = {d: int(weights.get(d, 0)) for d in _ORDER}
        self.mode = mode
        self.credit = {d: 0 for d in _ORDER}

    def pick(self, candidates: Sequence[str]) -> Optional[str]:
        cands = [d for d in _ORDER if d in candidates]
        if not cands:
            return None
        inc = {d: self.credit[d] + self.rank[d] for d in _ORDER}
        total_weight = sum(self.rank[d] for d in cands)
        score = {d: (inc[d] if self.mode else 3 - self.rank[d]) for d in cands}
        winner = max(cands, key=lambda d: score[d])           # max() keeps the FIRST maximal: the N>S tie-break
        if self.mode:
            for d in _ORDER:
                self.credit[d] = max(0, inc[d] - total_weight) if d == winner else inc[d]
        return winner


@dataclass
class BusResult:
    rounds: int
    served: Dict[str, int]
    sequence: str                              # who was served, in order ("A" = feed-in, "B" = return)
    max_wait: Dict[str, int]                   # the longest an offer waited, per end
    offers: Dict[str, int]

    @property
    def starved(self) -> List[str]:
        """Ends that made offers and were never served."""
        return [d for d in _ORDER if self.offers[d] > 0 and self.served[d] == 0]

    def share(self, end: str) -> float:
        tot = sum(self.served.values())
        return self.served[end] / tot if tot else 0.0


def run_bus(policy: str, rounds: int = 300, *, weights: Tuple[int, int] = (1, 1), gap_a: int = 0, gap_b: int = 0,
            service: int = 1, order: Tuple[str, str] = (FEED_IN, RETURN)) -> BusResult:
    """One shared port. `policy`: 'write_priority' (the RTL arbiter), 'read_priority', 'strict' (the priority cell, mode 0,
    weights read as ranks, LOWER = higher priority), 'weighted' (mode 1, weights are shares).
    `gap_a` / `gap_b`: an end offers again that many rounds after being served (0 = saturating: always ready)."""
    if policy not in ("write_priority", "read_priority", "strict", "weighted"):
        raise ValueError("policy is 'write_priority', 'read_priority', 'strict' or 'weighted'")
    if service < 1 or rounds < 1:
        raise ValueError("service >= 1 and rounds >= 1")
    srr = SurplusRoundRobin({FEED_IN: weights[0], RETURN: weights[1]}, mode=1 if policy == "weighted" else 0) \
        if policy in ("strict", "weighted") else None
    gaps = {FEED_IN: gap_a, RETURN: gap_b}
    next_offer = {FEED_IN: 0, RETURN: 0}
    waiting_since: Dict[str, Optional[int]] = {FEED_IN: None, RETURN: None}
    served = {FEED_IN: 0, RETURN: 0}
    offers = {FEED_IN: 0, RETURN: 0}
    max_wait = {FEED_IN: 0, RETURN: 0}
    seq: List[str] = []
    busy_until = 0
    for t in range(rounds):
        for d in _ORDER:                                     # each end raises its offer when it is due
            if waiting_since[d] is None and t >= next_offer[d]:
                waiting_since[d] = t
                offers[d] += 1
        if t < busy_until:
            continue
        ready = [d for d in _ORDER if waiting_since[d] is not None]
        if not ready:
            continue
        if policy == "write_priority":
            win = RETURN if RETURN in ready else FEED_IN
        elif policy == "read_priority":
            win = FEED_IN if FEED_IN in ready else RETURN
        else:
            win = srr.pick(ready)
        max_wait[win] = max(max_wait[win], t - waiting_since[win])
        waiting_since[win] = None
        next_offer[win] = t + service + gaps[win]
        served[win] += 1
        seq.append(win)
        busy_until = t + service
    return BusResult(rounds, served, "".join(seq), max_wait, offers)
