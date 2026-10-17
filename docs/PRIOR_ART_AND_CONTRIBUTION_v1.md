# Prior art, and what this project contributes

*Written 17 Oct 2026 (ledger #1177), from Alan's framing of 16 Oct: the system is built on a lot of prior art, and the work brings those pieces into one cohesive suite.*

## What it builds on

"Looked up" means a web search on 17 Oct (titles seen, pages not read in full). Everything else is general knowledge that has **not** been re-checked here, and must be checked before it is quoted as a citation.

| Building block | Prior art | Where it appears here |
|---|---|---|
| Every logic function from one gate (NOR) | Functional completeness of NOR/NAND is a classical result (Peirce, Sheffer). General knowledge, not looked up. | The founding constraint; the NOR cell |
| Data moving through a network of units, no instruction fetch | Dataflow architectures (1970s, Dennis, Arvind) and systolic arrays (Kung and Leiserson, 1978). General knowledge, not looked up. Alan's son's remark that this "looks like a systolic array" (#1036 addendum 53) points the same way. | Cell networks, the flex and sub families |
| Valid / acknowledge handshakes between units | A common hardware idiom (ready/valid streams). General knowledge, not looked up. | Flex (v4sa) cells; the standard line's arrived/fire/ack |
| CORDIC | Volder, 1959. General knowledge, not looked up. | The looped CORDIC examples |
| Microcontroller loads an FPGA | Looked up: Efinix AN 038, esp32ecp5, Xilinx XAPP058 and others; see `docs/ESP32_BITSTREAM_LOADER_v1.md`. | The proposed ESP32 loader (not built) |
| Open FPGA tools | yosys, nextpnr, Apycula, openFPGALoader (used, not written here). | Every Tang build and load |

## What this project contributes (stated carefully)

Not any one of the ideas above. The contribution is the **combination**, brought together in one working suite and **measured on real hardware**: one NOR-based cell architecture with an ICM description that runs in the VM, generates Verilog, and runs on the card with results equal to the simulation. The measured evidence is the table "Confirmed on the card, and what is still simulation only" at the top of the README. That table, not a claim of novelty, is what carries the case.

## What is not claimed

- No individual building block is claimed as new.
- Speed and scaling on larger chips (Kintex-7, Arria 10) are not claimed until measured.
- "No interrupts" is claimed only in the narrow, testable form in `docs/NO_INTERRUPT_PARALLEL_TEST_PLAN_v1.md`, and no result for it exists yet.

## Checks still to do

1. Look up and cite the classical sources above properly (they are general knowledge here).
2. Check the archive (Onion) before any new construction is called new, as the project rule says.
3. Search the literature for each specific claim at the time it is made.
