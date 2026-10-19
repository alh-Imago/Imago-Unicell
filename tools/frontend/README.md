# UniCell Bench -- the front end (ledger #1255, ICM panel #1260)

A local page for building designs and running them on a card, without typing the same cd and make lines again. Runs on your own PC; standard Python only (3.8+); the terminal library is bundled (`vendor/`), no internet needed.

## Start it (plain terminal, Linux)
    python3 unicell_frontend_v3.py --demo ~/openFPGALoader/build/demo-projects --repo <your Imago-Unicell clone>
`--repo` lets the page find the assembler and the example ICM files; without it the ICM panel asks for the folder.
It prints an address like `http://127.0.0.1:8765/?t=...` and opens it in the browser. Keep that terminal open; Ctrl-C stops it. Only this PC can reach it (127.0.0.1, with a one-off key in the address).

## The page
* **Designs** (left): every folder in the demo folder that has a Makefile. Click one: `cd <folder>` is sent to BOTH shells. The line under the name is the first heading of the folder's README (or `kit.json` "title").
* **Build** shell: button *Enter openXC7 shell* types `nix develop github:openxc7/toolchain-nix` (you can also type it). Then *Check environment* (are yosys, nextpnr-xilinx, openFPGALoader, make and KINTEX7_CHIPDB there?), *Build (make)* (writes `build.log` in the folder), *Load into the card (SRAM)* (asks first; `make program JTAG_LINK="-c ft232"`).
* **Card** shell: a plain shell; the buttons run the kit's OpenOCD scripts through `nix shell nixpkgs#openocd --command sh <script>` (read, freeze, release, save, load, round trip, sweep). Only buttons for scripts the folder really contains are shown. Count boxes take whole numbers only.
* **Results**: the build verdict (Fmax lines, "timing passed" or "TIMING FAILED - do not load"), and the files the scripts wrote (`.log .txt .csv`; new ones since you picked the design are marked). Click one: a card read is shown decoded (the same decoder as in the kit), a save/load round trip as PASS/FAIL lines, with the raw file under it.

The two terminals are real shells: you can type in them as usual. The buttons only send fixed commands from a list in the program; nothing it sends writes the card's flash.

## The ICM panel (end of the pipeline: composer / DSL / LLVM IR -> ICM file -> card)
* The panel shows which repo it uses and at which commit. If that copy of the repo is too old for the chosen card (for example no Kintex runner), it says so and refuses to make the folder: run `git pull` in the repo and restart the Bench.
* Pick an ICM file. The list searches the repo examples, Downloads, Documents and any folder you add in the panel (only `*.icm-hier.json`, the Composer's VIX save, is accepted by the assembler). Pick a card: the list is every MAN file in `docs/man/`.
* *Create build folder* runs the assembler for you and makes a new folder **inside the demo folder**, so the Designs list picks it up by itself. What it makes depends on the card's `flow` in its MAN file: `openxc7` (Kintex: a runner project with Makefile, constraints, test vectors and the OpenOCD scripts), `gowin-apicula` (Tang: a Gowin project), `export-only` (closed toolchains such as Arria 10: a plain Verilog folder and a README, for you to synthesise yourself).
* On a Kintex runner project the folder name carries the tag *sim vs VM: PASS/FAIL*: the generated hardware was simulated and its answers compared with the VM's. The tag is the simulation verdict. On the card, two such projects (`small_relay_chain`, #1264, and the 4-input `reduction_tree4_exit_v1`, #1265; two input sets each) have been run and agreed with the VM; other designs have not.
* Extra Card-shell buttons for a runner project: *Run vectors v1/v2* (feed the test words, read the counts, signatures and last clock) and *Read run*. Results shows each exit as PASS/FAIL against the VM's expected answer.
* If the MAN file has a `startup` command (a line your design needs typed first), the page asks you once and keeps your answer only on your PC (`~/.config/unicell_bench.json`).

## Not its job
It does not install Nix or openXC7, does not make the chip database and never builds or loads by itself. If the environment is not there, *Check environment* says what is missing.
