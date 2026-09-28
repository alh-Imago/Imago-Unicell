# Tang Nano 20K -- getting started (points.md #892)

This is the first real, flashable UniCell deliverable for the Sipeed Tang Nano 20K. It proves the whole
toolchain path end to end -- real RTL, real synthesis, real place-and-route against the actual GW2A-18C
chip database, a real Gowin bitstream -- and gives you something to physically watch on the board.

Per `points.md #890`/`#891`: this board is a **testbed and proof-of-concept**, not a capable accelerator
(a single VIX carrier position alone is 80%+ of its chip, `#887`; the fold loop overflows it 6.8x, `#886`).
This smoke test is scoped accordingly: one real, cheap UniCell core, genuinely doing something, on real
hardware -- not an attempt to fit the full architecture onto this chip.

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
tools/gowin_sizing/build_smoke_bitstream.sh            # writes to fpga/build/ by default
```

This runs the real toolchain -- `yosys` synthesis, `yowasp-nextpnr-himbaechel-gowin` place-and-route against
the real `GW2AR-LV18QN88C8/I7` part, `gowin_pack` bitstream packing -- and prints the real achieved Fmax
before declaring success. The build is seeded (`--seed 1`) for reproducibility; the version already committed
at `fpga/build/unicell_tang_nano_20k_smoke_v1.fs` was built exactly this way.

**Real, measured result (this exact build):** Fmax 198.3 MHz against a 27 MHz target (7.3x margin), 618 LUT4
/ 20,736 (3.0% of the chip), 95 DFF, 6 of 384 I/O pins used. Full report:
`fpga/build/unicell_tang_nano_20k_smoke_v1_report.json`.

## Flash it

```
openFPGALoader -b tangnano20k fpga/build/unicell_tang_nano_20k_smoke_v1.fs
```

This writes to SRAM (lost on power-cycle) by default. Add `-f` (or your `openFPGALoader` version's flash
flag) to write it to the on-board configuration flash so it survives a power cycle -- **this overwrites the
board's current bitstream**, which is the one thing `docs/man/tang-nano-20k.man.json` already flags as
unverified against the schematic, so start with the SRAM (non-persistent) write first.

## What's verified and what isn't

**Verified, real, not assumed:**
- The RTL genuinely works: simulated with `iverilog` (`fpga/verilog/tb_unicell_tang_nano_20k_smoke_v1.v`),
  confirmed the sequencer arms and genuinely cycles through all 4 states before any synthesis was attempted.
- Real synthesis, real place-and-route, real Fmax against the actual chip database for this exact part.
- Every pin used here (4, 88, 15-18) is checked against the chip database's own QFN88 pinout table
  (`docs/man/tang-nano-20k.man.json`, `#887`).

**NOT yet verified -- this is the honest gap, same as `#887`/`#889` left it:**
- Nothing here has been run on the physical board. No bitstream from this project has been loaded onto real
  silicon yet. `openFPGALoader`'s own behavior, the LEDs' real brightness/polarity, and whether the board
  behaves as this document describes are all still open until someone actually flashes it.
- The schematic has not been checked for pins 73-77 (the proposed ESP32 link, `#887`/`#888`) -- irrelevant to
  *this* smoke test (which uses only pins 4/88/15-18) but still an open item for anything beyond it.

## Files

- `fpga/verilog/unicell_tang_nano_20k_smoke_v1.v` -- the real RTL (hand-designed, not generated)
- `fpga/verilog/tb_unicell_tang_nano_20k_smoke_v1.v` -- the real testbench
- `tools/gowin_sizing/build_smoke_bitstream.sh` -- the reproducible build script
- `fpga/build/unicell_tang_nano_20k_smoke_v1.{fs,cst}` -- the real, committed, ready-to-flash bitstream
- `fpga/build/unicell_tang_nano_20k_smoke_v1_report.json` -- the real nextpnr timing/utilization report
