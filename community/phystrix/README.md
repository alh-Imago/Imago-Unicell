# PhysTrix

Physics domain for UniCell. SI unit system with dimensional analysis and
17 CODATA 2018 physical constants preloaded into fabric cells at configure
time. The `SI_CHECK` tile enforces dimensional correctness at compile time —
unit errors are caught before the computation runs, not after.

---

## Format

### SI_Physics
Values stored as MIF pairs internally (reuses MIF encoding).
Unit dimensions stored as a 7×4-bit signed exponent vector:
`[m, kg, s, A, K, mol, cd]` packed into a third cell word.

This enables compile-time dimensional analysis — the compiler checks that
units on both sides of every operation are consistent before generating
cell placements.

**3 cell words per value:**
- Word 0: value control (MIF format)
- Word 1: value mantissa (MIF format)
- Word 2: unit dimension vector (7 × 4-bit exponents)

---

## Available Tiles

### Arithmetic
| Tile | Operation | Unit behaviour |
|------|-----------|---------------|
| `SI_ADD` | add quantities | requires matching units |
| `SI_SUB` | subtract quantities | requires matching units |
| `SI_MUL` | multiply | adds unit exponents |
| `SI_DIV` | divide | subtracts unit exponents |
| `SI_SQRT` | square root | halves unit exponents |
| `SI_CONVERT` | unit conversion | preloaded conversion factor |

### Validation
| Tile | Operation | Notes |
|------|-----------|-------|
| `SI_CHECK` | dimensional consistency | fires 1 if units valid, 0 if not |

### Physical Constants (CODATA 2018)
| Tile | Constant | Value |
|------|---------|-------|
| `SI_CONST_C` | speed of light | 299,792,458 m/s |
| `SI_CONST_G` | gravitational constant | 6.67430×10⁻¹¹ m³/kg/s² |
| `SI_CONST_H` | Planck constant (ℏ) | 1.054571817×10⁻³⁴ J·s |
| `SI_CONST_KB` | Boltzmann constant | 1.380649×10⁻²³ J/K |
| `SI_CONST_NA` | Avogadro number | 6.02214076×10²³ mol⁻¹ |
| `SI_CONST_E` | elementary charge | 1.602176634×10⁻¹⁹ C |

### Bridge tile
| Tile | Operation | Confidence |
|------|-----------|-----------|
| `SI_HAWKING_TEMP` | T = ℏc³/8πGMk_B | 1.0 — exact physical identity |

---

## Worked Examples

### 1. Hawking Temperature
Compute the Hawking radiation temperature of a black hole from its mass.
T = ℏc³ / (8πGMk_B)

```
Constants preloaded: ℏ, c, G, k_B (CODATA 2018)
Input: M = 1.989×10³⁰ kg (solar mass)
SI_HAWKING_TEMP → T ≈ 6.17×10⁻⁸ K
SI_CHECK → units verify: K ✓
```

This is the flagship bridge tile — confidence=1.0 because the connection
between a gravitational quantity (black hole mass) and a thermal quantity
(radiation temperature) is an exact physical identity, not an analogy.

Pipeline: `SI_CONST_H → SI_CONST_C → SI_CONST_G → SI_CONST_KB → SI_HAWKING_TEMP → SI_CHECK`
Validation: M_sun → 6.17×10⁻⁸ K. T ∝ 1/M: doubling mass halves temperature.
Model: `community/phystrix/models/hawking_temperature.json`

### 2. Schwarzschild Radius
The event horizon radius of a black hole: r_s = 2GM/c²

```
Constants preloaded: G, c
Input: M = 1.989×10³⁰ kg
SI_MUL(2GM) → 2 × 6.674×10⁻¹¹ × 1.989×10³⁰ = 2.655×10²⁰ m³/s²
SI_DIV(c²)  → 2.655×10²⁰ / (3×10⁸)² = 2.953×10³ m ≈ 2.95 km
SI_CHECK    → units: m ✓
```

Pipeline: `SI_CONST_G → SI_CONST_C → SI_MUL → SI_DIV → SI_CHECK`
Validation: M_sun → r_s ≈ 2.95 km. r_s ∝ M: linear in mass.
Model: `community/phystrix/models/schwarzschild_radius.json`

### 3. Arrhenius Rate (bridge to ChemTrix)
Reaction rate constant via Arrhenius equation: k = A·e^(-Ea/RT)
This is a bridge model — connects PhysTrix (temperature T, gas constant R)
to ChemTrix (activation energy Ea, pre-exponential A).

```
Input: T=300K, Ea=50kJ/mol, A=1×10¹³ s⁻¹
SI_CONST_KB (or R=8.314 J/mol/K)
Bridge_Arrhenius → k at 300K
```

Bridge confidence: 0.95 (well-established, valid across most reaction types)
Model: `community/phystrix/models/arrhenius_rate.json`

---

## Dimensional Analysis

Every `SI_Physics` value carries its unit dimensions. The compiler checks
them automatically when tiles are connected. Example:

```python
from cell_format import FormatRegistry
reg = FormatRegistry.get_default()
fmt = reg.get("SI_Physics")

# velocity: m/s = [m=1, kg=0, s=-1, A=0, K=0, mol=0, cd=0]
velocity_dim = [1, 0, -1, 0, 0, 0, 0]

# energy: J = kg·m²/s² = [m=2, kg=1, s=-2, A=0, K=0, mol=0, cd=0]
energy_dim = [2, 1, -2, 0, 0, 0, 0]
```

If `SI_ADD` receives a velocity on one input and an energy on the other,
`SI_CHECK` fires 0 and the compiler raises a dimensional error.

---

## Adding a New PhysTrix Model

```json
{
  "id":          "my_phys_model",
  "name":        "My Physics Model",
  "domain":      "PhysTrix",
  "format":      "SI_Physics",
  "description": "What this computes",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-15",
  "tags":        ["physics", "my_tag"],
  "parameters": {
    "mass_kg": {"type": "float", "default": 1.0, "label": "Mass (kg)"}
  },
  "pipeline": [
    {"tile": "SI_CONST_G",  "note": "gravitational constant"},
    {"tile": "SI_MUL",      "note": "GM"},
    {"tile": "SI_CHECK",    "note": "verify units"}
  ],
  "expected_output": "result (SI_Physics, units depend on computation)"
}
```

---

## Bridge Connections

| Bridge | Connection | Confidence |
|--------|-----------|-----------|
| `Bridge_Hawking` | PhysTrix → MIF (thermal) | 1.0 |
| `Bridge_Navier_Stokes_Temp` | MIF → PhysTrix | 0.9 |
| `Bridge_Stefan_Boltzmann` | PhysTrix → MIF | 1.0 |
| `Bridge_Arrhenius` | PhysTrix → ChemTrix | 0.95 |
| `Bridge_LBM_Viscosity` | MIF → PhysTrix | 0.95 |

---

*See also:*
- `cell_format.py` — SI_Physics class definition and CODATA constants
- `community/README.md` — contribution guide and bridge tile reference
- `community/chemtrix/README.md` — ChemTrix domain (Arrhenius bridge target)
