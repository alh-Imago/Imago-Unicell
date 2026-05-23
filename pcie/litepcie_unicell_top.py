#!/usr/bin/env python3
"""
LitePCIe SoC top for YPCB-00338-1P1 (Inspur XC7K480T)

Architecture:
  Host (Linux)
    └── unicell.ko kernel driver
          └── PCIe BAR0 MMIO
                └── LitePCIe endpoint (S7PCIEPHY, x8 Gen2)
                      └── LitePCIeWishboneBridge
                            └── UniCell Wishbone slave
                                  └── UniCell array (openXC7)

The host driver writes/reads Wishbone addresses that map directly
to UniCell PTT registers (command, topology, a_data, output).

Build:
    python3 litepcie_unicell_top.py --build
    # Then program via Vivado Hardware Manager:
    # program_hw_devices [get_hw_devices xc7k480t_0] -bitfile build/ypcb003381p1/gateware/ypcb003381p1.bit

Requirements:
    pip install migen litex litex-boards litepcie
"""

import os
import argparse

from migen import *
from litex.gen import *
from litex.soc.cores.clock import S7MMCM
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone

from litepcie.phy.s7pciephy import S7PCIEPHY
from litepcie.core import LitePCIeEndpoint, LitePCIeMSI
from litepcie.frontend.wishbone import LitePCIeWishboneBridge
from litepcie.software import generate_litepcie_software

from platform_ypcb003381p1 import Platform

# Number of UniCells exposed over PCIe
# Start small for bring-up; scale up once link trains
NUM_CELLS = 64

# BAR0 layout (each cell gets 32 bytes = 8 x 32-bit registers)
# Offset = cell_index * 32
# +0x00  command     (write: configure cell)
# +0x04  topology    (write: set topology/sync_wait)
# +0x08  a_data      (write: preload A value)
# +0x0C  b_inject    (write: inject B packet — triggers computation)
# +0x10  output      (read:  cell output register)
# +0x14  status      (read:  a_arrived, output_valid flags)
# +0x18  reserved
# +0x1C reserved
CELL_STRIDE = 32  # bytes per cell

# CRG --------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        self.cd_sys = ClockDomain("sys")

        # PLL from 50 MHz system clock to sys_clk_freq
        self.pll = pll = S7MMCM(speedgrade=-2)
        pll.register_clkin(platform.request("clk50"), 50e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin)

# UniCell Wishbone Slave -------------------------------------------------------------------------

class UniCellWishboneSlave(LiteXModule):
    """
    Wishbone slave that exposes NUM_CELLS UniCells as a flat MMIO region.

    Each cell occupies CELL_STRIDE bytes in the address space.
    Writes trigger the unicell_array bus interface via a simple
    packet injection protocol.

    NOTE: This is a simulation-compatible register model for bring-up.
    The actual unicell_array.v integration happens in the next phase
    once PCIe link training is confirmed working.
    """

    def __init__(self, num_cells=NUM_CELLS):
        self.bus = bus = wishbone.Interface(data_width=32)

        # PTT register arrays (one per cell)
        # In the real integration these drive unicell_array.v signals
        self.command  = Array([Signal(32, name=f"cmd_{i}")    for i in range(num_cells)])
        self.topology = Array([Signal(32, name=f"topo_{i}")   for i in range(num_cells)])
        self.a_data   = Array([Signal(32, name=f"adata_{i}")  for i in range(num_cells)])
        self.output   = Array([Signal(32, name=f"output_{i}") for i in range(num_cells)])
        self.status   = Array([Signal(32, name=f"status_{i}") for i in range(num_cells)])

        # Wishbone address decode
        # adr[31:5] = cell index, adr[4:2] = register select (word-addressed)
        cell_idx = Signal(max=num_cells)
        reg_sel  = Signal(3)

        self.comb += [
            cell_idx.eq(bus.adr[5:5+bits_for(num_cells)]),
            reg_sel.eq(bus.adr[2:5]),
        ]

        self.sync += [
            bus.ack.eq(0),
            If(bus.cyc & bus.stb & ~bus.ack,
                bus.ack.eq(1),
                If(bus.we,
                    # Writes
                    Case(reg_sel, {
                        0: self.command[cell_idx].eq(bus.dat_w),
                        1: self.topology[cell_idx].eq(bus.dat_w),
                        2: self.a_data[cell_idx].eq(bus.dat_w),
                        3: Signal(),  # b_inject placeholder — triggers computation
                        "default": Signal(),
                    }),
                ).Else(
                    # Reads
                    Case(reg_sel, {
                        0: bus.dat_r.eq(self.command[cell_idx]),
                        1: bus.dat_r.eq(self.topology[cell_idx]),
                        2: bus.dat_r.eq(self.a_data[cell_idx]),
                        4: bus.dat_r.eq(self.output[cell_idx]),
                        5: bus.dat_r.eq(self.status[cell_idx]),
                        "default": bus.dat_r.eq(0xDEADBEEF),
                    }),
                ),
            ),
        ]

def bits_for(n):
    """Number of bits needed to represent values 0..n-1"""
    import math
    return max(1, math.ceil(math.log2(n))) if n > 1 else 1

# LitePCIe UniCell SoC ---------------------------------------------------------------------------

class LitePCIeUniCellSoC(SoCMini):
    def __init__(self, platform, nlanes=8):
        # x8 Gen2 = 128-bit data width, 200 MHz sys clock
        data_width    = 128
        sys_clk_freq  = int(200e6)

        SoCMini.__init__(self, platform, sys_clk_freq,
            ident     = f"Imago-UniCell PCIe Accelerator (x{nlanes} Gen2, {NUM_CELLS} cells)",
            with_ctrl = False,
        )

        # CRG ------------------------------------------------------------------
        self.crg = _CRG(platform, sys_clk_freq)

        # PCIe PHY -------------------------------------------------------------
        self.pcie_phy = S7PCIEPHY(platform,
            platform.request("pcie_x8"),
            data_width = data_width,
            bar0_size  = NUM_CELLS * CELL_STRIDE,  # BAR0 covers all cells
            cd         = "sys",
        )
        self.pcie_phy.add_ltssm_tracer()

        # PCIe Endpoint --------------------------------------------------------
        self.pcie_endpoint = LitePCIeEndpoint(self.pcie_phy,
            endianness           = "big",
            max_pending_requests = 8,
        )

        # Wishbone Bridge (PCIe TLP → Wishbone) --------------------------------
        self.pcie_bridge = LitePCIeWishboneBridge(self.pcie_endpoint,
            base_address = 0x00000000,
        )

        # UniCell Wishbone Slave -----------------------------------------------
        self.unicell = UniCellWishboneSlave(num_cells=NUM_CELLS)

        # Connect bridge master to unicell slave
        self.submodules += wishbone.InterconnectPointToPoint(
            self.pcie_bridge.wishbone,
            self.unicell.bus,
        )

        # MSI interrupt controller --------------------------------------------
        self.pcie_msi = LitePCIeMSI()
        self.comb += self.pcie_msi.source.connect(self.pcie_phy.msi)
        # No interrupts yet — will add output_valid MSI in next phase

        # LED heartbeat (blinks on PCIe link up) ------------------------------
        led0 = platform.request("user_led", 0)
        led1 = platform.request("user_led", 1)
        led2 = platform.request("user_led", 2)

        counter = Signal(26)
        self.sync += counter.eq(counter + 1)
        self.comb += [
            led0.eq(counter[25]),                      # heartbeat
            led1.eq(self.pcie_phy.link_up),            # PCIe link up
            led2.eq(self.pcie_phy.link_up & ~counter[24]),  # activity
        ]

# Build ------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LitePCIe UniCell SoC on YPCB-00338-1P1")
    parser.add_argument("--build",      action="store_true", help="Build gateware")
    parser.add_argument("--driver",     action="store_true", help="Generate LitePCIe driver skeleton")
    parser.add_argument("--nlanes",     default=8, type=int, help="PCIe lanes (1/4/8, default 8)")
    parser.add_argument("--num-cells",  default=NUM_CELLS, type=int, help=f"UniCells to expose (default {NUM_CELLS})")
    parser.add_argument("--output-dir", default="build/ypcb003381p1", help="Build output directory")
    parser.add_argument("--csr-csv",    default="csr.csv", help="CSR map CSV output")
    args = parser.parse_args()

    platform = Platform()
    soc      = LitePCIeUniCellSoC(platform, nlanes=args.nlanes)
    builder  = Builder(soc,
        output_dir = args.output_dir,
        csr_csv    = args.csr_csv,
    )
    builder.build(build_name="ypcb003381p1", run=args.build)

    if args.driver:
        generate_litepcie_software(soc,
            os.path.join(builder.output_dir, "driver"),
        )
        print(f"\nDriver skeleton generated in {builder.output_dir}/driver/")
        print("Build the kernel module with: cd driver && make")

    if args.build:
        print(f"\n=== BUILD COMPLETE ===")
        print(f"Bitstream: {builder.gateware_dir}/ypcb003381p1.bit")
        print(f"\nProgram via Vivado TCL:")
        print(f"  open_hw_manager")
        print(f"  connect_hw_server")
        print(f"  open_hw_target")
        print(f"  program_hw_devices [get_hw_devices xc7k480t_0] \\")
        print(f"    -bitfile {builder.gateware_dir}/ypcb003381p1.bit")

if __name__ == "__main__":
    main()
