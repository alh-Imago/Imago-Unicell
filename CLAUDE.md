# Imago UniCell — instructions for Claude sessions

Alan (the author) is not a programmer. Focus on concepts, architecture decisions and plain explanations; he often dictates by voice, so expect phonetic typos and interpret the intent.

## Start of every session

1. Read `current/START.md` (its "Current line" section first), then the top of `current/latest.md` (`head -c 12000`; about 170 KB, newest first; older state is in `current/latest_history.md`), the tail of the ledger (`tail -c 15000 points/points_active.md`, and the end of the newest sealed part, `points/points_12_946-1036.md`, which holds the recent work; the open file was sealed at #1036 and is small), and the newest update blocks at the top of `current/PLAN.md` (about 100 KB).
2. Check the toolchain before trusting any test run. Without `iverilog` the flex/sub suites print SKIP and exit 0, which looks like a pass (#965):
   `which iverilog yosys && python3 -c "import pytest, llvmlite"`
   Install steps are in `current/START.md`.
3. Tests: `tests/vm` has over 2,000 tests and a full run takes hours, so Alan runs them on demand or for what was touched.
   - Everyday: `python3 tools/quick_check_v1.py --changed` runs only the tests that name a file you changed (it also refuses to run without `iverilog`/`yosys` and fails any suite that prints SKIP).
   - Everything except the slow ones: `python3 tools/quick_check_v1.py`. Everything: add `--full` (run it in the background).
   - Refresh the slow-test list after a long run: `python3 -m pytest tests/vm -q -n 2 --log-durations=d.log`, then `python3 tools/update_slow_tests_v1.py d.log`.
   - `tests/test_status_files_v1.py` fails if `current/latest.md` does not mention the newest ledger entry: after adding a ledger entry, add its summary to `latest.md` and update its header line.

## Where things stand

The active line is the Tang Nano 20K with the sub (v4s) and flex (v4sa) cell families in `sub/`, the Flex-Sub assembler in `tools/`, and the VM's `FlexGrid`. The Arria 10 line is the reference for the VM's standard mode. `current/latest.md` is the live state; do not rely on counts or status written elsewhere without checking.

## Working rules

- RTL and measurements are ground truth. Check a claim against the actual file or a real measurement before logging it. Never state a guess as fact.
- Be honest and precise about scope. Report bugs and wrong hypotheses plainly.
- Clone proven files and increment the version; never edit them silently. Corrections get their own ledger entry that cross-references the original.
- The ledger (`points/`) is strictly numbered and append-only; never edit past entries. Finish a session with a check for unlogged decisions.
- Compose from existing cells before building new hardware ("prefer a core over a specialist cell"). Never remove a proven design; archive it instead.
- Check the archive (Onion) before building a new construction: prior art is real and has matched independent derivations line for line.

## Docs, manual and the download kit

- The docs are the source of truth. After editing any doc listed in `docs/build_manual.py`, run `python3 docs/build_manual.py` to regenerate `docs/manual.html`, and commit both.
- `python3 tools/make_package_v1.py --onion` builds the zip and `.onion` kit in `dist/` (git-ignored) from a clean commit, so rebuild it after committing.
- The tracked `.onion` files under `archeology/onion/` are archives. Do not modify them.

## Secrets

Never write a token, password or key into any file, commit message or note. If one appears in chat, tell Alan to revoke it.
