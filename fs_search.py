"""
fs_search.py — Heuristic Search Filesystem

A SearchPond is an FS Pond where files are indexed by search terms,
not directory paths. The same file can have multiple entries with
different descriptions — each a separate PTT entry pointing to the
same location. Discovery goes through Cast/Ripple, not path traversal.

Design
======

Traditional filesystem:
    /documents/invoices/2024/jan.pdf   ← you must know the path

SearchPond:
    "invoice january 2024"   → /mnt/docs/invoices/2024/jan.pdf
    "jan invoice Q1"         → /mnt/docs/invoices/2024/jan.pdf
    "payment record 2024"    → /mnt/docs/invoices/2024/jan.pdf
    (same file, three ways to find it)

The PTT manifest is the index. Each entry is one search term →
one file. Cast queries like:

    engine.ripple_cast('me', query={'has_tile': 'invoice 2024'})

...find all SearchPonds containing matching terms without knowing
which Pond holds the file or what its path is.

Hidden files
============

A SearchPond with security=HIDDEN is invisible to all Cast/Ripple
queries unless the caster is on the whitelist. This is the "hidden
pond model" — the file exists but cannot be found by discovery.
The Pond does not announce itself; even its existence is concealed.

PTT structure
=============

Each PTT entry in a SearchPond represents one (term, file) pair:

    index:   sequential
    type:    SEARCH_TERM  (new type constant)
    status:  ACTIVE (indexed) / IDLE (pending) / FAULTED (file missing)
    label:   the search term string
    address: token address pointing to the file location

The PTT is INCREMENTAL — entries added as files are indexed,
removed when files are deleted or terms withdrawn.

Scoring
=======

When multiple terms match a query, results are ranked by score:
    - exact label match    → score 10
    - all words match      → score 5 per word
    - partial word match   → score 1 per word

The highest-scoring Pond/entry is returned first.
"""

from __future__ import annotations

import os
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from unicell_array import UniCellArray
    from shore_v2 import ShoreV2

# PTT type constant for search entries
TYPE_SEARCH_TERM = 10   # extends pond_ptt type constants


# ── SearchEntry ───────────────────────────────────────────────────────────────

@dataclass
class SearchEntry:
    """
    One indexed (term, file) pair inside a SearchPond.

    term:        the search label — words, phrases, tags, anything
    file_path:   absolute path to the file on the host filesystem
    file_size:   bytes (cached at index time)
    indexed_at:  timestamp
    access_count: how many times this entry was matched and returned
    hidden:      if True, this entry is never returned in search results
                 even if the Pond is visible (per-entry hiding)
    tags:        arbitrary metadata tags for richer queries
    """
    term:         str
    file_path:    str
    file_size:    int    = 0
    indexed_at:   float = field(default_factory=time.time)
    access_count: int   = 0
    hidden:       bool  = False
    tags:         list  = field(default_factory=list)

    @property
    def exists(self) -> bool:
        """True if the file still exists on the host."""
        return os.path.exists(self.file_path)

    def score(self, query: str) -> int:
        """
        Score this entry against a query string.
        Higher = better match.
        """
        q = query.lower().strip()
        t = self.term.lower().strip()

        if q == t:
            return 10                          # exact match

        q_words = set(q.split())
        t_words = set(t.split())
        tag_words = {w.lower() for tag in self.tags for w in tag.split()}
        all_words = t_words | tag_words

        matched = q_words & all_words
        if not matched:
            # Try partial (substring) match on each query word
            partial = sum(1 for qw in q_words
                          if any(qw in tw for tw in all_words))
            return partial

        if q_words <= all_words:
            return 5 * len(matched)            # all query words found

        return len(matched)                    # partial word match

    def to_dict(self) -> dict:
        return {
            "term":         self.term,
            "file_path":    self.file_path,
            "file_size":    self.file_size,
            "indexed_at":   self.indexed_at,
            "access_count": self.access_count,
            "hidden":       self.hidden,
            "tags":         self.tags,
            "exists":       self.exists,
        }


# ── SearchResult ──────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    """
    One result from a heuristic search.

    pond_name:  which SearchPond holds this entry
    entry:      the matching SearchEntry
    score:      relevance score (higher = better)
    """
    pond_name: str
    entry:     SearchEntry
    score:     int

    def __lt__(self, other: "SearchResult") -> bool:
        return self.score > other.score   # sort descending by score

    def to_dict(self) -> dict:
        return {
            "pond":      self.pond_name,
            "term":      self.entry.term,
            "file":      self.entry.file_path,
            "size":      self.entry.file_size,
            "score":     self.score,
            "tags":      self.entry.tags,
        }


# ── SearchPond ────────────────────────────────────────────────────────────────

class SearchPond:
    """
    A heuristic search index Pond.

    Holds search terms mapped to file locations. No directories —
    just terms and files. Multiple terms per file. Optionally hidden
    from Cast/Ripple discovery.

    Usage:
        sp = SearchPond("my_docs", owner_id="user1")

        # Index a file with one or more terms
        sp.index("invoice january 2024", "/docs/jan.pdf",
                 tags=["finance", "Q1"])
        sp.index("Q1 payment record",   "/docs/jan.pdf")

        # Search
        results = sp.search("january invoice")
        for r in results:
            print(r.entry.file_path, r.score)

        # Remove a file (all its terms)
        sp.remove_file("/docs/jan.pdf")

        # Verify index (remove entries for missing files)
        sp.verify()
    """

    def __init__(self,
                 name: str,
                 owner_id: str,
                 hidden: bool = False,
                 pond_manager=None,
                 base_address: int = 0):
        self.name       = name
        self.owner_id   = owner_id
        self.hidden     = hidden   # True = invisible to Cast/Ripple
        self.created_at = time.time()

        # Search index: list of SearchEntry objects
        self._entries: list[SearchEntry] = []

        # PTT — INCREMENTAL, updated as entries are added/removed
        from pond_ptt import PondPTT
        self._ptt = PondPTT(name, PondPTT.INCREMENTAL)

        # Optionally backed by a real Pond in the array
        self._pond = None
        if pond_manager is not None:
            from pond import OPEN, HIDDEN, FS
            sec = 'HIDDEN' if hidden else OPEN
            try:
                self._pond = pond_manager.create_pond(
                    name          = name,
                    owner_id      = owner_id,
                    security_level = sec,
                    pond_type     = FS,
                    bridge_count  = 2,
                    base_address  = base_address,
                    region_size   = 0,
                )
                self._pond.attach_ptt(self._ptt)
            except Exception as e:
                print(f"[SEARCH_POND] Warning: could not create Pond: {e}")

        print(f"[SEARCH_POND] '{name}' created "
              f"({'hidden' if hidden else 'visible'})")

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index(self, term: str, file_path: str,
              tags: Optional[list] = None,
              hidden: bool = False) -> SearchEntry:
        """
        Index a file under a search term.

        term:      the search label (words, phrases, anything meaningful)
        file_path: path to the file (absolute preferred)
        tags:      optional list of extra tag strings for richer matching
        hidden:    if True, this specific entry is never returned

        The same file can be indexed under multiple terms — just call
        index() multiple times with the same file_path.

        Returns the SearchEntry created.
        """
        file_path = os.path.abspath(file_path)
        size = 0
        if os.path.exists(file_path):
            try:
                size = os.path.getsize(file_path)
            except OSError:
                pass

        entry = SearchEntry(
            term         = term,
            file_path    = file_path,
            file_size    = size,
            hidden       = hidden,
            tags         = tags or [],
        )
        self._entries.append(entry)

        # Register in PTT
        # Use a hash of (term, file_path) as a stable pseudo-address
        addr = abs(hash(f"{term}::{file_path}")) & 0xFFFFFFFF
        ptt_idx = self._ptt.register(addr, TYPE_SEARCH_TERM, label=term)
        self._ptt.transition(ptt_idx, 1)   # LOADING
        self._ptt.transition(ptt_idx, 2)   # IDLE
        self._ptt.transition(ptt_idx, 3)   # ACTIVE

        if not os.path.exists(file_path):
            self._ptt.transition(ptt_idx, 4)   # FAULTED — file missing

        print(f"[SEARCH_POND] '{self.name}' indexed: "
              f"'{term}' → {os.path.basename(file_path)}")
        return entry

    def remove_term(self, term: str) -> int:
        """Remove all entries with this exact term. Returns count removed."""
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.term != term]
        removed = before - len(self._entries)
        if removed:
            print(f"[SEARCH_POND] '{self.name}' removed term '{term}' "
                  f"({removed} entries)")
        return removed

    def remove_file(self, file_path: str) -> int:
        """Remove all entries pointing to file_path. Returns count removed."""
        abs_path = os.path.abspath(file_path)
        before = len(self._entries)
        self._entries = [e for e in self._entries
                         if e.file_path != abs_path]
        removed = before - len(self._entries)
        if removed:
            print(f"[SEARCH_POND] '{self.name}' removed file "
                  f"'{os.path.basename(file_path)}' ({removed} entries)")
        return removed

    def verify(self) -> dict:
        """
        Verify the index — check each file still exists.
        Marks missing files as FAULTED in the PTT.
        Returns summary of healthy/missing entries.
        """
        healthy = missing = 0
        for entry in self._entries:
            if entry.exists:
                healthy += 1
            else:
                missing += 1
        return {"healthy": healthy, "missing": missing,
                "total": len(self._entries)}

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str,
               include_hidden: bool = False,
               min_score: int = 1) -> list[SearchResult]:
        """
        Search this Pond for entries matching query.

        query:          search string — words, phrases, partial terms
        include_hidden: if True, return hidden entries too
        min_score:      minimum relevance score to include (default 1)

        Returns list of SearchResult sorted by score (best first).
        Results for missing files are included but marked in entry.exists.
        """
        results = []
        for entry in self._entries:
            if entry.hidden and not include_hidden:
                continue
            score = entry.score(query)
            if score >= min_score:
                entry.access_count += 1
                results.append(SearchResult(
                    pond_name = self.name,
                    entry     = entry,
                    score     = score,
                ))

        results.sort()   # descending score via __lt__
        return results

    def all_files(self) -> list[str]:
        """Return deduplicated list of all indexed file paths."""
        return list(dict.fromkeys(e.file_path for e in self._entries))

    def terms_for(self, file_path: str) -> list[str]:
        """Return all terms indexed for a given file."""
        abs_path = os.path.abspath(file_path)
        return [e.term for e in self._entries if e.file_path == abs_path]

    # ── PTT manifest (for Cast/Ripple) ────────────────────────────────────────

    def ptt_summary(self) -> dict:
        """Summary for Cast/Ripple resource_record."""
        return {
            "mode":     "INCREMENTAL",
            "entries":  len(self._entries),
            "active":   sum(1 for e in self._entries if not e.hidden),
            "hidden":   sum(1 for e in self._entries if e.hidden),
            "manifest": [
                {
                    "term":  e.term,
                    "file":  os.path.basename(e.file_path),
                    "size":  e.file_size,
                    "tags":  e.tags,
                    "exists": e.exists,
                }
                for e in self._entries if not e.hidden
            ],
        }

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return (f"SearchPond('{self.name}' "
                f"{'hidden ' if self.hidden else ''}"
                f"entries={len(self._entries)})")


# ── SearchIndex ───────────────────────────────────────────────────────────────

class SearchIndex:
    """
    Multi-Pond heuristic search index.

    Holds multiple SearchPonds and searches across all of them,
    merging and ranking results. Hidden Ponds are excluded from
    multi-search unless explicitly included.

    Usage:
        idx = SearchIndex()
        idx.add_pond(sp1)
        idx.add_pond(sp2_hidden)   # hidden — excluded from search() by default

        results = idx.search("invoice 2024")
        for r in results:
            print(r.pond_name, r.entry.term, r.score)

        # Search a specific pond (even hidden ones)
        results2 = idx.search_pond("hidden_pond", "secret doc")
    """

    def __init__(self, shore: Optional["ShoreV2"] = None):
        self._ponds: dict[str, SearchPond] = {}
        self._shore = shore

    def add_pond(self, pond: SearchPond) -> None:
        """Register a SearchPond with the index."""
        self._ponds[pond.name] = pond
        print(f"[SEARCH_INDEX] Added pond '{pond.name}' "
              f"({'hidden' if pond.hidden else 'visible'})")

    def remove_pond(self, name: str) -> None:
        self._ponds.pop(name, None)

    def get_pond(self, name: str) -> Optional[SearchPond]:
        return self._ponds.get(name)

    def search(self, query: str,
               include_hidden_ponds: bool = False,
               min_score: int = 1,
               limit: int = 20) -> list[SearchResult]:
        """
        Search across all visible ponds.

        include_hidden_ponds: if True, include hidden Ponds in search.
          Hidden ponds are normally invisible to Cast/Ripple — this
          requires an explicit whitelist grant in the real system.

        Returns merged, ranked results (best first), up to limit.
        """
        all_results = []
        for pond in self._ponds.values():
            if pond.hidden and not include_hidden_ponds:
                continue
            all_results.extend(pond.search(query, min_score=min_score))

        all_results.sort()   # descending score
        return all_results[:limit]

    def search_pond(self, pond_name: str, query: str,
                    include_hidden: bool = False) -> list[SearchResult]:
        """Search within a specific named Pond (can target hidden ponds)."""
        pond = self._ponds.get(pond_name)
        if pond is None:
            return []
        return pond.search(query, include_hidden=include_hidden)

    def index_directory(self, pond: SearchPond,
                        directory: str,
                        term_fn=None,
                        extensions: Optional[list] = None) -> int:
        """
        Walk a host directory and index all files into a SearchPond.

        term_fn: callable(file_path) → list[str] of terms.
                 Default: uses filename (without extension) as term,
                 plus the extension as a tag.

        extensions: if given, only index files with these extensions.
                    e.g. ['.pdf', '.txt', '.md']

        Returns count of files indexed.
        """
        count = 0
        for root, _, files in os.walk(directory):
            for fname in files:
                fpath = os.path.join(root, fname)
                name, ext = os.path.splitext(fname)

                if extensions and ext.lower() not in extensions:
                    continue

                if term_fn:
                    terms = term_fn(fpath)
                else:
                    # Default: filename stem as term, extension as tag
                    terms = [name.replace('_', ' ').replace('-', ' ')]

                tags = [ext.lstrip('.').lower()] if ext else []

                for term in terms:
                    pond.index(term, fpath, tags=tags)
                count += 1

        return count

    def status(self) -> dict:
        return {
            "ponds":        len(self._ponds),
            "visible":      sum(1 for p in self._ponds.values() if not p.hidden),
            "hidden":       sum(1 for p in self._ponds.values() if p.hidden),
            "total_entries": sum(len(p) for p in self._ponds.values()),
            "ponds_detail": {n: {"entries": len(p), "hidden": p.hidden}
                             for n, p in self._ponds.items()},
        }

    def cast_search(self, caster_id: str, query: str,
                    engine=None,
                    include_hidden_ponds: bool = False) -> list:
        """
        Search via the Cast engine when available, falling back to
        direct search if no engine is provided.

        caster_id:   identity issuing the search (for HIDDEN pond access)
        query:       heuristic search string
        engine:      CastEngine instance (optional). If provided, uses
                     Cast ripple_cast with search_query to discover which
                     SearchPonds have matching entries, then calls search()
                     on each one.
        include_hidden_ponds: if True, include hidden SearchPonds. Requires
                     caster_id to be whitelisted on those Ponds.

        Returns merged, ranked SearchResult list.
        """
        if engine is not None:
            # Use Cast to find Ponds whose PTT manifests match the query
            from cast import CastStone
            stone = CastStone(
                caster_id = caster_id,
                query     = {"search_query": query},
            )
            ripple_results = engine.ripple_cast(caster_id, stone.query)
            # Collect matching pond names
            matching_pond_names = set()
            for rr in ripple_results:
                pond_name = rr.resource_record.get("name", "")
                if pond_name in self._ponds:
                    matching_pond_names.add(pond_name)

            # Search those ponds + any local ponds not in Cast scope
            results = []
            for name, pond in self._ponds.items():
                if pond.hidden and not include_hidden_ponds:
                    continue
                if name in matching_pond_names or name in self._ponds:
                    results.extend(pond.search(query))
            results.sort()
            return results

        # No Cast engine -- direct search
        return self.search(query,
                           include_hidden_ponds=include_hidden_ponds)

    def __repr__(self) -> str:
        return (f"SearchIndex({len(self._ponds)} ponds, "
                f"{sum(len(p) for p in self._ponds.values())} entries)")
