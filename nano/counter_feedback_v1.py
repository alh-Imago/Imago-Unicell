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


def weighted_port_arbiter(weights: Tuple[int, int] = (1, 1)) -> Callable[[bool, bool], Optional[str]]:
    """A `port_arbiter` for `run(ports=1, ...)` backed by the REAL weighted-round-robin priority cell
    (`shared_bus_v1.SurplusRoundRobin`, verified against the real VM cell, points.md #814) -- Alan's side thought:
    place a priority cell on a single-bus unit instead of hardcoded write priority, so both ends keep moving at the
    rate of the RAM. `weights = (read_weight, write_weight)`, each 0-3 (the real cell's 2-bit field; a larger value
    is refused, not silently masked, unlike the RTL -- see `shared_bus_v1.SurplusRoundRobin`)."""
    import shared_bus_v1 as SB
    srr = SB.SurplusRoundRobin({SB.FEED_IN: weights[0], SB.RETURN: weights[1]}, mode=1)

    def arbiter(read_wants: bool, write_wants: bool) -> Optional[str]:
        cands = [d for d, w in ((SB.FEED_IN, read_wants), (SB.RETURN, write_wants)) if w]
        winner = srr.pick(cands)
        return {SB.FEED_IN: "read", SB.RETURN: "write", None: None}[winner]
    return arbiter


def default_release(ports: int, resource: str = "bram") -> str:
    """Alan's rule (2026-09-21): BRAM on TWO buses releases the next address on the feed-IN ack; BRAM on ONE bus on the
    feed-OUT ack; DSP on the feed-OUT ack. Mapped here onto 'delivered' (feed in) and 'result_out' (feed out) -- my
    reading of his words, NOT yet confirmed by him."""
    if resource == "dsp":
        return "result_out"
    if resource != "bram" or ports not in (1, 2):
        raise ValueError("resource must be 'bram' or 'dsp'; ports 1 or 2")
    return "delivered" if ports == 2 else "result_out"


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
        self.reserved = 0                                # slots promised to reads still in the BRAM pipeline

    @property
    def remaining(self) -> bool:
        return self.issued < len(self.items)

    @property
    def has_credit(self) -> bool:
        return self.sentinel.diff < self.cfg.window

    @property
    def has_room(self) -> bool:
        return len(self.in_q) + self.reserved < self.cfg.in_depth


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
    lost_reads: int = 0                                       # commands lost because the interface was busy
    issue_log: List[Tuple[int, int, int]] = field(default_factory=list)      # (round, chain, seq) address released
    deliver_log: List[Tuple[int, int, int]] = field(default_factory=list)    # (round, chain, seq) data out into the chain

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
        stall_in: Optional[Dict[int, Tuple[int, int]]] = None, max_rounds: int = 600,
        credit_link: Optional[int] = None, bram_latency=0, advance: str = "ack", outstanding: int = 1,
        fixed_period: int = 1, addresses: Optional[List[List[int]]] = None, bram: Optional[Dict[int, int]] = None,
        addr_source: str = "counter", release: Optional[str] = None,
        port_arbiter: Optional[Callable[[bool, bool], Optional[str]]] = None) -> Result:
    """Run the counter mechanism. `stall_out[c] = (a, b)`: chain c cannot hand its result over in rounds [a, b) (its
    tail is blocked -- the ack side withheld). `stall_in[c]`: chain c cannot accept an item in that window.

    `credit_link=None`: each chain's feedback is its own line and instantaneous (per-chain feedback -- which is NOT
    routable past 2 chains in 2D, see stream_layout_v1). `credit_link=d`: ONE shared credit-return channel keyed by the
    gather stamp: a collect's credit reaches the counters `d` rounds later, so the window must cover the return
    latency or throughput falls. The channel is also SERIAL (one credit per round), but with ONE write per round at
    most one credit is ever generated per round, so serialisation never binds here (lifting it is an EQUIVALENT
    mutation, checked): the cost is the DELAY, paid in buffer depth, not a throughput ceiling.

    BRAM SIDE (points.md #812). `bram_latency=L` (1-3): read data appears L rounds after the command (RTL: one registered
    cycle in v1, two in v2 (#284); Alan recalls 1-3 end to end). The read INTERFACE holds `outstanding` reads at once
    (default 1: the splitter latches one). `advance="ack"`: the next address is released only when the interface has a
    free slot -- "the feed's out, here's the next address" -- `addr_counter_v1`'s `advance_en` driven by the genuine
    ack (#256), never a cycle count. `advance="fixed"`: a counter that ASSUMES the latency and pulses a command every
    `fixed_period` rounds regardless; a command arriving while the interface is busy is LOST (the single-cycle
    pulse hazard) and the counter has already moved on, so the item is a hole. `addr_source="counter"` supplies
    sequential addresses; `"ram"` a stored, arbitrary sequence (`addresses`, read from `bram`); both use the SAME control.

    NO FIXED LATENCY (points.md #813). `bram_latency` may be an int, a SEQUENCE (one entry per read, cycled) or a
    callable `(chain, seq) -> rounds`: the latency is per read, and the interface returns data IN ORDER (it never
    reorders), so a short read behind a long one waits. The ack-driven control never sees the number.

    `release` names WHAT releases the next address: "delivered" = the previous data has been delivered INTO the chain
    (local to the read side; needs no path back from the chains) and "result_out" = the previous RESULT has left the
    chain (needs the return path). It overrides `feedback`: delivered -> feedback off, result_out -> feedback on.
    `default_release(ports, resource)` is Alan's rule (2026-09-21): BRAM on two buses -> feed in, on one bus -> feed
    out, DSP -> feed out -- MAPPED onto those two events by my reading of his words, which he has not confirmed.

    `port_arbiter` (points.md #818): on a SHARED single port (`ports=1`), replace the hardcoded WRITE-PRIORITY
    decision with any `f(read_wants: bool, write_wants: bool) -> "read"|"write"|None` callable -- for instance
    `weighted_port_arbiter()`, a real weighted-round-robin priority cell (`#814`), which keeps BOTH ends moving at
    the rate of the RAM instead of starving reads whenever writes saturate. `None` (the default) reproduces the
    original write-priority behaviour EXACTLY -- `write_wants` alone decides, with no read peek computed at all."""
    if arbiter not in ("scan", "priority") or gather not in ("scan", "priority"):
        raise ValueError("arbiter and gather must be 'scan' or 'priority'")
    if ports not in (1, 2):
        raise ValueError("ports must be 1 (shared, write priority) or 2")
    if advance not in ("ack", "fixed") or addr_source not in ("counter", "ram"):
        raise ValueError("advance must be 'ack' or 'fixed'; addr_source 'counter' or 'ram'")
    if release not in (None, "delivered", "result_out"):
        raise ValueError("release must be None, 'delivered' or 'result_out'")
    if release is not None:
        feedback = release == "result_out"
    if callable(bram_latency):
        lat_of = lambda c, q: int(bram_latency(c, q))                  # noqa: E731
        has_latency = True
    elif isinstance(bram_latency, (list, tuple)):
        if not bram_latency or any(int(x) < 1 for x in bram_latency):
            raise ValueError("a latency sequence needs at least one entry and every entry >= 1")
        lat_of = lambda c, q: int(bram_latency[q % len(bram_latency)])  # noqa: E731
        has_latency = True
    else:
        if not 0 <= bram_latency <= 64:
            raise ValueError("bram_latency must be 0-64 (0 = the data is available at once)")
        lat_of = lambda c, q: int(bram_latency)                        # noqa: E731
        has_latency = bram_latency > 0
    if outstanding < 1 or fixed_period < 1:
        raise ValueError("outstanding >= 1 and fixed_period >= 1")
    if addresses is not None:
        if bram is None:
            raise ValueError("addresses need the bram contents they index")
        if addr_source == "counter":
            for a in addresses:
                if list(a) != list(range(a[0], a[0] + len(a))) if a else False:
                    raise ValueError("a counter can only supply SEQUENTIAL addresses; use addr_source='ram' for an "
                                     "arbitrary sequence")
        inputs = [[bram[x] for x in a] for a in addresses]       # the address supply reads THROUGH the BRAM
    n = len(cfgs)
    chains = [_Chain(i, cfgs[i], inputs[i]) for i in range(n)]
    total = sum(len(c.items) for c in chains)
    stall_out, stall_in = stall_out or {}, stall_in or {}

    def credit_ok(c: "_Chain") -> bool:
        return c.sentinel.diff + lag[c.idx] + pending[c.idx] < c.cfg.window

    def blocked(table, c, rnd):
        w = table.get(c)
        return bool(w) and w[0] <= rnd < w[1]

    def peek_write_grant(rnd: int) -> Optional["_Chain"]:
        """Which chain the `gather` arbiter would pick to hand a result to BRAM this round -- a pure PEEK (no state
        mutation), so it can be asked before deciding, under `port_arbiter`, whether this round's write actually
        happens. With `port_arbiter=None` this is called ONCE and its result committed unconditionally, exactly
        reproducing the original write-priority code path byte for byte."""
        want = [c for c in chains if c.out_q]
        if not want:
            return None
        if gather == "priority":
            for k in range(n):
                c = chains[(gather_ptr + k) % n]
                if c.out_q and not blocked(stall_out, c.idx, rnd):
                    return c
            return None
        for k in range(n):                                     # blocking scan: wait on the pointer's chain
            c = chains[(gather_ptr + k) % n]
            if not c.out_q:
                continue                                        # an EMPTY chain is skipped, as the RTL does
            return c if not blocked(stall_out, c.idx, rnd) else None
        return None

    def peek_read_desire(rnd: int) -> bool:
        """EXISTENCE only (points.md #818): would SOME new read command be issued this round, ignoring port
        contention? Only computed when a `port_arbiter` is actually supplied -- the default write-priority path
        never calls this, so its read_wait/target-selection accounting is untouched. A stuck tree_slot or an
        in-flight delivery is not a NEW command and does not count (neither consumes the shared port to issue one)."""
        if has_latency:
            if not ((advance == "ack") or (rnd % fixed_period == 0)):
                return False
            busy = len(read_pipe) + len(ready_q)
            if not (advance == "fixed" or busy < outstanding):
                return False
            return any(c.remaining and (not feedback or (credit_ok(c) and c.has_room
                                                          and not blocked(stall_in, c.idx, rnd))) for c in chains)
        if tree_slot is not None:
            return False                                        # delivering the stuck item needs no new command
        if pending_read is not None:
            return True                                         # the queued read is re-issued FIRST, unconditionally
        return any(c.remaining and (not feedback or (credit_ok(c) and c.has_room
                                                      and not blocked(stall_in, c.idx, rnd))) for c in chains)

    bram_out: Dict[int, Tuple[int, int, int]] = {}
    out_addr = 0
    tree_slot: Optional[Tuple[int, int, int]] = None          # (chain, value, seq) that left BRAM but cannot enter yet
    pending_read: Optional[int] = None                        # single-port: one queued read (a chain index)
    read_ptr = gather_ptr = 0
    tree_blocked = read_wait = deferred = write_delayed = 0
    read_pipe: Deque[List[int]] = deque()                    # reads in the BRAM: [ready round, chain, value, seq]
    ready_q: Deque[Tuple[int, int, int]] = deque()           # data out of the BRAM, waiting to enter its chain
    pending = [0] * n                                        # reads issued but not yet delivered, per chain
    lost_reads = 0
    issue_log: List[Tuple[int, int, int]] = []
    deliver_log: List[Tuple[int, int, int]] = []
    history: List[List[int]] = []
    credit_q: Deque[Tuple[int, int]] = deque()               # (chain, round the credit becomes visible) -- shared link
    lag = [0] * n                                            # collects whose credit has not yet returned
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
        # the shared credit-return channel delivers AT MOST ONE credit per round, once its delay has passed
        if credit_link is not None and credit_q and credit_q[0][1] <= rnd:
            lag[credit_q.popleft()[0]] -= 1
        # ---- 1. WRITE side: hand results to BRAM ---------------------------------------------------------------
        wrote = False
        grant = peek_write_grant(rnd)
        do_write = grant is not None
        if ports == 1 and port_arbiter is not None:
            # Alan's side thought (#814/#818): a WEIGHTED priority cell instead of hardcoded write priority, so
            # both ends of a shared port keep moving at the rate of the RAM. `None` (no port_arbiter) below this
            # branch reproduces write priority exactly: do_write already equals "a grant exists".
            read_wants = peek_read_desire(rnd)
            winner = port_arbiter(read_wants, do_write)
            if winner not in (None, "read", "write"):
                raise ValueError(f"port_arbiter must return 'read', 'write' or None, got {winner!r}")
            do_write = winner == "write"
        if do_write:
            if grant is not None:
                val, seq = grant.out_q.popleft()
                bram_out[out_addr] = (grant.idx, seq, val)
                out_addr += 1
                grant.collected.append(val)
                grant.sentinel.step(feed_pulse=False, collect_pulse=True, out_wrap_pulse=False, host_unfreeze_pulse=False)
                if credit_link is not None:
                    lag[grant.idx] += 1
                    credit_q.append((grant.idx, rnd + credit_link))
                gather_ptr = (grant.idx + 1) % n
                wrote = True
                done_count += 1
                progressed = True
        # ---- 2. READ side: ask BRAM for the next item ------------------------------------------------------------
        port_free = ports == 2 or not wrote
        if has_latency:
            # data whose latency has elapsed comes out of the BRAM ...
            while read_pipe and read_pipe[0][0] <= rnd:
                _, rc, rv, rs = read_pipe.popleft()
                ready_q.append((rc, rv, rs))
            # ... and is delivered into its chain, in order, one per round
            if ready_q:
                rc, rv, rs = ready_q[0]
                cc = chains[rc]
                if len(cc.in_q) < cc.cfg.in_depth and not blocked(stall_in, rc, rnd):
                    ready_q.popleft()
                    pending[rc] -= 1
                    cc.reserved -= 1
                    cc.in_q.append((rv, rs))
                    cc.sentinel.step(feed_pulse=True, collect_pulse=False, out_wrap_pulse=False, host_unfreeze_pulse=False)
                    deliver_log.append((rnd, rc, rs))
                    progressed = True
                else:
                    tree_blocked += 1                          # the head item cannot enter: it holds up the delivery path
            busy = len(read_pipe) + len(ready_q)
            attempt = (advance == "ack") or (rnd % fixed_period == 0)
            if attempt and port_free and (advance == "fixed" or busy < outstanding):
                def ok_l(c: _Chain) -> bool:
                    return c.remaining and (not feedback or (credit_ok(c) and c.has_room
                                                             and not blocked(stall_in, c.idx, rnd)))
                target: Optional[int] = None
                if arbiter == "priority":
                    for k in range(n):
                        c = chains[(read_ptr + k) % n]
                        if ok_l(c):
                            target = c.idx
                            break
                else:
                    for k in range(n):
                        c = chains[(read_ptr + k) % n]
                        if not c.remaining:
                            continue
                        if ok_l(c):
                            target = c.idx
                        else:
                            read_wait += 1
                        break
                if target is not None:
                    c = chains[target]
                    seq = c.issued
                    c.issued += 1                              # the address counter / RAM has MOVED ON either way
                    read_ptr = (target + 1) % n
                    if busy >= outstanding:
                        lost_reads += 1                        # a command pulse into a busy interface: LOST
                    else:
                        # the interface never reorders: a short read behind a long one waits for it
                        ready_at = max(rnd + lat_of(target, seq), read_pipe[-1][0] if read_pipe else 0)
                        read_pipe.append([ready_at, target, c.items[seq], seq])
                        pending[target] += 1
                        c.reserved += 1
                        issue_log.append((rnd, target, seq))
                    progressed = True
        elif True:
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
                        return c.remaining and (not feedback or (credit_ok(c) and c.has_room
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
    return Result(rounds=len(history), done=finished,
                  deadlocked=(not finished and idle_rounds >= 20 and lost_reads == 0),
                  bram_out=bram_out, per_chain=[c.collected for c in chains], collected_by_round=history,
                  tree_blocked_rounds=tree_blocked, read_wait_rounds=read_wait, reads_deferred=deferred,
                  writes_delayed_by_reads=write_delayed, sentinel_errors=errors, max_in_flight=max_in_flight,
                  totals=[len(c.items) for c in chains], lost_reads=lost_reads, issue_log=issue_log,
                  deliver_log=deliver_log)
