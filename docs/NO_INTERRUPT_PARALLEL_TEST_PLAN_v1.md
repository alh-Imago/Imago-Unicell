# Test plan: no interrupts, and parallelism, shown by measurement

*Written 17 Oct 2026 (ledger #1177) from the discussion of 16 Oct. A PLAN only: nothing here has been built or run, and no result exists.*

## The claim being tested

Other systems share these features (FPGAs in general, dataflow machines, hardware event systems), so the claim is NOT "only UniCell can do this". It is narrower and measurable:

> An event arriving at one part of the design does not change the timing of unrelated work, because there is no shared processor for the event to take time from. And independent jobs run side by side without slowing each other.

## Honest limits to state up front

- **Flex cells use a valid/ack handshake**, so back-pressure can move their timing. Exact cycle-for-cycle determinism is only expected for the **sub (v4s) family**, which has no acknowledge. Flex runs should be reported as "unchanged result and bounded timing", not "identical to the cycle", unless measured to be.
- **Shared resources still queue**: the exit port, the UART and the SPI link. The tests must find where that starts and report it.
- The existing board wrapper adds random exit stalls on purpose, and its pass rule ignores the `last=` field for that reason. The timing tests below therefore need a **stall-free run or a fixed stall pattern**, so a change in timing can only come from the other load.

## Tests

| # | Test | What is measured | Pass looks like | Needs |
|---|---|---|---|---|
| T1 | Isolation: a long job (the divider stream) alone, then with a second part of the design hit by a heavy event storm | Cycle count and words of the long job | Same words; same cycle count (sub) or bounded change (flex) | Tang only |
| T2 | Response time: input edge to output change, many events, rest of design idle then busy | Minimum and maximum latency | Minimum equals maximum (no jitter) | Real input pins or the ESP32 link; a way to time it (the Tang's own counter over UART, or a logic analyser) |
| T3 | Cross-talk: several inputs driven at once | Whether one input's activity changes another's response time | No change | Sensor pins / ESP32 |
| T4 | Scaling: 1, 2, 4, 8 copies of the same job side by side | Total time for all copies | Flat while work done grows (the VM's sequential model grows with the number of copies) | Tang only |
| T5 | Where it stops | Throughput when copies share the exit port or UART | The point where queueing starts, reported | Tang only |
| C1 | Contrast: the same events on the ESP32 alone with an interrupt handler and a compute loop | Its jitter and slow-down under the same storm | A measurable difference, or none (reported either way) | ESP32 (expansion parts ordered 15 Oct) |

T1, T4 and T5 need only what is already on the bench, so they can run before the ESP32 expansion parts arrive.

## What is reused

The self-checking board wrapper and its UART line (`UCT <name> res= n= e= bad= to= last= sig=`), the group-run scripts, the ICM-to-Verilog path, and the sanity check (#1100), where the clocks counted on the card equalled the simulation exactly. Direct sensor mode (Tang pins 72/71, no ESP32, about 1 ms sampling) and the wiring in `docs/WIRING_REFERENCE_v1.md` cover T2 and T3; those pins are not yet checked on the board.

## Before building

Agree the pass criteria with Alan, decide the timing method for T2, and check the sensor pins on the header.
