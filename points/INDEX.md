# points.md — INDEX

**The canonical, append-only, numbered decision ledger for this project,
split across multiple files purely because GitHub will not render a file
over ~512KB in the browser (the single combined file had grown past 2MB).**
This is a real, size-only split — no entry content was changed, reworded,
or reordered. Every entry appears in its original file position, split only
at entry boundaries.

**Five real, pre-existing anomalies in the ledger's own numbering, predating
the splits (not introduced by them, not corrected by them — the discipline is
append-only, never edited):** entries #191-#201 physically appear in the
file AFTER #202-#203 (so parts 2 and 3 below have an overlapping labeled
range); #394 is used TWICE, for two different, real entries; **#824 is used
TWICE (two different entries, both in part 10); and #893 and #902 were never
used (skipped numbers, in part 11).** All are left exactly as they are in the
real historical record. (The older sealed parts' headers say "of 7" because
they predate parts 7-11; sealed parts are never edited, so they still do.)

## Naming convention

Sealed parts (closed, never appended to again) are named
`points_NN_XXX-YYY.md` — a fixed part number and their real, final entry
range. The **currently open** part is always named `points_active.md`
(no range in the name, so appending to it never requires a rename). When
`points_active.md` approaches ~350KB, it gets sealed with its own real
final range and a fresh, empty `points_active.md` starts.

## Parts, in real file order

| Part | File | Entries | Approx. range |
|---|---|---|---|
| 1 | [`points_01_001-083.md`](points_01_001-083.md) | 83 | #1-#83 |
| 2 | [`points_02_084-203.md`](points_02_084-203.md) | 108 | #84-#203 |
| 3 | [`points_03_191-297.md`](points_03_191-297.md) | 105 | #191-#297 |
| 4 | [`points_04_298-384.md`](points_04_298-384.md) | 87 | #298-#384 |
| 5 | [`points_05_385-480.md`](points_05_385-480.md) | 96 | #385-#480 |
| 6 | [`points_06_481-571.md`](points_06_481-571.md) | 91 | #481-#571 |
| 7 | [`points_07_572-652.md`](points_07_572-652.md) | 81 | #572-#652 |
| 8 | [`points_08_653-735.md`](points_08_653-735.md) | 83 | #653-#735 |
| 9 | [`points_09_736-810.md`](points_09_736-810.md) | 75 | #736-#810 |
| 10 | [`points_10_811-874.md`](points_10_811-874.md) | 65 | #811-#874 |
| 11 | [`points_11_875-945.md`](points_11_875-945.md) | 69 | #875-#945 |
| active | [`points_active.md`](points_active.md) | 1+ (growing) | #946 onward |

## Finding a specific entry

```bash
grep -l '^## 573\.' points/*.md      # which part has entry #573
grep -n '^## [0-9]*\.' points/*.md    # list every real entry across all parts
```

Most entries live in the part their number range suggests; check the
adjacent part first if a grep misses, given the real anomalies above.

## Session catch-up

Start with `current/latest.md`, then `points/points_active.md` (the open tail, fresh
since #946) AND the end of the most recent sealed part (part 11, `points_11_875-945.md`,
which holds the real recent work up to #945, e.g. `tail -c 70000 points/points_11_875-945.md`).
Older parts are historical background, read as needed.

## Status: what's done, pending, or just a thought direction

For a genuine done/pending/thought-direction breakdown (not just
where an entry lives, but what it actually means), see
`docs/shared/POINTS_STATUS_AUDIT.md` (#1-#330) and
`docs/shared/POINTS_STATUS_AUDIT_2.md` (#331-#592) and
`docs/shared/POINTS_STATUS_AUDIT_3.md` (#593-#996, 2026-10-06). Part 3's
quick reference is the current list of what is queued or open.

## Appending a new entry (for Claude, future sessions)

```bash
cat >> points/points_active.md << 'ENTRY'

## <next number>. <title>
...
ENTRY
```

Never append to a sealed part. Never edit any existing entry, in any
part — the ledger is append-only, full stop, same discipline as always.
