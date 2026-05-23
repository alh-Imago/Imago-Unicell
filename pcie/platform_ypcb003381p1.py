#!/usr/bin/env python3
import os
"""
LitePCIe platform definition for YPCB-00338-1P1
Inspur Kintex-7 XC7K480T PCIe x8 Gen2 accelerator card

Pin assignments reverse-engineered from:
  https://github.com/TiferKing/ypcb_00338_1p1_hack

GTX lanes: GTXE2_CHANNEL_X0Y16 - X0Y23
PCIe refclk: J8
PCIe perst:  Y26 (LVCMOS18, active low)
System clk:  AA28 (LVCMOS18)
System rstn: R28  (LVCMOS18)
LEDs:        P30, M30, N30 (LVCMOS18)
"""

from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform, VivadoProgrammer

# IOs --------------------------------------------------------------------------------------------

_io = [
    # System clock (50 MHz on-board oscillator, single-ended)
    ("clk50", 0, Pins("AA28"), IOStandard("LVCMOS18")),

    # System reset (active low)
    ("cpu_reset_n", 0, Pins("R28"), IOStandard("LVCMOS18")),

    # PCIe x8 Gen2
    # TX pins: F2 H2 K2 M2 N4 P2 T2 U4
    # RX pins: derived from GTX bank (not board-constrained, routed automatically)
    # Refclk: J8 (GTREFCLK)
    # Perst:  Y26
    ("pcie_x8", 0,
        Subsignal("rst_n", Pins("Y26"),   IOStandard("LVCMOS18")),
        Subsignal("clk_p", Pins("J8")),   # GTREFCLK — no IOSTANDARD for GT pins
        Subsignal("clk_n", Pins("J7")),   # GTREFCLK_N (adjacent)
        Subsignal("tx_p",  Pins("F2 H2 K2 M2 N4 P2 T2 U4")),
        Subsignal("tx_n",  Pins("F1 H1 K1 M1 N3 P1 T1 U3")),
        Subsignal("rx_p",  Pins("G4 J4 L4 N6 P6 R4 T6 V4")),
        Subsignal("rx_n",  Pins("G3 J3 L3 N5 P5 R3 T5 V3")),
    ),

    # User LEDs (3 bits, active high)
    ("user_led", 0, Pins("P30"), IOStandard("LVCMOS18")),
    ("user_led", 1, Pins("M30"), IOStandard("LVCMOS18")),
    ("user_led", 2, Pins("N30"), IOStandard("LVCMOS18")),

    # I2C temperature sensor (LM73)
    ("lm73", 0,
        Subsignal("scl",   Pins("N24"), IOStandard("LVCMOS18")),
        Subsignal("sda",   Pins("N25"), IOStandard("LVCMOS18")),
        Subsignal("alert", Pins("P25"), IOStandard("LVCMOS18")),
    ),
]

# GTX lane location constraints for LitePCIe S7PCIEPHY
# These must match the physical PCIe edge connector routing
_GTX_LOC = {
    0: "GTXE2_CHANNEL_X0Y23",
    1: "GTXE2_CHANNEL_X0Y22",
    2: "GTXE2_CHANNEL_X0Y21",
    3: "GTXE2_CHANNEL_X0Y20",
    4: "GTXE2_CHANNEL_X0Y19",
    5: "GTXE2_CHANNEL_X0Y18",
    6: "GTXE2_CHANNEL_X0Y17",
    7: "GTXE2_CHANNEL_X0Y16",
}

# Connectors -------------------------------------------------------------------------------------

_connectors = []

# Platform ---------------------------------------------------------------------------------------

class Platform(XilinxPlatform):
    default_clk_name   = "clk50"
    default_clk_period = 1e9 / 50e6   # 50 MHz

    def __init__(self):
        XilinxPlatform.__init__(self,
            device     = "xc7k480tffg1156-2",
            io         = _io,
            connectors = _connectors,
            toolchain  = "vivado",
        )
        # Required for PCIe: disable bitstream compression to avoid
        # partial reconfiguration interference
        self.add_platform_command("set_property BITSTREAM.GENERAL.COMPRESS FALSE [current_design]")
        # Required for 7-series PCIe: tandem PROM not used
        self.add_platform_command("set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]")
        # GTX lane LOC + refclk constraints (avoids Python format string issues)
        self.add_source(os.path.join(os.path.dirname(__file__), "gtx_loc.xdc"))

    def create_programmer(self):
        return VivadoProgrammer()

    def do_finalize(self, fragment):
        XilinxPlatform.do_finalize(self, fragment)
        # PCIe refclk period constraint (100 MHz)
        # GTX lane LOC constraints are written to gtx_loc.xdc by add_source below
