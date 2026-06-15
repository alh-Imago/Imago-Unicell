# FinTrix

Financial domain for UniCell. Currency codes and financial instruments
encoded as compact 8-bit identifiers with Q16.16 fixed-point values.
Interest rates, discount factors, and market prices are preloaded as
cell constants — reconfigurable daily without recompiling cell maps.

---

## Format

### Finance_Currency
8 bits per currency/instrument code, 4 codes per 32-bit cell word.
Values stored as Q16.16 fixed-point in a companion cell.
**2 cell words per entry:** code cell + value cell.

**Code space:**
- `1–127` — currency codes (ISO 4217 inspired): USD=1, EUR=2, GBP=3, JPY=4 ...
- `128–200` — instrument types: BOND=128, EQUITY=129, FUTURE=130, OPTION=131 ...

**Key design:** rates and prices live in preloaded-A constants, not in the
code word. A currency conversion rate can be updated by reloading one cell
constant — no recompile, no new bitstream, just a CMD_RECONFIGURE.

---

## Available Tiles

| Tile | Operation | Notes |
|------|-----------|-------|
| `FIN_CONVERT` | currency conversion | rate from preloaded LUT |
| `FIN_COMPOUND` | compound interest P(1+r)^n | r and n preloaded |
| `FIN_DISCOUNT` | present value FV/(1+r)^n | discounting cash flows |
| `FIN_YIELD` | yield to maturity | iterative approximation |
| `FIN_SPREAD` | basis point spread | difference in yields |
| `FIN_MARK_TO_MARKET` | portfolio mark | price from preloaded market data |
| `FIN_DURATION` | Macaulay/modified duration | interest rate sensitivity |
| `FIN_VaR` | Value at Risk (parametric) | σ-based, normal distribution |
| `FIN_CMP_RATE` | compare rates | fires higher/lower signal |

---

## Worked Examples

### 1. Currency Conversion
Convert a USD amount to GBP using a preloaded exchange rate.
The rate cell is updated daily via CMD_RECONFIGURE — no recompile.

```
Preloaded: USD_GBP_RATE = 0.7923 (Q16.16)
Input: USD 1000.00
FIN_CONVERT(USD → GBP) → GBP 792.30
```

Pipeline: `FIN_PACK(USD, 1000.00) → FIN_CONVERT → FIN_UNPACK`
Key property: updating tomorrow's rate costs one CMD_RECONFIGURE,
not a new bitstream.

### 2. Compound Interest
Calculate future value of an investment over N periods.
P(1+r)^n — r and n both preloaded, only principal varies per call.

```
Preloaded: r=0.05 (5% annual), n=10 (years)
Input: P = £10,000
FIN_COMPOUND → £10,000 × (1.05)^10 = £16,288.95
```

Pipeline: `FIN_COMPOUND` (single tile, constants preloaded)
Model: add to `community/fintrix/models/compound_interest.json`

### 3. Present Value / Discounting
Discount a future cash flow to its present value.
FV/(1+r)^n — core operation in bond pricing and DCF valuation.

```
Preloaded: r=0.06 (6% discount rate), n=5
Input: FV = £50,000
FIN_DISCOUNT → £50,000 / (1.06)^5 = £37,362.91
```

Pipeline: `FIN_DISCOUNT`
Multiple cash flows: parallel cells each discount one payment,
MIF_ADD accumulator sums to total present value.

### 4. Monte Carlo Option Pricing (MonTrix)
Thousands of independent price paths, each a short pipeline.
Natural UniCell workload — embarrassingly parallel.

```
For each of N paths:
  FIN_COMPOUND(random walk step) → price at expiry
  FIN_CMP_RATE(strike price) → payoff if in the money
MIF_ADD across all paths → expected payoff
MIF_DIV(N) → option price estimate
```

This is the MonTrix demo concept — parallel paths across all 448 cells
simultaneously. See `PLAN.md` MonTrix section.

---

## Adding a New FinTrix Model

```json
{
  "id":          "compound_interest",
  "name":        "Compound Interest",
  "domain":      "FinTrix",
  "format":      "Finance_Currency",
  "description": "Future value of investment: P(1+r)^n",
  "author":      "your_name",
  "version":     "0.1.0",
  "created":     "2026-06-15",
  "tags":        ["finance", "interest", "investment"],
  "parameters": {
    "principal":  {"type": "float", "default": 1000.0, "label": "Principal"},
    "rate":       {"type": "float", "default": 0.05,   "label": "Annual rate"},
    "periods":    {"type": "int",   "default": 10,     "label": "Periods (years)"}
  },
  "pipeline": [
    {"tile": "FIN_COMPOUND", "note": "P(1+r)^n, r and n preloaded"}
  ],
  "expected_output": "future value (Finance_Currency Q16.16)",
  "validation": "P=10000, r=0.05, n=10 → 16288.95"
}
```

---

## Rate Updates Without Recompile

The most practically important property of FinTrix: market rates change
daily but the cell map doesn't need to. Update a rate:

```python
# In fpga_bridge.py or unicell_server.py
bridge.send_preload(cell_id=FX_RATE_CELL, value=new_usd_gbp_rate)
# Done — next FIN_CONVERT call uses the new rate
```

This is the preloaded-A pattern applied to financial data. The cell topology
(the computation structure) is compiled once; the data (rates, prices) flows
in as configuration. ECU-style deployment model applied to finance.

---

## Bridge Connections

FinTrix has no built-in bridges in the current release. Candidate bridges:

| Bridge (proposed) | Connection | Notes |
|-------------------|-----------|-------|
| `FIN_to_MIF` | Finance_Currency → MIF | extract numeric value for arithmetic |
| `MIF_to_FIN` | MIF → Finance_Currency | wrap result back into currency format |

These are conversion helpers rather than physical bridges — no
`semantic_confidence` concept applies (it's a data format conversion,
not a domain connection). Planned as utility tiles in a future release.

---

*See also:*
- `cell_format.py` — Finance_Currency class definition
- `community/README.md` — contribution guide and bridge tile reference
- `PLAN.md` MonTrix section — Monte Carlo option pricing demo
