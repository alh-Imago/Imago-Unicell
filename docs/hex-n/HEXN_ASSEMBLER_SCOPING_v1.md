# Hex-N assembler: scoping (2 Nov 2026, 17:48; Alan: "lets scope out the assembler side")

Status: **SCOPING ONLY. Nothing here is built.** Facts are read from the files named; items marked PROPOSAL are for Alan to accept, change or drop; guesses are marked as guesses.

## 1. The job (Alan's words, 16:37)
The assembler "just grabs the latest version of the verilog for the components, and creates a specified top; that's its job, and it targets different cards too." It reads the ICM. The route is: ICM, then assembler, then place and route on the board (Alan, 17:17). The serial VM (`tools/hexn_vm_v2.py`) is the place to check the result.

## 2. What exists to copy (read, not assumed)
- `tools/project_assemble_v1.py` has a family flag (`-s flex|sub|nano|...`), `--man` (card capabilities), `--icm FILE`, `--target quartus|yosys`. The Flex-Sub family was added the same way: `tools/flexsub_assemble_v1.py` plus "one dispatch line" in the main file. A Hex-N family would be `-s hexn` dispatching to a new `tools/hexn_assemble_v1.py`.
- Flex-Sub already does what Hex-N needs: a table of cell shapes whose ports were read from each source file (`SHAPES`), `check_ports` against the real parsed module header, a generated top with anti-pruning stimulus and an XOR observer, dependency copy into a flat folder, a yosys script, `build.sh`, `ASSEMBLY.json`, and a `.cst` built from the MAN's pin table. `flexsub_icm_generate_v4.py` reads an ICM-VIX file as the netlist (that is Flex-Sub "step 2").
- Cards: `docs/man/tang-nano-20k.man.json` exists (Gowin GW2AR-18, open flow yosys, nextpnr-himbaechel, gowin_pack, openFPGALoader). **No MAN file for the Kintex card is in `docs/man`** (only the Tang and a Mustang Arria 10); Kintex builds so far used `fpga/build_hexn_kintex_v*.sh` with openXC7. So "targets different cards" needs a Kintex MAN file first.

## 3. The Hex-N components (the RTL in `sub/verilog`) and the mismatch between them
Two styles, both tested or probed, that a generator has to put in one grid:
- **A. Face-vector cells with a config SHIFT CHAIN:** `hexn_rcore_v1` (pure switch), `hexn_scell_v1`, `hexn_ramroute_v6`. Ports `fi[5:0]`, `fo[5:0]` (**six faces**), `cfg_en`, `cfg_in`, `cfg_out`. Routing select is 3 bits per output (18 bits per cell). The six-face width is already in the RTL; a four-face grid would leave two faces unused (and could drop their multiplexer inputs: a face-count parameter, not measured).
- **B. Pin-style cores:** `hexn_seq_core_v1`, `hexn_prio_core_v1`, `hexn_branch_core_v1`, `hexn_merge_core_v1`, `hexn_unary_core_v1`, `hexn_join_core_v2` (with `hexn_ramfifo_v8`), `hexn_latch_core_v1`. Separate data and start-flag pins per input, parallel config ports (`cfgload`, `vals[127:0]`, `mask`, `ranks`, `mode`...), no shift chain.
- **Gap 1, flags on the links:** the Python grid model carries a start flag with every word on every link (`rflag` in `hexn_wrgrid_v11.simulate9`); the face-vector routing probe routes ONE bit per face. A routing cell for the real grid needs a data lane and a flag lane. Not built, not measured.
- **Gap 2, no tested routing cell with program load:** `hexn_rcore_v1` is a measurement probe ("counts only"); the grid has no complete tile (routing cell + attached work core) as a module.

## 4. What the assembler has to do (PROPOSAL)
1. **Component catalogue** (like `SHAPES`): per component the file, parsed ports, config width and bit order, role (work / route / RAM), and a MEASURED cost on the target. Ports are checked against the parsed header; an unknown component is refused.
2. **Tile wrapper:** one uniform tile interface (four faces now, `faces` a parameter, six reserved) with data + flag per face, one config chain segment, and the clock. Style B cores get a small wrapper that turns a chain segment into their parallel config ports.
3. **Program load by chain, PROPOSAL:** every tile has a chain segment; the cells are set one after another in a fixed order. This matches Alan's 2 Nov 05:55 note (cells set one after another) and the three existing cell types. Cost to check: a core with a wide config (the sequencer's 128-bit `vals`) needs that many more flip-flops as a chain register.
4. **Top generator:** read an `icm-hexn-v2` file; instantiate tiles by (row, col) and the right core per record (`cross`, `corner`, `ram` relay and `route` records become routing-cell settings; work records pick the component); wire neighbours by face; stitch the chain; bind the pads named in `io` to ports; bridges (`io.bridges`) become the parallel/serial crossing ports.
5. **Frame:** the pattern's top carries `spi_bridge_v3` with the PATTERN_ID parameter from the pattern table (type K S NN, version), a chain loader that reads the program from scratch RAM and shifts it in, the general wipe, and the judges. Today's open tops (`hexn_open_top_v*`) are the model for this part.
6. **Outputs:** top `.v`, copied dependencies, yosys script (`synth_gowin -nowidelut`, JSON cell counting as measured earlier), `build.sh`, `.cst` from the MAN, `ASSEMBLY.json` with the pattern id and file hashes.
7. **Cost feedback:** the same tool, run per component on a target, writes a measured cost table. That replaces the estimates in `hexn_bases_v2` (routing cell 30, RAM routing cell 87, which are my own numbers) and feeds the pattern designer.

## 5. How we will know it is right (the check loop)
Same ICM file, two routes: (a) the serial VM; (b) assembler -> Verilog -> iverilog with a generated testbench that feeds the same inputs at the same ticks. Output words must be equal. Then place and route, then the board with the same inputs through SPI. The cores already have RTL-versus-twin tests; this adds a whole-grid test.

## 6. Order and size (relative sizes are my guess, not estimates in hours)
1. Tile wrapper + routing cell with flag lane, simulated alone (**medium**).
2. Wrappers for the style B cores plus chain loader, simulated (**medium**).
3. Top generator for one small pattern, simulated against the VM (**large**; the main piece).
4. Frame (bridge v3, wipe, judges), place and route on the Tang, measured costs (**medium**).
5. Board run (needs Alan).
6. Kintex MAN file and target (**small to medium**, after the Tang works).
7. The bridge to the UniCell parallel side (separate, later).

## 7. Open questions for Alan
- **Flag lane:** two wires per face (data + start) in the routing cells. Is that accepted, or should words be framed another way (a global word clock was used in the probes and cannot support self-timed cores)? My recommendation: data + flag.
- **Chain for everything:** accept the shift chain for all tiles, including wrappers for the pin-style cores?
- **Four faces now:** build the tile with `faces` as a parameter, default four. Confirmed by Alan 16:45.
- **Kintex MAN file:** who writes it, and from which source?
