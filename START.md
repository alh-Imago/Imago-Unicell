# Session Start

## Every session — do this first

```bash
git pull
cat PLAN.md
cat sessions/latest.md
```

PLAN.md is the single source of truth for what needs doing.
sessions/latest.md is the current state of the codebase.

## Current hardware
- iCEBreaker: silicon validated, v2.3 protocol
- Arria 10 GX1150 (IEI Mustang-F100): replacement for dead Kintex-7, arriving soon
- Quartus Prime 25.1: installed and licensed on F:\Q

## Test suite
```bash
PYTHONPATH=. python tests/vm/test_fp_tiles.py      # 187/187
PYTHONPATH=. python tests/vm/test_compiler_int32.py # 101/101
```

## Key files
- unicell.v / unicell_array.v — Verilog ground truth
- gate_states.py — bit constants (must match Verilog)
- compiler_int32.py — INT32 compiler
- fp_tiles.py — tile library
- controller.py — VM

## Git
```bash
git config user.email "alan@imago"
git config user.name "Alan"
git remote set-url origin https://<PAT>@github.com/alh-Imago/Imago-Unicell.git
```
