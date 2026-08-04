# Imago Native Filesystem Design
*Status: design phase — implementation after Arria 10 bring-up*
*Last updated: 2026-06-16*

---

## Core principle

No directory tree. No path hierarchy. No filenames as primary identity.

Files are blocks in a flat pool. Identity lives in the index, not the
path. Collections are not folders — they are saved mask filters over
the index. A file appears in multiple collections simultaneously without
being copied or linked. Collections cost nothing to create and nothing
to delete.

This is not a POSIX filesystem. It does not try to be. POSIX compatibility
is a bridge layer for legacy tools, not the native model.

---

## Stack

```
SATA Pond         (AHCI block device — raw storage)
    ↓
Filesystem Pond   (native format — flat block pool + Onion wrapper layer)
    ↓
Index Pond        (heuristic semantic index — wrapper metadata cache)
    ↓
Application Pond  (user-visible collections, search, access control)
```

USB and other devices handled by class drivers (HID, MSC, Audio, CDC,
UVC). Device Pond = driver inside + bridge for Shore registration.

---

## File identity

Every file is an Onion-wrapped block. The wrapper IS the identity:

```
[Onion header]     magic, version, size, CRC32
[Audit block]      compression recipe, algorithm chain
[Meta block]       semantic metadata — domain, concepts, owner, tags...
[Payload]          compressed (and optionally encrypted) content
```

The meta block is readable without decompressing the payload. This is
the key architectural property — the index never needs to open files,
only read their wrappers.

File identity = hash of wrapper metadata + payload CRC32. Stable across
moves, renames, re-tagging (metadata updates don't change payload hash).

---

## The Index Pond

A heuristic semantic index over wrapper metadata. Not a filename index —
a concept index.

**What it stores (per file):**
- File reference (block address in the flat pool)
- Wrapper metadata fields (domain, concepts, type, confidence, owner...)
- Concept graph distances (precomputed hops to related concepts)
- Access token hash (for whitelist mask evaluation)
- Last accessed, last modified timestamps

**What it does not store:**
- File contents
- Full paths (there are none)
- Directory membership (there are none)

**Query model:**
A search is a mask filter over index fields, ranked by semantic distance.

```
query: "energy data, high confidence, my files only"

mask:
  concepts WITHIN 2 HOPS OF "energy" in concept graph
  AND confidence >= 0.85
  AND whitelist_mask MATCHES current_token

result: ranked list of file references
  rank 1: concepts containing "kinetic_energy" (0 hops)        score 1.0
  rank 2: concepts containing "thermal_energy" (1 hop, 0.95)   score 0.95
  rank 3: concepts containing "reaction_enthalpy" (1 hop, 0.85) score 0.85
  ...
```

Semantic distance from the concept graph degrades gracefully. Exact
concept match scores 1.0. One hop scores by path confidence. Two hops
scores by product of path confidences. Results ranked, not binary.

The index is rebuilt from wrappers on mount. Loss of the index is not
data loss — it is rebuilt from the files themselves. The files are the
source of truth; the index is a cache.

---

## Collections

A collection is a saved mask filter. Nothing more.

```python
collection_auction_q2 = {
    "name": "Auction Q2 2026",
    "mask": {
        "type": "sql_table",
        "domain": "FinTrix/Auction",
        "created_after": "2026-04-01",
        "created_before": "2026-06-30",
    }
}
```

Creating a collection costs one index write (the mask definition).
Deleting a collection costs one index delete. No files move. No links
are created or destroyed.

A file appears in every collection whose mask it satisfies simultaneously.
A file can be in zero collections (invisible to saved searches but still
in the index and findable by direct query).

---

## Whitelist mask and privacy

The whitelist mask is a standard mask field evaluated by the Index Pond
before returning any result. Files not matching the current token's
whitelist are not returned — they do not appear in search results,
collections, or directory listings.

**Three levels of privacy, composable:**

**Level 1 — Masked only (fast, no encryption overhead)**
File exists in the pool. Wrapper readable by the filesystem. Index Pond
evaluates whitelist mask and does not return the file to unauthorised
queries. To other users' searches the file does not exist.
Good for: drafts, working files, anything not ready to share.

**Level 2 — Wrapper visible, content encrypted**
Wrapper is readable by anyone with index access. The file appears in
searches — its domain, concepts, and metadata are discoverable. But the
payload is Onion-encrypted; opening it requires the key.
Good for: shared catalogues where discoverability is useful but access
is controlled. A colleague can see "there is auction data here" without
being able to read it.

**Level 3 — Masked + encrypted**
Whitelist mask hides the file from unauthorised indexes. Content is also
encrypted. Two independent protection layers.
Good for: genuinely private data. The file does not appear to exist AND
cannot be read even if the block is found directly.

**Composing the masks:**

```
base search mask:   type="sql_table" AND confidence >= 0.85
whitelist mask:     owner_token=hash(user_A) OR shared_token=hash(group_X)

combined result:    only tables visible to user_A or group_X are returned
```

No central access control list. No permission system to misconfigure.
The whitelist token is in the wrapper; the index evaluates it; files
that don't match don't appear.

---

## Hardware-rooted identity (Security Module integration)

The whitelist token can be derived from hardware identity rather than
a password:

- Fabric topology hash (rolling — changes on reconfiguration)
- Biometric + NFC token combination
- Hardware attestation from UniCell Security Module

Token generation: hardware-rooted, in the Security Module.
Mask evaluation: software, in the Index Pond.
Content protection: Onion encryption layer.

Three independent mechanisms. Each does one job. None depends on the
others for its basic function. Together they compose a complete security
model with no single point of failure:

- Compromise the mask? Content still encrypted.
- Steal the encrypted file? Mask prevents index discovery; key required
  to open.
- Clone the hardware token? Rolling topology hash invalidates it on next
  reboot/reconfiguration.

No central authority. No ACL to maintain. No permission system. Identity
is in the hardware; visibility is in the index; protection is in the
wrapper.

---

## Onion wrapper as filesystem infrastructure

The Onion format was designed as a compression tool. Applied across the
filesystem it becomes the data layer's identity system.

**Every file is self-describing:**
The wrapper declares what the file contains before it is opened. The
index reads wrappers; it never reads payloads during search.

**The index IS the collection of wrappers:**
Rebuild the index by reading all wrappers in the block pool. No separate
metadata store to maintain or corrupt. The files are the source of truth.

**Catalogue query without opening files:**
A query over 10,000 files reads 10,000 wrappers. Each wrapper read is
O(wrapper size) — kilobytes. Total cost: milliseconds. Compare to
content-scanning search: O(total compressed size) — gigabytes. Hours.

**Structured data discovery:**
SQL tables wrapped with domain/concepts/confidence metadata are
discoverable by concept proximity. A query for "thermal data" finds
tables containing `thermal_energy`, `temperature`, `reaction_enthalpy`
(one hop), `kinetic_energy` (one hop via energy hub) — ranked by
semantic distance, without opening any file.

---

## SQL table integration

SQL tables (SQLite) stored in the filesystem as Onion-wrapped blocks.
The fabric does not store tables — it processes them. Tables stream
through the fabric row by row.

**TableBridge (PTT layer):**
- Reads rows from SQLite via standard SQL
- Packages rows as cell map inputs (one row = one bus transaction)
- Streams results back and writes to output table
- Cell count stays bounded — same 200-cell pipeline processes 50,000
  rows sequentially. DDR streaming handles the data volume.

**Wrapper for SQL tables (convention):**
```bash
onion -c mytable.sqlite mytable.onion \
  --meta type="sql_table" \
  --meta domain="FinTrix/Auction" \
  --meta concepts="C001,C047,C089" \
  --meta rows="47832" \
  --meta schema="lot_number,estimate_low,estimate_high,hammer_price" \
  --meta confidence="0.91" \
  --meta source="auction_2026_q2"
```

The inference engine reads the wrapper to decide whether to open the
table. Concept IDs in the wrapper are concept graph nodes — the engine
knows which mechanisms this data can inform without reading a single row.

---

## Concept graph integration

The Index Pond holds the precomputed concept graph path cache alongside
the wrapper index. A search query specifying a concept resolves to all
related concepts within N hops, weighted by path confidence. Files are
ranked by the minimum graph distance from the query concept to any
concept declared in their wrapper.

This is heuristic search in the literal sense — not keyword matching,
not embedding similarity, but graph distance over a declared ontology
of physical and abstract concepts with known conversion rates.

The heuristic degrades honestly. When graph distance is large, confidence
is low, and the ranking reflects that. The user sees not just results
but how confident the system is that each result is relevant.

---

## What is not in scope

- POSIX compatibility at the native layer (bridge layer only)
- Directory trees (collections replace them entirely)
- Filename-based identity (wrapper hash is identity)
- Central metadata server (index rebuilt from files on mount)
- Permission ACLs (whitelist masks replace them)
- Inode tables (flat block pool with wrapper-based addressing)

---

## Implementation gate

After Arria 10 bring-up and open source release. The design is settled;
the implementation depends on having a stable hardware target and a
community to validate the approach.

SATA Pond (AHCI) is the first storage target. The Index Pond runs on
the host initially; fabric acceleration of index queries is a later
optimisation once the basic model is proven.
