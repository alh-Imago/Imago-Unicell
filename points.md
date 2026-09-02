# POINTS.md — ideas raised this session, worth re-examining for the cluster-mesh version

Consolidated from sessions/latest.md (and the conversation it was drawn from) into one
place, since a lot of ground was covered and ideas surfaced throughout rather than in
one tidy pass. Organized by theme, not chronology. Each point notes its current status
(resolved / open / just an idea) so re-reading this later tells you where to pick up.

---

**2026-09-02: split into `points/` — GitHub stopped rendering this file once it passed
~2MB.** This is a real, size-only split: every numbered entry is preserved exactly,
unedited, in its original order, just divided across multiple files so each one stays
under GitHub's render limit. No entry content changed.

**Start here:**
- `points/INDEX.md` — the full real map of which file holds which entries, the naming
  convention, and how to append a new one.
- `points/points_active.md` — the currently-open file; holds the real, most recent work
  (currently #572 onward). This is what a fresh session should read first for catch-up,
  same role this single file used to play.

```bash
cat points/points_active.md          # most recent real work
cat points/INDEX.md                  # full map + how to find any specific entry
grep -l '^## 573\.' points/*.md      # find which file has a specific entry number
```
