# k7_tree4_v1 -- first Kintex-7 self-check (ledger #1234)

The design is the Tang Nano 20K `std_tree4` (a 4-input sum tree built from the standard cell shells, 2,109 LUT4 on the Tang),
unchanged. On the Tang it printed, on the card (ledger #1060), res=P, sig=7FEF5298, last=0000061A, equal to simulation.
Here the Kintex card runs the same RTL at 50 MHz (the Tang ran at 27 MHz). The wrapper reads the report line the design
prints and compares all 163 bytes with the Tang's line:

    UCT std_tree4 res=P n=0006 e=0006 bad=0000 to=0 n0=0000 st=3 last=0000061A sig=7FEF5298 w=0000000A,00000039,FFFFFFF6,00002710,FFF7E68A,7FFFFEAA,00000000,00000000

PASS means every byte is equal: the six sums (10, 57, -10, 10000, -530806 and the one that wraps 32 bits), the number of
clocks (`last=0000061A` = 1,562 clocks) and the checksum. The clock count is in clocks, so it should not change with the
clock speed; this is the check that it does not.

## LEDs (active-high assumed)
1. About 1.3 s after loading, all three LEDs are ON (lamp test). If instead they are OFF for that time and then come on,
   the LEDs are active-low: tell Alan/Claude, one parameter flips it.
2. Then: yellow (N30) blinks slowly = clock running. Green (M30) blinks fast = PASS. Red (P30) steady = FAIL.

A steady green on the card that is not driven by the design (seen in ledger #1195) may be a power LED: that is why PASS is a
blink, not a steady light.

## Simulation (done in the cloud workspace, see ledger #1234)
`make sim` (needs iverilog): expects `PASS`.  The same wrapper with one byte of the expected line changed gives FAIL.

## Build
Inside `nix develop github:openxc7/toolchain-nix`: copy this folder into demo-projects (next to `blinky-ypcb003381p1`),
`make`, then `make program JTAG_LINK="-c ft232"` (SRAM only). Never write the card's flash. Do not load a bitstream that failed timing.
