# Layer 3 in hardware: first plan and sizing (27 Oct 2026)

Status: plan and Python counts only. No Layer 3 RTL exists yet; nothing here has run on a card.

## What Layer 3 has to do (from the model, `tools/hexn_layer3_v1.py` to `v3.py`)
1. Line up the channels: changes within `align` ticks form one **moment**.
2. Keep a **snapshot** (the latest key of every channel) after each moment.
3. Remember, for the last 1..L snapshots (each seen through a channel mask), which moments followed, with weights that fade (half-life).
4. Give **weighted possible outcomes** (PPM-C blending, longest context first).
5. Compare outcome with the goal, produce reward and feedback records, and send them down to layer 2.

## Proposed mapping onto what already works
- The **moment builder** is a small counter plus a latch per channel; it is new, but tiny.
- The **snapshot table** and the **moment table** are the store v5 idea again: only values seen before get an ID, new ones are added. The synthetic world needs 49 snapshot IDs and 40 to 50 moment IDs, so about 6 bits each (store v5 events are 4 bits today; `EVB` is a parameter, so the index tag and entry widen).
- The **path memory** is store v5 keyed by (length, mask, snapshot IDs), with one index/heap pair shared by all masks (the mask is part of the token). Entries need a faded weight instead of the layer 2 `seen` byte.
- The **weighted possibles** need a read that walks all entries of a matched context and returns them ranked. Store v5 today returns only the best follower, so this is a new read.
- The reward/compare/feedback records reuse the layer 2 REW and OBS commands as already modelled (`hexn_layer3_v3.py`).

## Memory demand (measured in the model: `tools/hexn_layer3_size_v1.py`)
Synthetic coupled world, 3 channels, rows = 4-entry heap rows. Store v5 on the Tang holds 1,024 index slots, 512 rows, 2,048 entry slots.

| run | setting | contexts | entries | rows |
|---|---|---|---|---|
| 400 routines | L=2 full mask | 190 | 405 | 211 |
| 400 routines | L=4 full mask | 753 | 1,166 | 794 |
| 400 routines | L=4 all masks | 1,009 | 2,002 | 1,131 |
| 4000 routines | L=4 full mask | 1,757 | 3,258 | 1,909 |
| 4000 routines | L=4 all masks | 2,033 | 4,828 | 2,448 |
| 4000 routines | L=6 all masks | 5,654 | 11,164 | 6,392 |

What this says (for this synthetic world only):
- The demand grows with run length and with context depth; it does not settle. Deep contexts on a long run need several times what the Tang store holds.
- So on the Tang a Layer 3 would need either short contexts (L=2, about 370 rows after 16,000 moments), or **forgetting** (drop the oldest or lowest-weight contexts instead of refusing new ones; store v5 today drops the NEW entry when full).
- The Kintex card, with far more RAM, can hold the deeper settings; the cell count per part and the Layer 3 block size are to be set by card space, as Alan said.

## Open decisions (for Alan)
1. Forgetting rule when the memory is full (oldest first, lowest weight first, or fade to zero then free).
2. Whether the Tang gets a reduced Layer 3 (L=2, one mask) as a proof, or Layer 3 waits for the Kintex card.
3. Weight format in hardware (the model uses floating point with a half-life; hardware would use a fixed-point weight with a shift decay, like the layer 2 value step).

## Not yet done
Fixed-point model of the blend, RTL for the moment builder and ranked read, real coupled recordings (remote plus analog sensors captured at once).

## Memory tiers (Alan, 27 Oct 2026, 18:37)
Forgetting should not mean losing: patterns that have proven themselves move down to slower, larger memory instead of being deleted, and come back when needed.
- **Tang Nano 20K:** fast tier = BSRAM (the store v5 index and heap); slow tier = the SD card (Alan has a small one to use), reached through the on-board BL616 housekeeping firmware, which waits until a second Tang is available. Checked against the Sipeed spec page (wiki.sipeed.com Tang Nano 20K, 27 Oct 2026): the board has one TF card slot, 64 Mbit of 32-bit SDR SDRAM, 64 Mbit of flash (for the bitstream) and 46 BSRAM blocks (828 Kbit); the BL616 gives the FPGA a USB-to-UART link and a USB-to-SPI link. The page does NOT say whether the TF slot is wired to the FPGA or to the BL616, nor whether it is SDIO or SPI, and has no pin table (the pin diagram is an image); the Sipeed unbox page only uses the card to hold NESTang game images. Still to check from the schematic: the slot's wiring and the access speed.
- **Kintex card:** no SD card slot. Fast tier = local BRAM; slower tier = the card's main RAM; slowest tier = through the JTAG link. The PCIe route, which would normally serve as the slow path, is not available on this card. Not yet checked: which main RAM the card carries and what it takes to drive it.
- Design consequence: the store needs a **spill and recall** step (write a proven entry out, read it back on a miss) that is the same in principle on both cards, with a different slow tier behind it.

## SD card wiring: answered by Alan's SD loader file (27 Oct 2026, 18:55)
Alan supplied the SD loader module of the NESTang project (module `SDLoader`, which instantiates a separate `sd_reader`; the `sd_reader` source was NOT in the file). What it shows, read from the file:
- The **FPGA drives the SD card directly**: ports `sd_clk`, `sd_cmd` (inout), `sd_dat0` (input), and `sd_dat1`, `sd_dat2`, `sd_dat3` held at 1 ("must be 1 to avoid the card entering SPI mode"). So it is SD-native 1-bit mode with the FPGA as host, not through the BL616. This settles the earlier open question for the Tang: the SD tier can be driven from our own RTL, and the BL616 firmware is not needed for it.
- It is a **sector reader**: it starts a read with `rstart` and a 24-bit sector number, receives the sector as a byte stream (`outen`, `outbyte`) and a `rdone` pulse. Sector size is 512 bytes in that file (offsets are 9 bits). The SD clock divider is a parameter (`CLK_DIV`) of `sd_reader`, speed not given in the file.
- It is **read only**. There is no write path in this file, so spilling entries OUT to the card needs an SD writer (a write-block command plus its data and busy handling) that we do not have yet.
Consequences for the memory tiers:
- Slow-tier reads are whole 512-byte sectors, so a spilled context should be stored so that all its followers sit in one sector and come back in one read (this is the "bring a whole context back in one read" idea from the forgetting model).
- Because the card keeps its contents, the SD tier also gives the store a **save and reload across power-off** without the BL616.
- Reusing the NESTang `sd_reader` needs its source and its licence checked first; not done.
