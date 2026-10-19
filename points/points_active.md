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

Next entry: #1238.
