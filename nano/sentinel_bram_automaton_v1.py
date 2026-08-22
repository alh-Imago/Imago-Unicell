"""
sentinel_bram_automaton_v1.py — VM model of the shared-BRAM sentinel+
gather mechanism (points.md #410-#415), item (a) of the 2026-08-20
five-item roadmap (points.md #421). First time any of this thread
exists in the VM at all — checked directly at #417, zero prior
representation.

GROUND TRUTH, read directly before writing anything here:
`sentinel_counter_v1.v` (its own real always-block logic table, not a
paraphrase), `bram_controller_v1.v`, `addr_counter_v1.v`,
`top_sentinel_gather_shared_bram_v1.v` (`#415`, proven, passes clean,
deterministic, zero regression).

ABSTRACTION LEVEL, matching `unicell_super_automaton_v1.py`'s own
established precedent exactly: an event-driven, round-stepped model —
protocol, ordering, and result correctness, not cycle-for-cycle RTL
timing. A round here corresponds to one full "chain gets its turn"
cycle in the real round-robin, not one clock edge.

THE ONE REAL PROTOCOL INVARIANT THAT MUST BE MODELED FAITHFULLY, not
simplified away, because it is the entire point of `#415`'s own real
fix: a chain must not be exposed to the gather mechanism (i.e. treated
as "ready") until its OWN current round's real capture has genuinely
completed. Modeled here as an explicit `fresh` flag per chain, reset
at the start of every round and set only once that round's own read
has completed — mirroring `h*_fresh` in the RTL precisely, not
collapsed away just because a VM read can resolve "instantly."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sentinel — a direct, faithful port of sentinel_counter_v1.v's own real
# always-block logic table. Every rule below has a specific RTL line it
# mirrors; nothing here is invented or approximated.
# ---------------------------------------------------------------------------
@dataclass
class Sentinel:
    chain_length: int = 0
    diff: int = 0
    out_frozen: bool = True          # starts FROZEN at power-on (real RTL default)
    err_negative: bool = False       # sticky
    err_overflow: bool = False       # sticky

    def step(self, feed_pulse: bool, collect_pulse: bool,
             out_wrap_pulse: bool, host_unfreeze_pulse: bool) -> None:
        # diff: +1 on feed, -1 on collect, net-zero if both same round —
        # matches the real case statement exactly (2'b10/2'b01/default).
        if feed_pulse and not collect_pulse:
            self.diff += 1
        elif collect_pulse and not feed_pulse:
            self.diff -= 1
        # feed_pulse and collect_pulse both true, or both false: no change.

        # OUT-side freeze — set on wrap, cleared only by explicit host
        # action, never self-clears.
        if out_wrap_pulse:
            self.out_frozen = True
        elif host_unfreeze_pulse:
            self.out_frozen = False

        # Error latches — sticky, host_unfreeze takes PRIORITY over the
        # ongoing condition check (the real RTL's own fixed ordering,
        # #279/#281 -- an earlier draft got this backwards and a
        # still-true condition silently re-latched the same cycle
        # unfreeze fired).
        if host_unfreeze_pulse:
            self.err_negative = False
        elif self.diff < 0:
            self.err_negative = True

        chain_length_configured = self.chain_length != 0
        double_chain_length = self.chain_length * 2
        if host_unfreeze_pulse:
            self.err_overflow = False
        elif chain_length_configured and self.diff >= double_chain_length:
            self.err_overflow = True

    @property
    def need_data_flag(self) -> bool:
        return self.out_frozen

    @property
    def results_ready_flag(self) -> bool:
        return self.out_frozen and self.diff == 0

    @property
    def safe_to_intervene(self) -> bool:
        return self.need_data_flag and self.results_ready_flag

    @property
    def err_flag(self) -> bool:
        return self.err_negative or self.err_overflow

    @property
    def freeze_out(self) -> bool:
        return self.out_frozen or self.err_negative

    @property
    def freeze_in(self) -> bool:
        return self.err_overflow


# ---------------------------------------------------------------------------
# SharedBram — one shared read/write port, matching bram_controller_v1.v
# and #412's own real "1 in, 1 out" hardware constraint: every chain
# reads through this SAME single object, never its own private copy.
# ---------------------------------------------------------------------------
@dataclass
class SharedBram:
    data: Dict[int, int] = field(default_factory=dict)

    def write(self, addr: int, value: int) -> None:
        self.data[addr] = value

    def read(self, addr: int) -> int:
        return self.data.get(addr, 0)


# ---------------------------------------------------------------------------
# SentinelChain — one chain's own local address counter, running
# accumulator (event-counting, matching accumulator_cell_v1.v's own real
# behavior confirmed via sim trace -- it counts ARRIVALS, it does not sum
# their payload), sentinel, and per-round freshness gate.
# ---------------------------------------------------------------------------
@dataclass
class SentinelChain:
    name: str
    base_addr: int          # #409's own block-partitioned addressing: this
                             # chain's fixed offset into the ONE shared address
                             # space
    wrap_at: int             # local address wraps 0..wrap_at, matching
                              # addr_counter_v1.v's own WRAP_AT parameter
    bram: SharedBram
    local_addr: int = 0
    accumulator: int = 0
    fresh: bool = False       # #415's own real fix: gates readiness, reset
                               # every round, set only once THIS round's own
                               # capture has completed
    sentinel: Sentinel = field(default_factory=Sentinel)

    def __post_init__(self) -> None:
        self.sentinel.chain_length = 1

    def take_turn(self) -> None:
        """One round-robin visit. Mirrors #413-#415's real sequence:
        issue the read for this chain's current local address (if not
        frozen), capture the result, mark fresh, then -- and only then,
        matching "data in then confirm, not ready then capture" -- offer
        the freshly captured value to be gathered, gated on `fresh`."""
        self.fresh = False   # reset at the start of every round (RTL: on
                              # col_program_done for this chain's own turn)

        if self.sentinel.freeze_out:
            return   # this chain has wrapped and is genuinely done; a
                     # real round-robin visit to a frozen chain does
                     # nothing, matching the RTL's own shared_read_trigger
                     # gating on !this_chain_frozen

        global_addr = self.base_addr + self.local_addr
        _ = self.bram.read(global_addr)   # real read through the ONE shared port
        self.accumulator += 1             # event-counting, not payload-summing
        self.fresh = True                 # THIS round's own capture has now
                                           # genuinely completed

        out_wrap_pulse = (self.local_addr == self.wrap_at)
        # advance (matching addr_counter_v1.v: wrap to 0 at WRAP_AT, else +1)
        self.local_addr = 0 if out_wrap_pulse else self.local_addr + 1

        # Only a FRESH chain may be gathered -- the real invariant #415
        # closed. feed_pulse/collect_pulse are modeled as happening
        # together in the same round once `fresh` permits it (the VM's
        # own event-driven abstraction; the RTL's multi-cycle offer/ack
        # handshake collapses to one step here, matching how
        # unicell_super_automaton_v1.py already collapses its own
        # multi-cycle offer/ack sequences).
        feed_pulse = self.fresh
        collect_pulse = self.fresh
        self.sentinel.step(feed_pulse, collect_pulse, out_wrap_pulse,
                            host_unfreeze_pulse=False)

    def unfreeze(self) -> None:
        self.sentinel.step(feed_pulse=False, collect_pulse=False,
                            out_wrap_pulse=False, host_unfreeze_pulse=True)


# ---------------------------------------------------------------------------
# Round-robin orchestrator — matches the real RTL's own `seq_index`
# arbitration: exactly one chain's turn per round, cycling in order.
# ---------------------------------------------------------------------------
def run_shared_bram_gather(chains: List[SentinelChain], max_rounds: int = 200) -> int:
    """Runs round-robin turns until every chain reports safe_to_intervene
    (matching #415's own real self-test condition), or max_rounds is hit.
    Returns the number of rounds actually run."""
    for chain in chains:
        chain.unfreeze()

    for round_idx in range(max_rounds):
        chains[round_idx % len(chains)].take_turn()
        if all(c.sentinel.safe_to_intervene for c in chains):
            return round_idx + 1
    return max_rounds


def _self_test() -> None:
    """Reproduces #415's own real 3-chain result at the VM level for the
    first time: 3 chains, WRAP_AT=3 (4 values each), block-partitioned
    addressing (0-3/4-7/8-11), all reaching safe_to_intervene, zero
    errors."""
    bram = SharedBram()
    for i in range(12):
        bram.write(i, 100 + i)   # matches #415's own real preload values

    chains = [
        SentinelChain("H1", base_addr=0, wrap_at=3, bram=bram),
        SentinelChain("H2", base_addr=4, wrap_at=3, bram=bram),
        SentinelChain("H3", base_addr=8, wrap_at=3, bram=bram),
    ]

    rounds = run_shared_bram_gather(chains)

    ok = True
    for c in chains:
        if c.accumulator != 4:
            print(f"FAIL: {c.name} accumulator={c.accumulator}, expected 4")
            ok = False
        if not c.sentinel.safe_to_intervene:
            print(f"FAIL: {c.name} never reached safe_to_intervene")
            ok = False
        if c.sentinel.err_flag:
            print(f"FAIL: {c.name} sentinel err_flag set")
            ok = False

    if ok:
        print(f"PASS: all 3 chains reached count=4, safe=1, err=0 "
              f"in {rounds} rounds (matches #415's own real RTL result)")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    _self_test()
