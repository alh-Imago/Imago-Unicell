# Kintex card flash and multi-bitstream storage: facts so far (4 Nov 2026)

Read from Alan's own repo `~/ypcb-00338-1p1` (board README, board xdc, LOG, tools notes) and from UG470; the only thing run on the card was `openFPGALoader -c digilent_hs2 --detect` (chip ID 0x23751093, xc7k480t). Nothing was written to the card. See `docs/hex-n/HEXN_DESIGN.md`, ledger row 4 Nov 22:35.

## Corrections to `kintex-card-flow.md` (24 Oct)
- That note says Alan has no Xilinx tools. His board notes say **Vivado Lab Edition is installed** (`~/opt/Xilinx`, free, no licence needed). It is used for flash readback (`fpga flash-readback`, 64 MiB in about 60 s) and programming. Whether it can generate bitstreams with multiboot settings is not known; synthesis still goes through openXC7.
- The loader to use is his own build: `~/openFPGALoader/build/openFPGALoader -c digilent_hs2 ...` (the one on the PATH is older and does not know the chip). No nix shell is needed to run it.

## The flash
- Micron MT28GU512 **BPI NOR, 64 MiB, x16** (U4), not SPI. Pins A1-A25, DQ0-15, WE# T34, OE# T33, CE# V30, ADV# M31.
- The loader's SPI helper `spiOverJtag_xc7k480tffg1156` does not exist and would be the wrong kind; his README lists an openFPGALoader `bpiOverJtag_xc7k480tffg1156` (Vivado-built) as the flash-access helper.
- Holds one factory bitstream of 18.73 MB; the rest is erased. Master-BPI boot takes about 3.5 s. His rule: **ask before writing the BPI flash**; SRAM loads are fine.
- openFPGALoader's own flash read is about 2.6 KB/s (hours for 64 MiB); use Vivado Lab for readback.

## Sizing (UG470 Table 1-1 plus his file sizes)
7K480T bitstream = 149,880,032 bits = 18,735,004 bytes (17.87 MiB), uncompressed; his openXC7 `hex19_nc255` .bit is 18.7 MB, so the open flow writes the full size. 64 MiB holds **three** images (53.6 MiB), not four.

## Not known yet
How to jump between images (7-series MultiBoot: WBSTAR plus IPROG, from inside the design via ICAP or as command packets over JTAG); whether openXC7 can build ICAP; whether a finished bitstream can be patched to carry the commands (as the Tang header was); the BPI address units. Untested hypothesis: a PC could trigger the jump itself over JTAG, the Kintex counterpart of the Tang's `openFPGALoader -r`.
