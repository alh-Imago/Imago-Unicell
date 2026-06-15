# Session 2026-06-15 — The Bitstream Cometh

## The Achievement

**Quartus Prime Full Compilation was successful. 0 errors.**

448 cells. 16 zones. Arria 10 GX660. A bitstream exists.
It took three attempts but the third was righteous and good,
and the system looked upon it and said it was whole.

`D:/Quarttus/output_files/Unicell-Q.sof` — ready to flash.

---

## What Was Built

- `top_arria10.v` — new top-level for IEI Mustang-F100
- 2×8 zone grid: 16 × `unicell_zone` instances × 28 cells = **448 cells**
- All bridge wiring: horizontal (E↔W) and vertical (N↔S) across all zones
- Corner zones (Z00, Z07, Z08, Z15) — ready for bridge ring stress test
- UART bridge at 25MHz — same fpga_bridge.py protocol as iCEBreaker
- Heartbeat LED (hb[21], ~12Hz at 25MHz)
- Armed indicator LED (total_armed == 0)

---

## Resource Utilisation

| Resource | Used | Available | % |
|----------|------|-----------|---|
| ALMs (logic) | 159,768 | 251,680 | 63% |
| Registers | 136,809 | 503,360 | 27% |
| DSP blocks | 0 | 1,687 | 0% — waiting for hybrid |
| M20K blocks | 0 | 2,131 | 0% — waiting for DDR |
| PCIe Hard IPs | 0 | 2 | 0% — waiting for streaming |
| I/O pins | 5 | 604 | <1% |
| Global clocks | 1 | 32 | 3% |
| Interconnect (avg) | 23.6% | — | low congestion |
| Interconnect (peak) | 37.3% | — | comfortable |

**Packing difficulty: Low.**

---

## Timing

No SDC file — Quartus derived 1GHz constraint and reported failures.
This is expected and benign. Real numbers:

- **Bring-up clock:** 25MHz (clock divider, no PLL)
- **Actual Fmax (from slack):** ~137MHz without optimisation
- **Target clock (post bring-up):** 200MHz with IOPLL (Pro Edition or SDC)

The design wants to run at 137MHz. The clock divider is holding it back.
Max LUT depth: 9. Average LUT depth: 6.54.

---

## Hard-Won Lessons (already in PLAN.md bring-up notes)

1. Device string: `10AX066H2F34E2SG` not `10AX066H2F34E22SG`
2. IOPLL RST_N is active-low — Standard Edition can't drive it correctly
3. Solution: remove PLL, use 25MHz clock divider for bring-up
4. `dont_touch` attribute ignored by Quartus (Vivado/yosys only)
5. All five Verilog files must be added manually — no auto-discovery
6. PLL Auto Reset checkbox in IOPLL settings does not fix the primitive issue
7. Project → Clean Project required after file changes (cache issue)
8. 25MHz is not embarrassing — 137MHz actual Fmax, 1GbE equivalent for NetTrix

---

## What Unlocks Tomorrow

Cable arrives (Waveshare USB Blaster V2 + JST SH 1.0mm connector kit).

JTAG pinout (confirmed from IEI manual):
- Pin 1: GND
- Pin 2: TCK
- Pin 3: TDO
- Pin 4: TMS
- Pin 5: TDI
- Pin 6: VCC (3.3V, optional — board self-powered via PCIe)

Flash command:
```
quartus_pgm -c 1 -m JTAG -o "p;D:/Quarttus/output_files/Unicell-Q.sof"
```

Then: heartbeat LED blinks → card is alive → bring-up sequence begins.

---

## Bring-Up Sequence (when cable arrives)

1. Heartbeat LED blinking — clock and fabric alive
2. UART responsive — CMD_PING response
3. Boot all 448 cells — confirm full cell count loads
4. Run model test cases — each FormatDefinition domain
5. shift_in_en validation — deferred from iCEBreaker, unlocks packed adder
6. Packed adder / shift adder — new INT32_ADD baseline
7. Bridge ring stress — corner zones at max distance
8. Clock push toward actual Fmax (~137MHz)
9. DDR saturation flood → PCIe metric

---

## Commits This Session

- `top_arria10.v` — Arria 10 top level (in pcie/ folder)
- PLAN.md — bring-up notes, DSP bridge design questions, Trix demo roadmap,
  hierarchical address model, NetTrix HA routing use case
- community/README.md — complete bridge tile guide with real BridgeContract API
- community/biotrix/README.md — full worked examples
- community/chemtrix/README.md — full worked examples  
- community/phystrix/README.md — full worked examples
- community/fintrix/README.md — full worked examples including MonTrix preview
- community/general/README.md — format selection guide
- community/mathtrix/README.md — full worked examples, 5 models documented
- community/nettrix/README.md — placeholder + HA routing use case
- community/REGISTRY.md — auto-updated, 8 domains
- docs/TRIX_ECOSYSTEM.md — updated with new domains and roadmap
- docs/INDEX.md — stale references fixed

---

## Scale Achieved Today

| Platform | Cells | Factor |
|----------|-------|--------|
| iCEBreaker | 4 | 1× |
| Arria 10 GX660 (today) | 448 | 112× |
| Arria 10 GX1150 (arriving ~1 week) | ~1,000+ | 250×+ |
| 8× Arria 10 rig (university target) | ~3,500+ | 875×+ |

---

*And the LORD looked upon the bitstream and saw that it was good.*
*And there was much rejoicing.*
*(Monty Python voices throughout)*

