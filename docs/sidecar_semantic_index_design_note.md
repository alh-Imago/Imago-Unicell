# Sidecar Semantic Index — Design Note

**Status:** Concept / experiment, not yet built. Parallel track to native
Imago filesystem Pond design — validates the semantic-index idea on
conventional filesystems (Windows, Linux, any POSIX or NTFS host) ahead
of the native flat-pool filesystem being ready.

**Origin:** Arose from asking whether Onion (file wrapper/compression
tool) metadata could be attached without wrapping the file itself —
important because wrapping is only clean inside Imago's own native
filesystem, where the wrapper IS the file identity. On a conventional
OS, wrapping every file is invasive (breaks every other tool that
touches the file). This note describes a non-invasive alternative.

---

## Core idea

Two-tier index, sitting *beside* the real filesystem, touching no file
content:

```
Master index (upper tier)
    ↓ routes to
Local sidecar (per-directory, lower tier)
    ↓ contains
Full detail: file references, concept tags, confidence, hop-distances
```

Files themselves are never modified. A background watcher process
maintains the sidecars and propagates a subset of their content upward
to the master index.

This mirrors the Index Pond concept already designed for the native
Imago filesystem (concept graph, hop-distance ranking, mask-filter
queries) — the sidecar approach is that same design, minus the Onion
wrapper layer, running against someone else's filesystem instead of
the native one.

---

## Why not wrap files directly (recap)

- Breaks compatibility with every tool that isn't Onion-aware.
- Doesn't survive copy to other filesystems/tools untouched.
- NTFS Alternate Data Streams considered as a native "attach metadata
  without changing the file" mechanism — rejected for now because it's
  NTFS-specific (lost on FAT32/exFAT, mishandled by some backup/AV
  tools) and the project wants portability toward the native FS anyway.

---

## Local sidecar (per directory)

One metadata file per directory (granularity open — could be coarser,
e.g. per volume-subtree, if directory-level proves too fine-grained in
practice). Contains, per file in that directory:

- File reference (name/path within dir)
- Concept tags with hop-distance from primary concept (mirrors Index
  Pond's concept graph model)
- Confidence per tag
- Last modified / content hash (for reconciliation, see below)

This is the source of truth. Full detail lives here and only here.

## Master index (upper tier)

An inverted index: **term/concept → list of directories containing it**,
with no per-file detail. Deliberately lightweight.

**Tag promotion policy:** promote by hop-distance threshold, not fixed
count. E.g. promote all tags within 1 hop of a file's primary concept.
Rationale: a file with a generic primary concept may need more hops
promoted to be findable at the coarse tier; a highly specific file's
0-hop tag alone is enough since nothing broader would help route to it.
Avoids the "first N tags, whatever they are" trap, which either misses
deep/specific terms (too few promoted) or bloats the master file back
toward holding everything (too many).

**Master file scaling:** flat file is fine at small scale; plan to
shard/bucket (e.g. by term hash or first letters) once term count grows
past some threshold. Don't retrofit this under pressure — decide the
threshold and shard scheme before it's needed.

---

## Update propagation (the hard part)

- **Watcher mechanism:** inotify (Linux), ReadDirectoryChangesW
  (Windows) to catch create/delete/rename/modify events and keep local
  sidecars in sync.
- **Reconciliation as safety net:** event-driven watching will miss
  things (sleep/resume, crashes, external tools moving files while the
  daemon is down). Periodically reconcile by content hash rather than
  trusting the event stream alone.
- **Propagation to master — additions:** straightforward, push new
  distinct concept/term set from a directory up to master on sidecar
  change (real-time push is simplest but chatty; batched on a timer or
  on unmount is more efficient at the cost of brief staleness — a
  stale hit self-corrects on next sync, which is an acceptable
  tradeoff for search).
- **Propagation to master — removals (the tricky direction):** don't
  try to diff and infer deletions. Use a reference count per
  (term, directory) pair in the master index: increment on tag add,
  decrement on tag remove, drop the directory from that term's list
  when the count hits zero. Far simpler to reason about than trying to
  detect "this was the last instance of this term in this directory."

---

## Search flow: progressive / type-ahead

The depth question ("how far down the tags do you go before a finer
search misses something") is resolved by making search progressive
rather than picking one fixed cutoff:

1. First keystrokes → query hits master index only, matches coarse/
   promoted terms, returns candidate directories fast.
2. Additional keystrokes narrow the term → once the query is more
   specific than what master's coarse terms can resolve, search drops
   into the *already-narrowed* candidate directories' local sidecars
   for fine-grained matching.
3. Only the local sidecars of already-shortlisted directories get
   opened — never a full-tree sidecar scan on the fast path.

This means master's coarse terms don't need to be exhaustive or
perfectly chosen up front — they only need to be good enough to route
into the right handful of directories quickly. Correctness at the fine
grain always lives in the local sidecar.

**Residual risk, stated honestly:** if a deep/obscure term exists only
in a local sidecar and the query never passes through a promoted coarse
term first, the fast path won't find it. Mitigation: an explicit
"deep search" fallback that skips the master index and walks sidecars
directly — slower, but available when the person is confident a term
exists and the fast path came up empty.

---

## Worked example (from discussion)

Searching for a log file tied to a particular process:

- Master index holds the broad/top-level terms (e.g. "log", the
  process name if promoted within the hop-distance threshold) →
  routes to candidate directories.
- Typing further narrows toward the specific value (e.g. a particular
  crash signature or timestamp) → this finer term likely isn't in
  master, so the search drops into the local sidecars of the already-
  matched candidate directories to resolve the specific hit.

---

## Relationship to Windows Search / OS-level indexing

- **Windows Cache Manager** (block/page cache) — different layer
  entirely, no metadata/search overlap, not a concern.
- **Windows Search Indexer** (`Windows.edb`) — conceptually similar
  (watches filesystem, builds searchable index) but property/keyword
  based rather than concept-graph/semantic, and is a black box. This
  sidecar system would run as a parallel, independent indexer — worth
  deciding whether to exclude target directories from Windows Search to
  avoid two watchers doing redundant filesystem-watching work.

---

## Removable media

Watcher coverage is provably absent while a drive is disconnected — this
isn't a rare edge case to shrug off, it's the *normal, expected* state
every time removable media reconnects. Handled as its own case rather
than folded into the general reconciliation sweep:

**Identity: volume ID, never path.** The sidecar on the drive must be
self-contained and portable — file references relative to the drive's
own root, not absolute host paths (the same stick mounts as
`/media/alan/USB1` on one machine, `D:\` on another). On reconnect, the
system must positively recognise "this is the same drive I saw before"
using the volume's own ID (serial/UUID), never a mount point or drive
letter — those can differ across machines or even collide with an
unrelated drive. The volume ID only changes on reformat, which makes it
the one truly stable handle across the drive's whole working life.

**Flagged at the tier above.** The next meta block up (master index)
holds a simple flag: these file(s) live on removable media, identified
by volume ID. The fine-grained metadata itself stays on the media in its
own local sidecar — the master tier doesn't need to know more than
"ask this volume when it's present."

**Reconnect is the primary mechanism here, not a fallback.** Unlike the
general reconciliation sweep (a safety net for the rare missed-event
case on always-attached storage), this is the *only* path for removable
media — the watcher provably wasn't running while the drive was
elsewhere, so every reconnect is a full reconciliation by definition,
not an occasional correction.

**Cheap check first, hash only on suspicion.** mtime + size comparison
against the sidecar's last-known values is the first pass (same pattern
rsync/git use, for the same reason — a stat() call is nearly free,
hashing everything on every reconnect doesn't scale). Escalate to a real
content hash only when something looks off.

**What a clean mtime match actually means.** A match means *trusted for
re-indexing purposes* — it does not mean *verified unchanged*. Clock
skew between machines, or a tool that deliberately preserves timestamps,
could produce a clean mtime match over genuinely different content.
That's an acceptable risk here specifically because the sidecar's job is
search relevance, not integrity — it isn't trying to be Onion's own
CRC32/HMAC layer, which exists for a different, stricter purpose.

**Orphaned entries on reconnect.** If a sidecar entry can't be
correlated to anything present (no path match, no hash match anywhere
on the drive), it's ambiguous whether the file was deleted, renamed
+ edited beyond recognition, or the drive was edited on a machine
without the watcher running at all (metadata untouched, so the entry is
just stale but the file may well still exist under a different history
than the sidecar knows). Open decision, not yet resolved: delete the
orphaned entry outright, or flag it "stale, needs review" for some grace
period in case context reappears on a later reconnect. Leaning toward
flag-and-hold rather than silent delete, given the cost of guessing
wrong is losing tags with no way back, versus the cost of holding a
stale entry a while longer being just some sidecar bloat.

---

## Why this matters beyond the experiment

This is, in effect, the heuristic semantic-index Pond design (already
specified for the native Imago filesystem: concept graph, hop-distance
ranking, mask-filter queries, no path hierarchy) validated as a
standalone layer on top of *any* existing OS/filesystem, rather than
gated behind the native filesystem being finished. If it proves useful
here, it's a strong forward validation of the native design's core
premise — and opens the semantic search concept to immediate use on
current machines, independent of Arria 10/native-FS timelines.

**Gate:** none — this can be prototyped any time, independent of
FPGA/silicon work. Genuinely parallel track, not blocked by anything
else in the project.
