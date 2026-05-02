# Imago UniCell

A compute architecture built from identical NOR-gate cells arranged in arrays,
communicating via a shared bus. Each cell is independently configurable —
gate topology, input/output addresses, and operating mode are all set at
load time. Arrays of cells implement arbitrary logic by composition.

## Three Variants

This repository contains three independent implementations of the UniCell
architecture. Each is a complete, self-contained codebase with its own VM,
compiler, tests, and FPGA target. They share no code — changes to one
variant are applied to that variant only.

---

### `unicell-standard/` — Standard Model

The original implementation. Cells fire immediately on data arrival and
drive the bus in the same tick. No latency registers, no edge awareness.

**Use for:** simulation, reference implementation, algorithm development.

---

### `unicell-latch/` — Latch Model *(in development)*

Forked from Standard. Each cell has an input latch and an output latch.
The clock controls **flow only** — the gate tree runs combinatorially
at its own speed. Fixed 2-tick latency per cell. Timing is controlled
by topology: insert a PASS cell to add 2 ticks of delay anywhere.

**Use for:** FPGA deployment where timing stability matters, especially
large arrays. More predictable than edge model, immune to clock skew.

**Status:** Fork created 2026-05-02. Latch implementation pending.

---

### `unicell-edge/` — Edge Model (v2)

The current primary FPGA target. Cells are edge-triggered: A input on
rising edge, B input on falling edge, output buffer released on the
next configurable edge (GS_OUT_POSEDGE, bit 26). One-cycle latency
per cell in feed-forward paths.

**Use for:** iCEBreaker bring-up and FPGA validation.

**Status:** v2.1 tagged, 2,238 tests passing, iCEBreaker awaited.

---

## Choosing a Variant

| Question | Answer |
|----------|--------|
| Simulating or developing algorithms? | Standard |
| FPGA bring-up right now? | Edge |
| Large FPGA array, long-term stability? | Latch (when ready) |
| Unsure which FPGA model is more stable? | Build both Edge and Latch, compare |

## Repository Structure

```
README.md               — this file
MIGRATION_TODO.md       — architectural decisions and pending work
sessions/               — session logs (shared across variants)
SESSION_START.md        — quick-start prompt for new sessions

unicell-standard/       — Standard variant (complete)
unicell-latch/          — Latch variant (fork of standard, in development)
unicell-edge/           — Edge variant (complete, primary FPGA target)
```

## Architecture

Each UniCell is a 32-bit NOR-gate array with:
- Configurable gate topology (bits 0-8 of gate_state)
- Configurable input and output bus addresses
- Optional modes: SELECT, LOOP, LATCH, STORAGE, FREEZE
- ECC (SECDED) on bus values when enabled

Cells are grouped into **Ponds** (isolated compute environments with
security, access control, and bridge lanes). Ponds communicate via
**Bridges** (INBOUND, OUTBOUND, MONITOR, LOG). The **Shore** is a
service-discovery layer mapping names to Pond addresses.

See `docs/` inside each variant folder for full architecture documentation.
