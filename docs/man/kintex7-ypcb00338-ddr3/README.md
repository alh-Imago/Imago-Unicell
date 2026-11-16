# YPCB-00338 DDR3 pin files (received 16 Nov 2026 from Alan, from the TiferKing ypcb_00338_1p1_hack repo)

- MEMORY_CH0.ucf, MEMORY_CH1.ucf: pin locations for the two DDR3 channels (72 data bits, 9 strobe pairs, address 15, bank 3, clock, control).
- From the MIG project files (mig_0/mig_1/mig_01.prj, the authority) and the vendor software zip (read, not built): 2 channels x 2 GiB = 4 GiB
  at 0x1_0000_0000 and 0x1_8000_0000. Part MT41K256M8XX-125 (x8, 9 devices per channel incl. ECC), 72-bit, ECC on, tCK 1875 ps (DDR3-1066),
  CL 7, CWL 6, 4:1 PHY, 200 MHz input clock, bank VCCAUX_IO 1.8 V, DCI 50 ohm, memory 1.5 V. The "64" in the card's specs is the BPI flash (64 MiB), not RAM.
  CORRECTION: an earlier note here said DDR3-1600 / CL 11; those numbers came from a different IP block in the hand-off, not the memory controller.
- Clocks (part0_pins.xml): 200 MHz LVDS default_200mhz_clk1 AH27/AH28 (bank 12, channel 0) and clk2 G25/G26 (bank 17, channel 1); 50 MHz AA28.
- Speed grade: the vendor files all say -2 (xc7k480tffg1156-2); our MAN file says -1 (chip marking never read). Left at -1 (the slower, safe one).
- No open-source DDR3 controller exists here yet; whether nextpnr-xilinx supports the needed ISERDES/OSERDES/IDELAY cells is untested.
- Related prior art (Arria 10 side only): docs/stripped-cell/design-notes/ram_interface_collector_mechanism.md, ledger #266, #397, #407.
