#!/usr/bin/env python3
"""tests/test_status_files_v1.py -- the catch-up files must not fall behind or grow without limit (ledger #1036 addendum 45).

Two failures this prevents, both of which happened:
  * current/latest.md stopped at addendum 12 while the ledger went on to 43 (found 10 Oct 2026);
  * the files a new session must read grew until reading them cost a session its context
    (latest.md reached 1 MB; points_active.md is meant to be sealed at ~350 KB, GitHub stops rendering a file at ~512 KB).
Run:  python3 tests/test_status_files_v1.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "points", "points_active.md")
LATEST = os.path.join(ROOT, "current", "latest.md")
FAILS = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def newest_label(text):
    """The label of the LAST entry in the ledger, e.g. 'addendum 44' or '#1037' (append-only: the last heading is the newest)."""
    last = None
    for ln in text.splitlines():
        m = re.match(r"\*\*Addendum (\d+)\b", ln) or re.match(r"#{2,3} #\d+ addendum (\d+)\b", ln)
        if m:
            last = "addendum " + m.group(1)
            continue
        m = re.match(r"#{2,3} #(\d+)\b", ln)
        if m:
            last = "#" + m.group(1)
    return last


def main():
    ledger = open(LEDGER, encoding="utf-8").read()
    latest_raw = open(LATEST, encoding="utf-8").read()
    label = newest_label(ledger)
    check(label is not None, "found the newest ledger entry in points/points_active.md: %s" % label)
    check(label is not None and label.lower() in latest_raw[:30000].lower(),
          "current/latest.md mentions the newest ledger entry (%s) in its first 30 KB -- add a summary and update its header line" % label)
    kb = len(latest_raw.encode()) / 1024
    check(kb <= 300, "current/latest.md is %.0f KB (limit 300): move its oldest part to current/latest_history.md" % kb)
    kb = os.path.getsize(LEDGER) / 1024
    check(kb <= 450, "points/points_active.md is %.0f KB (seal at ~350 KB per points/INDEX.md; limit 450, GitHub stops rendering at ~512)" % kb)
    if 350 < kb <= 450:
        print("NOTE points_active.md is %.0f KB: time to seal it as the next points_NN part (see points/INDEX.md)" % kb)
    print("RESULT:", "FAILED" if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
