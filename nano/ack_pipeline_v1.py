"""
ack_pipeline_v1.py — points.md #813: the SAME ack-driven release mechanism applied to a CHAIN OF LINKS, each with its
own latency -- a DSP chain, or a BRAM read stage in front of one -- with NO fixed latency anywhere.

Alan (2026-09-21): the 3-cycle figure is from the documentation and is the same on the DSP side (`dsp_add_wrapper_v1.v`
records a real confirmed 3-cycle latency for `alterafpf_add_single`, #462, and says the event-driven handshake
"already tolerates arbitrary" pipeline latency), but it can be MORE per link in a chain -- so this mechanism can be
applied there too, it is no fixed value, and it is to be seen as the prompt for the next target to be recalled /
fed in. His rule for WHICH ack releases the next address: BRAM on two buses -> feed in; BRAM on one bus -> feed out;
DSP -> feed out.

THE MODEL. A chain of `K` links; link i holds ONE item for `latencies[i]` rounds, then offers it to link i+1, which
accepts only if it is EMPTY (the ack). The last link offers to a sink that may be stalled. A feeder recalls the next
target:
  * feeder="ack" -- released by an ack, never by a count. `release="stage_out"`: the head link's feed-out ack (it has
    passed its item on) frees the slot and the next target is fed in, so the chain PIPELINES and its rate is set by its
    slowest link. `release="tail_out"`: only when the previous RESULT has left the chain, so one item is in flight and
    the rate is the SUM of the latencies.
  * feeder="fixed" -- a counter that ASSUMES a rate and pulses a target every `fixed_period` rounds regardless. If the
    head link is still occupied the target is LOST (the counter has already moved on).

WHAT THIS DOES NOT DECIDE. Whether Alan's 'feed out' for DSP means the head link's out (`stage_out`, pipelined) or
the final result out (`tail_out`, one in flight) -- both are here, so the throughput difference can be seen; and it
does not model the DSP wrapper's real per-operation latencies (#469: 5/5/4/1/1/0), only that they differ per link.
Protocol-level, rounds not clock cycles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import List, Optional, Sequence, Tuple


@dataclass
class PipeResult:
    rounds: int
    outputs: List[Tuple[int, int]]            # (round, seq) in the order results left the chain
    lost: int                                 # targets dropped by a feeder that assumed a rate
    issued: int
    done: bool
    max_in_flight: int
    feed_rounds: List[int] = field(default_factory=list)

    @property
    def in_order(self) -> bool:
        seqs = [s for _, s in self.outputs]
        return seqs == sorted(seqs)

    @property
    def interval(self) -> Optional[float]:
        """The steady-state gap between results (median), or None with fewer than three results."""
        if len(self.outputs) < 3:
            return None
        gaps = [b[0] - a[0] for a, b in zip(self.outputs, self.outputs[1:])]
        return median(gaps)


def run_pipeline(latencies: Sequence[int], n_items: int, *, feeder: str = "ack", release: str = "stage_out",
                 fixed_period: int = 1, sink_stall: Optional[Tuple[int, int]] = None,
                 max_rounds: int = 4000) -> PipeResult:
    if feeder not in ("ack", "fixed") or release not in ("stage_out", "tail_out"):
        raise ValueError("feeder is 'ack' or 'fixed'; release is 'stage_out' or 'tail_out'")
    if not latencies or any(int(x) < 1 for x in latencies):
        raise ValueError("every link needs a latency >= 1")
    if fixed_period < 1 or n_items < 0:
        raise ValueError("fixed_period >= 1 and n_items >= 0")
    lat = [int(x) for x in latencies]
    K = len(lat)
    slots: List[Optional[List[int]]] = [None] * K            # [rounds left, seq]
    outputs: List[Tuple[int, int]] = []
    feed_rounds: List[int] = []
    issued = lost = max_in_flight = 0
    for rnd in range(max_rounds):
        for sl in slots:                                      # time passes inside every link
            if sl is not None and sl[0] > 0:
                sl[0] -= 1
        # the sink takes a finished result unless it is stalled (the ack is withheld)
        stalled = sink_stall is not None and sink_stall[0] <= rnd < sink_stall[1]
        if slots[-1] is not None and slots[-1][0] == 0 and not stalled:
            outputs.append((rnd, slots[-1][1]))
            slots[-1] = None
        # each finished link passes its item on IF the next link is empty (that is the ack), tail to head
        for i in range(K - 2, -1, -1):
            if slots[i] is not None and slots[i][0] == 0 and slots[i + 1] is None:
                slots[i + 1] = [lat[i + 1], slots[i][1]]
                slots[i] = None
        # recall the next target
        if issued < n_items:
            if feeder == "ack":
                free = slots[0] is None if release == "stage_out" else all(s is None for s in slots)
                if free:
                    slots[0] = [lat[0], issued]
                    feed_rounds.append(rnd)
                    issued += 1
            elif rnd % fixed_period == 0:
                seq = issued
                issued += 1                                    # the counter has moved on either way
                if slots[0] is None:
                    slots[0] = [lat[0], seq]
                    feed_rounds.append(rnd)
                else:
                    lost += 1                                  # a target pulsed into an occupied head link: LOST
        max_in_flight = max(max_in_flight, sum(1 for s in slots if s is not None))
        if len(outputs) + lost >= n_items and issued >= n_items and all(s is None for s in slots):
            return PipeResult(rnd + 1, outputs, lost, issued, len(outputs) == n_items, max_in_flight, feed_rounds)
    return PipeResult(max_rounds, outputs, lost, issued, len(outputs) == n_items, max_in_flight, feed_rounds)
