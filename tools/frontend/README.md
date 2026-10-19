# UniCell Bench -- the front end (ledger #1255, ICM panel #1260)

A local page for building designs and running them on a card, without typing the same cd and make lines again. Runs on your own PC; standard Python only (3.8+); the terminal library is bundled (`vendor/`), no internet needed.

## Start it (plain terminal, Linux)
    python3 unicell_frontend_v1.py --demo ~/openFPGALoader/build/demo-projects --repo <your Imago-Unicell clone>
`--repo` lets the page find the assembler and the example ICM files; without it the ICM panel asks for the folder.
It prints an address like `http://127.0.0.1:8765/?t=...` and opens it in the browser. Keep that terminal open; Ctrl-C stops it. Only this PC can reach it (127.0.0.1, with a one-off key in the address).

## The page
* **Designs** (left): every folder in the demo folder that has a Makefile. Click one: `cd <folder>` is sent to BOTH shells. The line under the name is the first heading of the folder's README (or `kit.json` "title").
* **Build** shell: button *Enter openXC7 shell* types `nix develop github:openxc7/toolchain-nix` (you can also type it). Then *Check environment* (are yosys, nextpnr-xilinx, openFPGALoader, make and KINTEX7_CHIPDB there?), *Build (make)* (writes `build.log` in the folder), *Load into the card (SRAM)* (asks first; `make program JTAG_LINK="-c ft232"`).
* **Card** shell: a plain shell; the buttons run the kit's OpenOCD scripts through `nix shell nixpkgs#openocd --command sh <script>` (read, freeze, release, save, load, round trip, sweep). Only buttons for scripts the folder really contains are shown. Count boxes take whole numbers only.
* **Results**: the build verdict (Fmax lines, "timing passed" or "TIMING FAILED - do not load"), and the files the scripts wrote (`.log .txt .csv`; new ones since you picked the design are marked). Click one: a card read is shown decoded (the same decoder as in the kit), a save/load round trip as PASS/FAIL lines, with the raw file under it.

The two terminals are real shells: you can type in them as usual. The buttons only send fixed commands from a list in the program; nothing it sends writes the card's flash.

## The ICM panel (end of the pipeline: composer / DSL / LLVM IR -> ICM file -> card)
* Pick an ICM file (the repo's examples, or any path). Pick a card: the list is every MAN file in `docs/man/`.
* *Create build folder* runs the assembler for you and makes a new folder **inside the demo folder**, so the Designs list picks it up by itself. What it makes depends on the card's `flow` in its MAN file: `openxc7` (Kintex: a runner project with Makefile, constraints, test vectors and the OpenOCD scripts), `gowin-apicula` (Tang: a Gowin project), `export-only` (closed toolchains such as Arria 10: a plain Verilog folder and a README, for you to synthesise yourself).
* On a Kintex runner project the folder name carries the tag *sim vs VM: PASS/FAIL*: the generated hardware was simulated and its answers compared with the VM's. This is simulation only; the runner has not yet been measured on the card.
* Extra Card-shell buttons for a runner project: *Run vectors v1/v2* (feed the test words, read the counts, signatures and last clock) and *Read run*. Results shows each exit as PASS/FAIL against the VM's expected answer.
* If the MAN file has a `startup` command (a line your design needs typed first), the page asks you once and keeps your answer only on your PC (`~/.config/unicell_bench.json`).

## Not its job
It does not install Nix or openXC7, does not make the chip database and never builds or loads by itself. If the environment is not there, *Check environment* says what is missing.
