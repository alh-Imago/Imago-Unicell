# Prior art, and what this project contributes

*Written 17 Oct 2026 (ledger #1177), from Alan's framing of 16 Oct: the system is built on a lot of prior art, and the work brings those pieces into one cohesive suite. v2 (ledger #1181) cloned v1 and updated what had been looked up; v3 (ledger #1183) clones v2 and records the card results of the Tang-only parallel tests. v1 and v2 are kept unchanged.*

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
- "No interrupts" is claimed only in the narrow, testable form in `docs/NO_INTERRUPT_PARALLEL_TEST_PLAN_v3.md`. Status on 17 Oct, measured on the Tang Nano 20K (`fpga/board_tests_parallel_v2/results_card_20261017/`): a 64-word job takes 131 clocks, exactly as in simulation, (T1) alone and beside 4 and 8 busy "storm" lanes, (T4) as one of 4 independent copies running at once, and (T5) when the same words go through 1, 2, 4 or 8 lanes behind one shared port. Words and signature are equal in all ten runs. Scope: one small job, one constant workload, no random stalls, one clock; the storm lanes share only the clock, the reset and the report line. It is not a claim about other designs or about the shared exit port, serial line or SPI, which do queue. Not run: T2 (response time to a rare event), T3 (cross-talk with the ESP32 on the bus) and C1 (the microcontroller contrast); they need the ESP32 parts. The first card run of T1 (#1182) was invalid because synthesis had deleted the storm lanes; the result above is from the corrected build.

## Checks still to do

1. Read the classical sources above (they are only located, not read) and cite them properly; settle who published NOR and NAND completeness first.
2. Look up Arvind and the ready/valid idiom, which have not been searched.
3. Check the archive (Onion) before any new construction is called new, as the project rule says.
4. Search the literature for each specific claim at the time it is made.
