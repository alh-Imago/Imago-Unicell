#!/usr/bin/env python3
"""tools/make_package_v1.py -- ledger #1036 addendum 20: build the one-stop download of Imago UniCell for people who do not use git.

    python3 tools/make_package_v1.py [--out dist] [--onion]

Makes, in dist/ (ignored by git):
  unicell-kit-<date>-<commit>.zip     every tracked file of the current commit (git archive), plus the Onion tool source (tools/onion, a separate project, GPL-3.0),
                                      plus START_HERE.txt. Unzip, then:  python3 quickstart.py --install
  unicell-kit-<date>-<commit>.onion   the same tree packed with the Onion tool itself (only with --onion; needs the `onion` command on PATH, built as in current/START.md),
                                      so the person who receives it can open it with the tool that is inside it. It carries Onion's searchable metadata block (name, author, description, tags, ref, commit, date, repo, licence, requires, start, contents, file count), readable with `onion -i` and found by `onion --search` without extracting. Round-trip checked (extract, compare every file's SHA-256).
The commit must be clean (everything committed): the package is made from the commit, not from loose files."""
import argparse
import datetime
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = """IMAGO UNICELL -- START HERE
===========================

1. You need Python 3.12 or newer (https://www.python.org/downloads/).
2. In this folder, run:

       python3 quickstart.py --install

   It makes a private environment inside this folder (nothing else on your computer is touched), installs what pip can supply, and runs a 20-second self-test.
   Windows: use  py quickstart.py --install   in a terminal opened in this folder.
3. Then read README.md, or run  python3 quickstart.py  to see what to do next.

Two programs pip cannot supply are listed, with the command for your system, only if you want to simulate hardware (iverilog) or load a bitstream onto the board (openFPGALoader).

tools/onion/ is the Onion archive tool (a separate project by the same author, GPL-3.0); the rest of the package is MIT (software) and CERN-OHL-P-2.0 (hardware). See LICENSE, LICENSE-HARDWARE, NOTICE.
"""


def sh(*a, **k):
    return subprocess.check_output(a, cwd=k.get("cwd", ROOT)).decode().strip()


def sha_tree(d):
    out = {}
    for dp, dn, fn in os.walk(d):
        for f in fn:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, d).replace(os.sep, "/")] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--onion", action="store_true", help="also pack a .onion with the Onion tool")
    a = ap.parse_args()
    if sh("git", "status", "--porcelain", "--untracked-files=no", "--ignore-submodules=all"):
        raise SystemExit("commit your changes first: the package is built from the current commit")
    commit = sh("git", "rev-parse", "--short", "HEAD")
    stamp = datetime.date.today().strftime("%Y%m%d")
    name = f"unicell-kit-{stamp}-{commit}"
    os.makedirs(a.out, exist_ok=True)
    stage = os.path.join(a.out, "_stage")
    shutil.rmtree(stage, ignore_errors=True)
    tree = os.path.join(stage, name)
    os.makedirs(tree)
    data = subprocess.check_output(["git", "archive", "HEAD"], cwd=ROOT)
    tarfile.open(fileobj=io.BytesIO(data)).extractall(tree, filter="data")
    onion_src = os.path.join(ROOT, "tools", "onion")
    if os.path.exists(os.path.join(onion_src, "setup.py")):
        dst = os.path.join(tree, "tools", "onion")
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(onion_src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "build", "*.so", "*.egg-info"))
    else:
        print("note: tools/onion is empty here (run: git submodule update --init tools/onion); the package will not carry the Onion tool")
    open(os.path.join(tree, "START_HERE.txt"), "w").write(START)
    zpath = os.path.join(a.out, name + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, dn, fn in os.walk(tree):
            for f in sorted(fn):
                p = os.path.join(dp, f)
                z.write(p, os.path.join(name, os.path.relpath(p, tree)))
    print(f"zip   {zpath}  {os.path.getsize(zpath)/1e6:.1f} MB")
    if a.onion:
        cmd = os.environ.get("ONION_CMD") or shutil.which("onion")
        if not cmd:
            raise SystemExit("no `onion` command: build the tool as in current/START.md (or set ONION_CMD)")
        opath = os.path.join(a.out, name + ".onion")
        if os.path.exists(opath):
            os.remove(opath)
        meta = [("name", "Imago UniCell kit"), ("author", "A. Hill"),
                ("description", "Imago UniCell: NOR-universal spatial computing. Source, Python VM and compiler, flex/sub cell families, the Tang Nano 20K small unit (SD card + SPI + ESP32 web sketch), tests, docs, and the Onion tool that packs this file."),
                ("tags", "unicell;imago;fpga;nor;spatial-computing;tang-nano-20k;esp32;verilog;python;onion-tool-included"),
                ("ref", f"imago-unicell-{commit}"), ("commit", commit), ("date", datetime.date.today().isoformat()),
                ("repo", "https://github.com/alh-Imago/Imago-Unicell"), ("licence", "MIT (software); CERN-OHL-P-2.0 (hardware); tools/onion GPL-3.0"),
                ("requires", "Python 3.12+ (everything else is installed by quickstart.py --install)"),
                ("start", "python3 quickstart.py --install   (read START_HERE.txt)"),
                ("contains", "UniCell source; tools/onion (the Onion tool, source, build as in current/START.md); docs/STATUS_MAP.md says what is live, experimental or archived"),
                ("files", str(sum(len(f) for _, _, f in os.walk(tree))))]
        cmdline = [cmd, "-c", tree, "-o", opath, "--no-default-ignores", "--no-audit"]
        for k, v in meta:
            cmdline += ["--meta", f"{k}={v}"]
        subprocess.check_call(cmdline)
        chk = os.path.join(stage, "_check")
        shutil.rmtree(chk, ignore_errors=True)
        os.makedirs(chk)
        subprocess.check_call([cmd, "-d", opath, "-o", chk])
        got = sha_tree(chk)
        want = sha_tree(tree)
        # the extract may or may not nest the folder name; compare by stripping a common prefix
        def norm(m):
            pre = name + "/"
            return {k[len(pre):] if k.startswith(pre) else k: v for k, v in m.items()}
        got, want = norm(got), norm(want)
        if got != want:
            miss = [k for k in want if k not in got][:5]
            bad = [k for k in want if k in got and got[k] != want[k]][:5]
            raise SystemExit(f"onion round-trip FAILED: {len(want)} files, missing {miss}, different {bad}")
        print(f"onion {opath}  {os.path.getsize(opath)/1e6:.1f} MB  (round trip verified: {len(want)} files identical)")
    shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    main()
