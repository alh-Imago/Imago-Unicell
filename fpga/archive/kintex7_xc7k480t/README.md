# Kintex-7 XC7K480T Archive (YPCB-00338-1P1)

Work completed June 2026. Card lost to PCIe interface failure after
timing violations stressed the hardware.

## What was proven
- PCIe Gen2 x8 enumeration confirmed
- XDMA driver loaded, /dev/xdma0_user accessible  
- BAR0 bridge write/read confirmed (0xA5A5A5A5 round trip)
- Architecture works on real K480T silicon

## What needs fixing before reuse on another K480T
- Timing closure: WNS=-2.4ns at 125MHz — fix Pblocks first
- Never flash with timing violations to PCIe hardware
- SYS_RSTN fix already in place (use pcie_perstn only)
- cmd_bus pipeline register already in unicell_zone.v

## Files
- top_xdma_unicell_zones.v — 2x2 zone grid, 200 cells, XDMA top level
- top_xdma_unicell_zones.xdc — pin constraints, Pblocks
- top_xdma_unicell.v — original single-zone design (working baseline)
- unicell_xdma.py — Linux MMIO tool for /dev/xdma0_user

## Lessons learned
See sessions/latest.md for full post-mortem.
