# Tests

*Updated 2026-10-06 (ledger #986). The old version of this file described
iCEBreaker UART tests from the archived full-cell line.*

## Before you trust a run: check the toolchain

The flex/sub suites and many `tests/vm` tests drive real RTL through
`iverilog`, and the cost tests call `yosys`. **When `iverilog` is
missing, those suites print `SKIP` and exit 0, which looks like a
pass** (ledger #965: a fresh sandbox had none of the tools installed).
Check first:

```bash
which iverilog yosys
python3 -c "import pytest, llvmlite"
```

Versions used for the recorded results: iverilog 12.0, yosys 0.33,
pytest 9.x, llvmlite 0.50. On Debian/Ubuntu: `apt-get update && apt-get
install -y iverilog yosys`, then `pip install pytest llvmlite`. Six `tests/vm`
tests also need `pip install apycula==0.32 msgpack networkx` (the Tang MAN
tests and one layout test); without them they skip.
Place-and-route measurements also need `yowasp-nextpnr-himbaechel-gowin`
(pip). The apt `nextpnr-gowin` package only covers GW1N, which is the
wrong family for the Tang Nano 20K (#889).

## `tests/vm/` — the VM, compiler, formats and FlexGrid (pytest)

```bash
python3 -m pytest tests/vm -q
```

This is the main suite: about 1,760 tests as of #986. It includes the
FlexGrid mirror tests (`test_flex_grid_*_v1.py`), which check the VM
against the **generated flex RTL** at several widths, and the fp32
stage tests (`test_fp32_*_v1.py`).

## `tests/test_flexsub_*.py` and `tests/test_icm_min_bit_width_v1.py` — the sub/flex families

Each is a self-contained script: it prints its checks and exits
non-zero on failure. Run them all:

```bash
for t in tests/test_*.py; do python3 "$t" || echo "FAILED: $t"; done
```

They cover the step-1 assembler (`test_flexsub_assemble_v1.py`), the
ICM netlist extractor, the `sub` and `flex` generators (corpus,
branch, merge, sequencer, level sources, loops, add-ons, multiplier
ladder), the `-nowidelut` flag, and the `min_bit_width` header flag.

## `tests/tools/` — the front end, MAN generator, assembler, Walker and Composer (pytest)

```bash
python3 -m pytest tests/tools -q
```

`test_composer_v1.py` (#1003, #1004) checks that an imported ICM file
re-exports exactly, that a hand move keeps the fp16 adder correct in
FlexGrid and in the generated RTL (that one needs iverilog), that refused
moves change nothing, that a design built from scratch and two library
blocks joined port to port compute the right sums in FlexGrid, that ports
and roles (latch set/clear, branch outcomes, sequencer with no input) are
respected, and the `/composer` page and its JSON API.

## Per-cell Verilog benches

Every sub/flex cell has a self-checking bench beside it in
`sub/verilog/tb_*.v`. The Arria 10 line's benches are in `tests/fpga/`
and `fpga/verilog/`. Run one with iverilog, for example:

```bash
cd sub/verilog
iverilog -g2012 -o /tmp/tb tb_merge_cell_v4sa.v merge_cell_v4sa.v && vvp /tmp/tb
```

## Legacy

`tests/fpga/test_*.py` (UART tests against an iCEBreaker),
`tests/vm/legacy*/` and `tests/design/legacy_full_cell/` belong to the
archived full-cell line. They are kept for reference and are not part
of the current runs.
