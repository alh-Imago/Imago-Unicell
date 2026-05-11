# Latest Session — 2026-05-11 (session 4)

## Tests
2,381+ passing / 6 failing (all pre-existing deprecated)
test_compiler.py: 39/39
test_compiler_int32.py: 82/82
test_ptt_sentry.py: 20/20 (new)

## Latest commit
TBD — code audit: sentry PTT wiring, model_library figures, boundary tests

## What was done

### Code audit 2026-05-11
Full sweep of TODO/FIXME/stub/placeholder/NotImplemented markers. Found and fixed:

**Critical fixes:**
- controller.load_map(): added ptt= parameter. When set:
  - Sets cell._ptt_ref = ptt on every loaded cell (was never set — PTT machinery was dark)
  - Patches sentry cells from PTT_BUS_BASE placeholder to correct ptt_bus_address(index)
- New test: test_ptt_sentry.py (20 tests) — verifies _ptt_ref wiring, sentry
  address patching, PTT status transitions, per-tile independence

**Stale figures fixed:**
- model_library.py: INT32_EQ corrected 63→95 cells, 6→7 depth
- model_library.py: "FP32 estimates" comment removed (figures verified v2)
- model_library.py: INT32_MIN/MAX descriptions corrected to "signed"
- gate_states.py: stale TODO comment removed (GS_OUT_POSEDGE already set)

**Boundary tests added:**
- test_compiler.py: chained comparison, non-range iterable, Pow, subscript AugAssign
- test_compiler_int32.py: chained int32 comparison, Pow

**Intentional stubs documented:**
- AudioBridge/VideoBridge: tracking comment added
- Peripheral tile stubs (records=[]): intentional, documented
- uniflex_fs FsDecoderStub: intentional simulator path

## Hardware status
- JTAG programmer: in transit, ~21 May 2026
- Kintex-7 XC7K480T: in transit, ETA Jul 2026

## Next session priorities
1. postcode_sort.py: use INT32 sort for real Haversine distances
2. Composer: add INT32_LT_U/S, MIN, MAX, CAS to model library UI
3. Review pre-existing test failures (IndexError, TypeError, CLA) — are they real?
