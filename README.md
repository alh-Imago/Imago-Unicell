# Imago UniCell

A computer built as a field of small cells, where the wiring is the program.

You are welcome to look around. This page gives the idea, the design features that make UniCell what it is, what has actually been shown on real hardware (and what has not), and where to begin. It is a research project by one author, Alan Hill, developed with Claude. It is not a finished product, and it does not pretend to be one.

*Status, 24 October 2026 (ledger #1318): a working research system with a confirmed path onto two cards, the Tang Nano 20K and the Kintex-7. Nothing is claimed beyond what the table further down lists. The full record is the ledger in [`points/`](points/INDEX.md); the previous, much longer README is kept whole as [`docs/README_STATUS_RECORD_20261020.md`](docs/README_STATUS_RECORD_20261020.md).*

---

## The idea

**Topology is computation.** There is no CPU, no instruction fetch, no decode stage, no program counter and no shared bus. A program is a *wiring*: which of a small set of fixed hardware cores sits where, joined to its physical neighbours. Values arrive, a cell does its one job, and the result moves on to the next cell, one hop at a time. In the sub family every cell takes exactly one tick, so a design's timing is known in advance; in the flex family the handshake absorbs the differences.

Memory and compute are not separate places: each cell holds its own state, so there is no separate memory to attach, and more cells means more compute and more memory together.

## What makes the design what it is

- **The wiring is the program.** A design is written down as an ICM file: what each cell is, how it is configured, and which neighbours it listens to and sends to. Cells have no addresses; they are wired to the cells next to them.
- **A small set of fixed cores.** Nano (a universal two-input gate built from NOR logic, with twelve selectable functions), adder, multiplier, divider, comparator, accumulator, latch, sequencer, ram, branch, priority, merge, and the crossing and corner tiles that let one lane pass over another. New behaviour is made by composing these, not by inventing a specialist cell. A counter and a comparator beside an adder is preferred to an adder that knows when to stop.
- **Two arrivals, and an acknowledge.** A cell fires when both of its operands have arrived, so small differences in path length do not matter. The timing pulse only schedules when a word is handed from one cell to the next; the cell internals are not clocked. In the handshake family it is the acknowledge that governs the flow.
- **Freeze, capture, restore.** A freeze line disconnects a cell from the flow, so it can be reprogrammed without moving any data, and a design that is only half loaded cannot start early. Each cell's state can be read out as a series of words and loaded back later, in the same card, a simulated card or the VM.
- **One design, several kinds of cell.** The same ICM describes a design for three families: **flex** (a valid and acknowledge handshake, width set at build time, 18 bits on the Tang), **sub** (fixed one-cycle cells, timed statically, no handshake) and the original **standard / carrier** cells that the Arria 10 line was built on. The ICM never names a target. It states what a design needs, and a target either provides it or refuses; it never truncates.
- **Cells can program cells.** The command core can freeze a neighbour and send it a new configuration. A standard command cell reprogrammed carrier cells (adder, accumulator, multiplier) live on the Tang (#1087-#1089).
- **The VM is held to the hardware.** The Python VM and the generated Verilog are checked against each other cycle by cycle. The flex VM (`FlexGrid`) was built using the generated RTL as the oracle, and that comparison found and closed real defects in both. On the Kintex card a **fingerprint** of the running design is read back and compared with the folder it was built from (a wrong design is refused), and **wire witnesses** let the card report which connections and cells actually carried a word.
- **Honest measurement.** Stripping the cells down paid: the adder went from 2,348 LUT4 to 66, and 37 with the handshake. A like-for-like test did not favour UniCell: a 4-stage 32-bit CORDIC was about six times larger than hand-written Verilog in the sub family ([`docs/measurements/UNICELL_VS_PURE.md`](docs/measurements/UNICELL_VS_PURE.md)). Both results are in the record, with their limits.

## What has been shown on real hardware

One card, small designs, one PC. This shows that the cells, the handshake, freeze and restore, and the tool chain work on silicon. It does not show capacity or speed at scale. The numbered rows of the full table, with the run lines and signatures, are in the [status record](docs/README_STATUS_RECORD_20261020.md#confirmed-on-the-card-and-what-is-still-simulation-only-20-october-2026).

| Card | What was confirmed | Ledger |
|---|---|---|
| **Tang Nano 20K** (Gowin GW2AR-LV18, 27 MHz) | A sequencer counting on the LEDs; ten self-checking flex-cell tests (10 of 10); mixed flex, standard, carrier and sub designs equal to simulation; loops and rings; back-pressure, freeze, and save and restore in flight with identical end state; faults injected during capture and restore all caught and retried; a LaTeX formula carried through to a bitstream; cross and corner tiles; the division core; "no interrupts" and parallel-work tests (131 clocks each, equal to simulation) | #896, #1024, #1087-#1187 |
| **Kintex-7** (XC7K480T) | An ICM file picked in the front end, built into a project with the open openXC7 flow and fed and read over JTAG: a relay chain, two 4-input reduction trees, the 36-cell CORDIC and a 61-cell looped CORDIC each equal the VM (the CORDIC and the 61-cell design also passed a 16-word signed set); design fingerprint accepted and a wrong design refused; wire witnesses saw every connection and cell on the card's own wires, 39 of 39 and 40 of 40 for the CORDIC and 60 of 60 and 61 of 61 for the 61-cell design | #1264-#1318 |
| **Arria 10** (IEI Mustang-F100-A10) | Every core of the super carrier shell, over JTAG. A measured ceiling of about 200 to 250 cells closed hardware work there; it is still the reference for the VM's standard mode | Aug-Sep 2026 |

**Not shown:** a design larger than a small one on any card, clock rates for the LaTeX-built designs beyond estimates, a direct sub-to-carrier crossing (the assembler refuses it on purpose), more than the five designs that have run through the Kintex path (the largest has 61 cells), or any 3D hardware. A hand-written Verilog design gets the same save and restore from a clock enable and a scan chain ([`docs/freeze/PURE_VERILOG_FREEZE.md`](docs/freeze/PURE_VERILOG_FREEZE.md)). Every mechanism here also has published relatives: dataflow circuits, elastic CGRAs, FPGA state save ([`docs/prior_art/PRIOR_ART_REPORT.md`](docs/prior_art/PRIOR_ART_REPORT.md)). The review is a first pass and is not a proof of novelty either way.

## Ways in

Start wherever suits you. Each page also shows the command-line equivalent of what it does.

| If you want to... | Use |
|---|---|
| Follow the whole build in order: MAN file, project, Walker | the tabbed front end, `python3 nano/frontend_v1.py` (port 7421) |
| Watch a design run, drive cells, see what changes | the **Workbench**, `python3 nano/workbench_v7.py` (port 7420), guide in [`docs/WORKBENCH_USER_GUIDE.md`](docs/WORKBENCH_USER_GUIDE.md); it can read a card's own SHAPE and show the difference |
| Turn an ICM file into a project for a real card and run it | **UniCell Bench**, `python3 tools/frontend/unicell_frontend_v6.py --demo <demo folder> --repo .`, notes in [`tools/frontend/README.md`](tools/frontend/README.md) |
| Write a formula instead of drawing cells | the LaTeX front end, `python3 nano/latex_cli_v1.py "y = (a + b)^2 - 3c" --set a=2 --set b=3 --set c=4 -o poly.icm` |
| Write a program | the DSL ([manual](docs/stripped-cell/UNICELL_S_DSL_MANUAL.md)), the Python-AST front end, or LLVM IR |
| Learn how computers work through the cells | the [teaching manual](docs/teaching_manual.html), 24 interactive tabs, every figure captured from a real run; not yet tried with real learners |
| Read the whole project as a manual | [`docs/manual.html`](docs/manual.html) |
| Explore six-face (stacked, 3D) cells | the 3D kit, below |

## Other parts that have been built

- **The sub and flex families** ([`sub/`](sub/README.md)): every cell with its own self-checking testbench, measured costs against width, and a second output port so that, for example, a 64-bit add from two 32-bit limbs works. The Flex-Sub assembler (`tools/project_assemble_v1.py`) turns an ICM file into Verilog for a chosen family and card.
- **Arithmetic from cells.** A division core (one cell instead of about 23,000 for a written-out division); a LaTeX front end that checks every design against a plain evaluation of the same formula; stored plans and blocks (Horner polynomials, sums, a multiply-accumulate block, matrices); and floating point built from cells (the adder complete in all five rounding modes with subnormals, inf and nan; the fp16 multiplier; the fp16 and bfloat16 comparator).
- **The small unit:** a Tang Nano 20K, an SD card and an ESP32 as a test tool for any flex design. The CORDIC design and a full SD-card round trip have run on the real board ([`docs/unit_bringup_guide.md`](docs/unit_bringup_guide.md)).
- **The 3D exploration** ([`experimental/three_d/`](experimental/three_d/README.md)): a software study of cells with six faces (north, south, east, west, up, down) for stacked-chip designs. It has its own composer (a floor plan, a rotatable 3D view and a depth slider that shows one layer and fades the rest), an automatic placer that proves each layout by running it, a file format (ICM-3D v2) and its own manual and **download kit** (`python3 experimental/three_d/make_bundle_v1.py`; the kit needs only Python). It is **exploration only**: there is no 3D RTL and no card, and the automatic placer's layouts are larger than the hand-placed one (80 cells against 44 for the NOR adder). The paper audit of what each cell type needs for six faces is [`experimental/three_d/CELL_AUDIT_6_FACE.md`](experimental/three_d/CELL_AUDIT_6_FACE.md).
- **Hex-N:** an idea for a silicon neural cell that shares roots with UniCell, kept on its own branch. It is a different design and nothing on it changes the UniCell results here.

## Quick start

Get the folder (`git clone`, or the zip or `.onion` kit built by `tools/make_package_v1.py`) and run:

```bash
python3 quickstart.py --install      # a private environment inside the folder, the pip tools, and a self-test
python3 quickstart.py                # what you have, and what to do next
which iverilog yosys && python3 -c "import pytest, llvmlite"   # check the toolchain before trusting a test run
```

Two programs pip cannot supply are listed with the command for your system: `iverilog` (simulation) and `openFPGALoader` (loading a board). **Without `iverilog` the flex and sub suites print SKIP and exit 0, which looks like a pass** (#965). The install path has been tried on Linux only.

```bash
python3 tools/quick_check_v2.py --changed   # only the tests that name a file you changed
python3 tools/quick_check_v2.py             # everything except the slow ones
python3 tools/quick_check_v2.py --full      # everything: takes hours
```

`tests/vm` held about 2,960 tests on 20 October and has grown since (the 3D work alone adds 55). The last full run (20 October, #1307) was 2,958 passed and 13 skipped; its only failures were old tests since replaced by newer files.

A first design, from an ICM file to Verilog for the Tang:

```bash
python3 tools/project_assemble_v1.py -s flex --icm nano/examples/small_relay_chain.icm-hier.json \
    --man docs/man/tang-nano-20k.man.json --output build/relay
```

## Documentation

- [`docs/README.md`](docs/README.md): the documentation index. [`docs/shared/DOCS_AND_STATIC_PAGES_AUDIT.md`](docs/shared/DOCS_AND_STATIC_PAGES_AUDIT.md) says which docs are current and which have fallen behind; read it before relying on an older reference.
- [`sub/README.md`](sub/README.md): the sub and flex families, every cell and its measurements. [`tools/README.md`](tools/README.md): the assembler and measurement tools.
- [`docs/stripped-cell/ICM_V3_FORMAT.md`](docs/stripped-cell/ICM_V3_FORMAT.md) and [`ICM_VIX_FORMAT.md`](docs/stripped-cell/ICM_VIX_FORMAT.md): the program formats. [`experimental/three_d/ICM_3D_FORMAT.md`](experimental/three_d/ICM_3D_FORMAT.md): the six-face format.
- [`docs/man/README.md`](docs/man/README.md): MAN files, one card's fixed capabilities; [`docs/man/tang-nano-20k-getting-started.md`](docs/man/tang-nano-20k-getting-started.md): the first flashable design.
- [`docs/PROJECT_PHILOSOPHY.md`](docs/PROJECT_PHILOSOPHY.md): why the project is built the way it is.
- [`points/`](points/INDEX.md): the append-only numbered ledger of every decision, measurement and correction; [`current/latest.md`](current/latest.md): a short summary of each recent entry, newest first.
- [`docs/README_STATUS_RECORD_20261020.md`](docs/README_STATUS_RECORD_20261020.md): the earlier, detailed README: the full card table, the Arria 10 shell history and its scale ceiling, the VIX carrier, the floating-point write-up and the notes on archived work.

## Earlier work

An older, addressed-bus architecture, its compiler and VM, an OS layer and a family of domain models were built for a different, incompatible design and have been archived, not deleted: every file is kept byte for byte in `archeology/onion/` with searchable metadata. The Arria 10 line (the super carrier shell, eight cores per cell) and the nine-core VIX carrier are described in the status record above; the VIX carrier has RTL and VM results only, with no Quartus or silicon data.

## Licence

Software (the Python VM, compiler and tools): [MIT](LICENSE). Hardware (Verilog RTL, cell architecture, FPGA gateware): [CERN Open Hardware Licence v2, Permissive](LICENSE-HARDWARE). Both are permissive and ask only that the notices are kept. See [NOTICE](NOTICE) for which licence covers which files.

**Copyright (c) 2026 Imago UniCell Project.**
