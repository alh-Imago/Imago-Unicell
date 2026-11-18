# Timing without interrupts: measured determinism in a NOR-universal fabric (working draft)

Working draft, started 17 Nov 2026, last updated 18 Nov 2026 · Alan (A. Hill). Parked in the repo on 18 Nov 2026; the live copy was written as a Claude document. Not submitted, not peer reviewed. The "Why it should hold" section is still a placeholder.

On a Tang Nano 20K, a UniCell job took exactly 131 clocks alone, beside 8 storm lanes, and as one of four copies, and the design's own response to an input edge was 8 clocks (296 ns) on every one of 4,096 edges; an ESP32 answering the same kind of edge storm by interrupt had a worst answer of 8.4 to 9.2 µs (22 µs with heavier handler work) against about 2 µs on average, and left up to 3 of 4,096 edges unanswered.

## Claim and scope

The claim is narrow and measurable: an event arriving at one part of the design does not change the timing of unrelated work, and independent jobs run side by side without slowing each other. It is not claimed that only UniCell can do this. FPGAs, dataflow machines and hardware event systems share these features (test plan v3, #1177).

Limits to state up front:

- Exact cycle-for-cycle timing is expected only for the sub (v4s) cell family, which has no acknowledge. Flex cells use a valid/ack handshake, so back-pressure can move their timing. The 131-clock job below is a flex lane run stall-free; under back-pressure the honest statement is "same result, bounded timing".
- Shared resources still queue: the exit port, the serial line and the SPI link (#1183).
- Every result is one card, one 27 MHz clock, one run per case.

## Why it should hold

UniCell has no instruction fetch, no decode pipeline, no program counter and no separation between compute and memory. A program is a network of cells, and a result appears at a known address after a fixed number of clocks. An input is a value arriving on a cell. It does not interrupt anything, because no shared processor exists for it to take time from. The prediction follows directly: work on other cells cannot be delayed by it.

This section is a placeholder to expand from the architecture sections of the main paper, with the cell's two-arrival firing described once there and cited here.

## Evidence on the Tang Nano 20K

Every timing figure below is a clock count on the board's 27 MHz clock (1 clock = 37.04 ns), and each equals the simulation.

| Test | What was varied | Result | Entry |
| --- | --- | --- | --- |
| Isolation | A 64-word job alone, beside 4 storm lanes, beside 8 storm lanes | 131 clocks in all three, words correct | #1183 |
| Copies | Four independent copies of the job at once | 131 clocks each | #1183 |
| Shared port | 1, 2, 4 and 8 lanes behind one input and output | 131 clocks each; no speed-up, the single port is the limit | #1183 |
| Response time | Edge on an input pin, 2,048 rising + 2,048 falling, design idle and busy (24 load lanes) | Design's own part: 8 clocks (0.296 µs), minimum = maximum, spread 0 | #1208 |
| Cross-talk | A second input changing at random moments (1,741 one-input events, 307 two-input events) | Still 8 clocks on every event, idle and busy | #1210 |

The storm in the isolation test was present: the corrected build is 8,123 LUT4 against 6,429 for the first build, whose storm lanes synthesis had deleted, so that first card run (#1182) was not counted (#1183). The idle and busy lines in the response tests match digit for digit because both builds use the same stimulus seed and the design is clocked and deterministic. That shows the load added no delay; it is not a second independent confirmation (#1208).

## Contrast: the same edge storm on an ESP32

The Tang generated random-timed edges and acted as the stopwatch. An ESP32 (240 MHz) answered each edge from an interrupt handler while a second pin sent a storm of about 15,650 edges a second (the ESP32's own counter read 15,565 to 15,728), each costing the handler 6 µs of busy work, or 20 µs in the heavy case. Each build timed 4,096 edges.

| ESP32 case | Answer time, average / worst | Edges left unanswered, of 4,096 | Its own compute job | Entry |
| --- | --- | --- | --- | --- |
| Quiet, compute loop on | 1.90 / 4.11 µs | 0 | 199 jobs/s | #1220 |
| Storm, 6 µs work, loop on | 2.14 / 8.44 µs | 0 | 172 jobs/s (about 14% fewer) | #1220 |
| Storm, 6 µs work, loop on, repeat | 2.19 / 9.19 µs (rising edges) | 3 | about 14% fewer | #1221 |
| Storm, 6 µs work, loop off | 2.30 / 7.78 µs | 3 | not applicable | #1219 |
| Storm, 20 µs work, loop on | 5.07 / 22.11 µs | 1 | about 128 jobs/s (about 35% fewer) | #1223 |

Across the quiet runs no edge went unanswered. In the storm runs between 0 and 3 did, and whether an unanswered edge was a missed interrupt or a late answer is not settled: with the 20 µs work the ESP32 counted exactly the 4,112 edges sent while the Tang saw one unanswered (#1223).

A separate test (#1213) ran 1, 2, 4 and 8 threads of the same job on the ESP32. On one core the watched job took 2.01, 4.01 and 8.02 times as long and throughput stayed at 226 to 227 jobs/s; with two cores throughput doubled to 453 jobs/s and then stayed flat. The watched job's time varied by whole scheduler slices, about 1 ms with 2 threads and about 3 ms with 4 or 8, against a 5 µs spread alone.

The point of the contrast is the variation under load, not the speed: the interrupt answer is faster than the design's input path in absolute terms (next section).

## The price: input sampling at 1 ms

The constant 8 clocks is the design's own part, from the last sample tick to the result. In direct sensor mode the unit samples an input pin once per millisecond, so the whole path from an edge to the result ranged from 18 to 26,973 clocks (0.667 µs to 999.0 µs) for rising edges, an average near 0.5 ms (#1208). That spread is the sampling window and nothing else, since the part after it is constant. An ESP32 interrupt answered in about 2 µs, so in absolute terms the interrupt path is far faster; what the design offers is a constant, not a short, latency.

Sampling also sets what the input can see. A pulse shorter than 1 ms is caught only in proportion to its width, as expected for a sampler that looks once per millisecond (#1225, 512 pulses per width, idle and busy identical):

| Pulse width | Caught, of 512 |
| --- | --- |
| 2 ms and 1 ms | 512 (100%) |
| 750 µs | 380 (74.2%) |
| 500 µs | 264 (51.6%) |
| 100 µs | 42 (8.2%) |
| 20 µs | 9 (1.8%) |
| 2 µs and 1 µs | 0 |

Every width was within 1.4 standard deviations of the binomial expectation, width divided by 1 ms. The ESP32's pulse-width limit has not been measured, so no comparison number is given. Whether the unit can sample faster than once per millisecond was not examined.

## Repeat runs on the Kintex card

On 18 November 2026 the Tang's four-lane add tree (13 cells) was run on the Kintex-7 card (XC7K480T, 50 MHz clock), restarted and read over JTAG only. The card counts clocks from restart to the last result itself.

- **2,000 restarts.** Every run gave 6 results, signature 7FEF5298, last word 7FFFFEAA, and the last result at clock 1562 (31.2 µs at 50 MHz). The run number rose by exactly one at every restart (1,999 steps of one), so each read was a new run. These are the figures the Tang gave in #1251.
- **250 freeze-and-release cycles.** Freezing at clock 60, 346, 700, 1000 and 1400, 50 times each, then releasing: every run finished with the same result and the same last-result clock of 1562. Each freeze held the count it was asked for.

This is a different job from the 131-clock isolation job, and it has no neighbouring load and no outside input, because the card has no pins and the JTAG reads come after a run ends. It shows that repeat runs and a stop-and-resume give identical clock counts on this chip; it does not show response to an outside event. Source: kit `fpga/kintex7_tests/k7_timing_repeat/` on branch `kintex-timing-repeat-kit`. Run on Alan's bench; the two full logs (free_2000.log, freeze_50.log) were re-checked independently and give the same result. A ledger entry is still to be added.

## What this does not show

- **One board.** The timing and ESP32 measurements are on the Tang Nano 20K at 27 MHz, one card, one run per case (#1208). The Kintex result is a different job and says nothing about input response.
- **One small job.** The isolation job is 64 words through an adder with a constant 5. The storm lanes share the clock, the reset and the report line with it, not cells (#1183).
- **Shared resources.** The exit port, serial line and SPI link do queue, and the shared-port test shows the port as the limit, not a gain (#1183).
- **Two inputs at most.** The cross-talk test used two inputs; other designs and other loads were not tried (#1210).
- **Not an independent clock.** The 8 clocks are measured against a tick counter copied into the test top. The pin's own synchroniser is inside the edge-to-result time, not the constant part (#1208).
- **Matching runs are not independent runs.** Idle and busy builds use the same stimulus seed, so identical lines show no added delay, not a second confirmation (#1208, #1210).
- **Small ESP32 counts.** Between 0 and 3 unanswered edges in five storm runs, one board, one scheduler setting; the cause of an unanswered edge is not established (#1221, #1223).
- **Simulation, not prediction.** The card equals the simulation. That the compiler predicted the 131 clocks before simulation was not checked here.

## What changed from the June 2026 plan

The June plan (PAPERS.md, 15 June 2026) listed three pieces of evidence. Two do not hold up as stated, and the blocker on the third is gone.

- **"Predicted depths match silicon (31/31 silicon tests)" on the iCEBreaker.** The 31 tests in the old main draft (section 4.2) are functional checks of gate functions, modes and reset on 4 cells. The draft lists no predicted-versus-measured depth, so those tests are not timing evidence and are not used here.
- **"LBM 1,714 and LIF 353 predicted ticks per update, VM-confirmed."** The figure 1,714 appears in the archived Trix code as the compiler's critical-path depth for the lattice Boltzmann collision step. The 353 figure was not found by a text search of that code, and the VM confirmation was not re-checked. The Trix family is archived, so these are left out until rerun.
- **"Arria 10 blocked."** The timing claim no longer depends on it: the evidence above was taken on the Tang Nano 20K.

## Before submission

Open work, in the order it would strengthen the paper. Items 1 to 3 are proposals, not planned runs.

1. **Repeat on the Kintex card.** Done on one chip for the Tang add tree (section above). Still open: a second chip, and a Kintex job like the 131-clock isolation job with load lanes running beside it.
2. **Compiler prediction against the card.** Show that the compiler's own depth for the 131-clock job equals the card, so the claim covers prediction and not only simulation.
3. **More runs.** Repeat loads and more cases. The design is deterministic, so repeats test the board, not chance.
4. **ESP32 open questions.** Log the answer writes to tell a missed interrupt from a late one (#1223), repeat the storm cases, and run the ESP32 pulse-width test (#1225).
5. **Exact timing in the sub family.** The cycle-exact claim is expected only there (test plan v3); the measured job was a flex lane.

**Constraint on the Kintex card.** Unlike the Tang, the Kintex card has no exposed pins, so an outside device such as the ESP32 cannot feed it live edges or a data stream, and the ESP32 contrast cannot be repeated there. It also has no PCIe interface, so real throughput cannot be measured. Every count or test on that card must therefore be taken on the card itself and read back over JTAG. This fits the clock-count test in item 1 (a counter on the card, read over JTAG), but it limits the Kintex to determinism of clock counts, not input response or throughput.

**Deferred to fuller hardware.** The tests that need pins or a host link are left until the bench changes: a card with exposed pins, or a working PCIe path, in a host with enough memory. That means input response from an outside device on the Kintex, real throughput, the ESP32 contrast on the same board, a second board for repeats, and the Arria 10 PCIe side. Until then the paper's claim rests on the Tang Nano 20K measurements and, once item 1 is done, clock-count determinism on the Kintex read over JTAG.

Venue, from the June plan: a short paper or workshop in systems, real-time or embedded, six to eight pages.

## Sources

Ledger entries in `points/points_13_1037-1235.md`; result files are in the repository under `fpga/`.

- #1177, #1180, #1182, #1183: test plan and the parallel and isolation tests (`docs/NO_INTERRUPT_PARALLEL_TEST_PLAN_v3.md`, `fpga/board_tests_parallel_v2/results_card_20261017/`)
- #1206, #1207, #1208: response-time test (`fpga/board_tests_latency_v2/card_run_18oct/`)
- #1209, #1210: second-input cross-talk (`fpga/board_tests_latency3/card_run_18oct/`)
- #1211 to #1223: ESP32 contrast (`fpga/board_tests_c1/`, `fpga/board_tests_c1_v2/`)
- #1224, #1225: pulse width at the input (`fpga/board_tests_pulse/card_run_18oct_a/`)
- June 2026 plan: `PAPERS.md` and the old main draft in the archived `old_papers_drafts.onion` and `archeology/shared/docs/software/PAPER_DRAFT.md`; archived Trix code in `old_trix_domain_family.onion`
