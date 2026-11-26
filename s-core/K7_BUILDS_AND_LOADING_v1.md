# S-Core on the Kintex-7 card: which build to load, how to build it, how to check it (DRAFT v1, 26 Nov 2026)

Status: DRAFT written from the ledger (#1473 to #1487). Everything marked **measured** was seen on the card or in a tool log; **read** means read from the RTL or a log without measuring; nothing here has been checked by anyone but the author and Claude.

## 1. Two build lines, and which one to use

| | open tools (yosys + nextpnr, openXC7) | Vivado 2026.2 (free Basic licence) |
|---|---|---|
| dispatcher | `sc_sys_v17` (keeps the falling-edge registers in front of the block RAMs) | `sc_sys_v18` (no falling-edge registers) |
| far RAM | `farram_bram_v1` (cascaded RAMB36 pairs) | `farram_bram_v2` (two 32K-word banks) |
| build files | `hd...` (`make_mb_v6.py`) | `hh...` (`make_mb_v9.py`) |
| top | `sc_top_k7_v12` | `sc_top_k7_v15` |
| tested on the card (measured) | 8x4: 8 of 8 jobs on 8 blocks (#1475) | 8x4, 2x16, 4x16, 8x8, 8x16: single job and 8 of 8 jobs; far RAM clean at 0x2000 and 0x8000 on 8x4 and 4x16 (#1481, #1483, #1484, #1487) |
| bigger shapes | 12x2 and 16x2 did not finish in the open tools (placement/router, #1473) | 8x8 and 8x16 work on the card (#1487); 12 and 16 blocks not built in the `hh` line |

**Do not mix the two.** The Vivado build of `sc_sys_v17` (`hd...`) loads and talks but every shared-RAM read returns word 0, so every job fails (#1476, #1477, #1478). The only change that fixed it was removing the falling-edge registers (v18). The registers were put in for the Tang Nano's block RAM (README, v6); the open-tool builds still need v17 until shown otherwise. Why Vivado mishandles them is **not known**.

Names: `hh8s4u1n1` = 8 blocks, 4 slices per block, unit width 1, 1 unit. These builds have **no fusion unit** (FZ 0): jobs run at width 1 (`--lw 0`). Fusion (`--lw` above 0) on the Vivado line has not been tried.

## 2. Build with Vivado (the `hh` line)

Plain terminal (not the nix shell), once per terminal:
```
source /media/alan/InternalHDD/Xilinx/2026.2/Vivado/settings64.sh
cd ~/Imago-Unicell-score && git pull
cd s-core/k7
python3 make_mb_v9.py 8 4 0 1                      # NB blocks, S slices per block (writes Makefile.hh... and sc_k7_hh...v)
S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_mb_v9.sh      # copies the RTL into rtl/ (once is enough for every shape)
vivado -mode batch -source vivado/run_vivado_v5.tcl -tclargs hh8s4u1n1 2>&1 | tee vivado_hh8s4u1n1_v5.log
```
Use `run_vivado_v5.tcl`: it reads only the files the Makefile lists. The older scripts (v2 to v4) read every file in `rtl/`, which pulled in old variants of the same modules (21 "overwriting previous definition" warnings; harmless in the end, #1476, but not what the build names).
Output: `vivado_out_<name>/` with `timing_summary.txt`, `utilization_routed.txt`, `routed.dcp` and `<name>.bit`. **Check before loading:**
```
grep -c "Synth 8-9873" vivado_<name>_v5.log                        # expect 0
grep -E "WNS|WHS" -A2 vivado_out_<name>/timing_summary.txt | head -4   # both slacks positive, 0 failing endpoints
```
Never load a bitstream whose timing failed. Vivado slack is not Fmax. Do not lower the far-RAM DRC `REQP-1962`; it printed "board damage or other functionality issues" when lowered. The two-bank far RAM avoids it (the cascaded far RAM tripped it at 2, 4, 12 and 16 blocks, not at 8x4; cause unknown, #1480).

## 3. Load (SRAM only, never the flash)

```
/nix/store/77r1cv86zjls4xix4kijr1sv9vn9a5yq-openfpgaloader-1.1.1/bin/openFPGALoader -c ft232 PATH/TO/NAME.bit
```
Expect `done 1`. The system `openFPGALoader` in `/usr/bin` fails with an IDCODE error on this machine; the nix-store one works. A USB write error part-way (measured once at 71 %) cleared on a second load. After a power-off the card is blank: load again.

## 4. Check the card after a load (do these in this order)

1. **Shared RAM, straight after the load** (the first-read test needs a fresh load): `python3 shared_ram_first_v1.py jtag 0` inside `nix shell nixpkgs#openocd --command ...`; healthy = `B C A B A`.
2. `shared_ram_check_v1.py jtag pattern 0 0 256`: expect `RESULT: shared RAM host path OK`.
3. `far_ram_check_v1.py jtag 0x2000 512` and `... 0x8000 512`: both banks of the two-bank far RAM.
4. One job: `scblocks.py jtag ladder_1_one_job.json --blocks N --lw 0 --out r1.json` (expect `[10]`, about 9,050 to 9,210 clocks measured at 4 and 16 slices per block).
5. Eight jobs: `ladder_6_eight_jobs.json` with the same `--blocks N`, then `python3 ladder_show.py ladder_6_eight_jobs.json r8.json`: expect `8 of 8 jobs match` (answers 1600, 244, 5950, 600, 13080, 1012, 23590, 1480).
`--blocks N` must be the number of blocks in the build (it is the one thing the host does not ask the board). Slices per block and shared-RAM size are read from the board.

## 5. Measured so far (Vivado `hh` line, 50 MHz; setup/hold slack are Vivado's, not Fmax)

| build | LUTs (of 298,600) | setup / hold slack | card |
|---|---|---|---|
| `hh8s4u1n1` | 48,153 (16.1 %) | +6.095 / +0.061 ns | single job and 8 of 8 |
| `hh2s16u1n1` | 29,118 (9.8 %) | +3.525 / +0.052 ns | single job and 8 of 8 |
| `hh4s16u1n1` | 57,291 (19.2 %) | +1.570 / +0.045 ns | single job, 8 of 8, far RAM 0x8000 |
| `hh8s8u1n1` | 68,451 (22.9 %) | +3.938 / +0.027 ns | first-read test, single job, 8 of 8 |
| `hh8s16u1n1` | 113,615 (38.1 %) | +1.423 / +0.025 ns | first-read test, single job, 8 of 8 (128 slices) |
| `hh16s4u1n1` | 95,071 (31.8 %) | +1.663 / +0.040 ns | first-read test, single job, 16 of 16 jobs on 16 blocks, shared RAM of blocks 8 and 15 (#1498, #1499) |
| `hi16s4u1n1` (grouped arbiter, top v16) | 95,177 (31.9 %) | +0.709 / +0.038 ns | built, not on the card; whole top not simulated (#1497) |
| `hh16s8u1n1` | 135,658 (45.4 %) | +0.703 / +0.018 ns | first-read test, single job, 16 of 16 jobs on 16 blocks, shared RAM of block 15 (#1502) |
| `hh16s16u1n1` | 226,031 (75.7 %) | +0.259 / +0.012 ns | built, not yet on the card (#1501) |

Size model fitted to the eight builds (Vivado units): LUT = 1,178 + 3,045 x blocks + 685.5 x total slices, every build within 1.5 % (#1501; the five-build fit of #1487, LUT = 1,120 + 3,055 x blocks + 686 x slices, predicted the 16x16 within 0.2 % and the 16x8 within 1.6 %; a first fit on three builds also reproduced the earlier 16x4 and 16x8 within 0.7 %, #1485). It says whether a shape fits, not whether it routes or meets timing.

## 6. Limits (read from the RTL and the host code, not all tested)

- shared data RAM 256 words per block (the build's DSH); code store 128 words (IMEM_WORDS); at most 16 jobs per batch (host default);
- far RAM 64K words of 32 bits (FAR_AW 16); the host and request port carry 21-bit addresses, so the limit is the build and the block RAM (64 RAMB36 per 64K words; the chip has 955);
- up to 16 blocks (4-bit block select); the dispatcher tracks at most 64 slices per block;
- the card also has DDR3 (UberDDR3 far RAM proven in the open flow at 4 slices, ledger #1338); it is not used by the `hh` builds.
