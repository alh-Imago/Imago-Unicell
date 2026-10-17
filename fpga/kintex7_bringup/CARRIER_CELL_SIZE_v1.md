# Size of ONE full carrier cell (unicell_vix_carrier_v1d), synthesis only — ledger #1186

17 Oct 2026. Measured with yosys 0.69 (YoWASP) on `fpga/verilog/*.v` (testbenches, `unicell_super` and top files left out), top `unicell_vix_carrier_v1d`, default parameters. **Synthesis only: no placement, no routing, no timing.** The IBUF/OBUF counts (448/287) are only the cell's ports being treated as chip pins and are not part of the cell's logic.

| Target | Result (raw stat files in this folder) |
|---|---|
| Xilinx 7-series (`synth_xilinx -family xc7 -flatten`) | 6,694 LUTs (LUT2 1,107; LUT3 929; LUT4 1,491; LUT5 2,227; LUT6 940), 1,517 flip-flops, 100 CARRY4, 3 MUXF7/F8, **0 DSP, 0 block RAM** |
| Gowin Tang Nano 20K (`synth_gowin -nowidelut`) | about 8,656 LUTs (LUT1 4; LUT2 1,632; LUT3 2,620; LUT4 4,400) plus 463 ALU blocks, about 1,517 flip-flops |

What it says: one complete carrier cell, with every core in it, is roughly 40–45% of the Tang Nano 20K (20,736 LUT4), which is why only trimmed carriers fit there. XC7K480T: 74,650 slices (datasheet DS180 table, read 17 Oct) = 298,600 6-input LUTs at four per slice, so one cell is about 2.2% of the chip, i.e. very roughly 40 cells by LUT count alone. Not a prediction of how many fit: routing, packing, clock speed and the grid wiring between cells are not included, and the XC7K480T DSP blocks (1,920) are unused by this cell. The real size of the full carrier system is for the Kintex run to measure.
