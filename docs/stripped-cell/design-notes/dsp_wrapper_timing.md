# DSP wrapper real timing and watchdog thresholds

Real, per-mode data for the four DSP wrapper variants built this
session (`points.md` #453/#461-#466). Two real, distinct kinds of
number here — keep them separate:

- **Real, confirmed DSP compute latency** — from Intel's own real
  documentation (`#462`), independent of anything this project built.
- **Real, measured wrapper round-trip** — from this project's own real
  sim runs (`tests/fpga/tb_dsp_four_modes_v1.v`), which includes the
  DSP latency plus this wrapper's own real protocol overhead (operand
  capture, the wait-state machine). The wrapper number is always a
  little larger than the raw DSP number — that's real, expected
  overhead, not a bug.

| Mode | Module | Real DSP latency (Intel, confirmed) | Real wrapper round-trip (measured, this session) | Confidence |
|---|---|---|---|---|
| ADD | `dsp_arith_wrapper_v1.v` (OP="ADD") | 3 cycles | 5 cycles | Confirmed (`#462`) |
| SUB | `dsp_arith_wrapper_v1.v` (OP="SUB") | 3 cycles | 5 cycles | Confirmed (`#462`) |
| MUL | `dsp_arith_wrapper_v1.v` (OP="MUL") | 3 cycles | 5 cycles | Confirmed (`#462`) |
| GE  | `dsp_compare_wrapper_v1.v` (OP="GE") | 1 cycle (assumed) | 4 cycles | **Assumed**, not independently confirmed — see below |
| LE  | `dsp_compare_wrapper_v1.v` (OP="LE") | 1 cycle | not yet tested | Confirmed (`#462`) |
| NEQ | `dsp_compare_wrapper_v1.v` (OP="NEQ") | 0 cycles | not yet tested | Confirmed (`#462`) — real 0-cycle path structurally present, not exercised in sim yet |

**On the GE assumption:** `#462`'s own real search result named
`alterafpf_ge_single_GE` but was cut off before showing its own real
cycle count. `LE`'s real, confirmed 1-cycle value is used as the
reasonable stand-in — same comparison class of operation, most likely
the same real cost — but this is a stated assumption, not a confirmed
fact, and should be checked against real Intel documentation (or the
real generated IP itself) before being trusted for anything that
matters.

**Real, honest note on measured wrapper timing:** these numbers reflect
this project's own real simulation, using stub megafunctions that
reproduce the real, confirmed *timing* but deliberately NOT real
IEEE-754 arithmetic (`tb_stub_alterafpf_*_v1.v`, see each file's own
header). Real hardware confirmation is still pending, same "build now,
confirm against real generation" pattern as every other real IP
integration this session.

## Real watchdog threshold recommendation

The watchdog's own `activity_pulse` resets on ANY real forward progress
(either operand arriving, or the operation completing) — not just full
completion (`#465`). So the threshold isn't really "how long does the
compute take" — it's "how long is it reasonable to wait for the *next*
real event," and the compute latency is only the real, hard *floor*
that value must clear.

A reasonable real starting point, not a fixed rule: **compute latency
× 4, minimum 10 cycles** — generous enough to absorb real routing/
fanout variance between the wrapper and its real neighbors, without
being so loose that a genuinely stuck chain goes undetected for an
unreasonable time.

| Mode | Real compute latency | Suggested real watchdog threshold |
|---|---|---|
| ADD / SUB / MUL | 3 cycles | 12 cycles |
| GE / LE | 1 cycle | 10 cycles (floor applied) |
| NEQ | 0 cycles | 10 cycles (floor applied) |

**This is a starting point for a first real build, not a fixed
constant.** The real, correct value for any given instance depends on
real, per-chain context this document can't know in advance — how far
upstream the real operand sources sit, how busy the shared BRAM path
is, how many other chains are contending for the same real fabric
resources. Matches `#464`'s own real design point precisely: the
threshold is a real, `cfg_valid`-loaded port specifically so each real
instantiation can be tuned for its own real context, not a single
number baked in for every use.
