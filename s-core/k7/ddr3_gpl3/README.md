# ddr3_gpl3 — GPL-3.0 code lives ONLY in this folder

**Everything under `upstream/` is NOT ours and is NOT under this project's MIT or CERN OHL licences.**
It is the UberDDR3 DDR3 memory controller by Angelo Jacobo, licensed **GNU GPL version 3** (full text in `upstream/LICENSE`).

## Decision (Alan, 2026-11-16)
Option 1: use UberDDR3 for the Kintex card's DDR3, keep it in this one folder, keep our own code in separate files, label everything.
The rest of the repository stays MIT (software) and CERN OHL-2 Permissive (hardware).

## Provenance
- Upstream: https://github.com/AngeloJacobo/UberDDR3
- Commit copied: `79d8fd3` ("Merge pull request #45 from jirgais/arty_a7_demo"), the commit sirmick tested on this card.
- Copied verbatim from upstream: `LICENSE`, `rtl/` (controller, PHY, top, AXI wrapper, ECC, SPD, ECP5 PHY), `README.md` (as `README-upstream.md`), and `example_demo/ypcb_00338_1p1/` (upstream's own example for this card: top, PLL, pin file, Makefile).
- No upstream file has been edited. If we ever must change one, copy it next to it with a new name and a header saying what changed and when (GPL requires modified files to carry notice of the change); never edit in place.

## What is ours, and what is GPL
| Where | Licence |
|---|---|
| `upstream/**` | GPL-3.0 (Angelo Jacobo) |
| Anything we write that is derived from, or is a modified copy of, `upstream/**` | GPL-3.0, put it in this folder and mark it |
| Our own wrapper / glue written against only the controller's ports | Our intent: keep it in this folder too, marked GPL-3.0 where it instantiates the controller, so the boundary is plain |
| The rest of `s-core/` (pool, sequencer, JTAG link, `farram_bram_v1.v`, scripts) | MIT / CERN OHL-2 as before |

## What this means for a bitstream or design that contains it
A build that includes `upstream/` is a combined work. If it is ever given to someone else, it has to be offered with its source under GPL-3.0.
Using it only on our own card does not trigger that. Not legal advice; if the project is ever sold or licensed commercially, get this checked by someone qualified.

## Keeping the boundary clean
- Our far-RAM interface (`req/ack`, same as `sdram_ctl` and `farram_bram_v1`) is the only thing the pool sees. The pool never includes a file from this folder.
- Builds that need DDR3 are separate top files (named `*_ddr3`) and are labelled GPL-3.0 in their header and in their Makefile. The existing BRAM build (`sc_k7_v1`) has no GPL code in it.
- Every file we add in this folder starts with a header naming this decision and the upstream commit.

## What the open toolchain needs changed (found 2026-11-16 from sirmick's `designs/uberddr3/prebuild.py` and UPSTREAM.md; now done by `make_mod.py`)
Upstream UberDDR3 does not build and calibrate on this card with the open flow as it stands. Sirmick patches copies of the PHY and top at build time. We do the same,
but as clearly marked MODIFIED copies in `mod/` (GPL-3.0, header naming the change; written by `make_mod.py`, which checks every edit), never edits of `upstream/`:
1. The single IDELAYCTRL moves out of the PHY into the top level (nextpnr allows one per design); the PHY gets an `i_idelayctrl_rdy` port.
2. The DDR3 CK output comes from an ODDR clocked by its own PLL output (`i_ck_clk`, +60 degrees from the DDR clock), and the DQS output stage uses the I/O tile's clock inversion
   (`IS_CLK_INVERTED`) instead of a fabric inverter. Without this CK/DQS arrive late by a placement-dependent amount.
3. This card's DDR3 banks have no ODELAY, so there is no write leveling; the fixed +60 degree CK offset suits all nine chips at DDR3-667 (sirmick's measurement).
4. BYTE_LANES is 9 (eight data lanes plus the ECC lane), so a Wishbone word is 9 x 8 x 8 = 576 bits wide.

## Files (stage 2, written 2026-11-16)
| File | What | Licence |
|---|---|---|
| `make_mod.py` -> `mod/ddr3_phy_ypcb_v1.v`, `mod/ddr3_top_ypcb_v1.v` | modified copies of upstream PHY and top (used INSTEAD of the upstream ones) | GPL-3.0 |
| `clk_ypcb_v1.v` | the PLL: 83.33 MHz controller, 333.33 MHz DDR3 (0, 90 and 60 degrees), 200 MHz reference, 50 MHz pool clock; from upstream's example clk_wiz | GPL-3.0 |
| `farram_ddr3_v1.v` | far-RAM wrapper: pool request/acknowledge <-> Wishbone, clock crossing, 32-bit word in a 576-bit line (word a: line a[20:4], slot a[3:0]) | GPL-3.0 (kept here by rule) |
| `sc_k7_ddr3_v1.v` | top (`module top`): PLL, IDELAYCTRL, ddr3_top, wrapper, pool | GPL-3.0 as a combined build |
| `make_xdc.py` -> `sc_k7_ddr3_v1.xdc` | pin file for DDR3 channel 0 (vendor MEMORY_CH0.ucf; I/O properties from upstream's example) and our clock and LEDs | GPL-3.0 |
| `Makefile`, `stage.sh` | build (copy this folder into demo-projects as `sc_k7_ddr3`, see the Makefile header) | GPL-3.0 |
| `tb_farram_ddr3.v` | wrapper testbench | GPL-3.0 |
| `../../fpga/sc_top_k7_v2.v` | the pool top with the far RAM brought out as ports; has no GPL code | MIT / CERN OHL as the rest of s-core |

## What has and has not been checked
Checked: the wrapper against a model of the controller's Wishbone port with the two clocks asynchronous and random stalls and latencies (4,827 pool operations, 0 errors; four deliberate
faults in the wrapper were each caught); the generated pin file against LiteX-Boards' pin list (117 of 117 identical for channel 0) and against the vendor file; the whole design elaborates in Yosys with no missing module.
NOT checked: the PHY and controller behaviour (no DDR3 model here), the build with the open toolchain (nextpnr, timing), calibration, any real read or write. The first test on the card is
therefore: build, load, and look at the LEDs (yellow steady = calibrated and the controller's built-in test finished).
Known risks: an unpatched nextpnr (sirmick's patches 0001-0003; 0003, OLOGIC T1, is the one DDR3 I/O is known to need); about one placement in four fails one lane in sirmick's builds (rebuild with another seed);
the controller's built-in memory test (BIST_MODE 1) runs through the address space before the ready state 23 and may take seconds; only 17 of the 25 line-address bits are used (8 MB window).
Sirmick records that LiteDRAM (the LiteX memory controller) never calibrated on this card under the open toolchain, which is why UberDDR3 is used first.
