# MAN files

A MAN file describes a **target card's real identity and capabilities** —
device facts (part, resources, real Chip Planner coordinates) plus board
facts (what the PCB actually wired to which pin). It is one of the four
architectural artifacts decided back at `points.md` #19/#23:

| Artifact | Describes | Card-specific? |
|---|---|---|
| **MAN** | the target card (this directory) | yes — one per physical card model |
| **ICM** | the user's model/program | no — shape- and card-neutral |
| **SHAPE** | a specific compiled design's own cell layout/adjacency | yes — one per build |
| **BITSTREAM** | `SHAPE + MAN → bitstream`, one generation run | yes |

**Don't confuse MAN with SHAPE.** MAN is authored once per card model, from
manufacturer specs and real Quartus/Chip Planner data — it changes rarely,
only when new real hardware facts are confirmed. SHAPE is extracted fresh
per compiled design (`points.md` #449) — it changes every time the RTL's own
cell layout changes. A single MAN file gets reused across many different
SHAPEs targeting the same physical card.

## The real payoff: capability gating

The `capabilities` block is what lets the loader/RTL generator refuse to
offer features a target card can't support. A card that lacks DSP hardware
entirely — an iCEBreaker (Lattice iCE40) is the concrete example that came
up — would simply have `dsp: false` in its own MAN file, and any loader
reading it would never present DSP-backed cell types as an option for that
target, rather than failing at synthesis time. Same idea for BRAM, PCIe, or
any other fixed feature a given device may or may not physically have.

## Files

- `mustang-f100-a10.man.json` — the first real MAN file, for the current
  primary hardware target (IEI Mustang-F100-A10, Arria 10 GX
  `10AX066H2F34E2SG`). Hand-assembled from real data already confirmed
  elsewhere in `points.md` (see its own `provenance` field) — **not yet**
  produced by the canonical `.pin`-file generator method (`#28`/`#29`).

## Real, honest gaps in the current file

- **A real `.pin` file now exists and has been partially processed
  (`points.md` #454, `mustang-f100-a10-v3.pin.txt`).** `CLK_100M`
  (explicitly constrained, stable), `LED0_N`/`LED1_N` (auto-placed, NOT
  guaranteed stable across recompiles, NOT independently confirmed
  against the board's own schematic), JTAG device pins, and
  configuration-mode pins are now real, cross-checked data rather than
  hand-assembled placeholders. `#28`/`#29`'s own canonical DEVICE-FACTS
  generator method still hasn't been run in full, though — the current
  extraction pulled out the real signals of interest by hand rather
  than mechanically parsing the entire pin table, so this is real
  progress, not the complete, exhaustive dataset that method describes.
- **PCIe pin facts are real and confirmed, but belong to the archived
  architecture.** See the file's own `board.pcie.status_note` — the refclk
  and lane assignments genuinely trained a link on real hardware, but the
  RTL that did it is legacy code, not the active Unicell-S/nano substrate.
  Now independently re-confirmed a second way (2026-08-23): every pin in
  all 4 transceiver banks in the real v3 `.pin` file reads unused.
- **No physical placement coordinates for the current substrate's own
  cells.** This MAN file covers fixed device/board facts only. Per-design
  cell placement (which specific CELL_ID landed at which X/Y) is real,
  separate, per-build data that would come from a real post-fit Quartus
  export — not something a MAN file (a per-card-model artifact) should
  hold at all; that belongs with a SHAPE file instead.
