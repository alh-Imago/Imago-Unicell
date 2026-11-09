# Hex-N neural tile: interface and stacking (v1 draft, 9 Nov 2026)

Written for Alan after his questions of 9 Nov 16:40 and 16:42: treat the whole bus network as one tile with one hop in and out, as the UniCell builds do, and let tiles stack with feedback across layer depths if the timing passes. Tags: **[rtl]** exists and is cross-checked, **[sim]** measured in the Python model, **[card]** measured by the nextpnr estimate on the Kintex flow, **[proposal]** not built, **[unknown]**. Nothing here has run on the card.

## 1. What a tile is
The merged bus network of direction doc sections 44 to 48: 3 layers x G buses x PER cells, a serialiser per source group, a merger and arbiter in front of each bus, tables, thresholds, leaky cells, feedback layer 3 to layer 1. Reference size: G=4, PER=16, 48 input lines (192 cells). Netlist `hexn_bnet_net_v3` with `hexn_bnet_tbus_v3`, `hexn_bnet_ser_v2`, `hexn_bnet_bus_v2`. [rtl]

## 2. The edge (what the outside sees)
| Signal | Direction | Meaning | State |
|---|---|---|---|
| `clk`, `tick` | in | one clock; `tick` is the shared leak tick | [rtl] |
| `ev[47:0]` | in | one wire per input line, an event sets that line's pending bit | [rtl] |
| table write: `wr_en, wr_layer, wr_bus, wr_addr, wr_data` | in | write one table row (a 4-bit weight per cell on the bus) | [rtl] |
| threshold write: `thw_en, thw_layer, thw_bus, thw_idx, thw_val` | in | set one cell's threshold | [rtl] |
| `rclr`, `rate_layer/bus/idx` -> `rate_q` | in/out | clear, then read one cell's fire counter | [rtl] |
| `fire1, fire2, fire3` | out | fired-cell vectors every clock (layer 1, 2, 3) | [rtl] |
| `lostv`, `lost_sel` -> `lost_q` | out | merge and drop counters, read one at a time; they report 4 clocks late | [rtl] |
| map recorder / matcher (`hexn_bnet_map_v1`) | out | 128-bit map of layer 2 and 3 fires in a run; best two stored maps by overlap | [rtl], not yet wired to the net |
| `run`/`done`, window length | in/out | run N clocks then read, so the host sees a fixed-length run | [proposal] (opcodes `N`, `E`, `M`, `J` of the design doc) |

## 3. How predictable is it
- **Fixed by design:** one packet per bus per clock; one source per serialiser per clock; one added clock per hop from the register after each serialiser; same netlist, same clock count for the same inputs. [rtl]
- **Not fixed:** how long a run takes to settle depends on the input, because cells fire when they reach a threshold. In the Python model, 4x16 pipelined: first layer-3 fire about 32 clocks and 90% of the map about 50 clocks, on the toy patterns. [sim]
- **So a tile is predictable as a bounded window, not as a single latency:** the controller runs a fixed number of clocks (chosen above the 90%-of-map figure) and reads the map. Drops depend on traffic and are counted, so the host can see when a window lost too much. [proposal]

## 4. Cost and clock (Kintex, nextpnr estimates, openXC7 flow, 50 MHz target)
| Shape | Logic sites (of 597,200) | Clock estimate | Note |
|---|---|---|---|
| 2 x 8, 16 lines (v2) | 7,313 (1.2%) | 72.5 / 84.3 MHz | [card] |
| 4 x 16, 48 lines (v2) | 34,777 (5.8%) | 54.6 / 58.1 MHz | [card] |
| 8 x 8, 48 lines (v2) | 70,994 (11.9%) | 49.4 MHz, fails 50 | [card] |
v3 (no multipliers) is not yet built on the card; locally it has 0 DSP blocks against 52. By logic alone ten or more 4x16 tiles would fit; routing, clock with many tiles and the shared host path were not tested. [unknown]

## 5. Stacking tiles
- **Chain:** the next tile's input lines are fed from the previous tile's map. A tile makes up to 128 fired cells (layers 2 and 3) and the next tile has 48 lines, so a **pooling step** is needed: fold the 128 cells into 48 lines (for example OR groups of cells, or select by weight). It does not exist. [proposal]
- **Same serialiser:** a pooled line is just an event, so it enters the next tile through the same serialiser and merger and nothing inside changes.
- **Parallel:** several tiles side by side, one per sensor group, each with its own tables and map; the matcher or judge sees all of them. [proposal]
- **Feedback across depth:** today only layer 3 feeds layer 1 (FB=1), inside one tile. Generalising to layer k+2 feeding layer k (3 to 1, 4 to 2, ...) is a table-row and wiring extension: each target bus gets rows for the later layer's cell numbers and the feeding group goes through its own serialiser and merger, as layer 3 does now. Across tiles, the later tile's map would be pooled and sent back as lines of the earlier one. [proposal]
- **Open question for feedback:** in the toy it has shown no measured benefit (sections 34 to 35, 41). Stacking it deeper adds cost and delay, so it should be tested on a real task before it is built into the tile. [unknown]

## 6. What the tile edge asks of the rest of the design
1. **J1:** how a sensor class and its burst length become the 48 lines. Decides what the tile can tell apart.
2. **J5:** the controller opcodes and a host program that loads tables, runs windows and reads maps.
3. **J3 / J4:** where the matched map goes: a program slot (as the batch judge does) and a record in the results RAM.
4. **Pooling rule** between tiles (section 5).
5. **Clock:** one tile closes at about 58 MHz in the estimate; the chain of tiles needs the clock agreed first.

## 7. Next steps, in order
1. Rebuild 8x8 and 4x16 with v3 on the card flow (kit default) and read the new logic use and clock.
2. If a tile closes timing, freeze the edge of section 2 (add `run`/`done` and wire the map recorder) as `hexn_bnet_tile_v1`, with a cross-check against the Python model.
3. Write the pooling rule and test two tiles in the Python model on the toy patterns before any hardware is built for chaining.
4. Test feedback across depth in the model on real sensor data, not the toy.

## 8. The layer as the tile (Alan's proposal, 9 Nov 16:47) [proposal]
Instead of one tile for the whole network, one tile per layer, stacked. Six ports:
1. **Events in:** G parallel streams, each {valid, source number}, from the layer below (layer 1: the external input lines through its own serialiser).
2. **Events out:** G parallel streams, one per bus, from this layer's serialisers. One stream per layer would cap it at one event per clock and give up the parallel buses.
3. **Map out:** the fire vector of this layer (G x PER bits). [rtl] exists now.
4. **Feedback out:** the same event streams as port 2, sent to a second destination (an earlier layer). No new data, a second destination.
5. **Feedback in:** events from a later layer, entering as extra source groups at this layer's mergers. [rtl] layer 1 already has this from layer 3 (FB=1).
6. **Command and programming:** the existing broadcast write bus; the tile answers when `wr_layer` equals its layer number [rtl: the match exists]. It also carries the readbacks (fire counters, lost counters), so it is a two-way port. Clock and the shared leak tick are global.
The layer number is a parameter. What changes from the present netlist: source numbers become local (source group, position in the group) instead of one global numbering (`NIN + ...`), so a tile does not need to know what is above or below it. Serialiser, merger and bus modules are reused as they are; the layer module and the local numbering are new and would need the same clock-for-clock cross-check against the Python model. The register after each serialiser is already the boundary between layers.

**Matcher per layer (Alan's question, same message):** the matcher takes any map width (`NB`) and number of stored maps, so each layer tile can carry its own recorder and matcher over G x PER bits (64 for 4 x 16), under 1K LUT in the 128-bit synthesis. What it would give: an answer at each layer (layer 2's map and layer 3's map each vote), a place to see where a pattern stops matching, and a confidence signal that could drive feedback. Not known: whether matching per layer recalls better than the combined layer 2 + 3 map used so far. That is a quick test in the Python model (recall by layer against combined) and has not been run. [unknown]
