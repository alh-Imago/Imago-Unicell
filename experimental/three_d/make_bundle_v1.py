#!/usr/bin/env python3
"""experimental/three_d/make_bundle_v1.py -- build the SEPARATE download kit for the 3D work: dist/imago-3d-kit-<date>-<commit>.zip (ledger #1314).

Not part of tools/make_package_v1.py (the main kit): the 3D kit is its own, small, standard-library-only bundle -- composer, placer, ICM-3D, the toy model, its manual and its tests.
Built from a CLEAN commit (files are read from git HEAD, never from the working tree, and the build refuses if any of them has uncommitted changes), so the kit is exactly what was committed.
The kit keeps the repository's folder layout for the files it needs, so every path in the code works unchanged.

    python3 experimental/three_d/make_bundle_v1.py            # build, then unpack and run the kit's own tests as a check
    python3 experimental/three_d/make_bundle_v1.py --no-verify
dist/ is git-ignored. Rebuild after committing. Rebuild manual3d.html first if a document changed (build_manual_3d_v1.py).
"""
import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOP = "imago-3d-kit"
FILES = [
    "LICENSE", "LICENSE-HARDWARE", "NOTICE",
    "nano/ui_theme_v1.py",
    "tools/nor_adder_3d_v1.py",
    "docs/measurements/nor_adder_3d_v1.json",
    "experimental/three_d/composer3d_v1.py", "experimental/three_d/composer3d_v1.js",
    "experimental/three_d/placer3d_v1.py",
    "experimental/three_d/icm3d_v1.py", "experimental/three_d/icm3d_v2.py",
    "experimental/three_d/experimental_3d_nor_v2.py",
    "experimental/three_d/MANUAL_3D.md", "experimental/three_d/manual3d.html",
    "experimental/three_d/ICM_3D_FORMAT.md", "experimental/three_d/CELL_AUDIT_6_FACE.md",
    "experimental/three_d/build_manual_3d_v1.py",
    "tests/vm/test_composer3d_v1.py", "tests/vm/test_placer3d_v1.py", "tests/vm/test_icm3d_v1.py", "tests/vm/test_icm3d_v2.py",
]
README_FIRST = """IMAGO UNICELL 3D KIT -- START HERE
==================================

An EXPLORATION of a six-face (north, south, east, west, up, down) cell grid, for stacked-chip designs:
  * a 3D Composer: floor plan, rotatable 3D view, and a depth slider that shows one layer and fades the rest
  * an automatic placer for netlists
  * ICM-3D v2, a file format for six-face designs
There is NO 3D hardware, NO 3D RTL and NO card to run this on. It runs in a software toy model. Read MANUAL_3D.html (section 1) before relying on anything.

1. You need Python 3.12 or newer (https://www.python.org/downloads/). Nothing else: the kit uses only Python's standard library.
2. In this folder, run:

       python3 run_composer.py

   Your browser opens at http://127.0.0.1:7422 . Stop with Ctrl+C.   Windows: use  py run_composer.py
3. Open MANUAL_3D.html (double-click it) for the manual; the same manual is at /manual inside the running composer.

Other commands (details in the manual):
   python3 run_placer.py --example adder --layers 3 --out adder.3d.json     place the NOR adder automatically
   python3 run_tests.py                                                      check the kit works (needs: pip install pytest)
Ready-made files are in examples/ : the adder netlist, the adder placed automatically, and the adder as ICM-3D (JSON and binary).

This kit is separate from the main Imago UniCell package. Software: MIT. Hardware design: CERN-OHL-P-2.0. See LICENSE, LICENSE-HARDWARE, NOTICE.
"""
RUN_COMPOSER = '''#!/usr/bin/env python3
"""Start the 3D Composer (see README_FIRST.txt). Extra options are passed on: --port N, --no-browser, --example adder_auto, --open FILE."""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv[0] = os.path.join(HERE, "experimental", "three_d", "composer3d_v1.py")
runpy.run_path(sys.argv[0], run_name="__main__")
'''
RUN_PLACER = '''#!/usr/bin/env python3
"""Run the automatic placer (see MANUAL_3D.html section 5). Options are passed on: --example adder | --netlist FILE, --layers N, --seed N, --out FILE."""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv[0] = os.path.join(HERE, "experimental", "three_d", "placer3d_v1.py")
runpy.run_path(sys.argv[0], run_name="__main__")
'''
RUN_TESTS = '''#!/usr/bin/env python3
"""Run the kit's own tests (needs pytest: pip install pytest)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    import pytest
except ImportError:
    sys.exit("pytest is not installed: run  pip install pytest  and try again")
sys.exit(pytest.main(["-q", os.path.join(HERE, "tests", "vm"), "-p", "no:cacheprovider"]))
'''


def git(*a):
    return subprocess.check_output(("git",) + a, cwd=ROOT)


def run(cmd, cwd, **k):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **k)


def main(argv=None):
    ap = argparse.ArgumentParser(description="build the 3D download kit")
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args(argv)
    dirty = git("status", "--porcelain", "--", *FILES).decode().strip()
    if dirty:
        sys.exit("refusing to build: uncommitted changes in files the kit contains:\n" + dirty + "\ncommit them first (and rebuild manual3d.html if a document changed)")
    missing = [f for f in FILES if subprocess.run(["git", "cat-file", "-e", "HEAD:" + f], cwd=ROOT, capture_output=True).returncode]
    if missing:
        sys.exit("not in git HEAD: " + ", ".join(missing))
    commit = git("rev-parse", "--short", "HEAD").decode().strip()
    date = datetime.date.today().strftime("%Y%m%d")
    work = tempfile.mkdtemp(prefix="i3dkit_")
    kit = os.path.join(work, TOP)
    try:
        for f in FILES:
            dst = os.path.join(kit, f)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(git("show", "HEAD:" + f))
        for name, text in (("README_FIRST.txt", README_FIRST), ("run_composer.py", RUN_COMPOSER), ("run_placer.py", RUN_PLACER), ("run_tests.py", RUN_TESTS)):
            with open(os.path.join(kit, name), "w", newline="\n") as fh:
                fh.write(text)
        shutil.copy(os.path.join(kit, "experimental/three_d/manual3d.html"), os.path.join(kit, "MANUAL_3D.html"))
        shutil.copy(os.path.join(kit, "experimental/three_d/MANUAL_3D.md"), os.path.join(kit, "MANUAL_3D.md"))
        # ready-made examples, produced BY THE KIT'S OWN CODE (so the kit is proven to run before it is zipped)
        ex = os.path.join(kit, "examples")
        os.makedirs(ex)
        three = os.path.join(kit, "experimental", "three_d")
        gen = ("import json,sys\nsys.path.insert(0,%r)\nimport placer3d_v1 as pl, icm3d_v2 as icm\nc,n=pl.adder_netlist()\n"
               "json.dump(pl.netlist_doc(c,n),open('adder.net.json','w'),indent=1)\nd,rep=pl.place(c,n,layers=3,seed=1,keep=3)\n"
               "json.dump(d.export(),open('adder.auto.3d.json','w'),indent=1)\ndoc=icm.from_design(d,'adder_auto')\n"
               "json.dump(doc,open('adder.auto.icm3d.json','w'),indent=1)\nopen('adder.auto.icm3d','wb').write(icm.pack(doc))\n"
               "print(rep['total'],'cells in all,',rep['verify']['trials'],'verified runs')\n") % three
        r = run([sys.executable, "-I", "-c", gen], ex)
        if r.returncode:
            sys.exit("could not build the examples with the kit's own code:\n" + r.stdout + r.stderr)
        print("examples:", r.stdout.strip())
        if not a.no_verify:
            r = run([sys.executable, "run_tests.py"], kit)
            tail = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
            if r.returncode:
                sys.exit("the kit's own tests FAILED when unpacked on their own:\n" + r.stdout[-3000:] + r.stderr[-1000:])
            print("kit's own tests, run from the unpacked kit:", tail)
        # manifest, checksums
        names = []
        for dp, dn, fn in os.walk(kit):
            dn[:] = sorted(d for d in dn if d not in ("__pycache__", ".pytest_cache"))
            names += [os.path.relpath(os.path.join(dp, f), kit) for f in sorted(fn) if not f.endswith(".pyc")]
        names.sort()
        sums = "".join("%s  %s\n" % (hashlib.sha256(open(os.path.join(kit, n), "rb").read()).hexdigest(), n) for n in names)
        with open(os.path.join(kit, "SHA256SUMS"), "w", newline="\n") as fh:
            fh.write(sums)
        with open(os.path.join(kit, "BUILD_INFO.txt"), "w", newline="\n") as fh:
            fh.write("Imago UniCell 3D kit\nbuilt %s from git commit %s\nfiles: %d\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), commit, len(names) + 2))
        names += ["SHA256SUMS", "BUILD_INFO.txt"]
        out = os.path.join(ROOT, "dist")
        os.makedirs(out, exist_ok=True)
        zpath = os.path.join(out, "imago-3d-kit-%s-%s.zip" % (date, commit))
        if os.path.exists(zpath):
            os.remove(zpath)
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for n in sorted(names):
                zi = zipfile.ZipInfo(TOP + "/" + n, (2026, 10, 23, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o755 if n.startswith("run_") else 0o644) << 16
                z.writestr(zi, open(os.path.join(kit, n), "rb").read())
        print("wrote %s (%d KB, %d files)" % (os.path.relpath(zpath, ROOT), os.path.getsize(zpath) // 1024, len(names)))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
