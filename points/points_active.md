# points.md — ACTIVE part (currently entries #1416 onward)

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

## #1416 (19 Nov 2026) -- THE LEDGER IS SEALED THROUGH #1415 (part 14), AND THIS FILE STARTS FRESH

*Asked by Alan (19 Nov, 20:58):* "yes seal and start a new one, it gets full fast" (answering my question after the status test failed on size: `points_active.md` was 465,537 bytes, limit 450 KB of `tests/test_status_files_v1.py`; the failure came with my entry #1415 and I had committed and pushed it before reading the test result: my mistake, noted).
*The seal.* `points_active.md` (#1236-#1415) is now `points/points_14_1236-1415.md`; this file starts fresh at #1416. Proof it is lossless: everything after the part's header is byte-for-byte the body of the old active file (the body, from the `## #1236` heading to the end, is 464544 bytes, sha256 `1b7e745aa08e97f238773ccdca6d8e15c26e0562623981a7b48edd61cb71b3e0`; the old whole file was 465537 bytes, sha256 `c29bd95ccb7413f4931e11206dc2fdb382d2dddf964d263e1db73d105d863e87`; checked by reading the new part back and comparing). Only a header was added, in the same words as part 13's with the range changed. No entry was edited, renumbered or reordered. The old file is also in git (the commit before this one).
*Pointers updated:* `points/INDEX.md` (a row for part 14, the open file's row, the "of N" note), root `points.md`, `current/START.md` (the lines that name the newest sealed part), `CLAUDE.md` (the ledger line and the sealed part to read), `current/latest.md`. Not changed: `tests/test_status_files_v1.py` and `_v2.py` both still exist (which one to keep is still Alan's call).
*Size note:* the open file filled to 455 KB over #1236-#1415 (180 entries in 31 days, about 15 KB a day with the width work); at this rate it reaches the 350 KB sealing mark in roughly three weeks, so sealing is likely to come up again.

Next entry: #1417.
