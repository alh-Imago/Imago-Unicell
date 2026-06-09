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

If your domain can connect to another domain, define bridges in `format.py`:

```python
from cell_format import BridgeTile   # coming in a future release

class MyFormat_to_SI(BridgeTile):
    source_format       = "MyFormat"
    target_format       = "SI_Physics"
    operation           = "my_value_to_si_mass"
    validity_check      = "source value must be positive"
    output_units        = "kg"
    output_dimension    = [0,1,0,0,0,0,0]   # pure mass
    semantic_confidence = 0.9
    notes               = "Maps my values to SI mass via preloaded LUT"
```

List your bridge tile names in `MANIFEST.json` under `"bridges"`.

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
