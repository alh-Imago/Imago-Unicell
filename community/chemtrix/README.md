# ChemTrix

Chemistry domain for UniCell. Full periodic table (118 elements + molecular
groups) encoded as atomic numbers in a compact 8-bit format. Element properties
live in preloaded cell constants — no arithmetic needed for lookups.

---

## Format

### Chemistry_Element
8 bits per element code, 4 elements per 32-bit cell word.

**Code space:**
- `0` — empty / vacuum
- `1–118` — standard elements, code = atomic number (H=1 .. Og=118)
- `119–127` — user-defined (isotopes, pseudo-atoms, custom species)
- `128–255` — molecular groups (H2O=128, CO2=129, NH3=130, ...)

Properties (mass, valence, electronegativity, density) are **not** stored in
the cell word — they live in the fabric as preloaded-A constants keyed by
atomic number. The cell holds the identity; the fabric holds the lookup.

---

## Available Tiles

| Tile | Operation | Notes |
|------|-----------|-------|
| `CHEM_MASS` | atomic mass lookup (u) | preloaded from periodic table |
| `CHEM_VALENCE` | valence electrons | group-based LUT |
| `CHEM_ELECTRONEGATIVITY` | Pauling scale | preloaded LUT |
| `CHEM_DENSITY` | density (g/cm³) | preloaded LUT |
| `CHEM_GROUP` | periodic table group (1–18) | |
| `CHEM_PERIOD` | periodic table period (1–7) | |
| `CHEM_BOND` | form bond (valence check) | fires if valence allows |
| `CHEM_UNBOND` | break bond | |
| `CHEM_OXIDISE` | apply oxidation state | |
| `CHEM_REDUCE` | apply reduction | |
| `CHEM_MATCH` | element equality | |
| `CHEM_IS_METAL` | metal/nonmetal classification | 1-bit result |

---

## Worked Examples

### 1. Molecular Weight
Sum atomic masses across all atoms in a molecule. The preloaded mass table
means no division or floating-point — just lookups and accumulation.

```
Input:  H2O → [H, H, O] = [1, 1, 8]
CHEM_MASS on each → [1.008, 1.008, 15.999]
MIF_ADD accumulator → 18.015 u
```

Pipeline: `CHEM_MASS → MIF_ADD (accumulate)`
Validation: H2O=18.015u, CO2=44.009u, C6H12O6=180.156u
Model: `community/chemtrix/models/molecular_weight.json`

### 2. Electronegativity Delta
Difference in electronegativity between two bonded atoms — determines
bond polarity. |Δχ| > 1.7 → ionic, 0.4–1.7 → polar covalent, < 0.4 → nonpolar.

```
Input: H (χ=2.20), O (χ=3.44)
CHEM_ELECTRONEGATIVITY on each → [2.20, 3.44]
MIF_SUB → |3.44 - 2.20| = 1.24 → polar covalent
```

Pipeline: `CHEM_ELECTRONEGATIVITY → MIF_SUB → MIF_ABS`
Model: `community/chemtrix/models/electronegativity_delta.json`

### 3. Valence Check
Verify whether a proposed bond is chemically valid before computing with it.
The cell fires only if valence allows the bond — invalid bonds are simply
never propagated.

```
Input: C (valence=4), H×4
CHEM_BOND fires for each H if valence remaining > 0
CH4: 4 bonds fire → methane valid
CH5: 5th bond does not fire → invalid
```

Pipeline: `CHEM_VALENCE → CHEM_BOND`
Model: `community/chemtrix/models/valence_check.json`

---

## Adding a New ChemTrix Model

```json
{
  "id":          "my_chem_model",
  "name":        "My Chemistry Model",
  "domain":      "ChemTrix",
  "format":      "Chemistry_Element",
  "description": "What this model computes",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-15",
  "tags":        ["chemistry", "my_tag"],
  "parameters": {
    "n_atoms": {"type": "int", "default": 10, "label": "Atom count"}
  },
  "pipeline": [
    {"tile": "CHEM_MASS", "note": "atomic mass lookup"}
  ],
  "expected_output": "molecular weight (MIF float, u)",
  "validation": "H2O → 18.015 u"
}
```

---

## Bridge Connections

| Bridge | Connection | Confidence |
|--------|-----------|-----------|
| `Bridge_Arrhenius` | PhysTrix → ChemTrix | 0.95 (reaction rate) |
| `Bridge_DNA_to_Chem` | BioTrix → ChemTrix | 0.9 (nucleotide chemistry) |
| `Bridge_Amino_to_Chem` | BioTrix/Amino20 → ChemTrix | 0.85 (residue formulas) |
| `Bridge_Chem_to_DNA` | ChemTrix → BioTrix | 0.9 (nucleotide synthesis) |

---

*See also:*
- `cell_format.py` — Chemistry_Element class definition
- `community/README.md` — contribution guide and bridge tile reference
