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

## Offline / detached media provisioning (jukebox and manual alike)

The removable-media case above assumed occasional, human-initiated
reconnect. Two related but distinct scenarios extend the same design
rather than needing a new one:

**Automated (robotic jukebox / tape or optical changer):** search must
work while nothing is physically loaded — a robot arm shouldn't need to
cycle through hundreds of volumes just to answer a query. This requires
a **persistent host/controller-level cache** of the fine-grained sidecar
detail, not just detail living on the media itself as in the plain
removable-media case. Search is always answered from this cache;
physical media handling only triggers once a specific file is actually
chosen for retrieval, never during search itself. The jukebox mechanism
itself (SCSI medium-changer commands, `mtx`, vendor APIs — no single
standard across hardware) sits behind a thin adapter, kept deliberately
decoupled from the search/index core, which only ever emits "load
volume with this ID" and doesn't need to know how that happens on any
given piece of hardware.

**Manual (a person's shelf of labelled disks/CDs/drives):** the same
persistent cache applies — search works across the *entire* collection
with nothing plugged in, since detail already lives in the cache from
the last time each volume was seen. The difference from the automated
case is what "load the volume" means: **the master/cache entry needs a
human-readable label alongside the volume ID**, not just the ID. A
UUID means nothing to someone looking through a box of CDs; whatever's
physically written on the disc or case (a name the person chose, not
one the system invented) has to be captured and surfaced back to them
at retrieval time. Volume ID stays the stable machine identity (survives
relabelling); the human label is a separate, editable field for exactly
this purpose.

**One shared "provision and confirm" abstraction underneath both.**
A search result that resolves to "found — on volume X, not currently
present" produces the same kind of request either way: a pending
retrieval waiting on that volume becoming available. What fulfils it
differs by actuator, not by mechanism:
  - Manual: the request surfaces the human label ("insert disk 'Family
    Photos 2019'"), and fulfilment is a simple confirm — a key press
    once the person has found and inserted it.
  - Automated: the request is a signal to the changer controller, which
    physically loads the volume and signals back completion itself, no
    person involved.

Same state machine either way: pending → (provisioning happens) →
confirmed/loaded → file access proceeds. Only the actuator swaps.

**Where the two genuinely diverge: error and timeout handling.** A
robotic changer failing is a hardware fault — rare, and there's no
ambiguity about what happened. A person being asked for a disk may
simply not find it, give up, or the disk may be lost or damaged —
common, and not a fault condition at all. The manual path needs a real
"cancel / can't find it" outcome as a normal, expected result rather
than an error state, while the automated path can reasonably treat
failure-to-load as exceptional.

This is the same shape of problem HSM (hierarchical storage management)
systems solve for tape/optical cold storage at scale — index searchable
without touching the media, physical retrieval only on actual access.
Worth being in that company rather than inventing the pattern fresh.

---

## Wrapped-archive metadata (ZIP/7z with an added metadata entry)

A separate but related idea, from the Onion side of this same
discussion: rather than a new Onion-format wrapper *around* an existing
archive, add a small metadata entry *inside* an existing ZIP/7z archive
itself, stored uncompressed. This keeps the file a fully valid,
ordinary archive to any tool with zero Onion awareness -- the addition
is purely additive, not a new shell around the old format.

**Why this is cheap, not a full unzip.** ZIP already carries its own
lightweight index -- the central directory, a small structure at the
end of the file listing every entry's name/offset/size/method -- built
for exactly this kind of targeted lookup. If the added metadata entry
is stored `STORED` (uncompressed) rather than `DEFLATED`, reading it is
a direct byte-range read at a known offset: no decompression library
invoked, no other entry touched. Same complexity class as Onion's own
TOC/META reads -- O(metadata size), not O(archive size). Established
precedent for exactly this pattern already exists: DOCX/XLSX/PPTX add
`docProps/core.xml` to a ZIP the same way; EPUB stores its first entry
uncompressed specifically so it can be read with zero parsing; JAR
carries `META-INF/MANIFEST.MF` identically.

**Known asymmetry: doesn't fall out for free on 7z.** 7z's default
"solid" compression groups multiple files into one compressed block for
better ratio -- an added metadata entry could require partially
decompressing that block to reach it, unless deliberately kept in its
own separate, non-solid block at write time. Not automatic the way
ZIP's independently-addressable entries make it; a deliberate choice
each time a 7z archive is wrapped this way.

**How this integrates with the sidecar system -- not a new mechanism,
a consequence of two already-decided ones.** Once Onion's own
`read_summary()`/`search()` understands this wrapped-metadata entry,
the daemon's watched-directories base table already does the "read
once, hold in memory, don't reopen until told to rescan" behaviour
automatically -- that's what the base table is for, applied to whatever
`read_summary()` recognises, no special-casing needed for this format.
On the sidecar side, a promoted/cached copy of a wrapped ZIP's metadata
is subject to the same mtime+size reconciliation check already designed
for plain files -- same honest caveat restated: a clean mtime match
means *trusted for indexing*, not *verified unchanged*.

**Precedence stays the same rule as before, one level deeper.** Query
through the sidecar and its promoted copy answers instantly, no file
touched -- a performance mirror, not authoritative. Query through Onion
directly and it reads the wrap itself, which is always the real
authority, even for an archive that was never natively `.onion`. Same
"whichever door you walked through wins" rule from the removable-media/
provisioning sections, applied here rather than a new special case.

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
