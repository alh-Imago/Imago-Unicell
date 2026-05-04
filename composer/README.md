# Imago UniCell Composer

A standalone visual design tool for building, sharing, and importing
UniCell programs and model libraries.

**No install. No server. Open `unicell_composer.html` in any browser.**

Current version: **v2** (2026-05-04)

---

## What it is

The Composer is the graphical entry point for the UniCell ecosystem.
It lets you:

- Place and wire cells visually, with full 32-bit gate_state control
- Drop pre-built model macros from the library panel
- Define lookup table cells (branding/dispatch pattern)
- Simulate designs in-browser before sending to hardware
- Export `.icm` files that load directly into the VM
- Import and verify `.icm` files from the community model library

---

## Controls

### Mouse

| Action | Gesture |
|:-------|:--------|
| Select cell | Click |
| Multi-select | Shift+click |
| Box select | Drag on empty canvas |
| Pan canvas | Middle-button drag, or Space+drag |
| Zoom | Scroll wheel (cursor-centred) |
| Start link | Drag from green output port (either tool mode) |
| Complete link | Release on blue input port (A or B) |

### Keyboard

| Key | Action |
|:----|:-------|
| `S` | Select tool |
| `L` | Link tool |
| `N` | New cell |
| `D` | Duplicate selection |
| `F` | Fit view |
| `Del` / `Backspace` | Delete selection |
| `Esc` | Deselect / cancel link |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+S` | Save .json |
| `Ctrl+A` | Select all |
| `Ctrl+O` | Open file |
| `Ctrl+D` | Duplicate |

---

## Panels

### Inspector

Shown when one or more cells are selected.

- **32-bit gate_state** — hex readout updates live. Four colour-coded
  bit groups: topology (blue), mode flags (teal), system flags (amber),
  debug flags (red).
- **16 presets** — PASS, NOT, NOR, AND, OR, NAND, XOR, XNOR, ZERO, ONE,
  NOT_A, SEL, LATCH, SENTRY, COUNTER, TABLE.
- **Address fields** — addrIn (A), addrInB (B, for SYNC_WAIT cells), addrOut.
  Duplicate addresses highlighted red; status bar shows conflict badge.
- **Lookup table editor** — appears when LATCH bit is set. Add/remove
  address→value rows, exported in `.icm` as `init` field.

### Library

All 25 models from `model_library.py` as clickable cards with description
and cell count. Groups: Integer, Float, Counters, I/O, OS Ponds.
Click any card to drop a model macro onto the canvas.

### Sim

Browser-local JavaScript tick engine for quick design validation.

- **Step** — advance 1 tick
- **10 ticks** — advance 10 ticks
- **Live** — auto-tick at 120ms intervals
- **Sim reset** — clear tick state and bus
- **Inject** — write a value to any bus address, then tick
- **Bus state** — all active bus addresses with current values.
  Amber highlight indicates values that changed on the last tick.
- **Cell overlay** — active output values shown on each card (`→N`)

Gates evaluated: PASS, NOT, NOR, AND, OR, NAND, XOR, XNOR, ZERO, ONE.
LOOP_MODE cells re-arm after each fire. Full unicell_array.py semantics
for the iCEBreaker bring-up gate set.

---

## File formats

### `.icm` — portable program image

Matches `ProgramImage.to_dict()` exactly. Loads directly into the VM:

```python
import json
from program_image import ProgramImage
from controller import ImagoController

with open("my_design.icm") as f:
    img = ProgramImage.from_dict(json.load(f))

ctrl = ImagoController()
ctrl.load_map(img.records, image_name=img.name)
```

### Integrity fields

Every `.icm` exported by the Composer contains:

**`record_hash`** — SHA-256 of the canonical record payload (fixed key
order: `alt, gs, in, inB, init, out, stor`, no whitespace). Identical
whether computed in the Composer (JS) or Python. On import, the Composer
recomputes and warns on mismatch.

**`security_context: null`** — intentionally blank. The system assigns
owner_id, pond_id, and security level at load time. A non-null value in
a shared `.icm` triggers a warning on import.

Verify a model in Python before loading:

```python
import json, hashlib

def verify_icm(path):
    with open(path) as f:
        d = json.load(f)
    if 'record_hash' not in d:
        print('WARNING: no record_hash — file predates integrity checking')
        return False
    canonical = json.dumps([
        {'alt':r.get('alt'),'gs':r['gs'],'in':r['in'],'inB':r.get('inB'),
         'init':r.get('init'),'out':r['out'],'stor':r.get('stor')}
        for r in d['records']
    ], separators=(',',':'))
    computed = hashlib.sha256(canonical.encode()).hexdigest()
    ok = computed == d['record_hash']
    print('PASS' if ok else 'FAIL', computed[:16]+'...')
    return ok
```

### `.json` — native canvas save

Saves the full canvas state including block positions and links.
Use for round-trip editing. Not directly loadable by the VM.

---

## Community model library

The `models/` directory is the shared model library.
Anyone can contribute a `.icm` file here.

### Submitting a model

1. Design your circuit in the Composer
2. Label your cells clearly
3. Export as `.icm` — hash is embedded automatically
4. Drop the file in `composer/models/<category>/`
5. Add an entry to `models/INDEX.md`
6. Open a pull request

### Naming convention

```
composer/models/<category>/<NAME>_v<version>.icm
```

### What makes a good community model

- Self-contained: all addresses relative, no external dependencies
- Documented: `name` and `description` fields clear
- Tested: runs correctly in the VM before submission
- Minimal: fewest cells that correctly implement the function
- Hashed: exported via the Composer so `record_hash` is embedded

---

## Examples

| File | Description | Cells |
|:-----|:------------|------:|
| `examples/not_gate.icm` | Single NOT gate | 1 |
| `examples/and_gate.icm` | Two-input AND (SYNC_WAIT) | 1 |
| `models/neural/LIF_NEURON_6CELL_v1.icm` | LIF neuron, latch model | 6 |

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

## Version history

| Version | Date | Changes |
|:--------|:-----|:--------|
| v1 | 2026-05-04 | Initial release — 32-bit gate_state, model library, explicit linking, .icm export |
| v1.1 | 2026-05-04 | SHA-256 record_hash, security_context field, integrity verification on import |
| v2 | 2026-05-04 | Multi-select, undo/redo (50-level), drag-from-port, browser simulation, address conflict detection, full keyboard shortcuts, cursor-centred zoom |

---

*Claudette v2.1 / unicell-latch variant*
