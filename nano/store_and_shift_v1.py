"""
store_and_shift_v1.py — points.md #826: the STORE-AND-SHIFT stage `fixed_structures_v1.BusPlan` has flagged as
needed (and, honestly, unbuilt) since `#808`, whenever a card's bus is narrower than the 32-bit value it must
carry: `Assembler` reconstructs a value from its `beats` narrow chunks on the read side; `disassemble()` splits a
value into those same chunks on the write side. Built directly on `BusPlan`, not a separate model of the bus.

THE BIT CONVENTION -- a genuine design choice, stated plainly, not assumed. This models a classic serial
shift-in accumulator: each new chunk shifts what has already arrived toward the HIGH end and ORs the new chunk
into the newly-freed LOW bits (`acc = (acc << data_bits) | chunk`) -- so the FIRST chunk received ends up most
significant, the LAST chunk received least significant, mirroring how a real SIPO (serial-in, parallel-out)
shift register accumulates bits over successive clocks. `disassemble()` is built to invert this exactly: it
splits the value from the HIGH end down, so `Assembler` fed `disassemble(v, plan)`'s own output, in order,
always reconstructs `v` exactly -- proven directly (`test_store_and_shift_v1.py`), not just documented.

THE UNEVEN CASE, worked out precisely. `beats * data_bits` need not equal `word_bits` (32) exactly -- e.g. a
26-bit bus with 5 feeds (`#808`'s own worked example) gives `data_bits=18`, `beats=2`, so `2*18=36` bits of
capacity for a 32-bit value: 4 bits of genuine SLACK. Rather than padding the LAST chunk (which would shift
which physical bits of the value land where), the slack lands as leading zero bits on the FIRST chunk only --
exactly what `value >> ((beats-1)*data_bits)` naturally produces for a value narrower than the chunk can hold,
with every OTHER chunk carrying a full, untouched `data_bits`-wide slice. No bits of the original value are
ever reordered or dropped.

REAL, HONEST LIMITS
  * Protocol-level: a chunk arrives and is fed to `Assembler.feed()`; nothing here models the BRAM read/write
    timing (`counter_feedback_v1`) or the routing byte (`fixed_structures_v1`) that would carry it in a real
    deployment -- this is purely the bit-level assemble/disassemble machinery `BusPlan` already names as
    missing, not a re-implementation of the surrounding protocol.
  * `beats=1` (no narrowing needed) is handled as a trivial one-chunk case, not a special code path -- the same
    logic degenerates correctly rather than being special-cased.
  * No RTL for this stage exists (`BusPlan`'s own honest note stands); this is a software model of what such a
    stage would need to do, useful for verifying the bit arithmetic before any hardware design is attempted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import fixed_structures_v1 as FS


class StoreAndShiftError(ValueError):
    """A chunk, or a sequence of chunks, does not fit the plan this assembler/disassembler was built for."""


def _mask(bits: int) -> int:
    return (1 << bits) - 1


def disassemble(value: int, plan: FS.BusPlan) -> List[int]:
    """Split `value` (a `plan.word_bits`-wide unsigned value) into `plan.beats` chunks of `plan.data_bits` bits
    each, high chunk first -- the exact inverse of `Assembler`'s own accumulation rule. Refuses a value that does
    not fit in `word_bits` bits, rather than silently truncating it."""
    if not 0 <= value <= _mask(plan.word_bits):
        raise StoreAndShiftError(f"value {value} does not fit in {plan.word_bits} bits")
    return [(value >> ((plan.beats - 1 - k) * plan.data_bits)) & _mask(plan.data_bits) for k in range(plan.beats)]


@dataclass
class Assembler:
    """Accumulates `plan.beats` chunks, in order, into the original `plan.word_bits`-wide value. `feed()` returns
    True once `done` -- the caller does not need to count beats itself, matching a real receiver that only knows
    it has enough once the counter it is built around says so."""
    plan: FS.BusPlan
    _acc: int = field(default=0, init=False)
    _received: int = field(default=0, init=False)

    @property
    def done(self) -> bool:
        return self._received >= self.plan.beats

    @property
    def value(self) -> int:
        if not self.done:
            raise StoreAndShiftError(f"only {self._received} of {self.plan.beats} beats received -- no value yet")
        return self._acc

    def feed(self, chunk: int) -> bool:
        """Shift in one more chunk (high end grows). Refuses a chunk wider than `plan.data_bits`, or a chunk fed
        after the value is already complete -- a real accumulator has nowhere to put an unexpected extra beat."""
        if self.done:
            raise StoreAndShiftError(f"already has all {self.plan.beats} beats -- an extra chunk arrived")
        if not 0 <= chunk <= _mask(self.plan.data_bits):
            raise StoreAndShiftError(f"chunk {chunk} does not fit in {self.plan.data_bits} bits")
        self._acc = ((self._acc << self.plan.data_bits) | chunk) & _mask(self.plan.word_bits)
        self._received += 1
        return self.done

    def reset(self) -> None:
        """Ready for the next value on the same bus -- a real accumulator is reused round after round, not
        rebuilt each time."""
        self._acc = 0
        self._received = 0


@dataclass
class TransferResult:
    rounds: int
    value: int
    chunks: List[int]


def simulate_transfer(value: int, plan: FS.BusPlan) -> TransferResult:
    """One value, `plan.beats` rounds, one chunk per round -- the real, measurable LATENCY COST `BusPlan`'s own
    note already names ('~beats x the latency'), demonstrated here as elapsed rounds, not just asserted."""
    chunks = disassemble(value, plan)
    asm = Assembler(plan)
    rounds = 0
    for c in chunks:
        rounds += 1
        asm.feed(c)
    if not asm.done:
        raise StoreAndShiftError("disassemble() did not produce enough chunks for this plan -- an internal error")
    return TransferResult(rounds, asm.value, chunks)
