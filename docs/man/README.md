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

## `tang-nano-20k.man.json` -- the first non-Intel MAN (points.md #887)

The Sipeed Tang Nano 20K (Gowin `GW2AR-LV18QN88C8/I7`), the project's planned coprocessor target, to be paired with an
ESP32-C-series host that owns the web front end, WiFi, and feeding/collecting data. **Generated, not hand-written:**

    python3 tools/man_gen/gen_tang_nano_20k_man.py            # rewrites the .man.json and the .cst
    python3 tools/man_gen/gen_tang_nano_20k_man.py --check    # exit 1 if either committed file is stale
    (needs: pip install apycula msgpack)

Two kinds of fact, kept apart:

- **CHIP facts are read from the Apicula chip database** -- the same one the open place-and-route flow uses: 648 logic
  tiles (x32 = 20,736 LUT4, x24 = 15,552 FF), 46 block-RAM tiles, 12 DSP tiles (48 18x18 multipliers), 8 I/O banks, the
  QFN88 pin table, and the **embedded-SDRAM port list** (55 ports: 11 address, 2 bank, 32 data, 4 mask, 6 control, all
  LVCMOS33; 64 Mbit, 32-bit, inside the package so it has no board pins).
- **BOARD facts** (clock pin 4 at 27 MHz; LEDs 15-20 active low; buttons 88/87; UART 69/70; flash 59-62; SD 80-85) come
  from two working third-party designs and the Sipeed wiki. Each pin is checked to *exist* in the chip database; that
  proves it is real, not that the board is wired that way.

**Not verified, and the file says so:** the schematic has not been checked, nothing has been run on the physical board,
the ESP32 link pins (edge connector 73-77) are a *proposal* taken from a third-party SPI-slave design, and the ESP32-C
variant has not been stated. HDMI, the RGB-LCD connector, the WS2812 and the audio amplifier are listed as unmapped.

**Schema 1.1 (additive; the Arria MAN is unchanged):** `vendor`; `device.logic` counted in LUT4 with `alm_total: null`;
block RAM under `bram` (Intel's is `m20k`); discrete block-RAM/DSP rows as one-row `y_segments`. `card_fit_v1.
target_from_man` takes its budget in LUT4 from `LUT4_PER_POSITION` (measured: `tools/gowin_sizing/`), and refuses an
ALM-measured shell on a LUT4 device. `project_assemble_v1.load_man` (the Quartus generator) now refuses a non-Intel MAN
with a clear message; `load_man_identity` is the vendor-neutral loader the VM mirror uses.

**What it says about fit (measured, synthesis only, pre place-and-route):** one VIX carrier position is 17,339 LUT4
(v1d) or 16,574 (v1) -- 83.6% / 79.9% of the chip, so it does **not** fit at the default 80% ceiling. Standalone cells
fit only a handful at a time (about 4-8 `nano`, 6-41 `ram`, depending on full or lean).

## Getting started on real hardware (points.md #892)

The first real, flashable deliverable for this board: `docs/man/tang-nano-20k-getting-started.md` -- a
one-cell (`sequencer`) proof-of-concept, built through the real toolchain (`yosys` -> real
`yowasp-nextpnr-himbaechel-gowin` place-and-route -> real `gowin_pack` bitstream), with a committed,
ready-to-flash `.fs` file (`fpga/build/`). Confirmed in simulation before synthesis, per real Fmax
(198.3 MHz at a 27 MHz target). Nothing has been run on the physical board yet -- flashing it is next.

## DSP primitives and abilities (read by the assembler)

A card's DSP *types*, how many it can host, and any card-specific abilities are **data about the card**, so they live here and the
assembler only reads them -- it assumes nothing about a vendor. (Alan, 2026-10-04: "the dsp type and availability and other resources
have to be held in the man file ... but used by the assembler.") Under `device.dsp`:

| field | meaning |
|---|---|
| `total_blocks` | how many DSP blocks the card has |
| `primitives` | the primitives the card offers that an assembler cell can instantiate: `{name, operands:[a,b], product_bits, blocks_per_instance}`. `name` is exactly the vendor primitive (it is what the cell instantiates). `blocks_per_instance` says how much of a block one instance uses (a 36x36 on the Tang = 1, an 18x18 = 0.25), so the instances a card can host = `total_blocks / blocks_per_instance`. Different primitives draw on the SAME blocks when `primitives_share_blocks` is true |
| `abilities` | an OPEN list of card-specific abilities, `{name, note}`, that a cell may ask for **by name**. Carried into the assembler's record; nothing consumes one until a cell needs it |
| `chain` | (Arria 10) cascade limits, a placement constraint |

How the assembler uses it (`--icm`, `--man`): a realisation declares which primitive it NEEDS (the DSP multiplier needs `MULT36X36`); the MAN says what the
card HAS. If the card lists the primitive and has blocks left, the DSP cell is used; otherwise the exact logic multiplier. **A card that lists no
primitives (the Arria 10 today) simply falls back -- because its MAN says so, not because of its vendor.** The logic multiplier's cost is a measured
property of that cell per logic unit (LUT4 on Gowin); a card whose unit has no measured cost cannot be budget-checked, and the assembler's record says so.

Provenance rules (same spirit as the rest of this file): the Tang's primitive operand and product widths are **read live from yosys's own declaration**
(`gowin/cells_xtra.v`); `blocks_per_instance` is arithmetic and is marked **DERIVED**; nothing is hand-typed from memory. `y_segments` in `columns` are
ROW coordinates of the DSP tiles, **not operand sizes** -- an earlier assembler mistook them for a "has 36x36" flag (it was only true for the Tang by
coincidence of the row number).

**Open:** the Arria 10's `primitives` and `abilities` are empty. An earlier version of this README and of the Arria 10 MAN said Alan had described a DSP
"shift" option for that card. That came from a voice-to-text message that may have been garbled; Alan does not recall it and the ledger has no record of one
(the only shift near the DSP work is the soft floating-point IP's alignment shifter, `points.md` #472, which is ordinary logic). It is NOT recorded -- add an
ability only from a real source.

`soft_units` (open list, informational): DSP-like blocks built from fabric logic that are KNOWN to work on the card. The Arria 10 has one: the Floating Point
Hardware 2 IP behind the DSP wrapper -- it uses 0 of the 1,687 DSP blocks (`points.md` #472, verified on actual hardware). It is a floating-point unit, not an integer
multiplier, so the assembler's `mul` core does not use it.

## Synthesis options (read by the assembler): `synthesis.nowidelut`

The card's open-toolchain synthesis facts live here too, and the assembler only reads them. Under the top-level `synthesis` block:

| field | meaning |
|---|---|
| `tool` | the synthesis flow this card's generated scripts target |
| `nowidelut.supported` | whether the toolchain offers `synth_gowin -nowidelut` (stop building wide-LUT / MUX2_LUT5..8 mux trees). The Tang's value is **read live** from `yosys -h synth_gowin` by the MAN generator, not hand-typed |
| `nowidelut.default` | whether the assembler turns it on when the user says nothing. A **decision**, not a derived fact: Alan's ruling after the sweeps in `docs/measurements/nowidelut_sweeps_950/` (LUT4 smaller in every cell; the LUT multiplier ~3x smaller and ~3x faster; the nano / comparator / sequencer slower but ~225 MHz against a 27 MHz clock) |

How the assembler resolves it (`flexsub_assemble_v1.resolve_nowidelut`): `--nowidelut` forces it on (**refused** if the MAN says `supported: false`, because it would be silently ignored), `--wide-lut` opts out and writes the historical `synth_gowin` line, and with neither the MAN's `default` decides (with no MAN, or an older MAN with no `synthesis` block, the Gowin generators default to on, since `synth_gowin` has the option). **The Arria 10 says `supported: false, default: false`**: `synth_intel_alm` has no equivalent. The choice and its reason are recorded in each `ASSEMBLY.json` (`synth_flags`, `synth_flags_reason`). The LUT multiplier's budget cost is flow-aware (4,277 LUT4 default flow, <= 1,398 under `-nowidelut`).
