# Imago UniCell Composer

A standalone visual design tool for building, sharing, and importing
UniCell programs and model libraries.

**No install. No server. Open `unicell_composer.html` in any browser.**

---

## What it is

The Composer is the graphical entry point for the UniCell ecosystem.
It lets you:

- Place and wire cells visually, with full 32-bit gate_state control
- Drop pre-built model macros (INT32_ADDER, FP32_MULTIPLIER, counters, I/O, OS ponds)
- Define lookup table cells (branding/dispatch pattern)
- Export `.icm` files that load directly into the VM via `ProgramImage.from_dict()`
- Import `.icm` files from the community model library

---

## File formats

### `.icm` — portable program image

The export format matches `ProgramImage.to_dict()` exactly:

```json
{
  "program_id": "a1b2c3d4",
  "name": "my_design",
  "os_name": "Claudette",
  "os_version": "1.3",
  "created_at": 1234567890.0,
  "models": ["INT32_ADDER"],
  "ranges": [],
  "records": [
    {"gs": 1, "in": 4096, "out": 4097, "inB": null, "alt": null, "stor": false, "init": null}
  ],
  "composer_meta": { ... }
}
```

`composer_meta` contains the canvas layout for round-trip editing.
It is ignored by the VM loader — the VM only reads `records` and `models`.

### Loading into the VM

```python
import json
from program_image import ProgramImage
from controller import ImagoController

with open("my_design.icm") as f:
    img = ProgramImage.from_dict(json.load(f))

ctrl = ImagoController()
ctrl.load_map(img.records, image_name=img.name)
ctrl.run(...)
```

---

## Community model library

The `models/` directory is the shared model library.
Anyone can contribute a `.icm` file here.

### Submitting a model

1. Design your circuit in the Composer
2. Give it a clear name and label your cells
3. Export as `.icm`
4. Drop the file in `composer/models/`
5. Add an entry to `models/INDEX.md`
6. Open a pull request

### Model file naming convention

```
composer/models/<category>/<NAME>_v<version>.icm
```

Examples:
```
composer/models/logic/XOR_32BIT_v1.icm
composer/models/neural/LIF_NEURON_6CELL_v1.icm
composer/models/crypto/CRC32_v1.icm
composer/models/signal/FIR_FILTER_8TAP_v1.icm
```

### What makes a good community model

- Self-contained: all addresses relative, no external dependencies
- Documented: `name` field describes what it does
- Tested: runs correctly in the VM before submission
- Minimal: uses the fewest cells that correctly implement the function

---

## Examples

The `examples/` directory contains worked designs:

| File | Description |
|:-----|:------------|
| `examples/not_gate.icm` | Minimal NOT gate — single cell |
| `examples/and_gate.icm` | Two-input AND — SYNC_WAIT + AND_V2 |
| `examples/lif_neuron.icm` | 6-cell LIF neuron (latch model) |

---

## Roadmap

The Composer is version 1. Things that will grow with community use:

- **Model registry**: index of contributed models with metadata search
- **Address auto-assignment**: automatic non-overlapping address allocation
- **Sub-circuit grouping**: collapse a selection into a named macro
- **Simulation mode**: run a tick in-browser (JS port of unicell_array.py)
- **Diff view**: compare two versions of the same design
- **Version tags**: `v1`, `v2` tracking on model files
- **FPGA target hints**: annotate which models fit on iCEBreaker vs larger FPGAs

---

## Architecture note

The Composer produces `.icm` files. The `.icm` format is the universal
portable program representation for the Imago architecture:

```
Composer (.html)  →  .icm  →  VM (Python simulator)
                   →  .icm  →  iCEBreaker (FPGA)
                   →  .icm  →  Future ASIC
```

Programs written today in the Composer run on silicon that does not
exist yet. Models shared now are nearly silicon-ready when the hardware
catches up.

---

*Claudette v2.1 / unicell-latch variant*
*Tool version: 1.0 (2026-05-04)*
