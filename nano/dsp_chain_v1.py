"""
dsp_chain_v1.py — points.md #815: the Arria 10 DSP chain's actual topology, as a card resource: a FIXED physical
chain of up to `max_length` blocks (27 on the Arria 10 -- a spine-clock-region limit, spatial not arithmetic,
points.md #26), each block already programmed with a known operation, tapped IN and OUT at any point along it --
and, no matter how much of the chain a tap uses, a chain accepts only ONE feed at a time.

Alan (2026-09-21). Per-block latency is a CARD property (`docs/man/*.man.json`'s `device.dsp.chain`,
`card_fit_v1.dsp_chain_from_man`) and is deliberately left LOOSE here -- no default is assumed. What IS fixed,
independent of the card, is the topology this module models:
  * a chain has ~1.6k DSP UNITS on an Arria 10, but a CHAIN cannot exceed 27 blocks (the spine limit, #26);
  * "the extra fun part": you can enter the chain at ANY block and leave at ANY later block -- so a chain can be
    PROGRAMMED ONCE with a known fixed sequence of operations, and different taps use different sub-sequences of
    it without reprogramming;
  * but "you can only feed one value per chain, no matter how much you use": the WHOLE PHYSICAL CHAIN accepts a
    single feed at a time, whichever tap is chosen -- two different taps on the SAME chain cannot be fed
    concurrently. Parallelism comes from using MORE CHAINS, not more taps on one.

WHAT THIS TIES TOGETHER. A tapped segment's per-block latencies are exactly the `links` list `dsp_blackbox_v1.run_dsp`
already takes, so #814's feed-in/return monitor applies unchanged to whichever segment of whichever chain is in use --
the monitor does not care that the segment is a slice of a longer physical chain.

REAL, HONEST LIMITS. `chains_available(total_blocks, max_length)` is an UPPER BOUND (`total_blocks // max_length`):
it assumes the die's DSP blocks pack cleanly into spine regions of exactly `max_length`, which #26 does not confirm --
the real count depends on the die's actual spine-region layout, not modelled here. The single-feed exclusivity is
enforced as a plain mutex on the chain object; no RTL arbiter for entry/exit selection is simulated. Per-block latency
being "loose" means `links_for()` raises rather than inventing a number when none has been supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


class ChainBusyError(RuntimeError):
    """A chain accepts one feed at a time; a second concurrent request, at any tap, is refused."""


class ChainLatencyUnknownError(ValueError):
    """No per-block latency figure has been supplied for this chain (kept LOOSE, points.md #815); refusing to guess."""


@dataclass(frozen=True)
class ChainSegment:
    """One tap: a contiguous sub-sequence [entry, exit] of a chain's PROGRAMMED blocks."""
    chain_length: int
    entry: int
    exit: int
    ops: Tuple[str, ...]

    @property
    def span(self) -> int:
        return self.exit - self.entry + 1

    def links(self, latency_per_block: Optional[float]) -> List[float]:
        """The per-block latencies of just this segment -- feed this straight to `dsp_blackbox_v1.run_dsp(links=...)`."""
        if latency_per_block is None:
            raise ChainLatencyUnknownError("no per-block latency is set for this card (kept loose, points.md #815); "
                                           "supply one before running the black-box model")
        return [latency_per_block] * self.span


@dataclass
class DspChain:
    """A single physical chain, programmed ONCE with a known sequence of operations at fixed positions -- Alan's
    'you could program known sequences at set points and just use those'. `tap(entry, exit)` reads a sub-sequence
    without reprogramming anything. `latency_per_block` is a card property (see module docstring); pass `None`
    (the default) to keep it loose -- taps and exclusivity still work, only `ChainSegment.links()` is unavailable."""
    max_length: int
    ops: Tuple[str, ...] = ()
    latency_per_block: Optional[float] = None
    _busy: Optional[Tuple[int, int]] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.max_length < 1:
            raise ValueError("a chain needs at least one block")
        if not self.ops:
            self.ops = tuple(f"op{i}" for i in range(self.max_length))
        elif len(self.ops) != self.max_length:
            raise ValueError(f"{len(self.ops)} ops programmed but the chain has {self.max_length} blocks")

    def tap(self, entry: int, exit: int) -> ChainSegment:
        """Read the sub-sequence [entry, exit] -- ENTER at any block, LEAVE at any later-or-equal block. Reading a
        segment does not by itself claim the chain (see `feed`); it only describes what a tap there would see."""
        if not 0 <= entry <= exit < self.max_length:
            raise ValueError(f"entry={entry}, exit={exit} is not a valid tap on a {self.max_length}-block chain "
                             f"(need 0 <= entry <= exit < {self.max_length})")
        return ChainSegment(self.max_length, entry, exit, self.ops[entry:exit + 1])

    def feed(self, entry: int, exit: int) -> ChainSegment:
        """Claim the chain for a feed at this tap. Refuses if the chain is ALREADY fed at any tap -- 'you can only
        feed one value per chain, no matter how much you use': entry/exit choice never changes this."""
        if self._busy is not None:
            raise ChainBusyError(f"chain is already fed at tap {self._busy}; only one feed per chain, regardless of "
                                 f"which span is used (requested {(entry, exit)})")
        seg = self.tap(entry, exit)
        self._busy = (entry, exit)
        return seg

    def release(self) -> None:
        """The in-flight feed has returned (points.md #814's monitor sees this); the chain is free for the next tap."""
        self._busy = None

    @property
    def busy(self) -> bool:
        return self._busy is not None


def chains_available(total_blocks: int, max_length: int) -> int:
    """UPPER BOUND on independent max-length chains a card's DSP block count could hold (`total_blocks // max_length`).
    This assumes blocks pack cleanly into spine regions of exactly `max_length` -- the real count depends on the die's
    actual spine-region layout (points.md #26), which is NOT modelled here; treat this as optimistic, not authoritative."""
    if total_blocks < 0 or max_length < 1:
        raise ValueError("total_blocks >= 0 and max_length >= 1")
    return total_blocks // max_length


@dataclass
class ChainPool:
    """Several independent physical chains sharing one card's DSP budget. Alan's point made operational: to run
    two DSP operations at once you need TWO chains (or two of a pool's chains), never two taps of one chain."""
    chains: List[DspChain]

    @classmethod
    def of_max_length_chains(cls, count: int, max_length: int, latency_per_block: Optional[float] = None) -> "ChainPool":
        return cls([DspChain(max_length, latency_per_block=latency_per_block) for _ in range(count)])

    def feed_any_free(self, entry: int, exit: int) -> Tuple[int, ChainSegment]:
        """Feed the first chain that is not busy at this tap; raises if every chain is occupied."""
        for i, ch in enumerate(self.chains):
            if not ch.busy:
                return i, ch.feed(entry, exit)
        raise ChainBusyError(f"all {len(self.chains)} chains are busy; no chain is free for a tap at {(entry, exit)}")

    @property
    def free_count(self) -> int:
        return sum(1 for ch in self.chains if not ch.busy)
