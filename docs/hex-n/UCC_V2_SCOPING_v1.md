# Hex-N UCC v2: scoping (1 Nov 2026, 21:30; direction added 2 Nov 05:45)

Status: **SCOPING ONLY. Nothing here is built, decided or measured unless it says so.** Every item marked PROPOSAL is for Alan to accept, change or drop.

## 0. DIRECTION from Alan, 2 Nov 05:45 (readings taken; supersedes parts of sections 3 and 4 below)
- v1 is **chaining**. v2 of the large Hex-N UCC should follow the **UniCell neighbour-shell scheme** (each cell has its own shell and knows its neighbours; paths are made by writing routing config, as with `routing_mask`), so it allows **routing**, not just chaining. The neighbour awareness is the UniCell side, not the hex-grid side; v2 should not be tied to a hex layout.
- **One cell kind instead of separate cores: a LOOK-UP-TABLE cell.** "Similar idea, just simpler." So the maths cells (section 3, kinds B and C) are not separate hardware; function comes from a table loaded into the cell. My reading, to be confirmed.
- Notes on that reading (mine, not decided): a table cell is simple and uniform, and the chip's block RAM is a natural place for the tables (the Tang has 46 blocks, 11 used by v1; the Hex-N judge's tanh already is a 512-entry table). It suits small inputs well (binning, curves, activation functions, small-digit logic). A table cannot hold wide arithmetic directly (two 18-bit operands would need 2^36 entries), so adds and compares on wide words would be built by slicing into small digits chained through cells, or by keeping one small adder helper. That trade-off is the main thing to settle.

## 1. Why a v2 (Alan, 20:27, 21:14, 21:18, readings taken)
- The chain with a bypass switch per unit (v1, stage 9) works on the Tang and is board-confirmed at 4 units. Alan: with bypass the routing is not needed at this stage; "but more stages yes, see how far it goes".
- For the larger cards (the Kintex XC7K480T) a version 2 or larger is needed: bring in some of the extra cores and add routing, so that more complex systems can be designed.
- Alan's Kintex card has **no working PCIe side** (JTAG only), which limits what can be done from a host. This shapes the design (section 6).
- A different direction Alan raised at 20:27: drop the maths cores and keep only logic and routing cells, doing maths in the chip's hard multiplier blocks. Section 3 keeps both open.

## 2. What v1 is (facts, measured or read from the code)
- A stage = config gate (drain, program, settle, fault policy) + `arith_block_v10` + output bridge, with a **bypass register** that turns the stage into a wire. Chain of N stages, one engine, one pattern bank (64 x 32-bit words in block RAM, space 7).
- Config word: [2:0] mode, [15:8] step/keep flags, [25:16] nano topology, [26] held-from-config, [28:27] second-operand source, [31] bypass.
- Commands: apply one unit, run a batch, program units from consecutive bank slots. The unit number is 4 bits (at most 15 units); the bank has 64 slots.
- Size on the Tang (place and route, NOT on a board beyond 4 units): 4 / 8 / 12 units = 11,321 / 14,139 / 17,051 slots (55 / 68 / 82 percent); about 705 to 728 slots per stage; clock 101 to 108 MHz against 27 required.
- Data path 18 bits wide. One word in flight per stage; about 5 clocks per word per stage.
- Known weakness found on the board: the unit starts a command when the command register changes, so a repeated identical word is ignored (fixed in the host by writing 0 first). v2 should use a command that cannot be missed (for example a toggle plus acknowledge).

## 3. Stage types for v2 (PROPOSAL of 1 Nov; see section 0: a single look-up-table cell may replace kinds A to C)
| Kind | What it does | Notes |
|---|---|---|
| A. Logic/route cell | truth-table (nano), mask, compare, select, bypass | the cheap one; no adder or shifter |
| B. Maths cell (soft) | v1's block: add, sub, accumulate, shifts | about 700 slots on the Tang |
| C. Maths cell (hard) | one hard multiplier / multiply-accumulate block per stage | counts: Tang 48 (18x18, from the Sipeed page); Kintex DSP count to be checked |
| D. Split | one input word to two outputs | new |
| E. Merge/join | two inputs to one; reuse `join_v1` ideas (pair mode, sticky B) | prior art exists |
| F. Memory port | read/write a word from the card's RAM | Kintex: DDR3 |
All kinds speak the same handshake and carry the same bypass bit, so the engine and the program format do not care which kind sits where. Question 1 in section 8 decides how many kinds to build first.

## 4. Routing (PROPOSAL, small first; section 0: follow the UniCell neighbour-shell scheme)
- v1 is a straight line. v2 needs branches, so each cell gets an **input choice** (which neighbour it listens to) and split/merge cells.
- Keep it **local**: a cell listens to one of a few nearby cells (previous, one back, or a named side input), chosen by a field in its config word. No global crossbar: it would break the flat timing the chain showed on the Tang.
- Paths are set by writing config words, as UniCell does with `routing_mask` (docs/shared/SYSTEM_MECHANICS.md); the host-side "walker" (discovery by ping/relay) is not a path creator and stays out of it.
- Prior art to check before building: `join_v1`, `routing_mask`, the hex-grid relays decided on 21 Oct (HEXN_DESIGN.md), and the Onion archive.

## 5. Scale: what must change from v1
1. Unit number: 4 bits to as wide as needed (8 bits gives 255).
2. Pattern bank: 64 slots to a program store sized by parameter; on the Kintex it can sit in DDR3 (two channels working; UberDDR3 at 83.33 MHz measured).
3. Config path: v1 broadcasts the config word to every stage. For hundreds of stages pass it **stage to stage** (a pipelined ring or shift path) so no wire reaches everything at once. Same for reset and the handshake back to the engine.
4. Command: replace "change the register" by a toggle with acknowledge.
5. Timing is not guaranteed to stay flat: Hex-N's own Kintex ladder fell from about 76 MHz (64 cells) to about 60 MHz (255 cells) by the tool's estimate. Must be measured, not assumed.

## 6. No PCIe: the card must run itself (PROPOSAL)
- Programs and working data live **on the card** (DDR3 on the Kintex, block RAM on the Tang).
- A small **on-card sequencer** reads program words, programs the stages, feeds data in and writes results back. The UniCell sequencer is the model.
- The host (JTAG on the Kintex, SPI through the ESP32 on the Tang) only loads programs, starts runs and reads results and status. No bulk streaming over JTAG.

## 7. Host side
- The existing front end (docs/hex-n/FRONT_END_UNIT_v1.md) is an ESP32 gateway that only moves words plus a PC module (`tools/hexn_open_host_v1.py`, class `OpenUnit`). The chain commands (fill the bank, program, apply one, run) belong in that PC module; the gateway sketch needs no change except where Alan wants a stand-alone ESP32 mode (his 19:38 direction).
- The sketch's C++ chain model is fixed at 4 units; it needs a parameter before bigger chains are tested on the board.

## 8. Questions for Alan
1. Cell kinds: with the single look-up-table cell of section 0, how wide is the table (address bits, data bits), and how should wide adds and compares be done: sliced into small digits, or one small adder helper kept?
1b. Neighbours: which UniCell neighbour set does v2 use (how many directions, and does the routing mask choose input, output or both)?
2. Branching: is **split + merge** enough for the first v2 systems, or do you want a general small crossbar?
3. Word width: stay at 18 bits or go to 32 on the big cards?
4. Target order: build and measure on the Tang first (cheap, quick) or go straight to a Kintex ladder (16 / 64 / 256 stages)?
5. Should the on-card sequencer be part of v2 or a separate step?

## 9. Plan (PROPOSAL, nothing started)
1. Alan answers section 8.
2. Measure on the Tang: one logic cell, one hard-multiplier stage (synthesis counts only); this also gives the soft against hard comparison.
3. Write the v2 word format and handshake (a short spec), simulate split/merge with the same style of model-checked tests as v1.
4. Tang build with the new cells, board test.
5. Kintex ladder, one build at a time (tens of minutes to over an hour each, openXC7 flow, `CHIPDB` set).

## 10. Not decided
Cell kinds, widths, the routing choice, the program store layout, the sequencer, and whether v1 stays frozen as the proven base (my assumption: it does, v2 is new files).
