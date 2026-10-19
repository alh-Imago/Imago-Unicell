# points.md — ACTIVE part (currently entries #1236 onward)

**This is the real, currently-open tail of the single, canonical
points.md ledger — the file new entries get appended to.** Split
across multiple files purely because GitHub won't render a file over
~512KB in the browser (the single combined file had grown past 2MB);
no entry content was changed, reworded, or reordered. See `points/
INDEX.md` for the full real map of which part holds which entries,
and `points.md` (repo root) for the short, canonical pointer every
session should still start from.

**Naming convention, for future-me:** this file keeps the stable name
`points_active.md` (no entry range in the filename) for as long as
it's still being appended to, so appending never requires a rename.
Once it approaches ~350KB, seal it — rename to `points_NN_XXX-YYY.md`
with its real final range, start a fresh, empty `points_active.md`
for continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## #1236 (19 Oct 2026) -- THE LEDGER IS SEALED THROUGH #1235 (part 13), AND THIS FILE STARTS FRESH

*Asked by Alan (19 Oct, 09:36):* "close the current and start a new doc". I read "doc" as the ledger file, which had reached 494,789 bytes against the 450 KB limit of `tests/test_status_files_v2.py` (the status test had been failing on size since before #1233; recorded in #1233's session). If he meant a new chat or another document, this seal can be undone from git (the commit before this one).
*The seal.* `points_active.md` (#1037-#1235) is now `points/points_13_1037-1235.md`; this file starts fresh at #1236. Proof it is lossless: everything after the part's header is byte-for-byte the body of the old active file (the body, from the `## #1037` heading to the end, is 493796 bytes, sha256 `1fc99ed3069ddd3a7e9a7fe00bf33e49d6247dfcafe49315416322c07d477283`; the old whole file was 494789 bytes, sha256 `eef29a34443b33833f5f14577ecce61527d39a6607a4d7aed5230777cd3cc198`). Only a header was added, in the same words as the earlier parts, with the range in it and no entry count (the headings do not all use one style, so I did not count entries: 92 level-2 headings, 67 of the form `## #N`). Numbering notes for this range were not examined; nothing was renumbered or corrected.
*Pointers updated:* `points/INDEX.md` (a row for part 13, the open file's row, and the "of N" note), root `points.md`, `current/START.md` (the lines that name the newest sealed part), `CLAUDE.md` (the ledger line), `current/latest.md`. Not changed: the status test file names (`test_status_files_v1.py` / `_v2.py` both exist; which should be kept is still Alan's call).

## #1237 (19 Oct 2026) -- KINTEX k7_tree4 ON THE CARD: the PASS pattern was seen (by eye)

*Run (Alan, 19 Oct, ~09:38):* the kit of #1234 built through openXC7 on his PC and loaded into SRAM (`make program JTAG_LINK="-c ft232"`; the flash was not touched). *What he saw:* the steady green LED (taken as power, #1195) stays on; red off; then, repeating, **green, yellow, green + yellow, off**. His first description was "green, green + yellow, off"; looking closely he added the yellow-only step. The design's PASS pattern is four steps of about 0.17 s (nothing, green only, yellow only, green + yellow) with red off; a FAIL is red steady on with no green blinking. The observed sequence is those four steps starting at a different point in the cycle.
*What this supports.* The wrapper's compare returned PASS: all 163 bytes of the report line the unchanged Tang design printed on the Kintex (inside the chip) equal the bytes the Tang printed, including `last=0000061A` (1,562 clocks, in clocks) and `sig=7FEF5298`, with the clock at 50 MHz here against 27 MHz on the Tang. The green M30 output blinks only when the compare has passed, and red P30 is on for a fail, so red off with green blinking is consistent only with PASS. LED polarity: red off with PASS means active-high, as assumed (if they were active-low, red would be lit on a pass); the lamp test at the start (all three on for about 1.3 s) was not reported, so that is an inference.
*What it does not show.* It is an observation by eye, not an instrument reading. No place-and-route report was given to me (Fmax, utilisation, and whether timing passed are not recorded here; ask Alan to paste the end of the `make` output). One run, one build. Nothing was read back over JTAG. The result says the same RTL gives the same answers in the same number of clocks on a Xilinx chip; it does not say anything about speed on the Kintex.
*Also changed.* The MAN file's `verification.designs_run_on_card` now records this run (marked "seen by eye"), and its test was updated to require that wording.

## #1238 (19 Oct 2026) -- FIRST DATA READ BACK FROM THE KINTEX CARD: the configuration status register, and what the loader can and cannot read on this chip

*Asked by Alan (19 Oct, 09:41):* "start small, let us see if we can get some data back from the card itself".
*Run (Alan, openXC7 Nix shell, the k7_tree4 design loaded in SRAM).* `openFPGALoader --Version` -> **v1.1.1**. `openFPGALoader -c ft232 --read-register STAT` -> raw value **0x04107AFC**: CRC error none; part secured 0; MMCM lock 1; DCI match 1; EOS 1; GTS_CFG_B 1; GWE 1; GHIGH_B 1; MODE 2 (binary 010); INIT complete 1; INIT_B 1; release done 1; DONE 1; ID error none; DEC error 0; XADC over-temperature 0; startup state 4 (binary 100); bus width x16. I re-decoded the raw value by hand from the bit positions in the loader's own output and they agree. These agree with the 26 May bring-up notes (`hardware/YPCB_00338_bringup_findings.md`: DONE 1, EOS 1, PLL lock 1, no CRC error, no ID error, startup phase 100, Master BPI mode 010), which were read after a boot from flash; today the design was loaded into SRAM and the status looks the same.
*Not readable with this loader on this chip.* `--read-dna` and `--read-xadc` both stop with "Failed to claim FPGA device: Error: read_xadc only supported for Artix 7" (the same message for both; not investigated further). So no die temperature, supply voltages or chip serial number from this tool.
*Mistakes of mine, recorded.* (1) I quoted the openFPGALoader v0.13.1 manual and assumed the options existed; they exist in v1.1.1 but are limited by chip family. (2) I suggested the earlier "option does not exist" and "Unknown device" messages (from runs with `sudo`) came from a different, older loader that `sudo` picked up; that is a **hypothesis only**: nobody ran `sudo openFPGALoader --Version`, and the same commands without `sudo` worked, which fits it but does not prove it.
*The cable.* Read from the openFPGALoader v1.1.1 source (`src/cable.hpp`, cloned in the cloud workspace): the cable named `ft232` is defined as an FT232H-type device (USB 0403:6014, interface A, initial value 0x08, direction 0x0B), i.e. the usual MPSSE JTAG layout. That is what the OpenOCD config in #1239 uses. Not yet run against the card.
*Alan's remark (10:22), recorded:* the "walker" (the part that mapped the real cell structure so an ICM could work directly on the actual card contents) was never fully realised; that comes later. Reading the design's registers over JTAG is groundwork for it, not the walker itself.

Next entry: #1239.

## #1239 (19 Oct 2026) -- JTAG USER-REGISTER KIT (k7_tree4_jtag_v1): read the design's own registers out of the chip; built and simulated, NOT built through openXC7 and not run on the card

`fpga/kintex7_tests/k7_tree4_jtag/`, written by `tools/kintex_tree4_pack_v2.py` (a clone of the v1 kit's output; v1 untouched). The k7_tree4 wrapper plus a BSCANE2 (JTAG chain USER1) user register: 96 bits read out LSB first: word 0 = 0x554E4943 ("UNIC", fixed), word 1 = a free-running 50 MHz clock counter taken at the scan, word 2 = {16'h0, idx, 4'h0, lamp_on, timeout, bad, seen} (the wrapper's own registers). Host side: `k7_ft232h.cfg` (OpenOCD, FT232H layout above, IDCODE 0x23751093, IR length 6), `scan_chain.sh` (step A: chain scan, no bitstream), `read_user1.sh` and `decode_user1.py` (step C: `irscan 0x02` then three 32-bit `drscan` fields). Only USER1 and the IDCODE scan are used; no JPROGRAM or configuration instruction is ever sent.
*Checked here.* iverilog: with a behavioural BSCANE2 (in the testbench only), a CAPTURE then 96 shift clocks returns word0 554E4943, a non-zero counter, seen=1 bad=0 timeout=0: PASS. yosys (cloud) reads the design and treats BSCANE2 as a known primitive (hierarchy with the Xilinx primitive library, no error). *Not checked, and the real unknowns:* whether nextpnr-xilinx can place a BSCANE2 at all (the build is the test; an error mentioning BSCANE2 is itself the answer); whether OpenOCD, driving this cable with these pins, sees the chip; whether the OpenOCD `drscan` output format matches what `decode_user1.py` expects (it takes hex words, with or without 0x; I have not seen OpenOCD's actual output). The snapshot crosses clock domains without synchronisers; fine for a bring-up read, noted in the file.
*Plan, in order (each only after the one before worked):* A) `nix shell nixpkgs#openocd`, `sh scan_chain.sh` (expect IDCODE 0x23751093); B) build and load the kit, LEDs show the same PASS pattern; C) `sh read_user1.sh`.
*What it is for.* Alan's idea (19 Oct): initiate a freeze and save over JTAG to get the actual states of the latches. This is the smallest step towards it: first prove a host can read a register of a running design out of the chip. The freeze/save itself (the UniCell's own saveload mechanism, `fpga/board_tests_saveload`) is not part of this kit.

## #1240 (19 Oct 2026) -- STEP A OF THE JTAG KIT PASSED: OpenOCD sees the Kintex through the cable

*Run (Alan, 19 Oct, ~10:32), from a plain terminal in `k7_tree4_jtag`:* `nix shell nixpkgs#openocd --command sh scan_chain.sh`. *Output:* Open On-Chip Debugger **0.12.0**; "clock speed 6000 kHz"; "JTAG tap: xc7.tap tap/device found: **0x23751093** (mfg: 0x049 (Xilinx), part: 0x3751, ver: 0x2)"; a warning "gdb services need one or more targets defined" (expected: the config defines a JTAG tap only, no debug target; not a fault); "shutdown command invoked". The scan changes nothing on the chip.
*What this supports.* The pin layout in `k7_ft232h.cfg` (the FT232H-type layout read from openFPGALoader v1.1.1's cable table, #1238) works with this card and cable, and the IDCODE matches the one read by the loader (#1189, #1238). The expected-id check in the config passed (it would have refused a different ID). It does not yet show that the USER1 register can be read: that needs the step-B bitstream.
*Slips on the way, recorded.* (1) My first `nix shell` instruction was to nest it inside the openXC7 shell, which dumped Alan out of that shell; the corrected form runs OpenOCD as a one-shot command from a plain terminal. (2) He ran the script from the first kit's folder (`k7_tree4`), where it does not exist; the JTAG kit is the separate `k7_tree4_jtag` folder.

Next entry: #1241.
