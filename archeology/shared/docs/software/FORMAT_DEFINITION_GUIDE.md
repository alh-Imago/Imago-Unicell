# UniCell Format Definition Guide

## How to Create a Domain-Specific Internal Format

This guide shows how to define a new internal data format for a UniCell
frontend. The pattern was discovered in MIF (MathTrix Internal Float) and
generalised into the `FormatDefinition` system in `cell_format.py`.

**Before you write a single tile — write the format definition.**
The format is the contract. It tells tile designers, model authors, and
the Composer exactly what the rules are. Everything else follows from it.

---

## The Pattern

Every format definition answers five questions:

```
1. ALPHABET    — what symbols exist in this domain?
2. PACKING     — how are they stored compactly in cells?
3. BOUNDARY    — how do external data and internal cells translate?
4. OPERATIONS  — what computations are valid within this format?
5. CONSTANTS   — what fixed values does this domain need?
```

MIF answers them for floating-point arithmetic:
```
1. ALPHABET    — real numbers (IEEE-754 floats)
2. PACKING     — split into two cells: control (exponent+flags) + mantissa
3. BOUNDARY    — MIF_UNPACK (IEEE→MIF) / MIF_PACK (MIF→IEEE)
4. OPERATIONS  — ADD, SUB, MUL, DIV, SQRT, MADD, CMP_*
5. CONSTANTS   — preloaded into cells at configure time (0.0, 1.0, 2.0, π...)
```

DNA answers them for genomics:
```
1. ALPHABET    — {A, T, G, C}
2. PACKING     — 2 bits per base, 16 bases per 32-bit cell word
3. BOUNDARY    — DNA_PACK (string→cells) / DNA_UNPACK (cells→string)
4. OPERATIONS  — COMPLEMENT, MATCH, HAMMING, REVERSE, WINDOW, GC_COUNT
5. CONSTANTS   — complement mask (0b11 per 2-bit pair), preloaded
```

---

## Step-by-Step

### Step 1 — Name the alphabet

List every distinct symbol in your domain.

| Domain | Symbols | Count |
|--------|---------|-------|
| DNA | A T G C | 4 |
| Standard elements | H He Li ... Og | 118 |
| Amino acids | A R N D C Q E G H I L K M F P S T W Y V | 20 |
| Decimal digits | 0 1 2 3 4 5 6 7 8 9 | 10 |
| Chess pieces | ♔♕♖♗♘♙♚♛♜♝♞♟ + empty | 13 |
| SI base units | m kg s A K mol cd | 7 |
| Currency codes | USD EUR GBP JPY ... | ~170 |

Count the symbols. That count determines the minimum bits per symbol:
`bits = ceil(log2(count))`

Round up to a power of 2 or a byte boundary for clean masking:
- 4 symbols → 2 bits (exact)
- 20 symbols → 5 bits (fits in byte nibble pair)
- 118 symbols → 7 bits, but use **8 bits** (byte-aligned, cleaner)
- 170 symbols → 8 bits (fits)

**Rule:** byte-aligned packing (4, 8, 16, 32 bits) is almost always
the right choice. The marginal cell savings from 7-bit packing are not
worth the masking complexity.

### Step 2 — Design the packing

How many symbols fit in one 32-bit cell word?
`symbols_per_word = floor(32 / bits_per_symbol)`

| bits/symbol | symbols/word | efficiency |
|-------------|-------------|------------|
| 2 | 16 | 100% |
| 4 | 8 | 100% |
| 5 | 6 | 93.75% (2 bits padding) |
| 7 | 4 | 87.5% (4 bits padding) |
| 8 | 4 | 100% |
| 16 | 2 | 100% |
| 32 | 1 | 100% |

If your format needs **multiple cell words per value** (like MIF's 2 cells
per float), set `cell_words > 1` and document why the split helps.

**MIF insight:** splitting exponent and mantissa into separate cells means
exponent arithmetic (comparison, addition for normalisation) never touches
the mantissa cell. Operations that only need the exponent don't wait for
the mantissa. This is the key performance benefit of the split.

**Ask yourself:** is there a natural split in your data where one part
is used more frequently than the other? If yes, consider `cell_words = 2`.

### Step 3 — Define the boundary

The boundary is where external data enters and exits the fabric.
Two tiles, always:

```
boundary_in:  external format → internal packed cells
boundary_out: internal packed cells → external format
```

The boundary cost is paid **once** per region entry/exit. All internal
computation runs in packed form. This is why MIF is efficient — you pay
the IEEE-754 decompose cost once, not on every arithmetic operation.

**Boundary tile design principles:**
- `boundary_in` receives raw external data (float, string, integer)
- It packs symbols using the LUT and the packing scheme
- `boundary_out` inverts the process exactly
- Both must be perfect inverses: `decode(encode(x)) == x`

You don't need to implement the boundary tiles before defining the format.
The definition specifies what they must do. Implementation follows the spec.

### Step 4 — List valid operations

What computations make sense within this format?

**Think in domain terms, not implementation terms:**

For DNA:
- Does "add" make sense? No.
- Does "complement" make sense? Yes — A↔T, G↔C.
- Does "distance" make sense? Yes — Hamming distance between sequences.
- Does "window" make sense? Yes — sliding k-mer window.

For chemistry:
- Does "bond" make sense? Yes — valence check + atom pair.
- Does "react" make sense? Yes — oxidation state change.
- Does "mass" make sense? Yes — sum atomic masses.

For physics:
- Does "unit conversion" make sense? Yes — multiply by conversion factor.
- Does "dimensional check" make sense? Yes — validate unit consistency.

**Name each operation.** The name becomes the tile name:
`DNA_COMPLEMENT`, `CHEM_BOND`, `PHYS_CONVERT`.

The tile name tells the Composer which tiles are valid when a model
declares this format. Placing a `CHEM_BOND` tile in a `MIF` model
is a design-time error — caught immediately.

### Step 5 — Identify constants

Every domain has fixed values that computations reference.

In UniCell, **constants live in cells** — not in memory, not in registers,
not in configuration files. They are preloaded into cell `a_data` at
configure time via the **preloaded-A pattern**.

The constant's address IS its identity. If you need the speed of light,
you reference address `0xPHYS_C`. That cell has `a_data = 299792458`
preloaded. When the cell fires, it outputs the constant with zero latency —
no memory fetch, no broadcast, just the cell's output address.

**For your format, list:**
```python
CONSTANTS = {
    "name":    (address_hint, value, description),
    "c":       (0xPHYS_C,  299792458,    "speed of light, m/s"),
    "G":       (0xPHYS_G,  6.674e-11,    "gravitational constant"),
    "avogadro":(0xPHYS_NA, 6.022e23,     "Avogadro number"),
}
```

These constants are declared in the format definition. The tile library
reads them at configure time and preloads them. The computation references
them by address.

---

## Worked Example: SI_Physics

```python
class SI_Physics(FormatDefinition):
    """
    SI unit system with physical constants.

    Values stored as MIF pairs (reuses MIF format internally).
    Unit dimensions stored as 7-bit packed exponent vector:
      [m, kg, s, A, K, mol, cd] — one 4-bit exponent per dimension
    This allows dimensional analysis at compile time.
    """
    name             = "SI_Physics"
    description      = "SI units with dimensional analysis and physical constants"
    domain           = "PhysTrix"
    bits_per_symbol  = 4       # 4 bits per unit exponent (-7 to +7)
    symbols_per_word = 7       # 7 SI base dimensions per word (28 bits)
    cell_words       = 3       # value_ctrl, value_mant, unit_dimensions
    boundary_in      = "SI_PACK"
    boundary_out     = "SI_UNPACK"
    valid_tiles      = [
        "SI_ADD",      # add same-unit quantities
        "SI_MUL",      # multiply (adds unit exponents)
        "SI_DIV",      # divide (subtracts unit exponents)
        "SI_SQRT",     # square root (halves unit exponents)
        "SI_CONVERT",  # unit conversion via preloaded factor
        "SI_CHECK",    # dimensional consistency check (returns 1-bit)
    ]
    # Physical constants — preloaded into fabric at configure time
    CONSTANTS = {
        "c":        299_792_458,          # speed of light, m/s
        "G":        6.674e-11,            # gravitational constant
        "h":        6.626e-34,            # Planck constant
        "hbar":     1.055e-34,            # reduced Planck
        "kB":       1.381e-23,            # Boltzmann constant
        "NA":       6.022e23,             # Avogadro number
        "e":        1.602e-19,            # elementary charge
        "epsilon0": 8.854e-12,            # vacuum permittivity
        "mu0":      1.257e-6,             # vacuum permeability
        "R":        8.314,                # gas constant
        "sigma":    5.671e-8,             # Stefan-Boltzmann constant
        "me":       9.109e-31,            # electron mass
        "mp":       1.673e-27,            # proton mass
        "mn":       1.675e-27,            # neutron mass
        "alpha":    7.297e-3,             # fine structure constant
    }
    constraints = {
        "dimensional_check": True,   # operations validate unit consistency
        "unit_exponent_range": (-7, 7),
    }
```

---

## Worked Example: Finance_Currency

```python
class Finance_Currency(FormatDefinition):
    """
    Financial instrument format.

    8-bit currency/instrument code, 4 per word.
    Values stored as fixed-point Q16.16 (separate cell).
    Operations include compound interest, discounting, yield.
    """
    name             = "Finance_Currency"
    description      = "Currency codes and financial instrument identifiers"
    domain           = "FinTrix"
    bits_per_symbol  = 8
    symbols_per_word = 4
    cell_words       = 2       # code cell + Q16.16 value cell
    boundary_in      = "FIN_PACK"
    boundary_out     = "FIN_UNPACK"
    valid_tiles      = [
        "FIN_CONVERT",       # currency conversion via rate LUT
        "FIN_COMPOUND",      # compound interest: P*(1+r)^n
        "FIN_DISCOUNT",      # present value: FV / (1+r)^n
        "FIN_YIELD",         # yield to maturity
        "FIN_SPREAD",        # basis point spread
        "FIN_MARK_TO_MARKET",# mark portfolio to current prices
    ]
    # Market constants — updated at configure time (not compile time)
    # These change daily; the preloaded-A pattern allows reconfigure
    # without recompiling the cell map.
    CONSTANTS = {
        "risk_free_rate":  0.05,    # 5% p.a. — reconfigured daily
        "basis_point":     0.0001,  # 1 bp = 0.01%
        "days_per_year":   365,
        "trading_days":    252,
    }
    symbol_lut = {
        "USD":1, "EUR":2, "GBP":3, "JPY":4, "CHF":5,
        "AUD":6, "CAD":7, "NZD":8, "CNY":9, "HKD":10,
        "SGD":11,"NOK":12,"SEK":13,"DKK":14,"MXN":15,
        # Instruments
        "BOND":128,"EQUITY":129,"FUTURE":130,"OPTION":131,
        "SWAP":132,"FWD":133,"CDS":134,"ETF":135,
    }
```

---

## The Trix Frontend Design System

Format definitions are the foundation of the Trix frontend system:

```
FormatDefinition        ← you write this first
        ↓
TileLibrary entries     ← tile designer builds to the spec
        ↓
ModelLibrary entries    ← models declare their format
        ↓
Compiler validation     ← wrong tile for format = error at design time
        ↓
Composer awareness      ← invalid tiles greyed out for active format
        ↓
Deployed server         ← PTT output labelled with format metadata
        ↓
Client decoding         ← client knows how to interpret the output
```

**The format definition empowers the system before any implementation exists.**
You can declare `SI_Physics` format with its constants and valid operations
today. Any model that declares `format = "SI_Physics"` will be validated
against that contract immediately — even before a single SI tile is built.

When the tiles are eventually implemented, they plug into a contract that
already exists. The format definition is the specification. The tiles are
the implementation. The model is the usage.

---

## Rules for Good Format Definitions

**1. Domain first, implementation never**
Define operations in domain terms: `DNA_COMPLEMENT`, not `XOR_32`.
The implementation (it's XOR with 0b11) is a detail. The domain name
is the contract.

**2. Boundary tiles are special**
`boundary_in` and `boundary_out` are always valid, regardless of the
`valid_tiles` list. They are the only tiles that touch external data.
Everything else stays in packed internal form.

**3. Constants belong in the format, not the model**
If a value is fixed for a domain (speed of light, Boltzmann constant,
complement mask), it belongs in the format definition's `CONSTANTS` dict,
not in individual model parameters. Models inherit the constants; they
don't redefine them.

**4. Packing efficiency matters**
100% bit efficiency (byte-aligned symbols) is always preferred.
Use the upper code range (> natural alphabet size) for groups and
extended types — as Chemistry does with molecular groups in 128-255.

**5. One format per domain concept**
MIF is for floating-point arithmetic. DNA is for nucleotide sequences.
They are different concepts and should be different formats, even though
both ultimately use cells and the NOR bus. The format boundary is a
semantic boundary, not a physical one.

**6. Validate early**
The format definition's `validate_tile()` and `validate_model()` methods
exist to catch errors at design time. Use them in the Composer, the model
library, and the compiler. An error caught at design time costs nothing.
An error caught at runtime on an Arria 10 costs a debugging session.

---

## Adding a Format to the Registry

```python
# In your frontend module (e.g. biotrix.py, chemtrix.py, phystrix.py):

from cell_format import FormatDefinition, FormatRegistry

class MyFormat(FormatDefinition):
    name             = "MyFormat"
    description      = "My domain format"
    domain           = "MyTrix"
    bits_per_symbol  = 8
    symbols_per_word = 4
    cell_words       = 1
    boundary_in      = "MY_PACK"
    boundary_out     = "MY_UNPACK"
    valid_tiles      = ["MY_OP1", "MY_OP2"]
    symbol_lut       = {"A": 1, "B": 2, "C": 3}
    CONSTANTS        = {"my_const": 42}

# Register with the default registry
reg = FormatRegistry.get_default()
reg.register_class(MyFormat)

# Validate a model against the format
errors = reg.validate_model({
    "format": "MyFormat",
    "tiles":  ["MY_OP1", "MIF_ADD"],   # MIF_ADD will fail validation
})
# → ["Tile 'MIF_ADD' is not valid in format 'MyFormat'..."]
```

---

## What This Means

You have defined a **math for anything**.

Any domain with:
- A finite alphabet of symbols
- A compact internal representation
- A set of valid operations
- A set of fixed constants

...can be expressed as a UniCell format and run on the fabric. The cells
are unchanged. The bus is unchanged. The NOR gate is unchanged.

The format is the domain-specific type system that sits above the universal
compute primitive. The fabric is the commons. The format is the language.

**Domains defined:**
- MathTrix → MIF (floating point)
- BioTrix → DNA_4Base, RNA_4Base, Amino20 (genomics, proteomics)
- ChemTrix → Chemistry_Element (periodic table + molecular groups)
- PhysTrix → SI_Physics (dimensional analysis + physical constants)
- FinTrix → Finance_Currency (instruments + market data)
- FlowTrix → FlowTrix_D2Q9 (lattice Boltzmann fluid simulation)
- NeuroTrix → MidiTrix (MIDI-to-LIF drive), SensorTrix, OptiTrix, NetTrix
- General → BCD_Decimal, FixedPoint_Q8_24

Each one is a `FormatDefinition` subclass, a set of tiles, and a model
library entry. The fabric runs all of them.

---

## Bridge contracts and compile-time validation

### Defining a bridge

When two format domains connect, the crossing must be declared as a
`BridgeContract`. This is the physical/semantic hypothesis about what the
connection means. The compiler enforces it.

```python
from cell_format import BridgeContract, FUNDAMENTAL_BRIDGES

class MyBridge(BridgeContract):
    name                 = "MYFORMAT_TO_SI_TEMP"
    source_format        = "MyFormat"
    target_format        = "SI_Physics"
    source_context       = "thermal"
    target_context       = "thermal"
    formula              = "T_si = my_value * scale_factor"
    constants_used       = ["MY_SCALE"]
    input_units          = "my_units"
    output_units         = "K"
    output_dimension     = [0, 0, 0, 0, 1, 0, 0]   # [m,kg,s,A,K,mol,cd]
    semantic_confidence  = 0.9
    requires_verification = False
    notes                = "Validated for values in [0, 1e4]. See lab notebook 3."

FUNDAMENTAL_BRIDGES.append(MyBridge)
```

**`semantic_confidence` scale:**

| Value | Meaning | Compiler policy |
|-------|---------|----------------|
| 1.0 | Discovered — law of nature | Auto-place, log only |
| 0.8–0.95 | Well-established empirically | Warn, place on confirmation |
| 0.6–0.8 | Model/approximation | Require explicit verification |
| < 0.6 | No established connection | Compiler rejects |

### SI dimensional analysis

For bridges delivering SI quantities, declare `output_dimension` as a
7-element `[m, kg, s, A, K, mol, cd]` exponent vector. Examples:
- Temperature (K): `[0, 0, 0, 0, 1, 0, 0]`
- Energy (J = kg·m²/s²): `[2, 1, -2, 0, 0, 0, 0]`
- Power (W = kg·m²/s³): `[2, 1, -3, 0, 0, 0, 0]`
- Rate (s⁻¹): `[0, 0, -1, 0, 0, 0, 0]`

`SI_Physics` has a `dimension_map` with 17 concepts. The compiler
automatically verifies `bridge.output_dimension` against what the target
format expects at its consuming concepts — catching unit errors (m + kg)
before any cell is placed.

For non-SI formats, leave `output_dimension = []` — the check is silently
skipped.

### Compile-time pipeline validation

```python
import json
from cell_format import FormatRegistry, CompilePipelineError

reg = FormatRegistry.get_default()

with open("my_pipeline.icm") as f:
    pipeline = json.load(f)

# Check only (no expansion)
report = reg.check_pipeline_bridges(pipeline)
if not report["ok"]:
    for err in report["errors"]:
        print("ERROR:", err)

# Check + auto-place bridge tiles
try:
    result = reg.compile_pipeline_icm(pipeline)
    # result["records"] — expanded, ready for controller.load_map()
    # result["warnings"] — warn-and-place bridges
    # result["bridge_count"] — number of bridge tiles inserted
except CompilePipelineError as e:
    print("Compilation blocked:", e)
```

`compile_pipeline_icm()` expands `BRIDGE_PLACEHOLDER` records (written by
the Region Connector, `gs=0x00000001`) into real `GS_PASS` cells with a
`meta` dict carrying full provenance (bridge name, confidence, formula,
compiler policy, units, `auto_placed` flag).

### Promoting a UI-defined bridge to code

In the Region Connector, custom bridges defined interactively have a
`⬆ promote` link in the connections list. Clicking it downloads a
`BridgeContract` subclass stub as a `.py` file — pre-filled with name,
formula, confidence, source/target format, notes, and TODO markers for
`constants_used`, `input_units`, `output_units`, `output_dimension`.
The batch `⬆ Export Custom Bridges` toolbar button exports all session
bridges at once.

---

*See also: `cell_format.py` — format definition base class and registry*
*See also: `fp_tiles.py` — MIF as the reference implementation*
*See also: `unicell_model_library.py` — model format validation*
*See also: `docs/PAPER_DRAFT.md` § Format-Typed Symbolic Computation*
