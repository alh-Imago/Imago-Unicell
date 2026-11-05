# Hex-N base: results RAM, data RAM, weights with programs, job list, and the JTAG limit

Scoping note v1, 5 Nov 2026. **Status: scoping only. Nothing in this note has been built.** Every statement is tagged **[measured]** (a run on the card or a tool run), **[documented]** (read from our own RTL, files or notes, not re-run today), **[arithmetic]** (worked out from the figures given) or **[unknown]**.

Alan's aim (5 Nov 2026, 13:58): store results into RAM and read them back over JTAG, "as that's what we have"; load a new program into the library (which is just programming); and load data into RAM to be run through the system. Alan (14:01): the JTAG limit is what really holds this back.

## 1. What we have

| # | Item | State | Evidence |
|---|---|---|---|
| 1 | Base on the Kintex card: judge (`hexn_scorer_v3`), 7x7 and 6x6 arrays, controller `hexn_base_ctl_v1`, JTAG bridge; 17,979 LUT sites (3% of the chip), 95.33 MHz estimated | **measured** (nextpnr, 5 Nov); tool estimate, not silicon | ledger 5 Nov |
| 2 | Program library: 1,024 bytes of block RAM, 4 slots x 256 bytes, each holds one array's config chain; commands `P` (write a slot), `Q` (replay a slot into the selected array) | **measured** on the card (library selftests pass, 7x7 prio4 and 6x6 addsub) | HEXN_DESIGN 5 Nov |
| 3 | Judge on the card: words in, result {pred, s1, s0} out; AFTER mode gives 0x00090014 | **measured** on the card | HEXN_DESIGN 5 Nov |
| 4 | Where output words go today: each array's frame keeps a log of **16** entries (row, 32-bit data, 16-bit tick); the controller keeps a queue of **8** judge results and a queue of 4 words for AFTER mode | [documented] (`hexn_frame_v6.v` line 23, `hexn_base_ctl_v1.v` lines 43-44) | RTL |
| 5 | Weights today: sent by the host as judge words (LOAD type 12, BIAS type 13) and held in the judge's own tables; **not stored with the programs** | [documented] | `hexn_scorer_v3.v`, controller |
| 6 | The link: bridge `hexn_jtag_bridge_v1`, one 160-bit scan per frame, **14 data bytes** each way per scan, CRC16, sequence number and ack, core side fed one byte every FSPACING = 128 clocks, an input buffer of one frame, an output queue of 32 bytes | [documented] (header of the bridge) | `rtl/hexn_jtag_bridge_v1.v` |
| 7 | Host side: OpenOCD with a Tcl port, one `drscan` per frame; the bridge header names TCK as 10 MHz in the repo config, with a documented ceiling of 12.5 MHz for the bridge's synchronizer | [documented]; the actual TCK on Alan's runs (`digilent_hs2`, `HEXN_CHAIN=2`) is **[unknown]** | bridge header, `hexn_jtag_host_v1.py` |
| 8 | Block RAM on the chip: 955 RAMB36 (about 4 MB); the open flow handles block RAM on the card, while inferred distributed RAM and shift registers did not work | **measured** (library works; the earlier no-output failure) | ledger |
| 9 | **JTAG throughput: never measured.** | **[unknown]** | |

## 2. What is missing

1. **A results RAM.** An output word that arrives while the 16-entry log is full is lost to the host. A long run cannot be recorded.
2. **A data RAM.** Today the host sends each input word through the link and the frame injects it. There is no store of inputs on the chip.
3. **Weights stored with programs.** The weights live only in the judge after the host has sent them; a library slot cannot recreate them.
4. **A job list.** The host issues J, W, Z, D, G, L in order; nothing on the chip sequences runs.
5. **A throughput figure.** Without it any RAM size is a guess.

## 3. The four pieces

### 3.1 Results RAM (smallest, first)

- A block RAM written by the controller whenever an array produces an output word (and whenever the judge produces a result). One record: **array number, tick, 32-bit data, optionally the judge's 32-bit result** = a fixed record, proposed 12 bytes (1 + 2 + 4 + 4 + padding), **[proposal, not tested]**.
- Depth: 1,024 records = 12 KB in one or a few RAMB36. A write pointer, a read pointer, a "full" flag, and a counter of lost records. A choice of what a full RAM does (stop and flag, or wrap and overwrite) is Alan's: stop-and-flag keeps the first results, wrap keeps the latest. Proposed default: stop and flag (nothing silently lost).
- Commands (new opcodes, to be chosen not to clash with existing ones): `X` clear and arm; `Y` status (count, lost, full); `V page` read one page of records (a page sized to the frame: 14 data bytes carry a whole number of bytes of records, so the page reply spans several frames; the host loops).
- It sits **beside** the existing 16-entry log, not instead of it (the old commands stay; proven files are cloned and incremented, not edited).

### 3.2 Data RAM

- A block RAM of 32-bit input words plus a small header per run: **start, length, tick spacing**. The host loads it with a write command (`K addr bytes...`, similar in form to `P`), then starts a run with one command; the controller feeds the array word by word at the stated spacing, reusing the frame's existing input path (`D`/`G` as the host uses them now).
- The controller must wait for the array to be idle (the `a_idle` output of frame v6) before feeding; it already forwards other opcodes only when idle.
- Size: the same block-RAM arithmetic as 3.1; 4 KB (1,024 words) in one RAMB36 as a first size. **[proposal]**
- Open: whether inputs are one word per tick, or any spacing the program needs (the Hex-N card format has ticks; timing semantics of repeated inputs must be read from the frame RTL, not assumed).

### 3.3 Weights stored with programs

- The judge can be loaded by LOAD and BIAS words (types 12 and 13). A library entry would hold, after the chain bytes, the **judge words for that program** (count, then 4 bytes each). `Q` would replay the chain into the array and the stored words into the judge, so "program plus weights" loads as one thing. **[proposal]**
- Slot size: today 256 bytes per slot; the 7x7 chain is 164 bytes, the 6x6 115, the 5x5 81 [documented]. The number of weight words per program is **[unknown]** and sets whether 256 is enough (it would not hold a chain of 164 bytes plus many weight words). Option: make the library 2,048 or 4,096 bytes (still one or four RAMB); this changes the layout of the library and so needs a new controller version (`hexn_base_ctl_v2`).
- Open: can the judge dump its weights back in the same format? That would allow "save what the judge learned" as a library entry. Not checked; **[unknown]** until the scorer RTL is read for it.

### 3.4 Job list

- A table in RAM; each job: **array, program slot, data range start/length, whether to score, repeat**. A small state machine walks it: select array, `Q` the slot, feed the data range, collect to the results RAM, next job.
- This is also where "before / during / after" becomes a state: *before* = the judge's choice picks the slot (already built, `Z`), *after* = AFTER mode scoring (built), *during* = a loop where output feeds the next input (not built; timing-sensitive).
- This needs 3.1 and 3.2 first.

## 4. The JTAG limit: what is hardware, what is ours

- **Per scan:** 160 bits, of which 14 bytes (112 bits) are data in each direction [documented]. The other 48 bits are header and CRC. At a TCK of 10 MHz one scan is 16 µs on the wire [arithmetic], **if the TCK really is 10 MHz** (unknown on Alan's setup).
- **Core side:** the bridge delivers one byte per 128 clocks; at 50 MHz that is 2.56 µs per byte, about 390 KB/s [arithmetic from FSPACING = 128 and the 50 MHz system clock]. A frame of 14 bytes also needs the core to finish the previous frame (input buffer must be empty) [documented].
- **Host side:** each frame is one OpenOCD Tcl command (`drscan`). The time per command (software round trip, USB) is **[unknown]** and is plausibly much larger than the 16 µs on the wire; if so, **the limit is the number of scans per second, not the TCK**, and the cure is more bytes per scan. [This is a hypothesis, not a measurement.]
- **What is ours to change, without touching hardware:** (a) the scan length: a JTAG shift register can be much longer than 160 bits, so a frame could carry hundreds of bytes (bridge change: a longer register, a larger input buffer and output queue; new file `hexn_jtag_bridge_v2`, the proven v1 stays); (b) the TCK setting in the OpenOCD config (up to the bridge's 12.5 MHz ceiling unless the synchronizer is changed); (c) pipelining: sending the next frame before the previous reply is processed (the protocol already has sequence numbers and acks).
- **What is Alan's:** the cable (the loader used is a Digilent HS2; the repo config names an HS3), the JTAG wiring and any change that raises the maximum TCK of the hardware.
- **The structural answer** is 3.1 to 3.4: if the chip holds the data, runs the job and stores the results, JTAG carries a program and a block of data in, and a block of results out. Speed then affects only the wait at each end.

### 4.1 Measuring tool (proposed first step)

A host script `hexn_jtag_speed_v1.py`, read-only, no writes to the chip's state beyond the existing echo path:

1. Read a fixed block of known bytes from the card (a built-in test pattern in a new controller command, or the library contents already written) at several **bytes per scan** (the 14 the bridge allows, until a v2 bridge exists) and several TCK values, with OpenOCD's `adapter speed` set by the script.
2. Report scans per second, bytes per second, CRC retries.
3. Also report the time for one empty poll scan to separate "per-scan overhead" from "per-byte cost".
4. Run once with each TCK; Alan pastes the output.

This answers: is the limit TCK, per-scan overhead, or the core's 128-clock byte spacing. **[Predicted, not tested]:** per-scan overhead dominates. The result sets whether a longer frame (4.a) is worth building and how large the RAMs need to be.

## 5. Proposed build order (each step simulated first, then run on the card by Alan)

| Step | What | Passes when |
|---|---|---|
| J1 | `hexn_jtag_speed_v1.py` and a test-pattern read | Alan's run prints bytes per second at 2 or more TCK values |
| R1 | Results RAM and `X`/`Y`/`V` in `hexn_base_ctl_v2` (clone of v1, v1 kept) | simulation: a 7x7 prio4 run records all words with array and tick, paged read equals the vector; overflow flag tested |
| R2 | Host support and tests: `results` command in the base host, session test through the real bridge RTL | same suite style as `test_hexn_kxbase_session_v1.py` |
| D1 | Data RAM, `K` load and `run` command | simulation: a data range fed word by word gives the same output as the host-fed run |
| W1 | Weights stored with programs; library layout decision (slot size) | `Q` of a slot sets chain and judge words; judge result equals the host-loaded run |
| B1 | Longer-frame bridge `hexn_jtag_bridge_v2` (only if J1 shows per-scan overhead dominates) | simulation through `bscane2_model.v`, then the speed tool shows the gain |
| S1 | Job list and sequencer | simulation: a two-job list (prio4 on 7x7, addsub on 6x6) runs with one start command and fills the results RAM |
| C1 | Build for the chip and run each step on the card (Alan) | the card matches the simulation |

Each step: new file versions, a test, a row in `HEXN_DESIGN.md`, a ledger row, commit and push.

## 6. Open questions for Alan

1. Results RAM full: **stop and flag** (keeps the first records, proposed) or **wrap** (keeps the latest)?
2. Which TCK did the runs use, and is the cable the HS2 or the HS3 (the OpenOCD config in the repo names the HS3)? The speed tool will print the setting it applies, but the cable type is yours to confirm.
3. What kinds of data will go through, and in what size? (A few hundred words suits one block RAM; megabytes would change the plan and make the link the main cost.)
4. Should "save what the judge learned" (dumping weights into a library entry) be in the first version or later?

## 7. Not claimed

No part of 3.1 to 3.4 exists; no JTAG throughput has been measured; the per-scan-overhead explanation is a hypothesis; the TCK on Alan's runs is not known; the judge's ability to dump its weights is not checked; record formats, depths and opcodes in this note are proposals; the base has not yet been run with `choose` on the card (waiting on Alan's build).

## 8. Update, 5 Nov 16:15: first JTAG measurement, and Alan's decisions

**Alan's decisions (14:18):** the results RAM **stops and flags when full, and the input side stops too**, so nothing new flows in and is lost (the controller must stop feeding with a margin for words already in the array's pipeline; margin to be sized from the array latency, not yet measured). Weights from the judge should be saved; whether they travel with the data or attach to the program side depends on how they were made (proposal: a label on each saved set, "for this program" or "from this run"; Alan to decide). Data RAM target: block RAM first, DDR3 later (the card has two channels of 2 GiB each, per `docs/man/ypcb-00338-1p1.man.json`; not used for this yet).

**Measured (Alan's run, 16:12, `tools/hexn_jtag_speed_v1.py`, base loaded, OpenOCD):**

| TCK asked | OpenOCD reports | raw scans/s | wire time per scan [arithmetic] | time per scan [arithmetic] | overhead per scan [arithmetic] | `N` info: scans per info | infos/s | bytes/s (7 per info) |
|---|---|---|---|---|---|---|---|---|
| 2 MHz | 2000 kHz | 3,291 | 80.0 us | 304 us | 224 us | 4.03 | 778.9 | 5,452 |
| 6 MHz | 6000 kHz | 5,558 | 26.7 us | 180 us | 153 us | 4.00 | 866.3 | 6,064 |
| 10 MHz | 10000 kHz | 5,583 | 16.0 us | 179 us | 163 us | 4.00 | 910.3 | 6,372 |

**What the numbers say (measured, then reading):**
- Going from 6 to 10 MHz changes nothing (5,558 against 5,583 scans/s). So above about 6 MHz **the clock is not the limit**. This agrees with Alan's observation that uploads ask for 10 MHz and run at 6 MHz; whether the real TCK is 6 MHz or the scan rate simply stops depending on it is not separated by this test.
- At 6 and 10 MHz a scan takes about 180 us, of which the wire is 27 and 16 us: **about 85 to 90% of each scan is overhead outside the wire** (OpenOCD, the Tcl socket, USB). This supports the earlier hypothesis (section 4) that the limit is the number of scans per second. It was a hypothesis before; this run measures it for this cable and OpenOCD setup.
- The protocol-level rate is lower than the raw rate: an `N` info costs 4 scans in about 1.1 ms (roughly 3,600 protocol scans/s, against 5,583 raw). The `N` test moves only 7 bytes per 4 scans, so 6.4 KB/s is a **floor for this command**, not the link's capacity.
- **Ceiling with the present 14-byte frame [arithmetic, not measured]:** 14 bytes per scan at 3,600 to 5,583 scans/s is about 50 to 78 KB/s each way, if the host keeps frames full. The core side takes a byte every 128 clocks (about 390 KB/s at 50 MHz), so it is not the limit at this size.
- **With a longer frame [arithmetic, assumes per-scan overhead stays near 160 us regardless of length; untested]:** a frame of about 128 bytes (1,024 data bits) adds about 100 to 170 us of wire time at 10 to 6 MHz, so roughly 300 to 350 us per scan, about 400 KB/s, which would reach the core's 390 KB/s limit.

**What this means for sizes [arithmetic]:** a full results RAM of 1,024 records x 12 bytes (12 KB) reads back in about 0.15 to 0.25 s at 50 to 78 KB/s, or about 2 s at the 6.4 KB/s floor; a 4 KB data RAM loads in under a second at either. A megabyte would take about 13 to 20 s at the present ceiling and about 3 s with long frames. **Conclusion, flagged as a reading:** at the sizes proposed for the first RAMs, the present bridge is good enough; the longer-frame bridge (B1) matters only if the stores grow towards megabytes. Build order stays as in section 5, with B1 moved after R1, R2 and D1.

**Also: the hardware side.** Since clocks above 6 MHz buy nothing here, the cable's maximum speed is not what limits this link; the per-scan overhead is in the host software path. That part is ours to change (longer frames, fewer round trips), not only Alan's to solve.
