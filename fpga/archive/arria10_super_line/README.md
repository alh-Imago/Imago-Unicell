# Archive: older Arria 10 / super-shell line (9 Oct 2026, ledger #1036 addendum 21)

Alan's ruling: the core versions to KEEP are **v4, v4c, v4s, v4sa** (plus the unnumbered add-ons, and the v5/v5c set that lives in one file); the older versions, and the Arria 10 scripts that use them, are archived. Arria 10 itself is still a target card, so nothing here is deleted: it can be reclaimed.

- 293 files moved with `git mv` (history follows them): `verilog/` (older cores), `quartus/` (the old Quartus projects naming them), `scripts/` (the Arria 10 Tcl / shell scripts that used them).
- `MANIFEST.tsv` lists every move (old path, new path).
- Kept in place on purpose: the `unicell_super_v1..v9` shells and their testbenches (the composer and `nano/shell_compat_v1.py` list them), the current VIX carrier line (`unicell_vix_carrier_v1d` is the latest; v1 stays because many testbenches instantiate it).
- Paths inside the moved files were rewritten, and `tools/project_assemble_v1.py` also searches this folder, so the old Arria 10 projects still generate.

## Bring files back
    python3 tools/archive_move_v1.py --reclaim            # everything
    python3 tools/archive_move_v1.py --reclaim v3_       # only moves whose old path contains "v3_"

## What was checked (before = after)
The 22 tests that name these files give identical results before and after (one pre-existing failure and one "no tests" file, both unchanged); 7 Arria / live projects generate byte-identical output (the `strip_6` project fails the same way before and after); the 20 flex/sub scripts and the small-unit suites pass. Quartus itself is not available here, so the archived `.qsf` files were not compiled.
