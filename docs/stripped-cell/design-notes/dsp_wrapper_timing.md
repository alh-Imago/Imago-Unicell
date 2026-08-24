# DSP wrapper — real status, timing, cost, and watchdog thresholds

Real, current status for the DSP wrapper family built and corrected
across `points.md` #453/#461-#475. This document was substantially
rewritten on 2026-08-24 to replace an earlier version that carried
wrong entity names, wrong latency figures, and was missing the two
most important real findings from actual hardware testing. If you find
an older cached copy of this file, don't trust it — this one reflects
what's actually confirmed as of `#475`.

## Real hardware confirmation status — read this first

**Only ADD has been run on real hardware and confirmed correct
(`#472`).** SUB and MUL share the identical real entity/port/protocol
path as ADD and are sim-verified only. GE/LE/NEQ are sim-only, and
their own real IP entity name is a reasoned placeholder pending real
generation (`#475`) — comparison operations use a different real
Nios II custom instruction ("Combinational") than the arithmetic ops
("Multi-cycle"), and this project has not yet seen a real, generated
`.qsys` file for that variant.

## The IP actually in use — and what it is NOT

The real, working IP is **"Floating Point Hardware 2 Multi-cycle"**
(module kind `altera_nios_custom_instr_floating_point_2_multi`, real
top-level instantiable name is whatever you name the instance in IP
Catalog — this project's own real instance is named
`alterafpf_add_single`, confirmed the hard way across `#469`-`#471`).

**Real, important finding from Alan's own real Fitter report (`#472`):
`Total DSP Blocks 0 / 1,687`.** This IP does **not** use the real hard
DSP silicon — it's a soft, LUT-based implementation. The real Control
Signals data shows genuine floating-point datapath logic (mantissa
alignment, exponent handling) built entirely from fabric ALMs. This
directly corrects this project's own original premise (`#453`/`#461`:
"the DSP does the math side completely, no fabric cost") for this
specific IP choice. A real alternative that likely does use hard DSP
blocks — "Native Floating Point DSP Intel Arria 10 FPGA IP," under
Primitive DSP in the IP Catalog — was seen but not pursued. Real,
explicitly deferred decision (`#475`): whether to chase that path is
on hold until real PCIe capability is available.

## Real, precise cost (`#473`, from Alan's own real Fitter Resource
Usage report — not estimated)

| Component | Real ALM |
|---|---|
| Real float-add core itself (`FPAddSub`) | 299.5 |
| Real float IP total (incl. own overhead) | 302.2 |
| This wrapper's own real glue logic | 51.8 |
| Real watchdog | 23.7 |
| **Real DSP_ADD wrapper total** | **354.0** |

**Use 354.0 ALM/instance for any real scaling estimate** — not the
568 ALM figure from the first real build, which included the one-time,
shared JTAG bridge + ISSP + SLD debug infrastructure (a real, one-time
cost, not paid per DSP instance in a larger design).

Real example: Alan's own "2 DSP wrappers per chain, normal card
profile" assumption, at the real 27-chain scale family (`#416`/`#425`):
27 × 2 × 354.0 = **19,116 ALM, 7.6% of total fabric**.

## Real timing

| Mode | Module | Real `n` | Real DSP latency (Intel, confirmed) | Real wrapper round-trip (measured) | Real hardware confirmed? |
|---|---|---|---|---|---|
| ADD | `dsp_arith_wrapper_v1.v` (OP="ADD") | 253 | 5 cycles | 9 cycles | **Yes (`#472`)** |
| SUB | `dsp_arith_wrapper_v1.v` (OP="SUB") | 254 | 5 cycles | 9 cycles | Sim only |
| MUL | `dsp_arith_wrapper_v1.v` (OP="MUL") | 252 | 4 cycles | 8 cycles | Sim only |
| GE  | `dsp_compare_wrapper_v1.v` (OP="GE") | 228 | 1 cycle (assumed, see `#475`) | 3 cycles | Sim only, entity name unconfirmed |
| LE  | `dsp_compare_wrapper_v1.v` (OP="LE") | 230 | 1 cycle (confirmed) | not yet tested | No |
| NEQ | `dsp_compare_wrapper_v1.v` (OP="NEQ") | 226 | 0 cycles (confirmed) | not yet tested | No |

These are the real, corrected numbers (Intel's own official "Floating
Point Custom Instruction 2 Operation Summary" table) — ADD/SUB take 5
real cycles, not the 3-cycle figure this document originally stated
before the real correction. MUL is genuinely 1 cycle faster than
ADD/SUB, and this is confirmed to show up correctly in the real
wrapper's own measured round-trip time (8 vs 9 cycles) — the wrapper's
`start`/`done` handshake tracks each operation's own real latency
directly, it does not assume a fixed number.

## Real watchdog thresholds — the most important real lesson from this
whole thread, found on actual hardware, not caught in sim

**Real, hard-won finding (`#472`): a watchdog threshold sized for fast
simulation will immediately false-trip on real, JTAG-driven hardware.**
Real JTAG round-trip time is on the order of **milliseconds**
(`#448`'s own real, measured figure: ~6.5ms/command ≈ 162,500 cycles
at the real 25MHz fabric clock) — nothing remotely close to the
handful of cycles a simulation-convenient threshold value assumes. A
real test run that used threshold=50 (2 real microseconds) watched the
watchdog correctly trip every single time, because no real JTAG
command can possibly arrive within 2 microseconds. **This was not a
watchdog bug — it was a threshold value that made sense in sim and
nowhere else.**

**Real, concrete guidance, split by real context:**

- **For a chain whose own activity is purely internal to the fabric**
  (operand sources are other fabric cells, not a slow, JTAG-paced
  host): the compute-latency-based rule from earlier remains reasonable
  — real compute latency × 4, minimum 10 cycles.

  | Mode | Real compute latency | Suggested real watchdog threshold |
  |---|---|---|
  | ADD / SUB | 5 cycles | 20 cycles |
  | MUL | 4 cycles | 16 cycles |
  | GE / LE / NEQ | 0-1 cycles | 10 cycles (floor applied) |

- **For a chain whose own activity is gated by a real, JTAG-driven
  host** (any bring-up/test build like `top_dsp_chain_v1.v`): the
  threshold needs real headroom well beyond `#448`'s own measured
  ~162,500-cycle real command gap — a real, generous multiple of that
  (e.g. 1,000,000+ cycles, using a wider `WATCHDOG_WIDTH`, 24 or 32
  bits, not the default 16-bit/65,535-cycle ceiling, which is itself
  smaller than one real JTAG round trip) is the honest, real starting
  point, not a small, sim-convenient number.

This is a real, deliberate, `cfg_valid`-loaded port (`#464`) precisely
so each real instantiation can be tuned for its own real context —
these are starting points for a first real build, not fixed constants.
