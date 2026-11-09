# Hex-N neural bus network: the merged design (v1, 8 Nov 2026)

Written for Alan from the simulation and synthesis work of direction doc sections 31 to 44. Every statement is tagged **[sim]** (Python model), **[rtl]** (logic written and checked clock-for-clock against the Python model in iverilog), **[synth]** (yosys count, nothing placed or timed), **[proposal]** (design intent, nothing built) or **[unknown]**. Nothing here has run on the Kintex card.

## 1. The picture in one paragraph
Sensor readings are cleaned and classed by the layer 1 detectors that already exist, and each (sensor, class) pair becomes a numbered **input line**. The lines feed a three-layer network of **small shared buses**. Each bus carries one packet (a source number) per clock; every cell on the bus has a weight for each source number in a table and adds it to its own accumulator, which leaks, fires at the cell's own threshold, then rests. A cell that fires is sent on to the next layer's buses; layer 3 also feeds back into layer 1. The set of cells that fired in layers 2 and 3 during a run is the **map**. The **judge** keeps stored maps and says which stored map, or which two, the live map is closest to. The **host** (the PC over JTAG) does all training: it writes the tables and thresholds, and reads fire counts and maps back. [proposal, parts [rtl]/[sim] as tagged below]

## 2. The parts and where each stands
| Part | What it does | State |
|---|---|---|
| Input lines | one wire per (sensor, class); an event on a line sets its pending bit | [rtl] in `hexn_bnet_net_v1` (48 lines); which sensor classes map to which lines is [unknown] |
| Source serialiser (`hexn_bnet_ser_v1`) | one per source group (the input lines, and each bus of cells): all events of a clock are taken at once, ONE is sent per clock, a rotating pointer so none starves; an event on a line still waiting is merged and counted | [rtl] cross-checked |
| Merger (inside `hexn_bnet_tbus_v1`) | in front of each bus: one small queue per feeding source group, a "does anyone here listen" bit per table row, a round-robin arbiter that passes one packet per clock | [rtl] cross-checked |
| Bus (`hexn_bnet_bus_v2`) | weight table (a row per source number, a 4-bit weight per cell), 16 cells, each with accumulator, own threshold, refractory counter, fire counter | [rtl] cross-checked against the Python bus model; the unbounded accumulator of the model is a 6-bit saturating one here (tested harmless, section 43) |
| Feedback | layer 3 groups feed layer 1 buses through the same serialiser and merger (FB=1) | [rtl] |
| Map recorder and matcher (`hexn_bnet_map_v1`) | records which layer 2 and 3 cells fired in a run; on `start` compares with each stored map (one per clock) and keeps the two best by overlap (shared over union, no division) | [rtl] cross-checked, incl. independent top-2 check |
| Weights, thresholds, pruning, map feedback training, homeostat | all on the host; the chip only holds the numbers and counts fires | [sim]; the host-side program for the chip does not exist yet |
| Controller commands | write a table row, write a threshold, clear and read fire counters, present an input stream, run N clocks, read the map, run the matcher | [proposal] (see section 4) |
| Existing base parts reused | JTAG bridge (USER2), results RAM, data RAM (a stream of input events per clock), weight store (4 sets of rows) | [file] on the card; the neural network is not in the base |

## 3. What happens in one clock (single-clock-per-hop netlist) [rtl]
1. Events on input lines set their pending bits. Each serialiser sends one pending source.
2. Each sent source is looked up (listen bit) at every bus it feeds and put in that bus's sub-queue for the sending group (dropped and counted if full).
3. Each bus's arbiter takes one packet, round robin over its sub-queues. The table row for that source is read; each cell adds its weight unless it is resting.
4. Every cell leaks (on the shared leak tick), compares with its own threshold, fires, resets and rests. Fired cells set pending bits in their group's serialiser for the next clock.
**All four steps are one combinational chain per clock in this netlist. That is fine in simulation and almost certainly too slow for the card's clock; it must be pipelined, which adds clocks of delay per hop, and the Python model has to be updated to match.** [rtl] Update, direction doc section 46: a register after every serialiser is built (`_v2` files) and the model is updated (`hexn_busnet_hw_v2.py`); the Tang Nano 20K yardstick went from 47 to about 75 MHz. [unknown: clock rate]

## 4. The host and the controller [proposal]
Training stays on the host, as agreed in sections 10 to 12: teacher mode is the only way into the saved library; live adjustments are small bounded steps within a drift ceiling; promotion after confirmed hits. For the neural network the loop per epoch is: write the tables and thresholds, present each pattern's events, run, read the map and the fire counts, compare with the target map (map feedback), nudge weights, let each cell's threshold move toward its target firing rate (self-adjusting threshold), repeat; later prune connections by weight size and keep adapting the thresholds (sections 37 to 40).
Controller commands to add to the base controller (new opcodes, same byte protocol as the existing ones): `R` write table row (layer, bus, row, 16 bits per 4 cells...), `T` write threshold, `K` clear fire counters, `k` read fire counter, `E` present events (from the data RAM, one word per clock: the line mask), `N` run n clocks, `M` read live map (128 bits), `m` write stored map, `J` start matcher and read best two. None of these are written. The weight store (4 sets) holds a trained table; loading a set into the network at the start of a session is the same as the existing `F` command with a longer row.

## 5. How this meets the other parts of the base
- **Detectors and cleaners (layer 1):** they decide what an input line means. The cleaners of sections 18 to 24 (carry, hold, per-sensor profiles) run before the lines, so the network sees a steadier class. How a class plus its burst length becomes lines is open. [unknown]
- **Batch judge:** unchanged. It scores class bins with two weight tables. The map matcher is a second, different judge (recall of a whole activity pattern). Whether the batch judge's result can be an input line, or the matcher's result a slot choice (the existing `C`/`Z` commands), is Alan's call. [open]
- **Hex arrays and the program library:** untouched. The network could choose which program to load from the matched map (the same slot mechanism the batch judge already uses). [proposal]
- **Results RAM:** a run's result (best map index, scores, lost-packet count) would be one record, like the judge's. [proposal]

## 6. Costs (synthesis counts, yosys, not placed or timed) and limits
[synth] Direction doc section 44 has the table: 4x16 depth 8 is 19.4K LUT (3.25%), 8x8 51K, map matcher under 1K; 16x4 synthesis crashed; DSP use unexplained. Not counted anywhere: pipelining, routing, the host path, the controller above.

## 7. What is decided, what is open
Decided by tests [sim]/[rtl]: shared buses with one packet per clock; a serialiser plus per-source sub-queues plus round-robin arbiter works as well as the ideal many-writes model in the toy; cells set their own thresholds; train then prune by weight size; map feedback trains the cells.
Open: how sensor classes become lines; pipelining and clock rate; the controller commands; the host program; whether feedback earns its cost (no measured benefit yet); sparse table storage for scale; fuzzy matching of two maps (best test so far 27 of 100, sections 33 and 38 not repeated with training and the self-adjusting threshold).
