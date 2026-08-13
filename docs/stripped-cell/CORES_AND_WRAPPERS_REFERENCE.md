# Cores & Wrappers — Cross-Reference Table

**A living reference, not a deep dive on any one cell.** For the
detailed internal structure of the original nano/stripped cell itself
(`unicell_stripped_v1.v`/`v2.v`), see `CELL_INTERNALS.md` — that
document isn't repeated here. This file exists to answer a different
question: *across everything built so far, what's a CORE, what's a
WRAPPER, what's neither, and what's actually been proven where?*

**Update this file whenever a new core/wrapper is built or a status
changes** — same discipline as everything else in this project:
`points.md` is the ground-truth ledger for the story of HOW something
was proven; this file is the settled, current SNAPSHOT of WHAT exists.
If they disagree, `points.md` wins — re-check the relevant entry
numbers cited below.

## The SHELL — identical across every core

Every cell in this table shares the same external interface, regardless
of what's inside. This is the whole point of the SHELL/CORE split
(`points.md` #253): only the CORE differs between rows below.

| Port group | Signals |
|---|---|
| Data | `data_in_n/s/e/w`, `data_out_n/s/e/w` (32-bit each) |
| Handshake | `arrived_n/s/e/w`, `fire_n/s/e/w`, `ready_in_n/s/e/w`, `ack_out_n/s/e/w`, `ack_in_n/s/e/w` |
| Control | `freeze_in`, `cfg_valid`, `cfg_data` (64-bit, field layout is CORE-specific — see each row's own file header) |
| Readiness | `ready_out` — present on most cores; **`accumulator_cell_v1.v`/`latch_cell_v1.v` genuinely lack this port** (see notes below, not an oversight for those two, though its ABSENCE from an early draft of `top_sentinel_discrete_test_v1.v`'s own wiring WAS a real bug, `points.md` #298) |

## CORES — what's inside the shell

| Core | File | Internal capture pattern | Internal shell connection | Real Quartus status |
|---|---|---|---|---|
| Nano (gate tree) | `unicell_stripped_v1.v` | Two-arrival, full gate computation | Direct combinational logic on captured operand(s), see `CELL_INTERNALS.md` for the complete internal model | **Real, standalone** — ~100–106 ALM (`#209`/`#224`) |
| RAM (latch) | `ram_cell_v1.v` | Single-arrival capture, held until drained | Captures once → holds → offers on drain | **Real, standalone** — 3.86 ALM, 277.32 MHz (`#250`) |
| Adder | `adder_cell_v1.v` | Two-arrival matched pair | Captures A, then B (direction-agnostic) → `adder_v1.v` carry chain → offers sum | **Real, standalone** — 5.24 ALM, 233.97 MHz (`#261`) |
| Memory-interface | `mem_interface_cell_v1.v` | Single-arrival, READ/WRITE mode | Captures addr/data → drives `bram_controller_v1.v` | Sim-only |
| Mux (routing) | `mux_cell_v1.v` | Single-arrival, routing-byte decode | Captures value+routing → decrements count → selects one of 3 usable output faces | Real only *inside* the full-system aggregate (`#280`/`#283`/`#286`) — no standalone ALM/Fmax breakdown exists |
| Combiner (root) | `combiner_cell_v1.v` (proven) / `v2.v` (tree-capable, `#295`'s own reference) | Fixed round-robin scan, unconditional advance | Scans configured slots → stamps ID → writes `bram_controller_v1.v`/`v2.v` directly (not through the cardinal offer/drain path) | Real only inside the aggregate — no standalone breakdown |
| Combiner (child) | `combiner_relay_v1.v` | Same round-robin scan as root | Same scan, offers UPWARD via cardinal data+routing instead of writing to BRAM | Real only inside the aggregate |
| Read-splitter | `mem_read_splitter_v1.v` (proven, READ-only) / `_test.v` (debug-write extension) / `_ext.v` (external-memory variant) | Single-arrival address capture | Captures address → drives BRAM → splits DATA/ROUTING onto separate outputs | Real only inside the aggregate |
| **Accumulator** | `accumulator_cell_v1.v` | Hold-and-refire, direction-tagged, capture NEVER blocked | Arrivals on `inc_dir`/`dec_dir` update the internal total unconditionally; the OFFERED snapshot only refreshes when free (`#294`'s own real protocol adaptation) | Sim-only — Quartus attempted, real bug found in the test harness, not the core (`#298`) |
| **Comparator** | `compare_cell_v1.v` | Single-arrival, STATELESS | Captures value → compares against a configured threshold → offers boolean result | Sim-only (same status as above) |
| **Latch** | `latch_cell_v1.v` | Hold-and-refire, SET/CLEAR, capture NEVER blocked | Arrivals on `set_dir`/`clear_dir` update the internal latch unconditionally; CLEAR takes priority if both arrive the same cycle (`#279`/`#284`'s own established rule) | Sim-only (same status as above) |

**A note on the accumulator/latch's missing `ready_out`:** genuinely
correct by design — since capture is never blocked, these two cores are
always ready, so a `ready_out` port would just be tied permanently high.
The REAL bug (`#298`) wasn't the absence of the port on the core itself
— it's that a later integration wired a downstream consumer's
`ready_in` to a wire that was never actually connected to anything,
because the port didn't exist to connect it TO. Worth remembering if
either core is extended: add the port explicitly rather than relying on
implicit "always ready."

## Building blocks the cores WRAP, not cores themselves

These have no shell, no cardinal ports — plain modules that a real core
instantiates internally.

| File | Role | Real Quartus status |
|---|---|---|
| `adder_v1.v` | Raw carry-chain adder | Confirmed real via `adder_cell_v1.v`'s own build |
| `addr_counter_v1.v` | Ack-gated wrapping counter | Confirmed real via its own dedicated top-level (`#249`) |
| `bram_controller_v1.v` | Single-stage synchronous read/write | **Real, standalone**: 145 ALM, 158.78 MHz, exact M20K bit-count match (`#265`) |
| `bram_controller_v2.v` | Registered-read-address fix for hierarchy-depth RAM-inference failure (`#284`) | Real, confirmed via the full-tree-system aggregate build (`#284`/`#286`) — no standalone breakdown |

## The other two architectural categories, per `#253`/`#293`

Not every real component built this project is a CORE (something that
fits inside the shell). Two more categories exist:

| Category | Definition | Real examples | Status |
|---|---|---|---|
| ADDON | Wraps around a cell's own shell from OUTSIDE to extend its capability, while the cell still participates in the cardinal fabric mesh | None built yet in the current (stripped-cell) line | Designed conceptually (`#253`), no real instance |
| HOST-INTERFACE | No cardinal ports at all, doesn't join the fabric mesh — bridges the fabric to something OUTSIDE it entirely (JTAG today) | `pcie/unicell_issp_bridge.v` (pre-existing, full-cell era), `sentinel_issp_bridge_v1.v` (`#288`) | **Real, hardware-confirmed** (`#291`) — but see `#293`'s own real cost: baked into the bitstream at synthesis time, no runtime toggle, every real hardware exercise needing one this session used its own dedicated Quartus project |

## Quick answers to "is X proven yet?"

- **Standalone Quartus data (its own dedicated build, ALM/Fmax isolated to that one core):** nano, RAM, adder, `bram_controller_v1.v`, `addr_counter_v1.v` — the original, earliest-built pieces.
- **Real Quartus data, but only as part of a larger aggregate (no isolated ALM/Fmax number exists for that core alone):** mux, combiner (both variants), splitter (all variants), `bram_controller_v2.v`.
- **Sim-only so far, Quartus attempted but blocked by a real bug in the test harness (not the core):** accumulator, comparator, latch (`#298`) — the actual RTL is fully proven in simulation via dedicated, focused testbenches; only the multi-pass self-test wrapper around them has an open issue.
