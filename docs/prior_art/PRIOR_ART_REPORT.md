# UniCell: prior art and comparison (condensed copy)

Written 10 Oct 2026 (ledger addendum 66). The full report, with the neighbour tables and the sources, is a document in Alan's Claude Docs ("UniCell: prior art and comparison report"); this is a condensed copy so the findings live in the repo. It is a FIRST PASS: about 100 searches and page fetches by four readers; summaries by the fetch tool were not checked against the PDFs.

## Verdict
Every single mechanism in UniCell has published prior art. No one source combines UniCell's particular set, but that is "not found in a shallow search", not proof of novelty.

- **Closest relatives:** Dynamatic and DynaRapid (LLVM to handshake dataflow circuits; DynaRapid uses a library of 74 pre-placed 32-bit components, about 1.8x LUTs, about 10% lower Fmax); Elastic CGRAs (FPGA 2013: +26% area, +8% critical path, +54% energy at 65 nm); STRELA (Branch/Merge cells with a handshake on every link); Triggered PEs ("remove the program counter completely"); CIRCT Handshake; Chext.
- **Handshake cost is a known result.** UniCell's own sub family came out about 6 times the hand design on a small CORDIC; flex runs one item per two cycles (single-slot output buffer; elastic-circuit papers use two-slot buffers).
- **Freeze and restore is standard on FPGAs:** CAPTUREE2, configuration readback (Morales FCCM 2013: 4 to 13 ms), EPOCH (2025: about 3.1 ms save, values sometimes wrong), scan chains. A hand-written Verilog CORDIC with a clock enable and a 132-bit scan chain does it at about one LUT per state bit (addendum 65).
- **SambaNova's quiesce patent (US 11,055,141, priority 2019; continuation US 11,928,512)** covers checkpointing a running spatial fabric: the fabric is stopped at configured quiesce boundaries and each unit's state is shifted out through serial shift registers and later loaded back to resume. Description read; CLAIMS NOT READ (the fetched text stopped before them). As far as read, it does not describe capture at an arbitrary cycle with data in flight.
- **PreTrans (TPDS 2025)** is not a checkpoint paper: it pre-maps configurations and shares memory so CGRA tasks can move without reloading data (abstract only).
- **NOR as the only primitive is known:** Apollo Guidance Computer (3-input NOR chips), MAGIC memristor NOR. Nothing found tying NOR to checkpointing. The flex and sub RTL cells are ordinary Verilog, not NOR-built, so none of the tests touch the NOR founding constraint.

## What may be distinct (unproven)
Capture of the whole computation, including data in flight, at any clock edge, because every cell registers its output and obeys a global freeze; one mechanism, no per-design work. Shown in simulation (VM and flex RTL: all 1,728 flip-flop bits of the CORDIC are in the capture list; forcing a captured state into a second copy resumed identically at every informative cut). NOT shown: a hardware load path, anything on a board, a state file that loads into both the VM and the Tang.

## Not read
Manchester and MIT tagged-token papers, the original Chandy-Lamport paper, the Jovanovic scan-path paper, Tenstorrent, ADRES/MorphoSys/RAW/TRIPS/HyCUBE primary papers, the claims of the SambaNova patents, the full text of PreTrans, the Hex-N neuron work.

## Main sources
Dynamatic (dynamatic.epfl.ch), DynaRapid (FPL 2024), Chext (FPGA 2026), R-HLS (arXiv 2408.08712), CIRCT Handshake (circt.llvm.org), SELF (DAC 2006), Carloni et al. (TCAD 2001), Elastic CGRAs (FPGA 2013), STRELA (arXiv 2404.12503), Triggered PEs (IEEE Micro 2014), WaveScalar (MICRO 2003), Plasticine (ISCA 2017), CGRA surveys, Groq (ISCA 2020), Graphcore IPU (arXiv 1912.03413), Dennis and Misunas (1975), Monsoon (ISCA 1990), Kung and Leiserson (1978), iWarp (1988), GA144 F18A datasheet, Epiphany reference, CAPTUREE2, Morales and Gordon-Ross (FCCM 2013), EPOCH (arXiv 2501.16205), OPTIMUS, Apollo Guidance Computer (righto.com), MAGIC (TCAS-II 2014), CAM-8, SambaNova US 11,055,141 and US 11,928,512 (Google Patents), PreTrans (IEEE TPDS 2025).
