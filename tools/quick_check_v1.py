#!/usr/bin/env python3
"""tools/quick_check_v1.py -- the one-command check, for a person and for CI (ledger #1036 addendum 45).

    python3 tools/quick_check_v1.py                    the quick set: toolchain guard, top-level suites, tests/vm without the slow ones
    python3 tools/quick_check_v1.py --changed          ONLY the tests that name a file you changed (see below): the everyday run
    python3 tools/quick_check_v1.py --changed --base HEAD~1   compare with another commit instead of origin/main
    python3 tools/quick_check_v1.py --changed --dry-run       show which tests that would pick, run nothing
    python3 tools/quick_check_v1.py --full             everything, including the slow tests (long: tests/vm has over 2,000 tests)
    python3 tools/quick_check_v1.py --no-vm            only the toolchain guard and the top-level suites

--changed: "changed" = what differs from origin/main (committed or not) plus new untracked files. A changed test file runs
itself; a changed source file (nano/, tools/, sub/, fpga/verilog/, ...) runs every test file whose text contains its name
(without the extension). It is a text match, so it can pick too many tests but it will not miss one that names the file; a
test that reaches the file only through another module is not found, so run the full set before a release. Changed docs run
nothing, except that the instant status check (tests/test_status_files_v1.py) always runs.

Why the guard exists (#965): without iverilog the flex/sub suites print SKIP and exit 0, which looks like a pass. So this tool
  1. FAILS if iverilog, yosys or a needed Python package is missing (it never skips quietly), and
  2. FAILS if any top-level suite prints SKIP, whatever its exit code.
Exit code 0 only when everything selected ran and passed."""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = ["iverilog", "yosys"]
PY = ["pytest", "numpy", "pycparser", "llvmlite"]
SOURCE_EXT = {".py", ".v", ".sv", ".json", ".tcl", ".sh", ".ino", ".h"}


def guard():
    miss = [t for t in TOOLS if not shutil.which(t)] + [m for m in PY if importlib.util.find_spec(m) is None]
    if miss:
        print("TOOLCHAIN MISSING: " + ", ".join(miss))
        print("  apt-get update && apt-get install -y iverilog yosys ; pip install pytest numpy pycparser llvmlite")
        print("  (without them the suites skip and look like a pass: refusing to continue)")
        return False
    print("toolchain ok: " + ", ".join(TOOLS + PY))
    return True


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.split("\n") if r.returncode == 0 else None


def changed_files(base=None):
    if not base or not git("rev-parse", "--verify", "-q", base + "^{commit}"):
        base = "origin/main" if git("rev-parse", "--verify", "-q", "origin/main") else "HEAD"
    diff = git("diff", "--name-only", base) or []
    new = git("ls-files", "--others", "--exclude-standard") or []
    return base, sorted({f for f in diff + new if f.strip()})


def all_test_files():
    out = []
    for d in ("tests", os.path.join("tests", "vm")):
        p = os.path.join(ROOT, d)
        out += [os.path.join(d, f) for f in sorted(os.listdir(p)) if f.startswith("test_") and f.endswith(".py")]
    return out


def pick_tests(changed):
    tests = all_test_files()
    text = {}
    for t in tests:
        try:
            text[t] = open(os.path.join(ROOT, t), encoding="utf-8", errors="replace").read()
        except OSError:
            text[t] = ""
    picked, why = [], {}
    for f in changed:
        stem, ext = os.path.splitext(os.path.basename(f))
        if f in text:
            hit = [f]
        elif ext in SOURCE_EXT and len(stem) >= 5 and not f.startswith(("archeology/", "docs/")):
            hit = [t for t in tests if stem in text[t]]
        else:
            hit = []
        why[f] = hit
        picked += [t for t in hit if t not in picked]
    return picked, why


def run_top(files, timeout):
    bad = []
    for f in files:
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, f], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            out = r.stdout + r.stderr
            why = "exit %d" % r.returncode if r.returncode else ("prints SKIP" if "SKIP" in out else "")
        except subprocess.TimeoutExpired:
            why = "timed out after %d s" % timeout
        print(f"  {'FAIL' if why else 'ok  '} {f}  ({time.time() - t0:.0f} s){'  -- ' + why if why else ''}")
        if why:
            bad.append(f)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="include the slow tests")
    ap.add_argument("--changed", action="store_true", help="only the tests that name a changed file")
    ap.add_argument("--base", default=None, help="with --changed: compare with this commit or branch (default origin/main)")
    ap.add_argument("--dry-run", action="store_true", help="with --changed: show what would run, run nothing")
    ap.add_argument("--no-vm", action="store_true", help="skip tests/vm")
    ap.add_argument("--timeout", type=int, default=900, help="seconds allowed per top-level suite")
    a = ap.parse_args()
    if not guard():
        return 2
    vm_files = None
    if a.changed:
        base, changed = changed_files(a.base)
        picked, why = pick_tests(changed)
        print(f"changed since {base}: {len(changed)} file(s)")
        for f in changed:
            print(f"  {f}  ->  " + (", ".join(os.path.basename(t) for t in why[f][:6]) + (" ..." if len(why[f]) > 6 else "") if why[f] else "no test names it"))
        top = [t for t in picked if t.startswith("tests" + os.sep + "test_") or os.path.dirname(t) == "tests"]
        vm_files = [t for t in picked if t not in top]
        guard_suite = os.path.join("tests", "test_status_files_v1.py")      # instant; always run, so latest.md cannot fall behind
        if os.path.exists(os.path.join(ROOT, guard_suite)) and guard_suite not in top:
            top.append(guard_suite)
        print(f"selected: {len(top)} top-level suite(s), {len(vm_files)} tests/vm file(s)")
        if a.dry_run:
            return 0
    else:
        top = [os.path.join("tests", f) for f in sorted(os.listdir(os.path.join(ROOT, "tests"))) if f.startswith("test_") and f.endswith(".py")]
    rc = 0
    if top:
        print("top-level suites:")
        bad = run_top(top, a.timeout)
        rc = 1 if bad else 0
    else:
        bad = []
    if not a.no_vm and (vm_files is None or vm_files):
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        if vm_files is not None:
            cmd += vm_files                      # touched files: run all of their tests, slow ones too
        else:
            cmd += ["tests/vm"] + ([] if a.full else ["-m", "not slow"])
        if importlib.util.find_spec("xdist"):
            cmd += ["-n", "auto"]
        print("tests/vm: " + " ".join(cmd[3:]))
        rc = max(rc, 1 if subprocess.run(cmd, cwd=ROOT).returncode else 0)
    print("RESULT: " + ("FAILED" + (": " + ", ".join(bad) if bad else "") if rc else "all passed"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
