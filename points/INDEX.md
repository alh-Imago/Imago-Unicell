# points.md — INDEX

**The canonical, append-only, numbered decision ledger for this project,
split across multiple files purely because GitHub will not render a file
over ~512KB in the browser (the single combined file had grown past 2MB).**
This is a real, size-only split — no entry content was changed, reworded,
or reordered. Every entry appears in its original file position, split only
at entry boundaries.

**Two real, pre-existing anomalies in the ledger's own numbering, predating
this split (not introduced by it, not corrected by it — the discipline is
append-only, never edited):** entries #191-#201 physically appear in the
file AFTER #202-#203 (so parts 2 and 3 below have an overlapping labeled
range); and #394 is used TWICE, for two different, real entries. Both are
left exactly as they are in the real historical record.

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
| active | [`points_active.md`](points_active.md) | 21+ (growing) | #572 onward |

## Finding a specific entry

```bash
grep -l '^## 573\.' points/*.md      # which part has entry #573
grep -n '^## [0-9]*\.' points/*.md    # list every real entry across all parts
```

Most entries live in the part their number range suggests; check the
adjacent part first if a grep misses, given the two real anomalies above.

## Session catch-up

Start with `points/points_active.md` — it holds the real, most recent
work. Older parts are historical background, read as needed.

## Appending a new entry (for Claude, future sessions)

```bash
cat >> points/points_active.md << 'ENTRY'

## <next number>. <title>
...
ENTRY
```

Never append to a sealed part. Never edit any existing entry, in any
part — the ledger is append-only, full stop, same discipline as always.
