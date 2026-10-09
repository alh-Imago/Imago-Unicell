#!/usr/bin/env python3
"""tools/archive_move_v1.py -- ledger #1036 addendum 21: move files into fpga/archive/arria10_super_line/ and put every reference right, or bring them back.

    python3 tools/archive_move_v1.py --apply LIST.txt     LIST.txt = one repo path per line (what to archive)
    python3 tools/archive_move_v1.py --reclaim [TEXT]     move archived files back (all, or only those whose path contains TEXT)

The archive keeps the repository layout:  fpga/verilog/X -> fpga/archive/arria10_super_line/verilog/X,  fpga/quartus/X -> .../quartus/X,  fpga/<script> -> .../scripts/<script>.
Every move is recorded in fpga/archive/arria10_super_line/MANIFEST.tsv (old path <TAB> new path) and done with `git mv`, so history follows the file.
References are rewritten (a) as repo-relative path strings in any text file, and (b) as relative paths inside the moved Quartus / Tcl / Verilog files themselves
(for example a project that named ../verilog/adder_v1.v, which stays put, now names ../../../verilog/adder_v1.v). Reclaiming moves the files back and undoes the
relative paths inside them; strings in OTHER files keep pointing at the archive (tools that search both places, such as project_assemble_v1.py, still work)."""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH = "fpga/archive/arria10_super_line"
MANIFEST = os.path.join(ARCH, "MANIFEST.tsv")
TEXT_EXT = (".py", ".v", ".vh", ".sv", ".tcl", ".sh", ".bat", ".qsf", ".sdc", ".json", ".txt", ".md", ".ys", ".cst", ".xdc", ".html")


def newpath(old):
    if old.startswith("fpga/verilog/"):
        return ARCH + "/verilog/" + old[len("fpga/verilog/"):]
    if old.startswith("fpga/quartus/"):
        return ARCH + "/quartus/" + old[len("fpga/quartus/"):]
    if old.startswith("fpga/") and old.count("/") == 1:
        return ARCH + "/scripts/" + old[len("fpga/"):]
    raise ValueError("not an archivable path: " + old)


def git(*a):
    return subprocess.check_output(["git"] + list(a), cwd=ROOT).decode()


def tracked_text():
    out = []
    for f in git("ls-files").split("\n"):
        if f and f.endswith(TEXT_EXT) and not f.startswith(("archeology/onion/", "tools/onion/", ".git/")):
            out.append(f)
    return out


REL_TOKEN = re.compile(r"(?<![\w/.-])((?:\.\./|\./)*[\w.-]+(?:/[\w.-]+)*\.(?:v|vh|sv|sdc|qsf|qip|sip|mif|tcl|py|sh|bat|json|stp|ip))(?![\w])")


def rewrite_relative(text, old_dir, new_dir, mapping, allfiles):
    """Inside a moved file: a token that names a real repo file relative to the OLD directory is re-expressed relative to the NEW directory (and to the target's own new place if it moved too)."""
    def fix(m):
        tok = m.group(1)
        cand = os.path.normpath(os.path.join(old_dir, tok)).replace(os.sep, "/")
        if cand in allfiles:
            tgt = mapping.get(cand, cand)
            rel = os.path.relpath(tgt, new_dir).replace(os.sep, "/")
            if tok.startswith("./") and not rel.startswith("."):
                rel = "./" + rel
            return rel if rel != tok else tok
        return tok
    return REL_TOKEN.sub(fix, text)


def apply(listfile):
    olds = [l.strip() for l in open(listfile) if l.strip() and not l.startswith("#")]
    allfiles = set(f for f in git("ls-files").split("\n") if f)
    olds = [o for o in olds if o in allfiles]
    mapping = {o: newpath(o) for o in olds}
    # 1. move
    for o, n in mapping.items():
        os.makedirs(os.path.join(ROOT, os.path.dirname(n)), exist_ok=True)
        git("mv", o, n)
    man = os.path.join(ROOT, MANIFEST)
    prev = open(man).read() if os.path.exists(man) else ""
    with open(man, "w") as f:
        f.write(prev + "".join(f"{o}\t{n}\n" for o, n in mapping.items()))
    # 2. relative paths inside the moved files
    for o, n in mapping.items():
        if not n.endswith(TEXT_EXT):
            continue
        p = os.path.join(ROOT, n)
        t = open(p, errors="surrogateescape").read()
        t2 = rewrite_relative(t, os.path.dirname(o), os.path.dirname(n), mapping, allfiles)
        if t2 != t:
            open(p, "w", errors="surrogateescape").write(t2)
    # 3. repo-relative strings everywhere else (longest first so a file path beats its folder)
    keys = sorted(mapping, key=len, reverse=True)
    changed = []
    moved_new = set(mapping.values())
    for f in tracked_text():
        if f in moved_new or f.startswith(ARCH + "/") or f.endswith((".md",)) and f.startswith(("points/", "current/")):
            continue
        p = os.path.join(ROOT, f)
        try:
            t = open(p, errors="surrogateescape").read()
        except OSError:
            continue
        t2 = t
        for k in keys:
            if k in t2:
                t2 = t2.replace(k, mapping[k])
        if t2 != t:
            open(p, "w", errors="surrogateescape").write(t2)
            changed.append(f)
    print(f"moved {len(mapping)} files to {ARCH}; rewrote path strings in {len(changed)} other files")
    for c in changed:
        print("   ", c)


def reclaim(text):
    man = os.path.join(ROOT, MANIFEST)
    rows = [l.rstrip("\n").split("\t") for l in open(man) if l.strip()]
    pick = [(o, n) for o, n in rows if not text or text in o]
    if not pick:
        print("nothing matches")
        return
    mapping_back = {n: o for o, n in pick}
    allfiles = set(f for f in git("ls-files").split("\n") if f)
    for o, n in pick:
        os.makedirs(os.path.join(ROOT, os.path.dirname(o)), exist_ok=True)
        git("mv", n, o)
    for o, n in pick:
        if o.endswith(TEXT_EXT):
            p = os.path.join(ROOT, o)
            t = open(p, errors="surrogateescape").read()
            allnow = (allfiles - set(mapping_back)) | set(mapping_back.values())
            t2 = rewrite_relative(t, os.path.dirname(n), os.path.dirname(o), mapping_back, allnow)
            if t2 != t:
                open(p, "w", errors="surrogateescape").write(t2)
    keep = [(o, n) for o, n in rows if (o, n) not in pick]
    open(man, "w").write("".join(f"{o}\t{n}\n" for o, n in keep))
    print(f"reclaimed {len(pick)} files")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply")
    ap.add_argument("--reclaim", nargs="?", const="")
    a = ap.parse_args()
    if a.apply:
        apply(a.apply)
    elif a.reclaim is not None:
        reclaim(a.reclaim)
    else:
        ap.print_help()
