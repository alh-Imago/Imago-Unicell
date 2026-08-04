# UniCell Configuration — Decision-Tree Architecture

Captured 2026-05-18. Updated 2026-05-29.
BranchPoint API confirmed: __init__(region_id, cell_a_in, ptt_addr, cell_addresses)
Methods: bind_regions, build, dispatch, freeze, load, run, status, thaw.

This documents the four node types for a compiled decision tree using
the two-arrival model. Each row is a UniCell TYPE, not an instance.

---

## 1. COMPARE Node (C)

Two-stage compare: stored reference vs live value → outputs 1 (match) or 2 (no match).

| Field               | Value                          |
|---------------------|--------------------------------|
| Purpose             | Compare stored vs live input   |
| topology            | `10'b0000111100` (XNOR = g8)  |
| sync_wait / two-arr | 1 (two-arrival: stored then live) |
| start_flag          | 1                              |
| dtype               | 00 (NUMERIC)                   |
| ctype               | 00 (STANDARD)                  |
| pair_flags [24:23]  | 01 (marks COMPARE role)        |
| input_address       | Where stored + live values arrive |
| output_address      | Where decision (1 or 2) is written |
| Output encoding     | YES = 1, NO = 2                |

Notes:
- First arrival = stored reference value (loaded at program-tile preload time)
- Second arrival = live input value (arrives at decision point)
- Output is a full 32-bit word containing 1 or 2

---

## 2. CHOICE Nodes (Y/N)

Both listen to COMPARE output and compute the next path value.
YES-choice and NO-choice are two separate cells, both listening on
COMPARE.output_address.

| Field               | Value                                      |
|---------------------|--------------------------------------------|
| Purpose             | Convert decision (1 or 2) + path → next path |
| topology            | ADD (XOR/AND/OR chain) or PASS_B for lookup |
| sync_wait / two-arr | 1                                          |
| start_flag          | 1                                          |
| dtype               | 00                                         |
| ctype               | 00                                         |
| pair_flags [24:23]  | 10 (marks CHOICE role)                     |
| input_address       | Same as COMPARE.output_address             |
| output_address      | next_path_value address                    |
| a_data (stored)     | YES-offset or NO-offset (per cell)         |

Notes:
- First arrival = decision value (1 or 2)
- Second arrival = current path value
- Output = current_path + offset(decision)
- One CHOICE cell holds the YES-offset, one holds the NO-offset
- Both fire; only the correct path propagates (decision acts as selector)

---

## 3. RESULT Node (R)

Masks the accumulated path into a table pointer.

| Field               | Value                          |
|---------------------|--------------------------------|
| Purpose             | Convert path code → table pointer |
| topology            | `10'b0000000111` (AND = g2)   |
| sync_wait / two-arr | 1                              |
| start_flag          | 1                              |
| dtype               | 00                             |
| ctype               | 00                             |
| pair_flags [24:23]  | 11 (marks RESULT role)         |
| input_address       | Where next_path_value arrives  |
| output_address      | Pointer address                |
| a_data (stored)     | Mask (e.g. 0x000000FF)         |

Notes:
- First arrival = mask (preloaded in a_data)
- Second arrival = path code
- Output = path & mask = table pointer

---

## 4. TABLE Node (T)

Final output stage — listens to pointer address and emits the result.

| Field               | Value                          |
|---------------------|--------------------------------|
| Purpose             | Lookup final action/state      |
| topology            | `10'b0000101100` (PASS_B)     |
| sync_wait / two-arr | 0 (single arrival fires)       |
| start_flag          | 1                              |
| dtype               | 00                             |
| ctype               | 00                             |
| pair_flags [24:23]  | 00 (not part of a pair)        |
| input_address       | Pointer address                |
| output_address      | Final output address           |
| a_data (stored)     | Optional default value         |

Notes:
- Single output point of the entire decision tree
- Multiple TABLE nodes can be attached for multi-output systems
- PASS_B outputs the trigger value (the pointer) not the stored value

---

## Summary

| Node    | Topology | Two-arrival | pair_flags | Output        |
|---------|----------|-------------|------------|---------------|
| COMPARE | XNOR     | Yes         | 01         | 1 or 2        |
| CHOICE  | ADD/PASS | Yes         | 10         | next_path     |
| RESULT  | AND      | Yes         | 11         | pointer       |
| TABLE   | PASS_B   | No          | 00         | final result  |

---

## Implementation status

**Deferred** — implementation blocked until:
- INT32 two-arrival chain propagation fixed (fp_tiles relay boundary issue)
- test_compiler_v2.py fully passing
- Model library updated

pair_flags [24:23] use the dtype field bits which currently encode
NUMERIC/SIGNED/ALPHA/DATETIME. This will need a separate field or
a compiler convention to avoid collision. Flag for design review when
implementation starts.

sync_wait noted in the table — this maps to the two-arrival model
(first arrival = A stored in a_data, second arrival = live input triggers).
GS_SYNC_WAIT is retired from gate_states; two-arrival is now the default.
