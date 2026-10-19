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

Next entry: #1237.
