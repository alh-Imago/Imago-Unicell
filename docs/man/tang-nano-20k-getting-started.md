# Tang Nano 20K -- getting started (points.md #892/#896)

This is the first real, flashable UniCell deliverable for the Sipeed Tang Nano 20K, and it has now been
**confirmed working on the physical board** (`#894`/`#895`/`#896`) -- not just simulated and synthesized.

Per `points.md #890`/`#891`: this board is a **testbed and proof-of-concept**, not a capable accelerator
(a single VIX carrier position alone is 80%+ of its chip, `#887`; the fold loop overflows it 6.8x, `#886`).
This smoke test is scoped accordingly: one real, cheap UniCell core, genuinely doing something, on real
hardware -- not an attempt to fit the full architecture onto this chip.

## Use v2, not v1

`unicell_tang_nano_20k_smoke_v1.v` (`#892`) used the reset button (`BTN_RST_N`) and **stayed permanently
reset on the real board** despite passing simulation, real synthesis, and real place-and-route timing
closure. A pull-up fix (`#893`) and holding the button down both made no difference. Real, physical
bisection testing (`#894`/`#895`) proved the actual sequencer core, config-loading, and handshake logic all
genuinely work on real silicon -- the fault was specifically `BTN_RST_N`, not the RTL. **`v2` (`#896`)
removes the reset button entirely** and uses a pure power-on reset instead, and has been confirmed working
on the physical board: real 2-bit binary counting on the LEDs, exactly as designed. Build and flash `v2`.

**Root cause of the `BTN_RST_N` failure is still an open, honest question** -- possibly related to that pin
also being the chip's boot-mode-select pin (`MODE0`), possibly something else on the board's own circuit.
Worth investigating later; not required to have a working demo tonight.

## What it does

One real `sequencer_shell_v1c` core (`#889`'s measured cost: ~80 LUT4 standalone, Fmax well above 400 MHz
in isolation) is loaded with a deliberate, fixed configuration -- **not** a random sample, unlike the
`#889` sizing sweep's LFSR-driven stimulus -- and left running. Its own real internal state machine
(`seq_index`, a genuine 2-bit register inside `sequencer_cell_v4c.v`) advances through all 4 of its states
in a loop, gated by its own real downstream-offer/acknowledge handshake (the same handshake shape every
data-carrying UniCell core uses) rather than by anything external.

**What you'll see on the board:**
- **LED0** blinks at roughly 1.6 Hz (a plain heartbeat -- proves the design is genuinely clocking).
- **LED1** and **LED2** together display the sequencer's real 2-bit state as a binary count: `00 -> 01 ->
  10 -> 11 -> 00 -> ...`, advancing roughly once per second.
- **LED3** blinks briefly each time a real advance happens -- one flash per state transition.

This is a genuinely running UniCell core, not a static pattern: the counting sequence you'll see on LEDs 1-2
is the sequencer's own real register value, not something wired directly from a clock divider.

## Build it yourself (reproducible from source)

```
pip install yowasp-nextpnr-himbaechel-gowin apycula   # once, if not already installed
tools/gowin_sizing/build_smoke_bitstream.sh            # writes to fpga/build/ by default (builds v2)
```

This runs the real toolchain -- `yosys` synthesis, `yowasp-nextpnr-himbaechel-gowin` place-and-route against
the real `GW2AR-LV18QN88C8/I7` part, `gowin_pack` bitstream packing -- and prints the real achieved Fmax
before declaring success. The build is seeded (`--seed 1`) for reproducibility.

**Real, measured result (v2):** Fmax 177.0 MHz against a 27 MHz target (6.6x margin), 619 LUT4 / 20,736
(3.0% of the chip), 99 DFF, 5 of 384 I/O pins used. Full report:
`fpga/build/unicell_tang_nano_20k_smoke_v2_report.json`.

## Flash it

```
openFPGALoader -b tangnano20k fpga/build/unicell_tang_nano_20k_smoke_v2.fs
```

This writes to SRAM (lost on power-cycle) by default. Add `-f` (or your `openFPGALoader` version's flash
flag) to write it to the on-board configuration flash so it survives a power cycle -- **this overwrites the
board's current bitstream**, which is the one thing `docs/man/tang-nano-20k.man.json` already flags as
unverified against the schematic, so start with the SRAM (non-persistent) write first.

## What's verified and what isn't

**Verified, real, not assumed, as of `#896`:**
- The RTL genuinely works: simulated with `iverilog` before every synthesis attempt, every time.
- Real synthesis, real place-and-route, real Fmax against the actual chip database for this exact part.
- **Confirmed on the physical board**: the sequencer core arms, loads its real config, and its handshake
  logic genuinely runs -- proven by direct LED observation (`#894`/`#895`), not just simulation.
- Every pin used here (4, 15-18) is checked against the chip database's own QFN88 pinout table
  (`docs/man/tang-nano-20k.man.json`, `#887`).

**NOT yet verified -- the honest gaps that remain:**
- WHY `BTN_RST_N` failed on real hardware. `v2` works around this rather than explains it.
- The schematic has not been checked for pins 73-77 (the proposed ESP32 link, `#887`/`#888`) -- irrelevant to
  *this* smoke test (which now uses only pins 4/15-18) but still an open item for anything beyond it.

## Files

- `fpga/verilog/unicell_tang_nano_20k_smoke_v2.v` -- the real RTL, use this one (v1 kept for the record)
- `fpga/verilog/tb_unicell_tang_nano_20k_smoke_v2.v` -- the real testbench
- `fpga/verilog/unicell_tang_nano_20k_diag_v1.v` / `diag2_v1.v` -- the real-hardware bisection diagnostics
  that found and isolated the `BTN_RST_N` issue (`#894`/`#895`)
- `tools/gowin_sizing/build_smoke_bitstream.sh` -- the reproducible build script (builds v2)
- `fpga/build/unicell_tang_nano_20k_smoke_v2.{fs,cst}` -- the real, committed, confirmed-working bitstream
- `fpga/build/unicell_tang_nano_20k_smoke_v2_report.json` -- the real nextpnr timing/utilization report

