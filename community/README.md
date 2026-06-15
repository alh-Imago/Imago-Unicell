# UniCell Community Contributions

This folder is the community space for UniCell format definitions,
frontends, models, and bridge tiles. Anyone can contribute. Everything
here is versioned, hashed, and searchable.

---

## What Lives Here

Each subfolder is a **domain contribution** — a self-contained package
that defines a compute domain and makes it available to the entire
UniCell ecosystem.

```
community/
  README.md               ← this file (contribution guide)
  REGISTRY.md             ← index of all contributions (auto-updated)
  mathtrix/               ← MathTrix (reference implementation)
  biotrix/                ← BioTrix (genomics, proteomics)
  chemtrix/               ← ChemTrix (chemistry, periodic table)
  phystrix/               ← PhysTrix (physics, SI units, constants)
  fintrix/                ← FinTrix (finance, currencies, instruments)
  general/                ← General (BCD, fixed-point, utilities)
  your_domain/            ← your contribution goes here
```

---

## What a Contribution Needs

Every domain folder must contain exactly these files:

```
your_domain/
  README.md       ← what this domain does and how to use it
  format.py       ← FormatDefinition subclass(es)
  frontend.py     ← domain language (models, operations)  [optional]
  models/         ← .json model files
    example.json  ← at least one example model
  MANIFEST.json   ← metadata (who/what/when/version/hash)
```

`README.md` and `format.py` and `MANIFEST.json` are **required**.
`frontend.py` and models are optional but strongly encouraged.

---

## MANIFEST.json Format

Every contribution has a `MANIFEST.json` that describes it completely.
This is the searchable index entry — it must be accurate and complete.

```json
{
  "name":        "BioTrix",
  "domain":      "BioTrix",
  "version":     "0.1.0",
  "created":     "2026-06-09",
  "updated":     "2026-06-09",
  "author":      "your_name_or_handle",
  "license":     "MIT",
  "description": "Genomics and proteomics frontend for UniCell",
  "requires":    "imago-vm>=0.2.0",
  "formats":     ["DNA_4Base", "RNA_4Base", "Amino20"],
  "models":      ["dna_complement", "gc_content", "codon_frequency"],
  "bridges":     [],
  "hash":        "sha256:abc123...",
  "tags":        ["genomics", "biology", "dna", "rna", "protein"],
  "homepage":    "",
  "contact":     ""
}
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✓ | Display name |
| `domain` | ✓ | Domain string (must match format.py domain field) |
| `version` | ✓ | Semantic version (MAJOR.MINOR.PATCH) |
| `created` | ✓ | ISO date of first submission |
| `updated` | ✓ | ISO date of last change |
| `author` | ✓ | Your name or handle |
| `license` | ✓ | License identifier (MIT, Apache-2.0, etc.) |
| `description` | ✓ | One sentence what this does |
| `requires` | ✓ | Minimum imago-vm version |
| `formats` | ✓ | List of FormatDefinition names defined here |
| `models` | ✓ | List of model IDs in models/ folder |
| `bridges` | ✓ | List of bridge tile names (empty if none) |
| `hash` | ✓ | SHA-256 of all files in this folder |
| `tags` | ✓ | Search keywords |
| `homepage` | — | Project URL (optional) |
| `contact` | — | Contact address (optional) |

The `hash` is computed by `community_tools.py hash your_domain/`.
It covers all `.py`, `.json`, and `.md` files in the folder.
Regenerate it whenever you change anything.

---

## format.py Requirements

Your `format.py` must:

1. Import from `cell_format.py` at the repo root
2. Define one or more `FormatDefinition` subclasses
3. Register them with `FormatRegistry.get_default()`
4. Be importable with `PYTHONPATH=.` from the repo root

```python
# community/your_domain/format.py

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cell_format import FormatDefinition, FormatRegistry

class MyFormat(FormatDefinition):
    name             = "MyFormat"
    description      = "One sentence description"
    domain           = "MyDomain"
    bits_per_symbol  = 8
    symbols_per_word = 4
    cell_words       = 1
    boundary_in      = "MY_PACK"
    boundary_out     = "MY_UNPACK"
    valid_tiles      = ["MY_OP1", "MY_OP2"]
    symbol_lut       = {"A": 1, "B": 2}
    CONSTANTS        = {"my_const": 42}

# Register on import
FormatRegistry.get_default().register_class(MyFormat)
```

Read `docs/FORMAT_DEFINITION_GUIDE.md` before writing your format.
The guide covers alphabet design, packing decisions, boundary tiles,
operation naming, and constant injection.

---

## models/ Requirements

Each model JSON file must be a valid user model for `unicell_model_library.py`:

```json
{
  "id":          "my_model_id",
  "name":        "My Model",
  "domain":      "MyDomain",
  "format":      "MyFormat",
  "description": "What this model computes",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-09",
  "base_model":  "gray_scott",
  "parameters": {
    "size":  {"type": "int",   "default": 32, "label": "Grid size"},
    "steps": {"type": "int",   "default": 50, "label": "Steps"}
  },
  "tile_config": {},
  "tags":        ["example", "my_domain"],
  "notes":       "Any additional notes"
}
```

The `format` field links the model to its format definition.
The model library validates tile placements against the declared format.

---

## Bridge Tiles

A bridge tile connects two format domains within a single cell map — for
example, linking a thermal simulation output to a fluid dynamics input via
a known physical relationship. Bridges are formal contracts: you declare
the physical relationship, its confidence, and the units on both sides.
The compiler uses this to decide whether to auto-place, warn, or require
explicit verification.

### Defining a bridge

In your `format.py`, subclass `BridgeContract` and register it:

```python
from cell_format import BridgeContract, FUNDAMENTAL_BRIDGES

class MyFormat_to_SI_Mass(BridgeContract):
    name                = "MYFORMAT_TO_SI_MASS"
    source_format       = "MyFormat"
    target_format       = "SI_Physics"
    source_context      = "mass_equivalent"
    target_context      = "mass_equivalent"
    formula             = "m_si = my_value * conversion_factor"
    constants_used      = ["MY_CONVERSION_FACTOR"]
    input_units         = "my_units"
    output_units        = "kg"
    output_dimension    = [0,1,0,0,0,0,0]   # [m,kg,s,A,K,mol,cd]
    semantic_confidence = 0.8
    requires_verification = True
    notes               = "Maps MyFormat values to SI mass. Validated for
                           values in range [0, 1e6]. Outside this range,
                           use with caution."

# Register alongside built-in bridges
FUNDAMENTAL_BRIDGES.append(MyFormat_to_SI_Mass)
```

### semantic_confidence scale

This is the most important field. Be honest — the system warns users based
on this value and the compiler placement policy depends on it:

| Value | Meaning | Compiler policy |
|-------|---------|----------------|
| 1.0 | Discovered — law of nature, first principles | Auto-place, log |
| 0.8 | Well-established — measured, validated, accepted | Warn, place on confirmation |
| 0.6–0.8 | Model or approximation — works within range | Require explicit verification |
| 0.2–0.6 | Speculative — useful in context, no general basis | Require explicit verification |
| < 0.6 | No established connection | Compiler rejects auto-placement |

**Do not inflate confidence.** A bridge claiming 0.9 for a speculative
mapping will be auto-placed by the compiler into pipelines without warning.
Claim what you can defend.

### output_dimension

A 7-element list of SI base dimension exponents: `[m, kg, s, A, K, mol, cd]`.
Examples:
- Pure mass: `[0,1,0,0,0,0,0]`
- Velocity (m/s): `[1,0,-1,0,0,0,0]`
- Energy (kg⋅m²/s²): `[2,1,-2,0,0,0,0]`
- Dimensionless: `[0,0,0,0,0,0,0]`

### Discovering bridges from the UI

The Region Connector (`composer/region_connector.html`) lets you define
custom bridges interactively when connecting two regions of different
formats. A custom bridge defined in the UI is saved in the `.icm` file
for that model but is not automatically added to `cell_format.py`.

To promote a UI-defined bridge to a permanent registered bridge,
use the **⬆ promote** link that appears in the connections list next to any
custom bridge, or the **⬆ Export Custom Bridges** toolbar button to batch-
export all custom bridges from the session. Each download is a ready-to-paste
`BridgeContract` subclass stub with name, formula, confidence, source/target
format, notes, and TODO markers for `constants_used`, `input_units`,
`output_units`, and `output_dimension`.

After downloading the stub:
1. Fill in `constants_used`, `input_units`, `output_units`, `output_dimension`
2. Paste the class into your `format.py`
3. Add it to `FUNDAMENTAL_BRIDGES`
4. Re-run `community_tools.py validate` and `hash`

### Compile-time validation

Before any cells are placed, the compiler checks every bridge in a pipeline
`.icm` against its declared contract. You can call this check directly:

```python
import json
from cell_format import FormatRegistry

reg = FormatRegistry.get_default()

with open("my_pipeline.icm") as f:
    pipeline = json.load(f)

result = reg.check_pipeline_bridges(pipeline)

if not result["ok"]:
    for err in result["errors"]:
        print("ERROR:", err)
for w in result["warnings"]:
    print("WARN: ", w)
print(result["summary"])
```

**Policy applied per bridge:**

| Confidence | Policy | Effect |
|------------|--------|--------|
| ≥ 0.95, context ok | auto_place | Silent — logged only |
| ≥ 0.80, context ok | warn_and_place | Warning — placed on confirmation |
| ≥ 0.60 or context mismatch | require_verification | Error — must fix |
| < 0.60 | reject | Error — must fix |

Use  to treat warnings as errors for production pipelines.
Use  to require discovered-physics confidence
for a safety-critical deployment.

**SI dimensional analysis (SI_Physics only):** if your bridge declares
 (a 7-element  vector), the
compiler also verifies the vector matches what the target format's
 declares for its consuming concepts. A dimension mismatch
is a compile-time error — catches unit errors (adding metres to kilograms)
before any cell is placed. Populate  on every bridge
that connects to or from .

### Checking bridge availability

```python
from cell_format import FormatRegistry

reg = FormatRegistry.get_default()

# Find bridges from your format to any target
bridges = reg.discover_bridges("MyFormat")

# Find bridges between two specific formats
bridges = reg.find_bridge("MyFormat", "SI_Physics")

for b in bridges:
    print(b.name, b.semantic_confidence, b.compiler_policy)
```

### Listing your bridges in MANIFEST.json

```json
{
  "bridges": ["MYFORMAT_TO_SI_MASS", "MYFORMAT_TO_THERMAL"]
}
```

List the `name` field of each `BridgeContract` subclass you define.

### Reference: built-in bridges

Nine fundamental bridges ship with UniCell, all high-confidence (≥0.8):

| Bridge | Source → Target | Formula | Confidence |
|--------|----------------|---------|-----------|
| Bridge_Hawking | PhysTrix → MIF | T = ℏc³/8πGMkB | 1.0 |
| Bridge_Navier_Stokes_Temp | MIF → PhysTrix | ν = μ/ρ(T) | 0.9 |
| Bridge_Arrhenius | PhysTrix → ChemTrix | k = Ae^(-Ea/RT) | 0.95 |
| Bridge_Stefan_Boltzmann | PhysTrix → MIF | P = σT⁴ | 1.0 |
| Bridge_DNA_to_Amino | BioTrix/DNA → BioTrix/Amino20 | codon table | 1.0 |
| Bridge_DNA_to_Chem | BioTrix/DNA → ChemTrix | base → nucleotide | 0.9 |
| Bridge_Amino_to_Chem | BioTrix/Amino20 → ChemTrix | residue → formula | 0.85 |
| Bridge_Chem_to_DNA | ChemTrix → BioTrix/DNA | nucleotide → base | 0.9 |
| Bridge_LBM_Viscosity | MIF → PhysTrix | ν = cs²(τ-0.5)Δt | 0.95 |

Use these as reference implementations when writing your own bridges.

---

## How to Submit

1. Fork `github.com/alh-Imago/Imago-Unicell`
2. Create `community/your_domain/` with all required files
3. Run `python community/community_tools.py validate your_domain/`
   — fixes all errors before submitting
4. Run `python community/community_tools.py hash your_domain/`
   — updates the hash in MANIFEST.json
5. Run `python community/community_tools.py register`
   — updates REGISTRY.md
6. Submit a pull request

The automated check on pull requests:
- All required files present
- MANIFEST.json is valid JSON with all required fields
- `format.py` imports cleanly
- Hash matches current file contents
- At least one model in `models/`
- Version is higher than previously registered version

---

## Rules

**1. Domain names are unique.** If `BioTrix` is taken, pick something else
or contribute to the existing BioTrix folder. Namespace collisions are
rejected automatically.

**2. Format names are unique.** `DNA_4Base` can only be defined once in
the registry. If you want a variant, name it differently (`DNA_4Base_v2`,
`DNA_IUPAC`).

**3. The format comes first.** Models and tiles are only accepted if the
format they declare exists in the registry. Submit the format definition
before (or together with) the models.

**4. Semantic honesty.** If a bridge has low semantic confidence (mapping
financial data to biological concentrations), declare it as such in
`semantic_confidence`. The system warns users. Don't claim 0.9 confidence
for a mapping that is speculative.

**5. Hash before submit.** A contribution whose hash doesn't match its
files will be rejected automatically.

**6. Keep it runnable.** `format.py` must import cleanly. Models must
validate against the format. The community_tools.py validator checks this.

---

## Finding Contributions

**Browse:** open `REGISTRY.md` — human-readable index of all contributions,
sorted by domain, with version, author, date, and description.

**Search:** `community_tools.py search <keyword>` searches REGISTRY.md and
all MANIFEST.json files. Returns matching domain names, model IDs, and tags.

**Load in server:** the UniCell server (`unicell_server.py`) discovers
community models automatically when this folder is present. No restart needed.
New community formats are available in the browser frontend immediately.

---

*See also:*
- `docs/FORMAT_DEFINITION_GUIDE.md` — how to write a format definition
- `cell_format.py` — FormatDefinition base class and registry
- `unicell_model_library.py` — model library and validation
- `docs/PAPER_DRAFT.md` § Format-Typed Symbolic Computation
