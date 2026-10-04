# points.md — ACTIVE part (currently entries #946 onward)

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
with its real final range, start a fresh, empty `points_active.md` for
continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## 946. THE LEDGER IS SEALED THROUGH #945: `points_active.md` (1,600,122 bytes, 373 entries, #572-#945) is now sealed as parts 7-11, and this file starts fresh at #946. Lossless, proven; three pre-existing numbering anomalies recorded, not "fixed".

Alan: "while there is space left, move this current record and archive it, so we can start a new one." This is the procedure in `current/START.md`'s close-out checklist (item 4) and `points/INDEX.md`: seal at entry boundaries only, never edit content, name each part `points_NN_XXX-YYY.md` with its real range, add rows to the INDEX, start a fresh `points_active.md`.

**Why five parts, not one:** the file was 1.6 MB against the ~350 KB sealing threshold (GitHub stops rendering past ~512 KB). The six earlier parts are each ~350 KB, so it was cut into five balanced parts at entry boundaries (317-323 KB each).

| Part | File | Entries | Range | Size | sha256 |
|---|---|---|---|---|---|
| 7 | `points_07_572-652.md` | 81 entries | #572-#652 | 323,451 bytes | `9929f9f0775db5798dd9f66afe7bce08fb15e09bbff2ec304306e1b27cc4c26e` |
| 8 | `points_08_653-735.md` | 83 entries | #653-#735 | 319,611 bytes | `5849f7f96ca469b4daffaf81fd3795b10f3659d93c887fcc93c42cd2f494fbed` |
| 9 | `points_09_736-810.md` | 75 entries | #736-#810 | 322,358 bytes | `95fafa910e1af4993e03785514e707bc9ea9dd8d1dcdc8efbd6caae7b3eb21e2` |
| 10 | `points_10_811-874.md` | 65 entries | #811-#874 | 317,213 bytes | `0f90f88551ebcb06b4577020cfe6f41bb2213aae2f29cb4c9f314ed3dc6b55d4` |
| 11 | `points_11_875-945.md` | 69 entries | #875-#945 | 319,314 bytes | `7a28f3da76a09f4310684d114c7f359232e1c25b37fcef7008f4300549a72e2c` |

**Lossless, proven before anything was replaced:** the entries of the five new parts, concatenated, are byte-identical to the original file's body (everything after its header): original sha256 `7a7e864680b077820f2bce606d8b14c52a8275f803d82450d361b8d27a5c2b5b`, 1,600,122 bytes. Only each part's own header line was added (`# points.md -- part N of 12 (entries ...)`, in the same words as the earlier parts). The unsplit file is also recoverable from git: `git show 0f9595a:points/points_active.md`.

**Three numbering anomalies already in this range -- recorded in the INDEX, left exactly as they are (the ledger is append-only):** #824 is used TWICE (two different entries, both in part 10); #893 and #902 were never used (skipped numbers, in part 11). The earlier anomalies (#191-#201 after #202-#203; #394 used twice) are unchanged.

**What else changed (documents only, no ledger entry touched):** `points/INDEX.md` (rows for parts 7-11, the active row now `#946 onward`, the anomalies, and a new catch-up paragraph, since the fresh active file is nearly empty and the real recent work is now in part 11); the root `points.md` pointer; `current/START.md`'s catch-up line; and the few docs that cited specific entries as living in `points_active.md` (`current/PLAN.md` for #827 and #596 and others, the DSL manual and `llvm_ir_compiler_scope.md` for "#612 onward") now name the part that holds them. The older sealed parts' headers still say "of 7" -- left unedited, as sealed parts never are; there are now 12 parts counting this one.

**Not done:** a session archive under `archeology/sessions/` (START.md close-out item 8, "if the session was substantial") -- a separate step Alan has not asked for; no `.onion` packing. The next entry is #947.
