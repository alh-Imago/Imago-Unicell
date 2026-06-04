# UniCell Codebase Audit — Known Bugs and Workarounds
*2026-06-04 — honest assessment, not session notes*

---

## Purpose

This documents real bugs and workarounds that have accumulated.
Some are minor, some are significant. The goal is to fix these properly
rather than let workarounds compound into something harder to untangle.

---

## CRITICAL — Bugs that affect correctness silently

### 1. MUX selector address space mismatch
**File:** compiler_int32.py — `_place_int32_mux`
**Symptom:** `if x > 0: return 10 else: return 20` always returns 20.
  Statement form and ternary form both broken for constant branches.
**Root cause:** The selector node comes from the IR graph (virtual address
  space used during lowering). `_place_int32_mux` uses `sel_node.output_addr`
  to wire a PASS relay into the tile placer address space — but these two
  address spaces aren't the same. The PASS relay writes to an address that
  the MUX tile's selector input never sees.
**Impact:** Any if/else returning int32 constants is silently wrong.
  The false branch always fires. The test suite doesn't cover this case.
**Fix needed:** Selector node must be lowered to a tile placer address
  before being passed to `_place_int32_mux`. Or restructure so the
  condition result is emitted as a tile record with a known bus address
  rather than relying on the IR graph address.

### 2. Output padding uses bare GS_PASS without GS_LATCH_IN
**File:** compiler_int32.py — `_pad_int32_to_depth` and `_place_int32_tile`
**Symptom:** Output bits at non-maximum depth may not fire in
  single-wave propagation. Padding cells wait for two arrivals but
  only one arrives.
**Root cause:** Padding chains use `CellMapRecord(GS_PASS, ...)` without
  `GS_LATCH_IN`. A bare PASS cell needs two arrivals to fire. In
  single-trigger-wave execution it never gets the second.
**Impact:** Depth-mismatched int32 results may have incorrect bits
  depending on which bits needed padding. Silent corruption.
**Fix:** All padding chain records need `GS_PASS | GS_LATCH_IN`.
  Line 371 and line 808 in compiler_int32.py are the main instances.

### 3. MUL preloaded_a normalisation
**File:** compiler_int32.py — `run_int32_function` Case 3
**Symptom:** MUL with values that produce intermediate 0/1 carry bits
  may get wrong results.
**Root cause:** In the forward simulation, values 0 and 1 may reach
  XOR cells as single bits (0 or 1) rather than bus-width values
  (0x00000000 or 0xFFFFFFFF). XOR(1, 0xFFFFFFFF) = 0xFFFFFFFE, not 0.
**Impact:** Intermittent wrong MUL results depending on operand values.
  The test suite passes specific cases that happen to avoid this.
**Note:** This becomes moot once a_preload_en lands in Verilog, which
  eliminates the forward simulation entirely. Worth fixing now or
  deferring to that point — but documented either way.
**Fix:** Normalise all forward sim values to 0x00000000 / 0xFFFFFFFF
  before they enter the XOR/AND/OR cell computations.

---

## STRUCTURAL — Dead code that creates confusion

### 4. Duplicate compile_int32_function
**File:** compiler_int32.py lines 136 and 1260
**Problem:** Two definitions of the same method. Python uses the last
  definition (line 1260, 5-tuple return). Line 136 (4-tuple return)
  is completely dead — never called, never tested, return type wrong.
  Any maintenance on line 1260 leaves line 136 silently wrong.
**Fix:** Delete lines 136-225 entirely. Straightforward.

### 5. Dead code block after return at line 380
**File:** compiler_int32.py lines 382-425
**Problem:** A full code block (init checks, segment span tracking,
  tile depth calculation) sits after a `return` statement. Never executes.
  It appears to be a copy-paste remnant from an earlier refactor.
**Fix:** Delete lines 382-425.

---

## WORKAROUNDS — Things that work but shouldn't have to

### 6. Multi-param function: put non-passthrough param first
**File:** compiler_int32.py — `run_int32_function`
**Symptom:** In functions with multiple int32 parameters, the first
  parameter is excluded from re-injection. If the first param feeds
  cells that need re-injection, results are wrong.
**Workaround:** Put the parameter that feeds directly into tile in_a
  as the first argument. The second parameter gets re-injected correctly.
**Root cause:** Re-injection logic in `run_int32_function` skips
  addresses in `input_bit_map[first_param]`.
**Fix needed:** Re-injection should cover all parameters equally.

### 7. Two-pass forward simulation for preloaded-A
**File:** compiler_int32.py — `run_int32_function`, `LoadedInt32Function`
**What it is:** Python forward-simulates the cell network twice per call
  to compute correct a_data preloads before running the controller.
**Why it's a workaround:** The hardware cell already has bits planned
  (a_preload_en / a_preload_val) to self-load at configure time.
  The Python sim is standing in for hardware that isn't built yet.
**Impact:** Performance — adds Python overhead per call. Not a
  correctness issue. Moot once Verilog a_preload_en lands.
**No action needed now** — but don't build more on top of this pattern.

### 8. one_shot exemption list in test_fp_tiles.py
**File:** tests/vm/test_fp_tiles.py line 94
**What it is:** Hardcoded list of tiles that must NOT use one_shot:
  `('INT32_ADD', 'INT32_ADD_CLA', 'INT32_SUB', 'INT32_MUL')`
**Why it's a workaround:** one_shot suppresses re-fires, which is
  correct for AND/OR reduction trees but breaks carry propagation.
  The test runner has to know which tiles carry-propagate.
**Better fix:** Tile metadata should declare whether it uses carry
  propagation. The test runner reads the flag rather than a hardcoded list.

---

## GAPS — Missing tests for known failure cases

### 9. MUX selector bug has no test
The if/else branch returning constants is untested. The bug is silent
and only visible when you actually run the code. Needs a test that
catches the always-false-branch failure.

### 10. Depth padding correctness untested
The GS_PASS padding bug (issue 2) has no test covering depth-mismatched
operands. A test pairing a shallow result with a deep result would
catch it.

### 11. Multi-param ordering workaround untested
No test that verifies both parameters contribute correctly to the result.
The test suite only tests single-param and same-depth two-param cases.

---

## Priority order for fixing

**Fix first (correctness, silent failures):**
1. Output padding GS_PASS → GS_PASS | GS_LATCH_IN (issue 2) — simple
2. Dead code removal (issues 4 and 5) — low risk, cleans up confusion
3. MUL normalisation (issue 3) — before MathTrix uses MUL heavily

**Fix when investigating MUX:**
4. MUX selector address space mismatch (issue 1) — needs proper
   investigation, don't rush it

**Fix when Verilog lands:**
5. Multi-param re-injection (issue 6) — related to preload redesign
6. one_shot exemption list (issue 8) — add tile metadata flag

**Defer:**
7. Two-pass forward simulation (issue 7) — moot after a_preload_en

---

## What to watch

The pattern to avoid: adding Python workarounds in `run_int32_function`
to handle special cases. That function is already carrying too much.
Each new workaround makes the next one harder to understand and the
eventual Verilog migration more complex.

The forward simulation (issue 7) was the right call at the time.
The one_shot list (issue 8) was a reasonable fix. But the MUX selector
bug (issue 1) should not be worked around — it needs a proper fix
because any workaround in the address space translation will be hard
to reason about and harder to remove later.
