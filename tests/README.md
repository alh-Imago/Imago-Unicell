# Tests

## FPGA Hardware Tests (`tests/fpga/`)
Run against live iCEBreaker hardware via UART. Require OSS-CAD Suite and a programmed iCEBreaker.

### Silicon-validated (current protocol)
```cmd
python tests/fpga/test_sync_wait.py COM4 0x2A5     # 16/16 PASS
python tests/fpga/test_new_opcodes.py COM4 0x2A5   # 26/29 PASS
python tests/fpga/test_all.py COM4 0x2A5           # runs both suites
```

### Legacy tests (pre-v2.1 protocol — may need updating)
- test_chain.py, test_ring.py, test_latch.py etc.

## VM / Software Tests (`tests/vm/`)
Run against the Python VM — no hardware needed.

```bash
pytest tests/vm/
```

Or individually:
```bash
python tests/vm/test_compiler.py
python tests/vm/test_pond.py
```
