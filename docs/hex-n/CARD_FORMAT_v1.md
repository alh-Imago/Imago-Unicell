# Hex-N card format, proposal v1 (28 Oct 2026)

**Status: a proposal for Alan to confirm. Nothing here is built.** It follows from three things Alan said on 28 Oct 2026: the key space must be larger; long runs mean the index gets cached onto the card, which is where "save" comes in; and models and datasets must be kept apart, which leads to some directory structure.

## What already exists and applies (checked in the UniCell repo)

`archeology/full-cell/docs/core/NATIVE_FS.md` (June 2026) and the standing decision recorded for the UniCell project: no directory tree; every block is self-describing (a header says what it belongs to); the index is rebuilt by reading the headers, so the blocks are the source of truth; collections are saved filters over the index. This proposal keeps that rule: the "directory" is a one-level **catalogue of volumes**, and every log block carries its own volume id and sequence number.

## Card layout (raw 512-byte blocks, no FAT; the card is used by Hex-N only)

| Region | Blocks | Content |
|---|---|---|
| Catalogue | 0 to 1 (two copies, the newer sequence wins) | magic, format version, catalogue sequence, up to 31 volume entries |
| Volume 1, 2, ... | start and length from the catalogue | header block, log region, two checkpoint slots, files region |

**Catalogue entry (one per volume):** volume id (8 bits), name (16 characters), model id, dataset id, state (empty, open, clean-saved), first block, block count, key bits, value bits, hash version, config hash (of `hexn_config.json`), creation time/sequence.

**Volume header block:** copy of the entry plus the full `hexn_config.json` text it was built with, so the volume describes the design that wrote it.

**Log region:** the circular log of tier v4, L blocks. **Log block:** 16-byte header (volume id, 40-bit sequence number, entry count, CRC16) and 62 entries of 8 bytes (tag word with valid bit and key hash, value word). The current v4 block has 64 entries and no header; this changes it to 62 plus a header (a 3% capacity cost) so a block can be recognised and ordered after a power cycle.

**Checkpoint region:** two slots (A and B, written alternately). A checkpoint holds the index, a sequence number, the log head and tail, and a CRC; the newer valid one is used. This is the "index cached onto the card".

**Files region:** ordinary named files stored with a small header (type, name, size, CRC): the design's `hexn_config.json`, the bitstream (`.fs`) that produced the data, the serial test captures, a note file. So the bitstream and its associated data live next to the data they made, as files, whatever loads them.

## Save and restore

* **Save** (clean shutdown or on demand): drain the fast table and the SDRAM level down into the log (every entry ends up on the card), flush the open sector, write the index checkpoint to the older slot, then set the volume state to clean-saved. After this the card alone holds everything.
* **Restore after a clean save:** read the catalogue, pick the volume, read the newer valid checkpoint into the SDRAM index (index size 1 MiB for 18-bit keys: about 2,000 block reads, 1.2 s), set head and tail. The fast table and SDRAM level start empty and refill by promotion on use.
* **Restore after a crash (no clean save):** read the checkpoint, then replay the log blocks with a sequence number newer than the checkpoint, in order. **Needed addition:** when a key is promoted away from the card its old log entry stays on the card, so replay would bring back a stale copy. Fix: a promotion appends a **tombstone** entry (the key with the valid bit clear) to the log, so replay removes it. Costs one extra log entry per promotion and is not in v4 yet.
* Restore without any checkpoint: scan every log block header, sort by sequence number, replay: the time is L blocks at 0.6 ms (4,096 blocks 2.5 s; 1 million blocks 10 minutes).

## Larger key space

The direct index (one word per possible key) stops being practical above about 20 bits. Options, in order of build size: (1) a **hashed index in the SDRAM**: index words hold the key hash tag, the sector and the entry number, found by probing; 8 MiB of SDRAM gives about 1.5 million live entries at a safe load; 24-bit keys give 16.7 million possible keys; (2) **index cached on the card**: the SDRAM index becomes a cache of the checkpointed index, so the live entry count is limited by the card, at the price of one extra card read for a lookup that misses the cached part. Alan gave no preference on width on 28 Oct; default proposal: build (1) with a 24-bit key first, design the block and checkpoint formats so that (2) can follow.

## Loading bitstreams from the card

**Not possible directly on this board.** From the Gowin configuration guide UG206 (read 28 Oct 2026): the GW2AR-18 QN88 package supports only the JTAG and MSPI (flash boot) modes; the SSPI, SERIAL and CPU slave modes that would let logic or a host feed a bitstream are marked unsupported for this package. A running design can trigger a reload with the RECONFIG_N pin, but the reload comes from the MSPI flash, not from the SD card. The SD slot is wired to ordinary FPGA pins (81 to 84), not to the configuration path. **Indirect routes, NOT verified:** a small loader design that reads a bitstream file from the card and writes it into the board's configuration flash, then pulses RECONFIG_N (needs the flash pins to be usable from user logic after configuration, and wears the flash); or the host loading over USB-JTAG as now. On the Kintex card there is no SD slot at all; bitstreams load over JTAG or from the BPI flash. The file region above keeps the bitstream and its data together regardless.

## Open questions for Alan

1. Volumes-and-catalogue (proposed, one level, matches the UniCell rule), real folders, or one store per card? (No answer given on 28 Oct; the question about bitstreams was added instead.)
2. Key width: 24 bits with the hashed index (proposed), or 32 bits with the card-cached index. (No preference given.)
3. Tombstones and the 62-entry block change the v4 log; agree before the card format is frozen.
