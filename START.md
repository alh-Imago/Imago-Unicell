# Session Start

## Every session — do this first

```bash
git pull
cat docs/ARCHITECTURE.md     # READ THIS FIRST — the overall scheme and design intent
cat docs/addressing_note.md  # flat cell address + block→die→card→backplane hierarchy
cat PLAN.md
cat sessions/latest.md
```

**Read `docs/ARCHITECTURE.md` before anything else.** The session log carries
facts and current state, not the architecture's shape. Reconstructing the design
from the RTL/gates misses intent and wastes a session. The doc is the source of
truth for: flat single-point cell addressing (block boundary = bus boundary),
bridges as dumb physical wire (routing is done by the destination address in the
cell, not the wire), the block→die→card→backplane address hierarchy (Shore owns
everything above the local cell address), and the design principle that richness
lives in layers above the cell, never in more cell bits.

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
