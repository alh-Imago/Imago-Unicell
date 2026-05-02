"""
test_fs_search.py — Heuristic Search Filesystem Tests
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from fs_search import SearchPond, SearchIndex, SearchEntry, SearchResult

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    results.append((status, name))
    if not ok:
        print(f"  [{status}] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [{status}] {name}")


# =============================================================================
print("\n=== SearchEntry scoring ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    fpath = os.path.join(d, "test.txt")
    open(fpath, 'w').close()

    e = SearchEntry(term="invoice january 2024",
                    file_path=fpath, tags=["finance", "Q1"])

    check_eq("score: exact match = 10",
             e.score("invoice january 2024"), 10)

    check("score: all words match > 0",
          e.score("invoice january") > 0)

    check("score: all words > partial",
          e.score("invoice january") > e.score("invoice"))

    check_eq("score: no match = 0",
             e.score("totally unrelated"), 0)

    check("score: tag match works",
          e.score("finance") > 0)

    check("score: partial word in term",
          e.score("jan") > 0)   # 'jan' in 'january'

    check("exists: real file",  e.exists)

    e_missing = SearchEntry(term="ghost file",
                            file_path="/nonexistent/ghost.txt")
    check("exists: missing file = False", not e_missing.exists)


# =============================================================================
print("\n=== SearchPond — indexing ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    f1 = os.path.join(d, "invoice_jan.pdf")
    f2 = os.path.join(d, "report_q1.docx")
    f3 = os.path.join(d, "secret.txt")
    for f in [f1, f2, f3]:
        open(f, 'wb').close()

    sp = SearchPond("docs", owner_id="user1")

    # Index f1 under multiple terms
    sp.index("invoice january 2024", f1, tags=["finance", "Q1"])
    sp.index("Q1 payment record",    f1, tags=["finance"])
    sp.index("jan invoice",          f1)

    # Index f2
    sp.index("quarterly report Q1 2024", f2, tags=["reports"])
    sp.index("Q1 summary",               f2)

    # Index f3 as hidden
    sp.index("secret document",          f3, hidden=True)

    check_eq("pond: 6 entries total", len(sp), 6)
    check_eq("pond: all_files has 3 files", len(sp.all_files()), 3)
    check_eq("pond: terms_for f1 has 3",
             len(sp.terms_for(f1)), 3)

    # PTT entries created
    check("pond: PTT has entries", len(sp._ptt) > 0)


# =============================================================================
print("\n=== SearchPond — searching ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    f1 = os.path.join(d, "invoice_jan.pdf")
    f2 = os.path.join(d, "report_q1.docx")
    f3 = os.path.join(d, "secret.txt")
    for f in [f1, f2, f3]:
        open(f, 'wb').close()

    sp = SearchPond("docs2", owner_id="user1")
    sp.index("invoice january 2024", f1, tags=["finance", "Q1"])
    sp.index("Q1 payment record",    f1, tags=["finance"])
    sp.index("quarterly report Q1",  f2, tags=["reports"])
    sp.index("secret document",      f3, hidden=True)

    # Basic search
    r1 = sp.search("invoice")
    check("search: invoice finds f1",
          any(r.entry.file_path == f1 for r in r1))

    # Best score first
    r2 = sp.search("Q1 payment record")
    check("search: best score first",
          len(r2) > 0 and r2[0].score >= r2[-1].score)

    # Hidden entries excluded by default
    r3 = sp.search("secret")
    check("search: hidden excluded by default", len(r3) == 0)

    # Hidden entries visible with flag
    r4 = sp.search("secret", include_hidden=True)
    check("search: hidden visible with flag", len(r4) > 0)

    # No match
    r5 = sp.search("completely unrelated xyz")
    check("search: no match returns empty", len(r5) == 0)

    # Score sorting
    r6 = sp.search("invoice january 2024")
    check("search: exact match scores highest",
          len(r6) > 0 and r6[0].score == 10)

    # Access count incremented
    e = r1[0].entry
    check("search: access_count incremented", e.access_count >= 1)


# =============================================================================
print("\n=== SearchPond — remove and verify ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    f1 = os.path.join(d, "file1.txt")
    f2 = os.path.join(d, "file2.txt")
    open(f1, 'w').close()
    open(f2, 'w').close()

    sp = SearchPond("test_remove", owner_id="owner")
    sp.index("term one",   f1)
    sp.index("term two",   f1)
    sp.index("other file", f2)

    check_eq("remove: 3 entries before", len(sp), 3)
    sp.remove_term("term one")
    check_eq("remove: 2 entries after remove_term", len(sp), 2)

    sp.remove_file(f1)
    check_eq("remove: 1 entry after remove_file(f1)", len(sp), 1)

    # Verify — all files exist
    v1 = sp.verify()
    check_eq("verify: 1 healthy", v1["healthy"], 1)
    check_eq("verify: 0 missing", v1["missing"], 0)

    # Delete file2 from host, verify again
    os.remove(f2)
    v2 = sp.verify()
    check_eq("verify: 1 missing after deletion", v2["missing"], 1)


# =============================================================================
print("\n=== SearchIndex — multi-pond ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    f1 = os.path.join(d, "invoice.pdf")
    f2 = os.path.join(d, "report.docx")
    f3 = os.path.join(d, "classified.pdf")
    for f in [f1, f2, f3]:
        open(f, 'wb').close()

    # Visible pond
    sp1 = SearchPond("public_docs",  owner_id="user")
    sp1.index("invoice 2024",  f1, tags=["finance"])
    sp1.index("annual report", f2, tags=["reports"])

    # Hidden pond
    sp2 = SearchPond("secret_docs", owner_id="user", hidden=True)
    sp2.index("classified report",  f3)
    sp2.index("invoice classified", f3)

    idx = SearchIndex()
    idx.add_pond(sp1)
    idx.add_pond(sp2)

    # Search across visible ponds only
    r1 = idx.search("invoice")
    check("index: visible search finds public file",
          any(r.entry.file_path == f1 for r in r1))
    check("index: hidden pond excluded",
          all(r.pond_name != "secret_docs" for r in r1))

    # Search including hidden ponds
    r2 = idx.search("invoice", include_hidden_ponds=True)
    check("index: hidden pond included with flag",
          any(r.pond_name == "secret_docs" for r in r2))

    # Target hidden pond directly
    r3 = idx.search_pond("secret_docs", "classified")
    check("index: search_pond targets hidden directly",
          len(r3) > 0 and r3[0].entry.file_path == f3)

    # Results merged and sorted
    r4 = idx.search("invoice", include_hidden_ponds=True)
    check("index: results sorted by score",
          len(r4) >= 2 and r4[0].score >= r4[-1].score)

    # Status
    st = idx.status()
    check_eq("index: 2 ponds in status", st["ponds"], 2)
    check_eq("index: 1 visible pond",    st["visible"], 1)
    check_eq("index: 1 hidden pond",     st["hidden"], 1)
    check_eq("index: 4 total entries",   st["total_entries"], 4)


# =============================================================================
print("\n=== SearchIndex — directory indexing ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    # Create some files
    for name in ["project_notes.txt", "budget_2024.csv",
                 "meeting_minutes.md", "photo.jpg"]:
        open(os.path.join(d, name), 'w').close()

    sp = SearchPond("auto_indexed", owner_id="owner")
    idx = SearchIndex()
    idx.add_pond(sp)

    # Index only text/document files
    count = idx.index_directory(sp, d,
                                 extensions=['.txt', '.csv', '.md'])
    check_eq("dir index: 3 files indexed (jpg excluded)", count, 3)

    # Search by filename stem
    r1 = sp.search("project notes")
    check("dir index: search by filename stem", len(r1) > 0)

    r2 = sp.search("budget")
    check("dir index: partial filename match", len(r2) > 0)

    # jpg not indexed
    r3 = sp.search("photo")
    check("dir index: excluded extension not indexed", len(r3) == 0)


# =============================================================================
print("\n=== PTT manifest for Cast/Ripple ===\n")
# =============================================================================

with tempfile.TemporaryDirectory() as d:
    f1 = os.path.join(d, "doc.txt")
    open(f1, 'w').close()

    sp = SearchPond("cast_test", owner_id="user")
    sp.index("important document", f1, tags=["urgent"])
    sp.index("doc urgent notes",   f1)

    summary = sp.ptt_summary()
    check("ptt: summary has entries",  summary["entries"] == 2)
    check("ptt: manifest not empty",   len(summary["manifest"]) == 2)
    check("ptt: manifest has term",
          any("important document" in m["term"]
              for m in summary["manifest"]))
    check("ptt: manifest has tags",
          any("urgent" in m["tags"]
              for m in summary["manifest"]))

    # Cast-style query simulation — has_tile matches term substring
    manifest = summary["manifest"]
    query = "important"
    matches = [m for m in manifest
               if query.lower() in m["term"].lower()]
    check("ptt: cast has_tile query works", len(matches) == 1)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
