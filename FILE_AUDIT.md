# Stale Root File Audit
**Created: May 2026 — tracks files not touched in 2-4 weeks**

Organised by dependency order (foundations first) and urgency.
Check off each item as it is updated and tested.

---

## Tier 1 — Foundations (no internal deps, others depend on them)

These must be correct before anything higher up can be validated.

| File | Last touched | Lines | Status | Notes |
|------|-------------|-------|--------|-------|
| `model_library.py` | 2026-05-11 | 980 | [ ] | No internal deps. Used by compiler.py + workbench.py. Pre-compiled tile/model registry — needs audit against current tile API (preloaded-A, 32-bit words). |
| `llvm_frontend.py` | 2026-05-09 | 817 | [ ] | No internal deps. Used by llvm_ir_mapper.py only. LLVM IR parser — likely self-contained, check supported instruction subset is still correct. |
| `shore.py` | 2026-04-17 | 277 | [ ] | **Oldest file — 6 weeks.** Depends on pond + cast. Used by nothing currently. Shore v2 spec may have changed — validate against current pond model. |

---

## Tier 2 — Core runtime (depend on Tier 1 or standard libs only)

| File | Last touched | Lines | Status | Depends on | Used by |
|------|-------------|-------|--------|------------|---------|
| `pipeline_queue.py` | 2026-05-10 | 493 | [ ] | controller, gate_states | nothing currently |
| `workspace.py` | 2026-05-11 | 792 | [ ] | nothing internal | workbench.py |
| `fs_search.py` | 2026-05-10 | 1046 | [ ] | nothing internal | run_companion.py, vm_image.py |

**pipeline_queue.py** — pipelined input queue with parallel reference tracking.
Uses controller + gate_states which have both changed significantly.
Needs: validate against new CellMapRecord / preloaded-A model.

**workspace.py** — user's desk (loaded program, named I/O, file index).
Wired into workbench.py. Likely needs VAR_TRUE/FALSE and 32-bit word updates.

**fs_search.py** — heuristic search filesystem (SearchPond).
Used by run_companion and vm_image. Likely self-consistent but needs
validation against current pond model and ICM format v2.

---

## Tier 3 — Application layer (depend on Tier 1+2)

| File | Last touched | Lines | Status | Depends on | Used by |
|------|-------------|-------|--------|------------|---------|
| `display_pond.py` | 2026-05-10 | 694 | [ ] | pond_types | nothing currently |
| `companion.py` | 2026-05-10 | 985 | [ ] | imago_log only | compiler_pond, program_image, run_companion, vm_image, workbench |
| `llvm_ir_mapper.py` | 2026-05-10 | ~400 | [ ] | llvm_frontend | nothing currently |

**display_pond.py** — delta-rendering pixel display. Depends on numpy + pond_types.
Wait until pond layer fully settled. Lower priority unless display features needed.

**companion.py** — COMPANION base OS controller. Central authority for all ponds.
Used by 5 other files. High impact if stale — key thing to check: boot sequence
matches current controller/program_image API. Only 1 stub/TODO found — may be OK.

**llvm_ir_mapper.py** — lowers LLVM IR to CellMapRecord list. Depends on
llvm_frontend.py (Tier 1). Check lowering still produces valid ICM format v2 output.

---

## Tier 4 — Entry points / runners (depend on everything)

| File | Last touched | Lines | Status | Depends on | Notes |
|------|-------------|-------|--------|------------|-------|
| `run_companion.py` | 2026-05-10 | ~300 | [ ] | companion, device_bridge, fs_search | Full system boot. Only valid once Tiers 1-3 are settled. |
| `device_bridge.py` | 2026-05-11 | 1078 | [ ] | imago_log only | **Wait for PCIe on Optiplex.** 21 stubs/TODOs — most are device driver stubs that need hardware. |

---

## Claudette files (referenced but not found in root — may be in subdir)

| File | Last touched | Status | Notes |
|------|-------------|--------|-------|
| `claudette_v1.py` | unknown | [ ] | Not in root — find location |
| `claudette_v2.py` | unknown | [ ] | Not in root — find location |

---

## Suggested work order

```
1. shore.py          ← oldest, foundational, no blockers
2. model_library.py  ← needed by compiler + workbench, self-contained
3. pipeline_queue.py ← validate against new controller API
4. workspace.py      ← needed by workbench, relatively isolated
5. fs_search.py      ← needed by run_companion, validate against ICM v2
6. companion.py      ← central authority, audit boot sequence
7. llvm_frontend.py  ← self-contained, then llvm_ir_mapper.py
8. display_pond.py   ← wait for pond layer to settle
9. device_bridge.py  ← wait for PCIe on Optiplex
10. run_companion.py ← last, only valid when all others done
```

---

## Progress

- [ ] shore.py
- [ ] model_library.py
- [ ] pipeline_queue.py
- [ ] workspace.py
- [ ] fs_search.py
- [ ] companion.py
- [ ] llvm_frontend.py + llvm_ir_mapper.py
- [ ] display_pond.py
- [ ] device_bridge.py  *(blocked on PCIe hardware)*
- [ ] run_companion.py  *(blocked on above)*
- [ ] claudette_v1/v2   *(locate files first)*
