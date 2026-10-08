#!/usr/bin/env python3
"""
gen_tang_nano_20k_man.py -- points.md #887: generate docs/man/tang-nano-20k.man.json and
docs/man/tang-nano-20k.cst for the Sipeed Tang Nano 20K, from ONE source of truth.

Two kinds of fact go in, and the file says which is which:
  * CHIP facts (resource counts, block-RAM / DSP / PLL positions, package pin locations, I/O banks, the
    embedded-SDRAM port list) are READ from the Apicula GW2A-18C chip database -- the same database the open
    place-and-route flow uses. They are reproducible: run this script again.
  * BOARD facts (which package pin the crystal, LEDs, buttons, flash, SD card and UART are wired to) come from
    published working designs and the Sipeed wiki, listed in `provenance`. Every pin number was then CHECKED
    against the chip database (it must exist in the QFN88 table); that proves the pin is real, not that the
    board is wired that way. NOTHING here has been checked against the schematic or on the physical board.

Needs:  pip install apycula msgpack
Usage:  python3 tools/man_gen/gen_tang_nano_20k_man.py            # writes both files
        python3 tools/man_gen/gen_tang_nano_20k_man.py --check    # exit 1 if the committed files are stale
"""
import argparse
import importlib.metadata
import json
import lzma
import os
import re
import sys

import apycula
import msgpack

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_MAN = os.path.join(ROOT, "docs", "man", "tang-nano-20k.man.json")
OUT_CST = os.path.join(ROOT, "docs", "man", "tang-nano-20k.cst")

DEVICE_KEY, PACKAGE_KEY = "GW2AR-18C", "QFN88"      # Apicula's names for GW2AR-LV18QN88C8/I7


def load_chipdb():
    path = os.path.join(os.path.dirname(apycula.__file__), "GW2A-18C.msgpack.xz")
    return msgpack.unpackb(lzma.open(path).read(), raw=False, strict_map_key=False, use_list=False)


def tiles_of(db, letter):
    ttyps = set(db["tile_types"][letter])
    return sorted((y, x) for y, row in enumerate(db["grid"]) for x, t in enumerate(row) if t in ttyps)


def columns(positions):
    """[(y,x),...] -> [{"x":..., "y_segments":[[y,y],...]}] -- discrete rows expressed as one-row segments, which
    card_fit_v1._rows_of already understands."""
    by_x = {}
    for y, x in positions:
        by_x.setdefault(x, []).append(y)
    return [{"x": x, "y_segments": [[y, y] for y in sorted(ys)]} for x, ys in sorted(by_x.items())]


def pin_record(db, pin, extra=None):
    loc, funcs = db["pinout"][DEVICE_KEY][PACKAGE_KEY][str(pin)]
    rec = {"pin": pin, "package_location": loc, "bank": db["pin_bank"][loc], "io_standard": "LVCMOS33"}
    if funcs:
        rec["chip_function"] = "/".join(funcs)
    rec.update(extra or {})
    return rec


def dsp_primitives(blocks_total, multipliers_18x18):
    """The card's DSP primitives, as the assembler needs them. Operand and product widths are read LIVE from yosys's own declaration of the Gowin
    multipliers (gowin/cells_xtra.v), not hand-typed. How they share the blocks is plain arithmetic and is marked DERIVED: a block holds
    multipliers_18x18 / blocks_total 18x18 multipliers (48 / 12 = 4), and a 36x36 needs (36/18)^2 = 4 of them, i.e. a whole block -- so
    blocks_per_instance is 1 for MULT36X36 and 1/4 for MULT18X18, and the two draw on the SAME blocks."""
    path = "/usr/share/yosys/gowin/cells_xtra.v"
    text = open(path).read()
    per_block = multipliers_18x18 // blocks_total
    out = []
    for name in ("MULT18X18", "MULT36X36"):
        m = re.search(rf"module {name} \(\.\.\.\);(.*?)endmodule", text, re.S)
        if not m:
            raise RuntimeError(f"{name} is not declared in {path}")
        body = m.group(1)
        a_bits = int(re.search(r"input\s+\[(\d+):0\]\s+A\b", body).group(1)) + 1
        d_bits = int(re.search(r"output\s+\[(\d+):0\]\s+DOUT", body).group(1)) + 1
        uses_18 = (a_bits // 18) ** 2
        out.append({"name": name, "operands": [a_bits, a_bits], "product_bits": d_bits,
                    "blocks_per_instance": uses_18 / per_block,
                    "blocks_per_instance_provenance": (f"DERIVED, not read from a datasheet: {name} needs ({a_bits}/18)^2 = {uses_18} of a block's "
                                                       f"{per_block} 18x18 multipliers"),
                    "operands_provenance": f"read live from {path} (yosys's own Gowin cell library)"})
    return out


def synthesis_block():
    """The card's open-toolchain synthesis facts. WHETHER the option exists is read LIVE from the installed yosys (`yosys -h synth_gowin` must list -nowidelut), not
    hand-typed. `default: true` is a DECISION (Alan, after ledger #950), not a derived fact -- the evidence is the sweeps in docs/measurements/nowidelut_sweeps_950/:
    LUT4 smaller in every cell measured (14,793 -> 5,129 in real place-and-route), the LUT multiplier ~3x smaller AND ~3x faster, the nano/comparator/sequencer slower
    but still ~225 MHz against this card's 27 MHz clock."""
    import subprocess
    out = subprocess.run(["yosys", "-h", "synth_gowin"], capture_output=True, text=True).stdout
    return {"tool": "yosys synth_gowin (open flow) -> nextpnr-himbaechel-gowin",
            "nowidelut": {"supported": "-nowidelut" in out, "supported_provenance": "read live from `yosys -h synth_gowin`",
                          "default": True, "default_provenance": "DECISION (Alan, after ledger #950), evidence in docs/measurements/nowidelut_sweeps_950/",
                          "effect": "stops the mapper building wide-LUT (MUX2_LUT5..8) mux trees: smaller in every cell measured; the LUT multiplier also ~3x faster; the nano, comparator "
                                    "and sequencer lose clock speed (still ~225 MHz vs this card's 27 MHz). Opt out with --wide-lut."}}


def native_ff_variants():
    """points.md #907: read the real Gowin flip-flop primitives straight from
    yosys's own cell library (not hand-typed, so this can never silently drift
    from what the toolchain actually knows) and derive each one's real native
    control input beyond clock+data -- CE (clock-enable), or an initialisation
    pin (synchronous SET/RESET, asynchronous PRESET/CLEAR). Real, checked
    finding: #906's `adder_cell_v4sa` measured 37 LUT4 against the no-ack
    version's 66, and this table is why -- DFFRE's native CE pin gives
    "hold the value unless genuinely capturing" for free, no LUT required.
    One real limit, worth recording precisely: each primitive offers only ONE
    native control input beyond clock/data -- CE alone, an init pin alone, or
    CE plus exactly one init pin. Anything needing two independent async
    conditions on the same register still needs real LUT logic for the second
    one.
    """
    path = "/usr/share/yosys/gowin/cells_sim.v"
    if not os.path.exists(path):
        return None
    text = open(path).read()
    variants = []
    for m in re.finditer(r"^module (DFF\w*) \(output reg Q, input ([^)]+)\);", text, re.MULTILINE):
        name, ports = m.group(1), [p.strip() for p in m.group(2).split(",")]
        edge = "negedge" if name.startswith("DFFN") else "posedge"
        ce = "CE" in ports
        init = next((p for p in ("SET", "RESET", "PRESET", "CLEAR") if p in ports), None)
        variants.append({"name": name, "clock_edge": edge, "native_ce": ce, "native_init_pin": init})
    return {
        "source": f"read live from {path} (yosys's own Gowin cell library), not hand-typed",
        "variants": variants,
        "note": ("Every real Gowin DFF primitive gives exactly ONE free native control input beyond "
                 "clock+data: a clock-enable (CE, for hold-current-value-for-free logic) or an "
                 "initialisation pin (SET/RESET=synchronous, PRESET/CLEAR=asynchronous); DFFRE/DFFSE/"
                 "DFFPE/DFFCE combine CE with one init pin. A register needing TWO independent async "
                 "conditions still needs real LUT logic for the second one -- only one native extra "
                 "input exists per flip-flop, not two. Real, confirmed use: #906's adder_cell_v4sa "
                 "measured 37 LUT4 against the plain adder_cell_v4s's 66, specifically because its "
                 "\"hold unless capturing\" logic maps onto DFFRE's own native CE pin rather than "
                 "needing extra LUT-level muxing. Worth designing v4s/v4sa RTL deliberately around this "
                 "table rather than relying on the synthesiser to find the mapping by chance."),
    }


def cell_costs_block():
    """The measured LUT4/ALU/DFF/MULT of every flex (v4sa) cell at several widths (ledger #975), read from the committed sweep results so the numbers have one source."""
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "measurements", "flex_width_sweep_975", "costs.json")
    d = json.load(open(src))
    return {
        "unit": "[LUT4, ALU, DFF, MULT] as counted by yosys synth_gowin (open flow); the device totals are device.logic.lut4_total / ff_total",
        "source": "docs/measurements/flex_width_sweep_975/costs.json, produced by tools/flex_width_sweep_v1.py (ledger #975, #976). MEASURED by synthesis only: no place-and-route, no timing, nothing run on the board.",
        "widths_measured": d["widths"],
        "flow": "single_nowidelut is the card's default flow (synthesis.nowidelut.default); single_widelut is the historical flow, whose numbers are NOT smooth in W (the wide-LUT mapper changes its mind) -- project from nowidelut.",
        "how_to_read": ("single_*: the cell module alone with every configuration port a real input -- the honest per-cell cost of a runtime-configurable cell. array3x3_nowidelut: nine cells inside the generated assembler "
                        "top with the configuration pinned by the harness, so constant-config logic folds away -- it shows what a hard-wired cluster costs, and is NOT a per-cell figure (adder: 9 cells cost less than 2 singles)."),
        "second_port": "adder / mul / mul_dsp: single_nowidelut_port2 is the cell built WITH its second output port (SECOND_PORT=1, set from the compiler's ICM flag: adder carry_mode, mul wide_mode); single_nowidelut is without it (the default). The multiplier's port needs the full 2W-bit product, so it costs about as much again.",
        "fits": d["fits"],
        "fits_note": "lut4_vs_W_nowidelut is a least-squares polynomial of the single-cell nowidelut LUT4 count against the width (degree 1, mul degree 2); max_abs_residual says how well it holds over the measured widths. The sequencer is not a function of W (it saturates at 8 bits) and is refused below 8 bits on FlexGrid.",
        "cells": d["cells"],
    }


def build(db):
    logic_tiles = tiles_of(db, "M")
    bsram, dsp, pll = tiles_of(db, "B"), tiles_of(db, "D"), tiles_of(db, "P")
    sdram = db["sip_cst"][DEVICE_KEY][PACKAGE_KEY]
    pins = lambda *a, **k: pin_record(db, *a, **k)      # noqa: E731
    apy = importlib.metadata.version("apycula")

    THIRD = ("calint/tang-nano-20k--riscv--cache-sdram tangnano20k.cst (a working RV32I design using the on-board "
             "SDRAM, flash and SD card)")
    ARTHUR = "ArthurHeymans/tang_20k_spi_flash README (open-flow SPI-slave design on the edge connector)"
    KIT = "https://docs.sunfounder.com/projects/esp32-starter-kit/en/latest/"
    WIKI = "Sipeed wiki, en.wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html"

    man = {
        "man_version": "1.1",
        "card_id": "sipeed-tang-nano-20k-01",
        "generated": "2026-09-28",
        "generated_by": ("GENERATED by tools/man_gen/gen_tang_nano_20k_man.py (Alan/Claude session). Chip facts read "
                         f"from the Apicula {apy} GW2A-18C chip database; board facts from the published sources in "
                         "`provenance`. NOT read from Gowin's FloorPlanner, NOT checked against the schematic, and "
                         "NOT tested on the physical board -- see `verification`."),
        "vendor": "gowin",
        "synthesis": synthesis_block(),
        "cell_costs": cell_costs_block(),
        "device": {
            "part": "GW2AR-LV18QN88C8/I7",
            "family": "Gowin GW2AR-18",
            "package": "QFN88",
            "apicula": {"device": DEVICE_KEY, "family": "GW2A-18C", "version": apy, "package": PACKAGE_KEY},
            "toolchain_open_flow": "yosys synth_gowin -> nextpnr-himbaechel -> gowin_pack -> openFPGALoader",
            "jtag_idcode": None,
            "alm_total": None,
            "logic": {
                "unit": "LUT4",
                "lut4_total": len(logic_tiles) * 32,
                "ff_total": len(logic_tiles) * 24,
                "tiles": len(logic_tiles), "lut4_per_tile": 32, "ff_per_tile": 24, "ff_per_lut4": 0.75,
                "shadow_sram_bits": 41472,
                "note": ("Derived from the chip database: 648 logic tiles x 32 LUT4 = 20,736 and x 24 FF = 15,552, "
                         "matching the published datasheet figures. A LUT4 is NOT an Intel ALM: card_fit_v1 keeps "
                         "the two units apart."),
                "native_ff_variants": native_ff_variants(),
                "native_width": 18,
                "native_width_note": ("Native data width for the Flex-Sub (v4sa) cell family on this card: 18. Gowin's "
                                      "own BRAM inference table (yosys gowin/brams.txt) lists native widths 1, 2, 4, 9, "
                                      "18, 36 -- and the DSP primitive is MULT18X18, so both fundamental blocks share "
                                      "18 (points.md #903/#904). The assembler's --family flex reads this as WIDTH "
                                      "(points.md #914); a MAN without it falls back to 32."),
            },
            "bram": {
                "kind": "BSRAM", "blocks": len(bsram), "kbits_datasheet": 828,
                "columns": columns(bsram),
                "note": ("46 block-RAM tiles in the chip database, matching the datasheet's 46 B-SRAMs. Positions "
                         "are Apicula die tile coordinates (x = column, y = row), the analogue of the Arria MAN's "
                         "Chip Planner coordinates. The key name is `bram`, not Intel's `m20k`."),
            },
            "dsp": {
                "total_blocks": len(dsp), "multipliers_18x18": 48, "multipliers_per_block_derived": 48 // len(dsp),
                "columns": columns(dsp),
                "primitives": dsp_primitives(len(dsp), 48),
                "primitives_share_blocks": True,
                "abilities": [],
                "abilities_note": ("An OPEN list of card-specific DSP abilities, each {name, note}, that an assembler cell may ask for by name. None is "
                                   "recorded for this card. (Not to be confused with columns[].y_segments, which are ROW coordinates of the DSP "
                                   "tiles in the chip database, not operand sizes.)"),
                "note": ("12 DSP tiles in the chip database; the 48 18x18 multipliers is the published figure "
                         "(48 / 12 = 4 per tile is DERIVED, not read). Unlike the Arria, these blocks do NOT chain "
                         "along a spine clock region as far as this file knows -- unverified."),
            },
            "pll": {
                "total_on_board": 2,
                "tiles_in_die": [{"x": x, "y": y, "side": "left" if x < len(db["grid"][0]) // 2 else "right"}
                                 for y, x in pll],
                "note": ("Datasheet: 2 PLLs. The chip database has PLL tiles at x=0 (rows 9, 45) and x=55 "
                         "(rows 9, 45); the QFN88 pin table only exposes the LEFT PLLs' inputs (LPLL1_T_IN on "
                         "pin 4, LPLL2_T_IN on pin 13), consistent with 2 usable PLLs. Right-hand PLL "
                         "availability is unverified."),
            },
            "io": {"banks": 8, "package_io_pins": len(db["pinout"][DEVICE_KEY][PACKAGE_KEY]),
                   "board_io_voltage": "3.3 V (LVCMOS33) on every pin the reference designs use"},
            "die_grid": {"rows": len(db["grid"]), "cols": len(db["grid"][0]),
                         "note": "Apicula tile grid; (row, col) = (y, x)"},
            "embedded_memory": {
                "sdram": {
                    "bits": 64 * 1024 * 1024, "megabytes": 8, "data_width": 32, "type": "SDR SDRAM",
                    "banks": 4, "row_address_bits": 11, "column_address_bits_derived": 8,
                    "geometry_note": ("4 banks x 2048 rows x 256 columns x 32 bit = 64 Mbit. Bank count and row "
                                      "bits are READ from the port list below (2 BA, 11 A); the 8 column bits are "
                                      "DERIVED from the capacity and are not read from any source."),
                    "in_package": True, "board_pins": None,
                    "ports": [{"name": n, "die_row": r, "die_col": c, "half": h, "io_standard": std}
                              for (n, r, c, h, std) in sdram],
                    "port_count": len(sdram),
                    "clocking": ("A working open-flow design ran this SDRAM from a 27 MHz -> ~132 MHz PLL "
                                 "(ArthurHeymans/tang_20k_spi_flash); its own timing report passed at 167 MHz for "
                                 "the main clock. Those are that design's figures, not a device limit."),
                    "source": ("port names and die locations READ from the Apicula chip database `sip_cst` table "
                               "for GW2AR-18C/QFN88; capacity and 32-bit width from the Sipeed/retailer "
                               "specifications and the open-flow design above"),
                },
                "user_flash_kbits_claimed": 608,
                "user_flash_note": "608 Kbit on-chip user flash appears only in retailer listings; unverified.",
            },
            "source": ("Apicula GW2A-18C chip database (read by tools/man_gen/gen_tang_nano_20k_man.py); resource "
                       "counts cross-checked against the published datasheet figures"),
        },
        "board": {
            "name": "Sipeed Tang Nano 20K",
            "size_mm": [22.55, 54.04],
            "clock": {
                "CLK_27M": pins(4, {"freq_hz": 27000000, "period_ns": 37.037,
                                    "net": "PIN04_SYS_CLK", "role": "on-board 27 MHz crystal",
                                    "evidence": [THIRD, "olofk/serv PR #147 (create_clock -period 37.04)"]}),
                "note": ("Pin 4 is a dedicated PLL input (chip function LPLL1_T_IN). The reference constraint file "
                         "notes Gowin warning PR1014 when a design uses it directly as a clock."),
                "ms5351": {
                    "CLK0": pins(10, {"net": "PIN10_5351CKP", "default_freq_hz": 27000000}),
                    "CLK1": pins(11, {"net": "PIN11_5351CKN", "default_freq_hz": 27000000}),
                    "CLK2": pins(13, {"net": "PIN13_HSPI_SCLK", "default_freq_hz": 27000000}),
                    "note": ("The MS5351 generates 3 extra clocks and is configured by the BL616. Pins 10/11 are a "
                             "global-clock differential pair. The reference file notes an rPLL 'lock' signal may "
                             "not assert when clocked from some of these pins (its wording; unverified here)."),
                    "evidence": [THIRD, WIKI],
                },
            },
            "buttons": {
                "S1": pins(88, {"net": "PIN88_MODE0_KEY1", "evidence": [THIRD, ARTHUR]}),
                "S2": pins(87, {"net": "PIN87_MODE1_KEY2", "evidence": [THIRD, ARTHUR]}),
                "note": ("Both are the chip's MODE0/MODE1 configuration pins (dual-purpose): using them as user "
                         "inputs needs them released as regular I/O in the toolchain. Idle level is not stated by "
                         "any source read."),
            },
            "leds": {
                "LED0_N": 15, "LED1_N": 16, "LED2_N": 17, "LED3_N": 18, "LED4_N": 19, "LED5_N": 20,
                "active": "low",
                "pins": {f"LED{i}_N": pins(15 + i, {"net": f"PIN{15 + i}_SYS_LED{i}"}) for i in range(6)},
                "note": ("Six user LEDs, active low (Sipeed wiki: low-level enable). LED0 and LED1 (pins 15/16) "
                         "share pins with PLL2's feedback (LPLL2_T_FB / LPLL2_C_FB): do not use external PLL2 "
                         "feedback and those LEDs together. A separate WS2812 RGB LED exists; its pin is NOT mapped."),
                "evidence": [THIRD, ARTHUR, WIKI],
            },
            "uart": {
                "tx": pins(69, {"net": "PIN69_SYS_TX", "direction": "FPGA transmit -> host"}),
                "rx": pins(70, {"net": "PIN70_SYS_RX", "direction": "host -> FPGA receive"}),
                "bridge": "on-board BL616 USB-to-serial (appears as a serial port over the USB-C cable)",
                "max_baud_seen": 3000000,
                "note": ("3 Mbaud was used by a working design; a serv PR notes the on-board UART 'does not work "
                         "well' under a large output volume and suggests an external FTDI. This UART reaches the "
                         "PC over USB; it is NOT a link to the ESP32."),
                "evidence": [THIRD, ARTHUR, "olofk/serv PR #147"],
            },
            "spi_flash": {
                "capacity_mbit": 64, "part_marking_read_from_photo": "XT25F64F (partly legible)",
                "role": "holds the configuration bitstream",
                "clk": pins(59, {"net": "MSPI_CLK"}), "cs_n": pins(60, {"net": "MSPI_CS"}),
                "mosi": pins(61, {"net": "MSPI_DI"}), "miso": pins(62, {"net": "MSPI_DO"}),
                "note": ("These are the FPGA's dedicated MSPI configuration pins (chip functions MCLK / MCS_N / "
                         "MO / MI, shared with configuration data lines D4-D7). Reading or writing the flash from "
                         "fabric needs them released as regular I/O. Erasing it removes the bitstream that boots "
                         "the board."),
                "evidence": [THIRD, WIKI],
            },
            "sd_card": {
                "slot": "microSD (TF), 4-bit SDIO",
                "clk": pins(83, {"net": "PIN83_SDIO_CLK"}), "cmd": pins(82, {"net": "PIN82_SDIO_CMD"}),
                "dat0": pins(84, {"net": "PIN84_SDIO_D0"}), "dat1": pins(85, {"net": "PIN85_SDIO_D1"}),
                "dat2": pins(80, {"net": "PIN80_SDIO_D2"}), "dat3": pins(81, {"net": "PIN81_SDIO_D3"}),
                "note": ("The slot sits on the underside of the board (not visible in the top-side photo). The "
                         "reference file lists no pull-ups for these pins; SD cards need them, so check before "
                         "relying on card detection."),
                "evidence": [THIRD, WIKI],
            },
            "sdram": {"ref": "device.embedded_memory.sdram",
                      "note": ("The RAM interface is INSIDE the package: no board pins, no IO_LOC lines. The port "
                               "list and die locations are in the chip database and are applied by port name.")},
            "jtag": {
                "programmer": "on-board BL616",
                "roles": ["JTAG for the FPGA", "USB to UART for the FPGA", "USB to SPI for FPGA communication",
                          "configures the MS5351 clock generator"],
                "test_points": "unpopulated JTAG test points exist for an external debugger",
                "update_button": "UPDATE button puts the BL616 into firmware-update mode",
                "evidence": [WIKI],
            },
            "host_link": {
                "role": "coprocessor",
                "host": {
                    "device": ("ESP32-D (stated by the project owner, 2026-09-28); the kit documents its board as an "
                               "ESP32-WROOM-32E"),
                    "family": ("classic ESP32: dual-core Xtensa LX6, 2.4 GHz Wi-Fi and dual-mode Bluetooth, up to 38 "
                               "GPIO, module with a 3.3 V SPI flash (SunFounder kit documentation)"),
                    "kit": {
                        "name": "SunFounder ESP32 Ultimate Starter Kit with ESP32 Camera Extension board",
                        "docs": KIT,
                        "arduino_board_setting": "ESP32 Dev Module",
                        "extension_board": [
                            "micro SD slot, used through the ESP32's SDMMC host peripheral (the kit's SD_MMC example)",
                            "24-pin FFC connector for an OV2640 camera",
                            "14-pin screw terminal and female headers",
                        ],
                        "extension_pinout": ("the kit's pin tables are IMAGES and were NOT READ; instead the project owner sent three "
                                             "photographs of the board (2026-10-08) and the screw-terminal / header labels were READ from them: "
                                             "left block top to bottom I36 I39 I34 I35 IO32 IO33 IO25 IO26 IO27 IO14 IO12 IO13 GND 5V; right block "
                                             "IO23 IO22 TXD RXD IO21 IO19 IO18 IO5 IO4 IO0 IO2 IO15 GND 3V3. Which of these the camera connector or the SD slot "
                                             "also use is general knowledge of the common ESP32 camera board / SDMMC pinout, NOT read from this kit, "
                                             "and must be checked with a continuity test"),
                        "extension_terminals": {"left": ["I36", "I39", "I34", "I35", "IO32", "IO33", "IO25", "IO26", "IO27", "IO14", "IO12", "IO13", "GND", "5V"],
                                                "right": ["IO23", "IO22", "TXD", "RXD", "IO21", "IO19", "IO18", "IO5", "IO4", "IO0", "IO2", "IO15", "GND", "3V3"]},
                    },
                    "chip_inside_module_note": ("an ESP32-WROOM-32E module contains an ESP32-D0WD-V3; that is general "
                                                "knowledge of the module, NOT from the kit documentation, and has not "
                                                "been checked against the physical part"),
                    "strapping_pins": [0, 2, 5, 12, 15],
                    "strapping_note": ("kit documentation: IO12 (MTDI) pulled high at power-up stops the ESP32 booting "
                                       "normally, because the module has a 3.3 V flash; IO0 low enters download mode"),
                    "responsibilities": ["web front end", "WiFi / network connections", "feeding input data",
                                         "collecting results"],
                    "io_voltage": "3.3 V, matching this board's LVCMOS33 I/O (no level shifter expected)",
                },
                "planned_interface": "SPI, ESP32 = master, FPGA = slave",
                "esp32_side_pins": {
                    "SCLK": "IO18", "MOSI": "IO23", "MISO": "IO19", "CS_N": "IO5", "READY_IRQ": "IO34",
                    "GND": "GND (either terminal block): the two boards must share ground",
                },
                "esp32_side_pins_note": ("PROPOSED, not wired. These are the ESP32's default VSPI pins (IO18 / IO23 / IO19 / IO5 -- the dedicated "
                                         "route, so no GPIO-matrix clock limit), taken from the terminal labels read in the owner's photographs. The FPGA "
                                         "drives only MISO (IO19, not a strapping pin) and READY (IO34, an input-only pin, never a strapping pin); IO5 is "
                                         "a strapping pin but is driven by the ESP32 (CS_N) and only listened to by the FPGA. The SD slot's own pins "
                                         "(IO14 / IO15 / IO2 / IO4 / IO12 / IO13, general knowledge) are left alone. UNVERIFIED: whether a camera "
                                         "(if one is fitted) or anything else on the extension board also drives IO18 / IO19 / IO23 / IO5 / IO34; "
                                         "with no camera fitted these are expected to be free."),
                "reference_pins": {
                    "CS_N": pins(73, {"net": "edge connector"}),
                    "SCLK": pins(74, {"net": "edge connector"}),
                    "MOSI": pins(75, {"net": "edge connector"}),
                    "MISO": pins(76, {"net": "edge connector"}),
                    "READY_IRQ_candidate": pins(77, {
                        "net": "edge connector",
                        "note": ("used as a power-detect INPUT by the reference design; nothing forces that use, "
                                 "so it is only a candidate for a ready/interrupt line")}),
                    "spare_debug": pins(27, {"net": "edge connector"}),
                },
                "status": ("PROPOSED. The pin assignment is taken from a working third-party SPI-slave design on "
                           "this board's edge connector that reports handling SPI clocks up to 48 MHz "
                           f"({ARTHUR}). It has NOT been wired to an ESP32 by this project, and whether these "
                           "pins are shared with the FPC/LCD, HDMI or other board circuitry has NOT been checked "
                           "against the schematic."),
                "notes": [
                    "SCLK on pin 74 (IOT34B) is not clock-capable; pins 76 and 77 (GCLKC_1 / GCLKT_1) are. The "
                    "reference design met timing anyway; a cleaner design would move SCLK to 76 or 77.",
                    "The UART on pins 69/70 goes to the BL616 (a PC over USB), not to the ESP32.",
                    "The BL616's 'USB to SPI' is a separate PC-to-FPGA path.",
                    "HAZARD (derived): do not put an FPGA-driven line (MISO, ready/interrupt) on an ESP32 strapping "
                    "pin (IO0, IO2, IO5, IO12, IO15). How the FPGA's pins behave while it configures has NOT been "
                    "checked; a high on IO12 at reset would stop the ESP32 booting (kit documentation).",
                    "The ESP32's second SPI bus defaults to IO12/13/14/15, and the SD slot uses the SDMMC host, whose "
                    "fixed pins on this chip family are IO14/15/2/4/12/13 (general knowledge, NOT read from the kit's "
                    "images), so avoid that bus on this kit.",
                    "SPI on non-default ESP32 pins goes through the GPIO matrix, which limits the practical clock "
                    "(general knowledge, unverified here).",
                ],
            },
            "not_yet_mapped": [
                "HDMI (TMDS pins)", "40-pin RGB LCD / FPC connector", "WS2812 RGB LED", "MAX98357A audio amplifier",
                "the rest of the edge-connector header pins and any sharing between them and on-board circuits",
            ],
        },
        "capabilities": {
            "bram": True, "bram_integrated": False,
            "dsp": True, "dsp_integrated": False,
            "dsp_note": "48 18x18 multipliers; the project's `mul` cell does not use them (no DSP inferred, #886)",
            "sdram_embedded": True, "sdram_integrated": False,
            "spi_flash_onboard": True, "sd_card": True,
            "usb_jtag": True, "usb_uart": True,
            "hdmi": True, "rgb_lcd": True,
            "host_coprocessor_link": "planned", "host_coprocessor_link_integrated": False,
            "pcie_hardware": False, "pcie_integrated": False,
            "ddr4_onboard": False, "ddr4_integrated": False,
        },
        "verification": {
            "chip_database": ("every pin number below was checked to exist in the QFN88 package table; resource "
                              "counts and the SDRAM port list were read from the same database"),
            "third_party_designs": "pin roles agree between at least two independent working designs where noted",
            "official_docs": "chip, BL616, MS5351, LED polarity and storage facts from the Sipeed wiki",
            "schematic": "NOT CHECKED",
            "physical_board": "NOT TESTED -- no bitstream has been loaded on the board by this project yet",
        },
        "provenance": [
            "points.md #664: the Tang Nano 20K + ESP32 as the project's planned next hardware target",
            "points.md #886: cell and carrier sizing for this architecture (yosys synth_gowin)",
            f"Apicula {apy}: GW2A-18C chip database (resource counts, positions, QFN88 pinout, sip_cst)",
            WIKI, THIRD, ARTHUR,
            "olofk/serv PR #147 (github.com/olofk/serv/pull/147): Tang Nano 20K constraints incl. clock period",
            "the owner's photo (2026-09-28): board and chip markings",
            f"SunFounder ESP32 Starter Kit documentation ({KIT}): the host board and its extension board",
        ],
    }
    return man


def build_cst(man):
    b, d = man["board"], man["device"]
    L = []
    add = L.append
    add("// GENERATED by tools/man_gen/gen_tang_nano_20k_man.py from docs/man/tang-nano-20k.man.json -- do not edit.")
    add("// Pin numbers are QFN88 package pins, checked against the Apicula chip database; NOT checked against the")
    add("// schematic or on the board. Port names are suggestions: rename them to match your top-level.")
    add("")
    add("// --- clock: 27 MHz crystal (pin 4 is a dedicated PLL input) ---")
    c = b["clock"]["CLK_27M"]
    add(f'IO_LOC "clk" {c["pin"]};')
    add('IO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=NONE;')
    add("")
    add("// --- user buttons: chip MODE0/MODE1 configuration pins; release them as regular I/O in the tool ---")
    for n, port in (("S1", "btn_s1"), ("S2", "btn_s2")):
        add(f'IO_LOC "{port}" {b["buttons"][n]["pin"]};')
        add(f'IO_PORT "{port}" IO_TYPE=LVCMOS33;')
    add("")
    add("// --- LEDs: active low. LED0/LED1 share PLL2's feedback pins ---")
    for i in range(6):
        add(f'IO_LOC "led_n[{i}]" {b["leds"]["pins"][f"LED{i}_N"]["pin"]};')
        add(f'IO_PORT "led_n[{i}]" IO_TYPE=LVCMOS33 PULL_MODE=UP DRIVE=8;')
    add("")
    add("// --- UART via the on-board BL616 USB bridge (to the PC, not the ESP32) ---")
    add(f'IO_LOC "uart_tx" {b["uart"]["tx"]["pin"]};')
    add('IO_PORT "uart_tx" IO_TYPE=LVCMOS33 PULL_MODE=UP DRIVE=8;')
    add(f'IO_LOC "uart_rx" {b["uart"]["rx"]["pin"]};')
    add('IO_PORT "uart_rx" IO_TYPE=LVCMOS33 PULL_MODE=UP;')
    add("")
    add("// --- on-board SPI configuration flash: dedicated MSPI pins; release them as regular I/O to use ---")
    for k, port in (("clk", "flash_clk"), ("cs_n", "flash_cs_n"), ("mosi", "flash_mosi"), ("miso", "flash_miso")):
        add(f'IO_LOC "{port}" {b["spi_flash"][k]["pin"]};')
        add(f'IO_PORT "{port}" IO_TYPE=LVCMOS33 PULL_MODE=NONE;')
    add("")
    add("// --- microSD, 4-bit SDIO (no pull-ups listed by the reference; add PULL_MODE=UP as your design needs) ---")
    for k, port in (("clk", "sd_clk"), ("cmd", "sd_cmd"), ("dat0", "sd_dat[0]"), ("dat1", "sd_dat[1]"),
                    ("dat2", "sd_dat[2]"), ("dat3", "sd_dat[3]")):
        add(f'IO_LOC "{port}" {b["sd_card"][k]["pin"]};')
        add(f'IO_PORT "{port}" IO_TYPE=LVCMOS33;')
    add("")
    add("// --- PROPOSED ESP32 link (SPI slave on the edge connector). Unverified against the schematic. ---")
    hl = b["host_link"]["reference_pins"]
    for k, port in (("CS_N", "esp_cs_n"), ("SCLK", "esp_sclk"), ("MOSI", "esp_mosi"), ("MISO", "esp_miso"),
                    ("READY_IRQ_candidate", "esp_ready")):
        add(f'IO_LOC "{port}" {hl[k]["pin"]};')
        add(f'IO_PORT "{port}" IO_TYPE=LVCMOS33 PULL_MODE=NONE;')
    add("")
    n = d["embedded_memory"]["sdram"]["port_count"]
    add(f"// --- embedded SDRAM: {n} ports, NO IO_LOC needed. They live inside the package and the chip database")
    add("// carries their die locations. Declare these top-level ports (Gowin names) and the tools map them:")
    add("//   O_sdram_clk, O_sdram_cke, O_sdram_cs_n, O_sdram_cas_n, O_sdram_ras_n, O_sdram_wen_n,")
    add("//   O_sdram_dqm[3:0], O_sdram_addr[10:0], O_sdram_ba[1:0], IO_sdram_dq[31:0]   (all LVCMOS33)")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed files differ from what would be generated")
    a = ap.parse_args()
    man = build(load_chipdb())
    man_text = json.dumps(man, indent=2) + "\n"
    cst_text = build_cst(man)
    if a.check:
        stale = [p for p, t in ((OUT_MAN, man_text), (OUT_CST, cst_text))
                 if not os.path.exists(p) or open(p).read() != t]
        if stale:
            print("STALE:", *stale, sep="\n  ")
            sys.exit(1)
        print("up to date")
        return
    os.makedirs(os.path.dirname(OUT_MAN), exist_ok=True)
    open(OUT_MAN, "w").write(man_text)
    open(OUT_CST, "w").write(cst_text)
    print(f"wrote {OUT_MAN}\nwrote {OUT_CST}")


if __name__ == "__main__":
    main()
