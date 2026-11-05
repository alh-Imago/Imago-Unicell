# The Hex-N Kintex base: the full picture so far

Written 5 Nov 2026 (evening) for Alan, from the repository files and the runs pasted in the session. Every line is tagged **[card]** (measured on the Kintex card, with Alan's run), **[sim]** (iverilog only), **[file]** (read from our own files, not re-run today) or **[unknown]**. Nothing here is silicon timing; clock figures are nextpnr estimates.

## 1. What the base is, in one paragraph
One bitstream on the Kintex-7 card (YPCB-00338-1P1, XC7K480T) holding: two pattern arrays (7x7 and 6x6 hex cells), a program library, a judge (the Tang's batch scorer), and a controller around them, all reached through one JTAG link. Programs are the arrays' config chains; data goes in as 32-bit words; results come out as words with ticks. The card has no sensor wiring in this design: all input is words over JTAG, from the PC or from a RAM on the chip. [file]

## 2. The parts
| Part | What it is | Where | State |
|---|---|---|---|
| Pattern arrays | 7x7 (id 90894555) and 6x6 (id 8F532C4A) hex arrays, each in a frame (`hexn_frame_v7`) that takes commands I W B D G L S | `sub/verilog/hexn_frame_v7.v` + generated pattern | [card] (v1 base onwards; flip-flop variant `HEXN_NORAM=1`) |
| Program library | 1,024 bytes block RAM, 4 slots x 256 B, each a config chain; `P` write, `Q` load into the selected array | `hexn_base_ctl_v*.v` | [card] |
| Judge | the Tang's batch scorer `hexn_scorer_v3`: 8 sensor readings (0..11) in, two tables of 128 weights (class 0, class 1) + a bias, result = prediction bit and two scores | `fpga/verilog/hexn_scorer_v3.v` | [card] (AFTER mode result 0x00090014) |
| Selector | `A n` picks which array the host talks to | controller | [card] |
| Slot choice | `C a b`, `Z`, `U`: the judge's prediction picks which library slot loads | controller | [card] (5 Nov 16:09) |
| Results RAM | 2**RA records of 8 bytes (array, row, tick, word, index), judge results too; `X` arm/clear, `Y` status, `V` read; stop-and-flag with the input stopped | controller v2 | [card] (run, then fill: 1,008 records, refusal `F`) |
| Data RAM | 2**DA entries of 8 bytes (set input / go + wait); `T` store, `H` run by itself | controller v3 | [card] (run, then drain: 500 gos, 2,000 records, one stop at FULL, resumed) |
| Weight store | 4 sets x 512 words of the judge's weights (257 used), separate from the library; `O` save, `F` load, `E` cross-index slot to set, `r` read; `Q`/`Z` load tied weights first | controller v4 | **[sim] only; not built for the chip** |
| Bridge | JTAG USER2, 160-bit scans, 14 data bytes each way | `rtl/hexn_jtag_bridge_v1.v` | [card] |

## 3. Commands, all versions (opcode bytes)
- Forwarded to the selected array's frame: `I` ident, `W` wipe, `B` chain, `D` row word, `G` go mask, `L` log, `S` status [file].
- Controller v1: `A` select, `N` info, `P` write slot, `Q` load slot, `J` judge word, `M` mode (AFTER, flush), `R` next judge result, `C` slot table, `Z` choose and load, `U` last choice [card].
- v2: `X` arm/clear results, `Y` status, `V` read records [card]. A host `G` while armed and FULL is refused with `F`.
- v3: `T` store entries, `H` run entries [card].
- v4: `O` save weights, `F` load weights, `E` cross-index, `r` read words [sim].

## 4. Numbers
- **Sizes (nextpnr estimates, not silicon):** base v1 17,986 LUT sites; v2 18,461; v3 19,100 (3% of 597,200), flip-flops 14,153, 677 CARRY4; clock estimates 79 to 93 MHz at the bridge clock against the 50 MHz the card runs [card builds, SUMMARY pasted].
- **Build times:** 9.5 min (v3), 94 min (v2); why they vary is [unknown].
- **JTAG:** 3,291 raw scans/s at 2 MHz TCK, 5,558 at 6 MHz, 5,583 at 10 MHz: no gain above 6 MHz; about 180 us per scan, of which the wire is 16 to 27 us, so the limit is per-scan overhead, not the clock [card, speed tool]. Drain test: about 20 KB over JTAG in 2.0 s [card].
- **Capacity:** results RAM 1,024 records (8 KB) with a margin of 16 for words in flight, which has NOT been exercised [card, `fill`/`drain` stopped on whole runs]; data RAM 512 entries (4 KB); 955 RAMB36 on the chip.

## 5. How it relates to the layers (Alan, 5 Nov 19:48 and 19:54)
Layer 1 = the detector system; layers 2 to 4 were combined; the neural judge was added. **On the Kintex base: none of the detector bank, none of the layer 2 to 4 stack, and not the neural judge.** The judge here is the Tang's batch scorer (a different thing from the neural judge `rtl/hexn_neural_v1.v`, which is 7 inputs of 6 bits, 8 weights of 16 bits, learns on the chip, simulated only, in no top-level design) [file]. **Alan's account, 5 Nov 20:50 (his words, not yet checked against every row):** the batch judge system runs in parallel to the original layer 1 (which sorted and smoothed incoming data, weighted and learned); the layer 2 to 4 designs were combined and may since have been removed; the neural network has been replaced in part by the batch judge; the hex cell designs are the additional layer now being worked on. **What the files say, point by point:**
1. *Batch judge against layer 1:* the scorer's header says it "scores layer-1 bin words", so it takes layer 1's output (sensor readings sorted into bins 0..11) and sits after layer 1, not beside it [file]. Layer 1 is the counted detector bank, which holds a class steady with a hold counter and can learn with a local counting rule [file, LAYER_INTERFACES_v4].
2. *Layers 2 to 4:* the log shows them combined into one Python training module on 31 Oct (rows 13:30 and 14:10) and layer 2 as a hardware store in the Tang core; layer 3, layer 4 and helper hardware were not built as of the 30 Oct layer note. On 30 Oct 20:10 the neural side was moved off the critical path with the rule 'archive, never remove'. **I found no row saying they were removed.** [file]
3. *Neural replaced in part by the batch judge:* both score layer-1 outputs, the scorer as two linear tables whose weights the host works out, the neural judge with a tanh output that learns on the chip. **I found no row saying one replaced the other**; recorded as Alan's decision if he confirms it. [file]
4. *Hex cells as the additional layer:* recorded as Alan's statement; no document maps the hex arrays onto the layer numbers.
**[unknown] items above stand until Alan confirms or corrects.**

## 6. What is learned, and where it is kept
- The batch scorer's weights are worked out on the host and sent in as LOAD words; nothing on the chip trains them [file]. They are now saved into the weight store and tied to programs [sim].
- The neural judge learns on the chip but is not in the base. Its weights would fit the same store (8 words per set), with a small read-out walker [proposal].
- The arrays' config chains are the programs; the array frame can load a chain but not read it back [file].

## 7. Not tested / open
1. Margin of 16 for words in flight: not exercised. 2. A wait too short between two goes: not exercised. 3. The `E` (timeout) paths of `H` and `O`: not exercised. 4. Weight store: chip build (size, block RAM mapping) and the card: not done. 5. Job list (which array, program, data range per run, one command for a sequence): not started. 6. Judge picking the array (not the slot): not started. 7. "During" (output feeding the next input): not started. 8. Repeat and power-cycle runs on the card: not done. 9. Longer-frame bridge (B1): not needed at present sizes; not built. 10. Where the neural judge fits (three roles proposed in the session; needs Alan's choice of inputs, teacher source and role). 11. Whether detectors or the layer 2 to 4 stack should be brought into the Kintex base: Alan's call. 12. Persistence: the weight store and RAMs are SRAM; host `dump`/`restore` files are the carrier.
