# Hex-N: what is board-specific, for a move to a PCIe card and a new PC

Written 20 Nov 2026 for Alan, from the branch files only (nothing run, nothing built). Every line is **[file]** (read in the repository), **[doc]** (a statement in our own documents, not re-checked) or **[unknown]**. The Hex-N logic is not the thing that changes; the layer around it is.

## 1. The four things that change
| Layer | Today | What the move replaces |
|---|---|---|
| Host link | JTAG USER2 through `rtl/hexn_jtag_bridge_v1.v` (uses `BSCANE2`; simulated with `rtl/sim/bscane2_model.v`): 160-bit scans, 14 data bytes each way [file] | A PCIe interface (a DMA or BAR block). The command bytes (`I W B D G L S A N P Q J M R C Z U X Y V T H`) and the controller behind the bridge stay; only the carrier changes [file, `HEXN_KINTEX_BASE_PICTURE_v1.md` section 3] |
| Pins, clocks, voltages | `docs/hex-n/sources/ypcb00338_board.xdc`, `fpga/ypcb/hexn*/hexn.xdc` for the Kintex card; `fpga/build/hexn_*/unit_top.cst` for the Tang Nano 20K [file] | The new board's own constraint file. The old board file already lists the PCIe x8 pins and refclk of the current card, so it is a model for the file format, not for the new card [file] |
| Memory | Block RAM for the library, results RAM and data RAM; `rtl/hexn_ddr3_port_v1.v` with a DDR3 simulation model `rtl/sim/wb_ddr_model_v1.v` for the larger store [file] | The new card's memory controller. Which of these the new card has is [unknown] |
| Toolchain | openXC7 (nextpnr-xilinx) on the Kintex card, build in the nix shell, load with openFPGALoader; the Tang uses the Gowin flow [doc, README] | Probably the vendor tool for the PCIe block; check for the exact chip before relying on openXC7 [unknown] |

## 2. Files by group
- **Link:** `rtl/hexn_jtag_bridge_v1.v`, `rtl/sim/bscane2_model.v`, the host-side scripts that scan it.
- **Command layer (should carry over):** `hexn_base_ctl_v*.v`, `rtl/hexn_tier7_cmd_v1.v`, `v2`, `hexn_frame_v7.v`, the pattern arrays and the speech chain [file].
- **Memory ports:** `rtl/hexn_ddr3_port_v1.v`, the tier files (`rtl/hexn_tier_v6.v` to `v8.v`), and the block-RAM tests `fpga/ypcb/*/memtest.v`, `memlat.v` [file].
- **Board build folders:** `fpga/ypcb/hexn`, `hexn_arr`, `hexn_joint`, `hexn_ram`, `hexn_recall`, `hexn_speech2`, `hexn_sweep`, `hexn_tier`, `hexn_tier2`, `hexn_u2` [file]. Each holds its own constraint file or top-level wrapper.
- **Tang line:** the `.cst` files, `unit_top` wrappers and the display/buzzer driver `hw262_shield_v1.v` [file].

## 3. What should carry over unchanged [doc]
The arrays, the controller commands, the stores, the judge, the speech chain, the Python models and training, and the recorded results. The speech chain was tested on the card as exact equal to the reference, and the order of work (simulate, then card) is kept.

## 4. What to do before the move
1. Keep the link layer thin: no controller logic inside the bridge file.
2. Record which memory the new card has, then choose between the block-RAM and DDR3 paths.
3. Rerun the simulation suite against the new link before touching the card (the branch's own test list is in `README.md`).
4. Remeasure sizes, clocks and JTAG-equivalent speeds on the new card; the figures here are for the Kintex card and are nextpnr estimates, not silicon [doc].

## 5. Not known
The new card's chip, memory and tool flow. Whether the three Tang line items need any change at all. Which of the four models you will move first.
