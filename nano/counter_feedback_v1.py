"""
counter_feedback_v1.py — points.md #810: the COUNTER mechanism WITH FEEDBACK, at protocol level.

Alan (2026-09-21): the counters need some degree of feedback -- which limits the chain options (probably to 2) but
allows flexibility and a degree of control over stalled chains, and lets RAM requests avoid stalling
THEMSELVES on a loaded chain: backpressure stalls any call to a stalled chain until it clears, via the ACK side.
And the priority cell must be used, or one part can stall and stop the whole chain. Start with the two-port
version, then the single (shared) port.

WHAT THE REAL v3 BUILD DOES (top_sentinel_gather_shared_bram_v3.v, read before modelling): each chain has its own
address counter (`addr_counter_v1`, block-partitioned addresses); a collector scans the chains round-robin and
its ready is asserted ONLY for the active chain, and only once that chain's own capture is `fresh` -- the scan
advances on THAT chain's ack; and the collector's ack ("collect_pulse") ALSO PACES THE NEXT FEED. That is the
feedback loop: roughly one item in flight per chain, gated by the ack. And the scan waiting on the active
chain's ack is exactly where head-of-line blocking lives.

THE THING GROUNDED ON THE REAL VM (test_counter_feedback_v1): a priority cell in PRIORITY mode passes the live
source when the other source never offers; in SEQUENCER mode (fixed order) it passes NOTHING -- the stalled part
stops everything. So merges must use the priority cell.

WHAT IS MODELLED (rounds, not clock cycles -- the abstraction `sentinel_bram_automaton_v1` states for itself):
  * per chain: an address counter over its own block of inputs, a leaf buffer (`in_depth`), a chain that takes
    `latency` rounds per item, an output buffer (`out_depth`), and a SENTINEL (feed at the head, collect at the tail).
  * FEEDBACK ON: a chain is asked for an item only if the sentinel shows credit (in flight < `window`), its leaf
    buffer has room AND it is READY to accept (the ack side), so a request can never land on a full chain and the tree is never held.
    FEEDBACK OFF: the counter free-runs; an item for a full chain sits IN THE TREE and blocks every read behind it
    ("RAM requests stalling themselves"), and the sentinel latches overflow.
  * READ ARBITER: "scan" = a strict round-robin that WAITS on the current chain (a fixed-order sequencer);
    "priority" = the priority cell: serve whoever is ready, losers wait pending without blocking anyone.
  * WRITE SIDE: the same two choices for the gather.
  * PORTS: 2 = independent read and write ports; 1 = ONE shared port, WRITE PRIORITY, a blocked read QUEUED as a single
    outstanding request (`shared_bram_arbiter_v1.v`: never dropped, re-issued when no write contends).

REAL, HONEST LIMITS
  * The limit "probably to 2 chains" is Alan's estimate and is NOT derived here: the model runs any N, and I have not
    identified what physically fixes it (a face budget at the interface cell is a guess, not something checked).
  * Protocol-level only; no address-counter or arbiter RTL is simulated; the chains are abstract (a function and a
    latency), not the placed grid layouts of `stream_layout_v1`.
  * The host stall/refill lifecycle and the open empty/full status signal (#257) are not modelled.
"""
from __future__ import annotations

import os
import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sentinel_bram_automaton_v1 import Sentinel  # noqa: E402


@dataclass
class ChainCfg:
    latency: int = 2         # rounds an item spends inside the chain
    in_depth: int = 1        # leaf buffer between the tree and the chain head
    out_depth: int = 1       # buffer at the chain tail
    window: int = 1          # credits: max items in flight (sentinel diff) when feedback is on


class _Chain:
    def __init__(self, idx: int, cfg: ChainCfg, items: List[int]):
        self.idx, self.cfg, self.items = idx, cfg, list(items)
        self.in_q: Deque[Tuple[int, int]] = deque()
        self.pipe: Optional[List[int]] = None            # [rounds left, value, seq]
        self.out_q: Deque[Tuple[int, int]] = deque()
        self.sentinel = Sentinel(chain_length=max(1, cfg.window), out_frozen=False)
        self.issued = 0                                  # the address counter: next item to request
        self.collected: List[int] = []

    @property
    def remaining(self) -> bool:
        return self.issued < len(self.items)

    @property
    def has_credit(self) -> bool:
        return self.sentinel.diff < self.cfg.window

    @property
    def has_room(self) -> bool:
        return len(self.in_q) < self.cfg.in_depth


@dataclass
class Result:
    rounds: int
    done: bool
    deadlocked: bool
    bram_out: Dict[int, Tuple[int, int, int]]                 # address -> (chain, seq, value)
    per_chain: List[List[int]]                                # values collected, per chain, in order
    collected_by_round: List[List[int]]                       # per round: how many each chain has collected so far
    tree_blocked_rounds: int                                  # rounds a stuck item held up EVERY read
    read_wait_rounds: int                                     # rounds a blocking scan waited on one chain
    reads_deferred: int                                       # single-port: reads pushed back behind a write
    writes_delayed_by_reads: int                              # must be 0: writes have priority
    sentinel_errors: List[str]
    max_in_flight: List[int]
    totals: List[int] = field(default_factory=list)

    def finished_round(self, chain: int) -> Optional[int]:
        """The first round by which `chain` had collected ALL its results (None if it never did)."""
        for r, row in enumerate(self.collected_by_round):
            if row[chain] >= self.totals[chain]:
                return r
        return None

    def progress_between(self, chain: int, start: int, end: int) -> int:
        """How many results `chain` collected in rounds [start, end)."""
        end = min(end, len(self.collected_by_round))
        if start >= end:
            return 0
        return self.collected_by_round[end - 1][chain] - (self.collected_by_round[start - 1][chain] if start > 0 else 0)


def run(cfgs: List[ChainCfg], inputs: List[List[int]], func: Callable[[int], int], *, arbiter: str = "priority",
        gather: str = "priority", feedback: bool = True, ports: int = 2,
        stall_out: Optional[Dict[int, Tuple[int, int]]] = None,
        stall_in: Optional[Dict[int, Tuple[int, int]]] = None, max_rounds: int = 600) -> Result:
    """Run the counter mechanism. `stall_out[c] = (a, b)`: chain c cannot hand its result over in rounds [a, b) (its
    tail is blocked -- the ack side withheld). `stall_in[c]`: chain c cannot accept an item in that window."""
    if arbiter not in ("scan", "priority") or gather not in ("scan", "priority"):
        raise ValueError("arbiter and gather must be 'scan' or 'priority'")
    if ports not in (1, 2):
        raise ValueError("ports must be 1 (shared, write priority) or 2")
    n = len(cfgs)
    chains = [_Chain(i, cfgs[i], inputs[i]) for i in range(n)]
    total = sum(len(c.items) for c in chains)
    stall_out, stall_in = stall_out or {}, stall_in or {}

    def blocked(table, c, rnd):
        w = table.get(c)
        return bool(w) and w[0] <= rnd < w[1]

    bram_out: Dict[int, Tuple[int, int, int]] = {}
    out_addr = 0
    tree_slot: Optional[Tuple[int, int, int]] = None          # (chain, value, seq) that left BRAM but cannot enter yet
    pending_read: Optional[int] = None                        # single-port: one queued read (a chain index)
    read_ptr = gather_ptr = 0
    tree_blocked = read_wait = deferred = write_delayed = 0
    history: List[List[int]] = []
    max_in_flight = [0] * n
    idle_rounds = 0
    done_count = 0

    def try_deliver(item: Tuple[int, int, int], rnd: int) -> bool:
        ci, val, seq = item
        c = chains[ci]
        if c.has_room and not blocked(stall_in, ci, rnd):
            c.in_q.append((val, seq))
            c.sentinel.step(feed_pulse=True, collect_pulse=False, out_wrap_pulse=False, host_unfreeze_pulse=False)
            return True
        return False

    for rnd in range(max_rounds):
        progressed = False
        # ---- 1. WRITE side: hand results to BRAM ---------------------------------------------------------------
        wrote = False
        want = [c for c in chains if c.out_q]
        if want:
            grant: Optional[_Chain] = None
            if gather == "priority":
                for k in range(n):
                    c = chains[(gather_ptr + k) % n]
                    if c.out_q and not blocked(stall_out, c.idx, rnd):
                        grant = c
                        break
            else:                                              # blocking scan: wait on the pointer's chain
                for k in range(n):
                    c = chains[(gather_ptr + k) % n]
                    if not c.out_q:
                        continue                               # an EMPTY chain is skipped, as the RTL does
                    grant = c if not blocked(stall_out, c.idx, rnd) else None
                    break
            if grant is not None:
                val, seq = grant.out_q.popleft()
                bram_out[out_addr] = (grant.idx, seq, val)
                out_addr += 1
                grant.collected.append(val)
                grant.sentinel.step(feed_pulse=False, collect_pulse=True, out_wrap_pulse=False, host_unfreeze_pulse=False)
                gather_ptr = (grant.idx + 1) % n
                wrote = True
                done_count += 1
                progressed = True
        # ---- 2. READ side: ask BRAM for the next item ------------------------------------------------------------
        port_free = ports == 2 or not wrote
        if tree_slot is not None:                              # an item is stuck in the tree: it blocks EVERY read
            if try_deliver(tree_slot, rnd):
                tree_slot = None
                progressed = True
            else:
                tree_blocked += 1
        else:
            target: Optional[int] = None
            from_queue = False
            if ports == 1 and pending_read is not None:
                target, from_queue = pending_read, True         # the queued read is re-issued FIRST, never dropped
            else:
                def ok(c: _Chain) -> bool:
                    # FEEDBACK = the sentinel's credit, the leaf buffer's room, AND the chain's READY (its ack side):
                    # a chain that is not accepting must not be asked, or the item would sit in the tree.
                    return c.remaining and (not feedback or (c.has_credit and c.has_room
                                                             and not blocked(stall_in, c.idx, rnd)))
                if arbiter == "priority":                       # the priority cell: serve whoever is READY
                    for k in range(n):
                        c = chains[(read_ptr + k) % n]
                        if ok(c):
                            target = c.idx
                            break
                else:                                           # strict scan: WAIT on the current chain, skip finished ones
                    for k in range(n):
                        c = chains[(read_ptr + k) % n]
                        if not c.remaining:
                            continue
                        if ok(c):
                            target = c.idx
                        else:
                            read_wait += 1                      # head-of-line: everyone behind this chain waits
                        break
            if target is not None:
                if port_free:
                    if from_queue:
                        pending_read = None
                    c = chains[target]
                    item = (target, c.items[c.issued], c.issued)
                    c.issued += 1
                    read_ptr = (target + 1) % n
                    if not try_deliver(item, rnd):
                        tree_slot = item
                    progressed = True
                elif pending_read is None:
                    pending_read = target                       # the shared port is busy with a write: QUEUE the read
                    deferred += 1
        # ---- 3. the chains work -------------------------------------------------------------------------------
        for c in chains:
            if c.pipe is not None:
                c.pipe[0] -= 1
                if c.pipe[0] <= 0 and len(c.out_q) < c.cfg.out_depth:
                    c.out_q.append((func(c.pipe[1]), c.pipe[2]))
                    c.pipe = None
                    progressed = True
            if c.pipe is None and c.in_q:
                val, seq = c.in_q.popleft()
                c.pipe = [c.cfg.latency, val, seq]
                progressed = True
            max_in_flight[c.idx] = max(max_in_flight[c.idx], c.sentinel.diff)
        history.append([len(c.collected) for c in chains])
        if done_count >= total:
            break
        stalling = any(blocked(stall_out, i, rnd) or blocked(stall_in, i, rnd) for i in range(n))
        idle_rounds = 0 if (progressed or stalling) else idle_rounds + 1
        if idle_rounds >= 20:
            break

    errors: List[str] = []
    for c in chains:
        c.sentinel.step(feed_pulse=False, collect_pulse=False, out_wrap_pulse=True, host_unfreeze_pulse=False)
        if c.sentinel.err_flag:
            errors.append(f"chain {c.idx}: sentinel error (negative={c.sentinel.err_negative}, overflow={c.sentinel.err_overflow})")
    finished = done_count >= total
    return Result(rounds=len(history), done=finished, deadlocked=(not finished and idle_rounds >= 20),
                  bram_out=bram_out, per_chain=[c.collected for c in chains], collected_by_round=history,
                  tree_blocked_rounds=tree_blocked, read_wait_rounds=read_wait, reads_deferred=deferred,
                  writes_delayed_by_reads=write_delayed, sentinel_errors=errors, max_in_flight=max_in_flight,
                  totals=[len(c.items) for c in chains])
