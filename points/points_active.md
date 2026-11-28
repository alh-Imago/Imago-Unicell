# points.md — ACTIVE part (currently entries #1583 onward)

**This is the real, currently-open tail of the single, canonical
points.md ledger — the file new entries get appended to.** Split
across multiple files purely because GitHub won't render a file over
~512KB in the browser; no entry content was changed, reworded, or
reordered. See `points/INDEX.md` for the full real map of which part holds
which entries, and `points.md` (repo root) for the short, canonical pointer
every session should still start from.

**Naming convention, for future-me:** this file keeps the stable name
`points_active.md` (no entry range in the filename) for as long as
it's still being appended to, so appending never requires a rename.
Once it approaches ~350KB, seal it — rename to `points_NN_XXX-YYY.md`
with its real final range, start a fresh, empty `points_active.md`
for continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## #1583 (28 Nov 2026) -- THE LEDGER IS SEALED THROUGH #1582 (part 15), AND THIS FILE STARTS FRESH

*Asked by Alan (28 Nov, 01:27):* "yes seal and restart a new one thanks" (answering my note after the status test said `points_active.md` was 354 KB, past the ~350 KB sealing mark).
*The seal.* `points_active.md` (#1416-#1582) is now `points/points_15_1416-1582.md`; this file starts fresh at #1583. Proof it is lossless: everything after the part's header is byte-for-byte the body of the old active file (the body, from the `## #1416` heading to the end, is 361651 bytes, sha256 `9ea48d1e354bbf4095a24936d56fb8b69700c894ee25592279feb90380e83220`; the old whole file was 362596 bytes, sha256 `87ec65930255d94295ecf3a613b5616578ff1527ddacfe29016685af603ea794`). Only a header was added, in the same words as part 14, with the range in it. Nothing was renumbered or corrected. Note: #1582 is written as `#1582 (27 Nov) --` without the `##` of the other headings, as it stands in the sealed part.
*Pointers updated:* `points/INDEX.md` (a row for part 15, the open file's row, the "of N" note), root `points.md`, `current/START.md`, `CLAUDE.md`, `current/latest.md`.

Next entry: #1584.
