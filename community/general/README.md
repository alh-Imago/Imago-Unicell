# General

Utility formats for UniCell — BCD decimal and Q8.24 fixed-point.
These are the lowest-level numeric formats, useful at domain boundaries
and for interfacing with integer-domain systems (displays, sensors,
embedded controllers, legacy data formats).

---

## Formats

### BCD_Decimal
4 bits per decimal digit, 8 digits per 32-bit cell word.
Nibble arithmetic with carry propagation between nibbles.

**Why BCD:** natural for financial display, measurement instruments,
and any system where decimal rounding must be exact. Binary floating-point
(including MIF) cannot represent 0.1 exactly; BCD can.

**Code space:** digits 0–9 only. Values 10–15 are invalid — the
`invalid_guard` constraint causes the compiler to flag any operation
that could produce them.

### FixedPoint_Q8_24
Q8.24 fixed-point — 8 integer bits, 24 fractional bits.
**2 cell words:** integer cell + fraction cell.

**Why Q8.24:** matches common embedded and DSP interfaces. 24 fractional
bits gives ~7 decimal digits of precision, sufficient for sensor data,
audio samples, and control system outputs. The integer range (−128 to +127)
covers most physical measurement scales at reasonable units.

**Relationship to MIF:** MIF is the native UniCell floating-point format.
FixedPoint_Q8_24 is the boundary format for interfacing with systems
that expect fixed-point. Use `FIXED_TO_MIF` / `FIXED_FROM_MIF` tiles
at the boundary; compute in MIF internally.

---

## Available Tiles

### BCD_Decimal
| Tile | Operation | Notes |
|------|-----------|-------|
| `BCD_ADD` | nibble addition with carry | handles 9+1=10 → carry |
| `BCD_SUB` | nibble subtraction with borrow | |
| `BCD_CMP` | digit-by-digit comparison | |
| `BCD_SHIFT` | decimal shift | ×10 or ÷10 |

### FixedPoint_Q8_24
| Tile | Operation | Notes |
|------|-----------|-------|
| `FIXED_ADD` | fixed-point addition | carry between integer/fraction cells |
| `FIXED_SUB` | fixed-point subtraction | |
| `FIXED_MUL` | fixed-point multiply | result shift applied |
| `FIXED_CMP` | comparison | |
| `FIXED_TO_MIF` | convert to MIF | for internal computation |
| `FIXED_FROM_MIF` | convert from MIF | for output to fixed-point systems |

---

## Worked Examples

### 1. BCD Addition (exact decimal arithmetic)
Adding two decimal values without floating-point rounding error.

```
A = 12345678  (packed: 0001 0010 0011 0100 0101 0110 0111 1000)
B = 00000003
BCD_ADD → 12345681  (nibble carry: 8+3=11 → 1 carry 1 → digit becomes 1, carry to next)
```

Use case: financial totals where 0.1 + 0.2 must equal exactly 0.3,
not 0.30000000000000004.

Pipeline: `BCD_PACK → BCD_ADD → BCD_UNPACK`

### 2. Sensor Data Pipeline (FixedPoint boundary)
Sensor produces Q8.24 fixed-point output. Compute in MIF. Return Q8.24.

```
Sensor → FIXED_PACK → FIXED_TO_MIF
                            ↓
                    [MIF pipeline — filter, scale, transform]
                            ↓
                    FIXED_FROM_MIF → FIXED_UNPACK → actuator
```

The boundary tiles (`FIXED_TO_MIF`, `FIXED_FROM_MIF`) act as format
bridges at the edge of the fabric. All computation in MIF; Q8.24 only
at the physical interface.

### 3. Display Formatting (BCD)
Convert a numeric result to display-ready decimal digits.
BCD output maps directly to 7-segment display drivers or LCD controllers
without software conversion.

```
MIF result: 3.14159
MIF_TO_BCD → 0314159 (7 digits BCD)
BCD_UNPACK → 7 nibbles → display driver
```

Pipeline: `MIF_TO_BCD → BCD_UNPACK`

### 4. Decimal Shift (multiply/divide by powers of 10)
Shift decimal point without arithmetic.

```
Input:  00012345  (= 12345)
BCD_SHIFT(+2) → 01234500  (= 1234500, shift left 2 digits = ×100)
BCD_SHIFT(-3) → 00000012  (= 12, shift right 3 digits = ÷1000)
```

Use case: unit scaling (mm → m, pence → pounds) without division.

---

## When to Use Each Format

| Situation | Recommended format |
|-----------|-------------------|
| Internal arithmetic | MIF (native UniCell float) |
| Physical constants | SI_Physics (PhysTrix) |
| Sensor input/output boundary | FixedPoint_Q8_24 |
| Financial display, exact decimal | BCD_Decimal |
| Financial computation | Finance_Currency (FinTrix) |
| Genomics | DNA_4Base / RNA_4Base / Amino20 (BioTrix) |
| Chemistry | Chemistry_Element (ChemTrix) |

General formats are **boundary formats** — they appear at the edges of
pipelines where the external world speaks a different numeric language.
The bulk of computation happens in MIF or domain-specific formats.

---

## Adding a New General Model

```json
{
  "id":          "bcd_sum",
  "name":        "BCD Accumulator",
  "domain":      "General",
  "format":      "BCD_Decimal",
  "description": "Sum N decimal values with exact BCD arithmetic",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-15",
  "tags":        ["bcd", "decimal", "accumulator"],
  "parameters": {
    "n_values": {"type": "int", "default": 8, "label": "Values to sum"}
  },
  "pipeline": [
    {"tile": "BCD_ADD", "note": "accumulate with nibble carry"}
  ],
  "expected_output": "sum (BCD_Decimal, 8 digits)"
}
```

---

## Bridge Connections

General formats connect to MIF (the native UniCell format) via conversion
tiles, not BridgeContract bridges — these are format conversions, not
domain bridges, so `semantic_confidence` does not apply.

| Conversion | Tiles |
|-----------|-------|
| BCD ↔ MIF | `MIF_TO_BCD`, `BCD_TO_MIF` (utility tiles) |
| FixedPoint ↔ MIF | `FIXED_TO_MIF`, `FIXED_FROM_MIF` |

---

*See also:*
- `cell_format.py` — BCD_Decimal and FixedPoint_Q8_24 class definitions
- `community/README.md` — contribution guide
- `community/fintrix/README.md` — FinTrix (Finance_Currency uses BCD internally)
