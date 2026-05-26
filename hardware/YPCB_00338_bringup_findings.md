# YPCB-00338 Hardware Bring-Up Findings
**Date:** 2026-05-26  
**Board:** YZCA-00338-104 (PCB: 00338-P1, Serial: QTF507TT0066A01)  
**Session goal:** First-time BPI flash programming and PCIe XDMA enumeration

---

## Hardware Identification

| Property | Value |
|----------|-------|
| Board PN | YZCA-00338-104 |
| PCB Rev | 00338-P1 / 00338-108 |
| Serial | QTF507TT0066A01 |
| FPGA (physical) | xc7k480t (Kintex-7 480T) |
| IDCODE | 23751093 |
| JTAG cable | Digilent JTAG-SMT2 (210251A08870) |
| Config flash | mt28gu512aax1e-bpi-x16 (512MB BPI x16) |
| Config mode pins | M[2:1:0] = 0:1:0 (Master BPI) ✅ |

---

## What Was Accomplished

### BPI Flash Programming ✅
- Resolved SPI_BUSWIDTH=4 conflict with BPI16 by clearing SPI properties before write_bitstream
- Correct Tcl sequence established:
  ```tcl
  set_property BITSTREAM.CONFIG.SPI_BUSWIDTH NONE [current_design]
  set_property BITSTREAM.CONFIG.SPI_FALL_EDGE NO [current_design]
  set_property CONFIG_MODE BPI16 [current_design]
  set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
  write_bitstream -force <path>/top_xdma_unicell.bit
  write_cfgmem -format mcs -interface BPIx16 -size 512 \
    -loadbit "up 0x0 <path>/top_xdma_unicell.bit" \
    -file "<path>/top_xdma_unicell.mcs" -force
  ```
- MCS programmed to flash via Hardware Manager → Program Memory Configuration Device
- Erase / Program / Verify all passed ✅

### FPGA Boots from Flash ✅
Post power-cycle JTAG status confirmed:
- `DONE_PIN = 1` ✅
- `END_OF_STARTUP (EOS) = 1` ✅  
- `PLL_LOCK = 1` ✅
- `CRC_ERROR = 0` ✅
- `IDCODE_ERROR = 0` ✅
- Startup state machine phase = 100 (normal)

FPGA is fully configured and healthy from flash boot.

---

## Root Cause: PCIe Not Enumerating

**The Vivado project targets `xc7vx485tffg1157-1` (Virtex-7).**  
**The physical device is `xc7k480t` (Kintex-7).**

These are different device families. The XDMA PCIe core, GT transceiver pin assignments, and I/O constraints are all wrong for the physical silicon. The bitstream loads (the two devices are similar enough for configuration to complete) but PCIe cannot enumerate because the transceiver and pin mappings are incorrect.

---

## Next Steps

1. **Determine exact package** of the xc7k480t on this board:
   ```tcl
   get_parts -filter {IDCODE == 23751093}
   ```
2. **Retarget the Vivado project** to the correct `xc7k480tffg<package>-<speed>` part
3. **Re-run synthesis and implementation** with corrected device target
4. **Verify/update XDC constraints** — PCIe GT transceiver pins and ref clock must match the Kintex-7 package
5. **Regenerate bitstream, MCS, reflash**

---

## Notes
- Project path: `E:/xilinx/ypcb_00338_1p1_hack/examples/YPCB_00338_1P1_systest/`
- Bitstream: `top_xdma_unicell.bit`
- MCS: `top_xdma_unicell.mcs`
- BPI page size and read cycle settings in COR1 are at defaults (00/00) — may need tuning for mt28gu512aax1e timing once correct device is targeted
