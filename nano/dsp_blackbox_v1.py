"""
dsp_blackbox_v1.py — points.md #814: the DSP chain as a BLACK BOX whose latency varies, and the two monitors that keep it safe.

Alan (2026-09-21): the DSP side, from the original doc, had a variance from 0 (or 1) to OVER 8 per link in the DSP chain, so a
PROGRAMMED chain of DSP units takes a varied amount of time depending on its function and how many are linked. So BOTH the
feed in and the return to the DSP must be MONITORED, or collisions could occur INTERNALLY, away from the UniCell substrate --
and we have no control over those. And (his answer to my question): for the DSP the release is the FEED OUT -- the RETURN
values -- because the links inside a hard chain have no ack we can see.

THE MODEL. `links` gives each link's latency (0 allowed); the chain's total latency is their sum (at least 1). Inside, there is
NO backpressure: whatever is fed advances every round and emerges `total` rounds later. Two hazards exist that nothing inside
the block can prevent:
  * RETURN collision -- a result emerges while the return side still holds the previous one (its `return_slots` are all full):
    the emerging result OVERWRITES and one is lost.
  * FEED collision -- a new item is fed less than `ii` rounds after the previous one (`ii` is the initiation interval of the
    PROGRAMMED function, e.g. an accumulating cascade cannot take a new operand every round): both items are corrupted.
The MONITOR sits at the two ends the substrate CAN see -- like the sentinel, a feed-in count and a return count -- and feeds only
when (in flight + held results) < `return_slots` (a place to land it is guaranteed) and `ii` rounds have passed. It never
needs to know the latency; Little's law then sets the rate: about return_slots / total latency, capped at 1 / ii.

REAL, HONEST LIMITS. The latency profile, `ii` and the hazards are MODELLED from Alan's description (variance 0/1 to over 8 per
link; internal collisions we cannot control) -- I have not checked them against a real DSP cascade or the Quartus IP; the
wrapper RTL (`dsp_arith_wrapper_v1.v`) holds ONE operation at a time (`computing`), so a multi-item pipeline like this is the
CHAIN case Alan describes, not the single wrapper. Rounds, not clock cycles.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


@dataclass
class DspResult:
    rounds: int
    returned: List[int]                 # sequence numbers taken by the return side, in order
    fed: int
    lost_return: int                    # results overwritten because the return side was full
    lost_feed: int                      # items corrupted by feeding inside the initiation interval
    max_in_flight: int
    total_latency: int
    monitor_counts: Tuple[int, int] = (0, 0)     # (feed-in count, return count) at the end

    @property
    def collisions(self) -> int:
        return self.lost_return + self.lost_feed

    @property
    def ok(self) -> bool:
        return self.collisions == 0 and self.returned == sorted(self.returned)

    def rate(self) -> Optional[float]:
        return None if len(self.returned) < 2 else (len(self.returned) - 1) / max(1, self.rounds)


def total_latency(links: Sequence[int]) -> int:
    if not links or any(int(x) < 0 for x in links):
        raise ValueError("a chain needs at least one link and every latency >= 0")
    return max(1, sum(int(x) for x in links))


def run_dsp(links: Sequence[int], n_items: int, *, monitored: bool = True, ii: int = 1, return_slots: int = 1,
            return_period: int = 1, feed_period: int = 1, return_stall: Optional[Tuple[int, int]] = None,
            max_rounds: int = 5000) -> DspResult:
    """Feed `n_items` through the black box. `feed_period`: how often the (unmonitored) feeder pulses a target -- the RAM's rate.
    `return_period`: how often the return side can take a result (its own pace); `return_stall`: a window in which it takes none."""
    L = total_latency(links)
    if ii < 1 or return_slots < 1 or return_period < 1 or feed_period < 1 or n_items < 0:
        raise ValueError("ii, return_slots, return_period, feed_period >= 1 and n_items >= 0")
    inside: List[Tuple[int, int]] = []          # (emerges at round, seq): the hard block -- no ack, no stall
    held: List[int] = []                        # results waiting on the return side
    returned: List[int] = []
    fed = feed_count = ret_count = lost_return = lost_feed = max_in_flight = 0
    last_feed = -10 ** 9
    for t in range(max_rounds):
        # results emerge from the block whether or not anyone can take them
        for item in [x for x in inside if x[0] <= t]:
            inside.remove(item)
            if len(held) >= return_slots:
                held.pop(0)                     # the previous result is OVERWRITTEN: a collision the block cannot prevent
                lost_return += 1
            held.append(item[1])
        # the return side takes one result when it can
        stalled = return_stall is not None and return_stall[0] <= t < return_stall[1]
        if held and not stalled and t % return_period == 0:
            returned.append(held.pop(0))
            ret_count += 1
        # feed
        if fed < n_items and t % feed_period == 0:
            go = True
            if monitored:
                # the monitor's own view is the two COUNTERS it can see: fed minus returned, plus results still held
                in_flight = len(inside) + len(held)
                go = in_flight < return_slots and t - last_feed >= ii
            if go:
                seq = fed
                fed += 1
                feed_count += 1
                if t - last_feed < ii:
                    lost_feed += 1               # a PHYSICAL hazard, whoever fed it: inside the initiation interval, corrupted
                else:
                    inside.append((t + L, seq))
                last_feed = t
        max_in_flight = max(max_in_flight, len(inside) + len(held))
        if fed >= n_items and not inside and not held:
            return DspResult(t + 1, returned, fed, lost_return, lost_feed, max_in_flight, L, (feed_count, ret_count))
    return DspResult(max_rounds, returned, fed, lost_return, lost_feed, max_in_flight, L, (feed_count, ret_count))
