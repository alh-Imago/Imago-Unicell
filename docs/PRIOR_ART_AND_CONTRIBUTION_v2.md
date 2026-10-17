# Prior art, and what this project contributes

*Written 17 Oct 2026 (ledger #1177), from Alan's framing of 16 Oct: the system is built on a lot of prior art, and the work brings those pieces into one cohesive suite. v2 (ledger #1181) clones v1 and updates what has since been looked up and run; v1 is kept unchanged.*

## What it builds on

"Looked up" means a web search on 17 Oct (result titles and links seen, pages **not** read in full). That confirms the source exists and is findable; it does not confirm any detail of its content, and nothing here should be quoted as a citation until the page has been read. Anything marked "general knowledge" has not been searched at all.

| Building block | Prior art | Where it appears here |
|---|---|---|
| Every logic function from one gate (NOR) | Functional completeness of NOR/NAND is a classical result. Looked up: search results include Wikipedia pages on the Sheffer stroke, functional completeness and logical NOR, and the Internet Encyclopedia of Philosophy page on the Sheffer stroke (pages not read in full). Who first published which gate (Peirce, Sheffer) is not checked here. | The founding constraint; the NOR cell |
| Data moving through a network of units, no instruction fetch | Dataflow architectures (1970s, Dennis; Arvind) and systolic arrays (Kung and Leiserson, 1978). Looked up: results include a 1974 Dennis paper PDF hosted at virginia.edu, a US patent on a dataflow processor, and a 1978 Kung-Leiserson CMU report PDF hosted at Harvard (none read in full). Arvind's work was not searched. Alan's son's remark that this "looks like a systolic array" (#1036 addendum 53) points the same way. | Cell networks, the flex and sub families |
| Valid / acknowledge handshakes between units | A common hardware idiom (ready/valid streams). General knowledge, not searched. | Flex (v4sa) cells; the standard line's arrived/fire/ack |
| CORDIC | Volder, 1959. Looked up: a Wikipedia page on Jack E. Volder and several CORDIC pages and patents appear in results (not read in full); the 1959 paper itself was not opened. | The looped CORDIC examples |
| Microcontroller loads an FPGA | Looked up: Efinix AN 038, esp32ecp5, Xilinx XAPP058 and others; see `docs/ESP32_BITSTREAM_LOADER_v1.md`. | The proposed ESP32 loader (not built) |
| Open FPGA tools | yosys, nextpnr, Apycula, openFPGALoader (used, not written here). | Every Tang build and load |

## What this project contributes (stated carefully)

Not any one of the ideas above. The contribution is the **combination**, brought together in one working suite and **measured on real hardware**: one NOR-based cell architecture with an ICM description that runs in the VM, generates Verilog, and runs on the card with results equal to the simulation. The measured evidence is the table "Confirmed on the card, and what is still simulation only" at the top of the README. That table, not a claim of novelty, is what carries the case.

## What is not claimed

- No individual building block is claimed as new.
- Speed and scaling on larger chips (Kintex-7, Arria 10) are not claimed until measured.
- "No interrupts" is claimed only in the narrow, testable form in `docs/NO_INTERRUPT_PARALLEL_TEST_PLAN_v2.md`. Status on 17 Oct: the Tang-only tests (T1 isolation, T4 independent copies, T5 shared port) are built and pass in **simulation** (job takes 131 clocks alone, beside 4 and beside 8 storm lanes, and as 4 copies). They have **not yet been run on the card**, so there is no hardware result. T2, T3 and C1 need the ESP32 parts and are not built.

## Checks still to do

1. Read the classical sources above (they are only located, not read) and cite them properly; settle who published NOR and NAND completeness first.
2. Look up Arvind and the ready/valid idiom, which have not been searched.
3. Check the archive (Onion) before any new construction is called new, as the project rule says.
4. Search the literature for each specific claim at the time it is made.
