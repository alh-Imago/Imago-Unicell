# The S-Core manual (v1, DRAFT, 27 Nov 2026)

For Alan and for anyone who gets an S-Core card from him. It takes you from "I have the card" to "my own jobs run, and I know what the limits are".

**How to read the labels.** *Measured* = seen on the card or in a tool log (the ledger number is given). *Read* = read from the code or a file, not measured. Anything else is stated as a plan. If this manual and the code disagree, the code is right: fix the manual and log it.

**What this version covers:** the Kintex-7 card over JTAG, the `hk` build line (the newest), the shell (`score_shell_v9.py`) and the browser window (`scwin_v18.py`). It does not cover the Tang Nano 20K line (older commands, see `README.md`), PCIe (not built; everything here goes over JTAG), or an interpreter for a higher-level language (chapter 11 says what exists and what does not).

---

## 1. What S-Core is

S-Core is a pool of very small RISC-V cores ("slices", each one bit wide) that you can **fuse**: 2, 4, 8, 16 or 32 slices join to make one wider, faster core for one job. The same program runs at every width and gives the same answer; only the speed changes. There are **no interrupts**: a core runs its own instruction stream until it finishes.

You do not talk to cores directly. You give the host (your PC) a set of **jobs**. A job is one small program plus one list of data words. The host works out where each job goes, loads everything into the card, starts it, reads the answers back and checks them against the answers it computed itself.

Words used throughout:

| word | meaning |
|---|---|
| slice | one 1-bit core |
| block | a group of slices with its own code store, shared data RAM and dispatcher. The card build has several blocks (8 in the biggest) |
| fusion unit | the piece in each block that joins slices into one wide core. `unit-lw` = log2 of its lanes (5 = 32 lanes) |
| `lw` | the width asked for a job: 2**lw slices fused. `lw 0` = one slice, `lw 5` = 32 |
| job | a program (its *kind*) plus data. Result = a list of 32-bit words |
| window | the part of a block's shared RAM that one job can see: header, inputs, room for outputs |
| far RAM | the big memory (65,536 words on the card builds) that holds the scripts, code and data for all jobs of a run |
| batch | a group of jobs that fit in a block's code store and shared RAM at once |
| wave | one whole run of a design that was too big to run at once; the front end cuts a big design into waves |
| build | one bitstream (one shape of the card: blocks x slices x unit) |
| manifest | the small file next to a build that says its size, timing and what fits where |

---

## 2. What you need

- The **Kintex-7 XC7K480T card**, powered, with the JTAG cable (ft232 type). *Read from the notes:* the card is blank after a power-off; load a build each time.
- A PC with **Python 3** and **nix** (the commands use `nix shell nixpkgs#openocd`, which gives the card link its tools).
- The **openFPGALoader 1.1.1** from the nix store (path below). *Measured (#1535, #1536):* the system `openFPGALoader` on Alan's machine does not know this chip (IDCODE 0x23751093) and fails; the nix 1.1.1 one works. The shell tries its `loader` setting first, then the nix path, then PATH.
- This checkout (branch `S-Core_go` of alh-Imago/Imago-Unicell), folder `s-core/`.
- **Only to make a new build:** Vivado 2026.2 (free Basic licence). You do not need it to run the builds that already exist.
- Optional: the Python package `prompt_toolkit` (coloured prompt in the shell).

You need **no card** for: `add`, `show`, `plan`, `waves`, `make`, `save`, `open`, `fit`, `builds`, `target`. Only `load` and `run` touch the card.

**Safety rules that never change:**
- Loading is **SRAM only**. The flash is never written.
- A build whose timing failed is **never loaded**. A build with unknown timing needs the word `confirm`.
- No secrets (tokens, passwords) go in files, commit messages or notes.

---

## 3. The first start

```
cd ~/Imago-Unicell-score
git pull
cd s-core
```

**The shell** (a command line):
```
nix shell nixpkgs#openocd --command python3 score_shell_v9.py
```
**The window** (the same shell inside a browser page, with panels):
```
nix shell nixpkgs#openocd --command python3 scwin_v18.py
```
then open http://localhost:8766 (the program tries to open it for you). The window only talks to your own PC (127.0.0.1); pages from other sites are refused.

Without `nix shell ...` the programs still start; `plan`, `add`, `make` and the rest work, and `run` tells you the card link is missing.

Type `help` for the command list, `help COMMAND` for one command. **Tab** completes commands, job kinds, settings and file names. Several commands on one line are separated by `;`. A line starting with `#` is a comment.

**A first try with no card:**
```
add vsum 1 2 3 4
add vmax seq 5 80 3
show            # the jobs, with the answers they should give
plan            # what the host would do with them
save first.json
```

**Then with the card** (chapters 4 and 5 first): `use hk8s32u32n1i1024`, `load hk8s32u32n1i1024`, `run`.

---

## 4. Builds

### 4.1 Reading a build name

`hk8s32u32n1i1024` = line **hk**, **8** blocks, **32** slices per block, fusion unit of **32** lanes, **1** unit per block, **1024** code words per block. (Total 256 slices.)

### 4.2 The lines

| line | dispatcher / top | far RAM | notes |
|---|---|---|---|
| `hd...` | `sc_sys_v17` | `farram_bram_v1` | open tools (yosys + nextpnr). Do not build these with Vivado: every shared-RAM read returned 0 (#1476 to #1478) |
| `hh...` | `sc_sys_v18` | two 32K-word banks (`farram_bram_v2`) | Vivado. No fusion unit in most; widths 1 only |
| `hj...` | `sc_sys_v21` | two banks | adds `i...` = code store size in block RAM; 32-lane unit failed at lw 5 on the card (#1530) |
| **`hk...`** | **`sc_sys_v22`**, top `sc_top_k7_v18` | two banks | **use this line.** The store-wait fix; lw 0 to 5 correct on the card (#1533) |

### 4.3 What exists (Vivado, 50 MHz; slack = Vivado's, not Fmax; LUTs of 298,600)

| build | LUTs | setup / hold slack | on the card |
|---|---|---|---|
| `hk4s16u16n1i1024` | 70,077 (23.5 %) | +3.699 / +0.039 ns | not tested |
| **`hk8s32u32n1i1024`** | 246,006 (82.4 %) | +0.493 / +0.026 ns | **first-read test; lw 0 to 5 correct; 8 jobs at once at lw 5 on 8 blocks (#1533)**; shell and window runs (#1537 to #1548) |
| `hj8s32u32n1i1024` | 243,417 | +0.595 / +0.034 ns | lw 0 to 4 correct; lw 5 failed (#1530), cause found (#1531) |
| `hh16s16u1n1` | 226,031 (75.7 %) | +0.259 / +0.012 ns | 16 of 16 jobs on 16 blocks (#1503) |

More rows are in `builds_measured_v1.json` and `K7_BUILDS_AND_LOADING_v1.md`. The front end shows them with `builds`. "Fit" means: recommended = within the 80 % working target, tight = over it but built, no = does not fit.

### 4.4 Make a new build

Needs Vivado. In a plain terminal (not the nix shell), once per terminal:

```
source /media/alan/InternalHDD/Xilinx/2026.2/Vivado/settings64.sh
cd ~/Imago-Unicell-score && git pull
cd s-core/k7
python3 make_mb_v13.py 8 32 5 1 1024      # NB S ULW NU IMEM  -> Makefile.hk8_s32_u32_n1_i1024, the top, and the manifest
S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_mb_v12.sh        # copies the RTL into rtl/
sh run_builds_v1.sh hk8s32u32n1i1024       # one or several names; log, bitstream and a summary
```
(`ULW` = log2 of the lanes: 5 = 32 lanes. `make_mb_v13.py` writes the manifest by calling `make_manifest_v2.py`.) The 8 x 32 build took about 1 hour 5 minutes (#1532); the 4 x 16 about 23 minutes.

**Check before loading.** `run_builds_v1.sh` prints a summary; look for: Vivado exit 0, `Synth 8-9873` count 0, ERROR lines 0, both slacks positive with 0 failing endpoints. Do not lower the far-RAM DRC `REQP-1962` (it warned of board damage when lowered).

**Where builds go.** Bitstreams live in `vivado_out_<name>/` (with `timing_summary.txt`). The front end finds a build through its manifest `sc_k7_<name>.manifest.json`, either in your **store folder** or in `s-core/k7`. Set the store folder once with `store FOLDER`; it is remembered in `~/.score_shell.json` (or the file named by `SCORE_SHELL_CONFIG`).

**Size guide without building.** `fit BLOCKS SLICES ULW UNITS [IMEM]` (for example `fit 8 32 5 1 1024`) estimates the LUTs and says which boards it fits. *Read:* the model is LUT = 1,042 + 3,151 x blocks + 674 x slices plus units, within about 1.5 % over nine builds (#1501); it is a model, not a promise. The Tang Nano 20K has no S-Core pool built on this line, so it says "unknown".

---

## 5. Loading a build and checking the card

In the shell or the window:

```
builds                       # what is in the store, what fits, timing, bitstream found
use hk8s32u32n1i1024         # sets blocks, slices, unit-lw and code words to the build's own; shows its timing
load hk8s32u32n1i1024        # puts the bitstream in the card (SRAM), then runs the checks below
```
A unique piece of a name is enough: `use hk8s32u32` works if only one build matches.

**What is on the card.** `use` only changes the host's settings and never touches the card. Only `load` puts a build on the card. The card itself reports version, slices per block, code words and shared RAM size, but not its block count, lanes or name. So after a successful `load` the shell writes a **label** into far RAM (words 0x0100 to 0x0112: the build name, blocks, slices, lanes, units, code words, time and a checksum) and counts the card's blocks with a probe (`card_label_v1.py`). `card` reads them back, so a new shell or the window learns what is on the card without having loaded it. `card stamp BUILD` writes the label for a build you loaded by hand, after checking that the board matches it. `run` is refused when the label names a different build than the one chosen, or when the settings ask for more blocks than the card has (fewer is fine). *Status (#1556):* tested on a fake card only. *Not yet measured on the card:* that far RAM words below 0x2000 store data, that loading a bitstream clears the label (block RAM is expected to reset), and that the block probe counts correctly (it relies on the host command `O k` ignoring a block number at or above the real count, read from the hardware code). Run `card_label_v1.py test` once, then load a build by hand and `card_label_v1.py read` (expect "LABEL none: empty").

**Link check.** Before `run` the shell checks that the USB adapter (FT232H, 0403:6014) is on the bus and that it has not dropped off and come back since the last check (a loose header board or lead does this), then pings the card (reads the board's version reply). Before `load` and `card` it checks the adapter only. If anything fails the command stops, says nothing was sent, and says what to look at; a link error in the middle of a command is followed by the same advice. `set linkcheck off` skips all of it. `link_check_v2.py usb` and `link_check_v2.py ping` do the checks on their own. It cannot tell a loose connection from a bad cable or a card power fault: it reports what it saw and what to check first. *Status (#1564):* tested on fakes only (a fake /sys and fake pings); not yet tried on the real card.

**Which openocd.** More than one openocd can exist on a machine, and the JTAG code starts whichever comes first on PATH. `set openocd PATH` names the one to use and saves it in `~/.score_shell.json`; the shell then puts it first on PATH for itself and everything it starts, and `card` and the run pre-flight print which openocd and version were used. Without a setting it takes the environment variable `SCORE_OPENOCD`, then the nix build seen on this card (openocd 0.12.0, a store path of this machine's nixpkgs: if nix replaces it, the next choice is used and the shell says so), then PATH. *Status (#1569):* seen working on the card: `set openocd` was not needed, the default took the nix build and `card` printed `openocd: /nix/store/zi88f99wi0fbaa9992jzwb8jykvnpaa5-openocd-0.12.0/bin/openocd - Open On-Chip Debugger 0.12.0 (the nix build proven on this card)`.

**Which loader.** `set loader PATH` names the openFPGALoader for `load`; this machine's is `/nix/store/77r1cv86zjls4xix4kijr1sv9vn9a5yq-openfpgaloader-1.1.1/bin/openFPGALoader` (also the built-in default, so it is only needed if another one comes first). *Not saved:* in shell v9 the loader setting lasts for the session only (unlike `set openocd`); `card` does not print which loader it used.

`load` does three things: it runs `openFPGALoader -c ft232 FILE`; it runs the **first-read test** (`shared_ram_first_v1.py jtag 0`, healthy = the card's shared RAM answers `B C A B A`, which needs a fresh load); and it compares what the board reports (slices per block, code words) against the build. *Measured (#1536):* "first-read test healthy; the board reports 32 slices per block and 1024 code words, as the build says." If any step fails, nothing runs; the message says which.

**By hand** (without the shell), from `K7_BUILDS_AND_LOADING_v1.md`:
```
/nix/store/77r1cv86zjls4xix4kijr1sv9vn9a5yq-openfpgaloader-1.1.1/bin/openFPGALoader -c ft232 PATH/TO/NAME.bit     # expect: done 1
```
After a power-off the card is blank. A USB write error part-way once cleared on a second try (*measured*, 71 %).

Other checks of the card (older scripts, still valid): `shared_ram_check_v1.py` (shared RAM of a block), `far_ram_check_v1.py` (the two far-RAM banks at 0x2000 and 0x8000), and the ladder in `LADDER.md`.

---

## 6. Running jobs

### 6.1 Add jobs

```
add vsum 1 2 3 4               # kind, then data (numbers; hex is ok)
add vmax seq 5 80 3            # seq START COUNT STEP: 5, 8, 11 ... 80 numbers
add vxor 1 2 3 arg=255         # arg = one extra 32-bit number the program may read
add vsum 1 2 3 lw=5            # width for this job; lw=auto lets the host choose
add vsum 1 2 3 crit            # put it in the critical queue
show                           # the jobs and the answers they should give (computed on your PC)
```
The expected answer is shown the moment you add a job; it is computed by Python (or by the instruction-set simulator, chapter 8), independent of the card.

Other job commands: `list`, `remove N`, `dup N [TIMES]`, `clear`, `new` (also forgets registered programs), `save FILE.json`, `open FILE.json`.

### 6.2 Job kinds that exist

| group | kinds |
|---|---|
| built in | `vsum` (total), `vscale`, `vstress` |
| library (come in by themselves) | `crc32`, `vgain`, `vmax`, `vprefix` (running total), `vmin`, `vxor`, `vcount` |
| yours | made with `make` (no program to write) or `register` (your own assembly). Chapter 7 and 8 |

`programs` lists what is available.

### 6.3 Plan and run

```
set blocks 8       # (use already sets it from the build)
set lw 5           # width for every job: 0..5, auto, or none (each job keeps its own)
plan               # what the host will do, no card needed
run                # runs on the card, then checks every answer
```
`run` prints, per block, the clocks used, then `N of N jobs correct`, then the comparison job by job (`MATCH` or `DIFFERENT`). The answers are written to `shell_results.json` (setting `out`). `check RESULT.json` compares a result file again later.

**Reading the numbers.** The card runs at 50 MHz, so 50,000 clocks = 1 ms. "Slowest block" is the clock count of the block that took longest, which decides the run time. *Measured (#1540):* eight jobs (the ladder-6 set) went from 87.6k to 6.5k clocks on the slowest block from `lw 0` to `lw 5`, about 13.4 times, repeating within 0.03 % at lw 0 and 0.4 % at lw 5. The first run after a load can be slower; compare repeats with repeats.

### 6.4 Many jobs, big data, and designs larger than the card

| need | command | what happens |
|---|---|---|
| many similar jobs | `many N KIND seq START COUNT STEP [stride=K] [arg=] [lw=] [crit]` | adds N jobs at once, validated once (1000 jobs in seconds) |
| one data set longer than one job can hold (about 247 words) | `addbig KIND DATA [chunk=N] [combine=RULE]` | cut into piece-jobs; `run` puts the answers back together and checks the whole. Totals (sum, min, max, xor, or, and) are totalled again; `vprefix` carries the running sum; `crc32` and recipes with diff or prefix cannot be split |
| more than the far RAM holds in one run | nothing extra: `run` does it | the front end cuts the design into **waves**, runs them one after another and merges the answers. `waves` shows the plan without the card |
| a job that needs an earlier job's answer | `add KIND from=J argfrom=J` | a **pipeline**: J must be an earlier job; its card answer feeds this job's data (`from`) or `arg` (`argfrom`); each stage is its own wave |

*Measured (#1548):* 300 jobs of `vsum` over 40 words, with far RAM held to 12,288 words on purpose, ran as 7 waves (43 x 6 + 42 jobs): 300 of 300 correct. A three-stage pipeline (sum of 1 to 100 = 5050, scaled by 3 = 10101, summed again = 10101): 3 of 3 correct, each stage fed the card's own answer. Today a stage can read **one** earlier job, and at most about 247 words.

*Not yet measured:* a design that really exceeds the card's far RAM (the automatic halving path), and a stage that reads several jobs.

### 6.5 Batch files

A batch is a text file of the same commands you type. One per line, or separated by `;`; `#` starts a comment. It stops at the first error unless you add `continue`; at the end it lists every run (jobs correct, slowest block, `lw`, waves).

```
use hk8s32u32n1i1024
open ladder_6_eight_jobs.json
set lw 0
run
set lw 5
run
```
Run it with `batch FILE [continue]` in the shell or the window's prompt; in the window also the **Batch box**. From the command line: `python3 score_shell_v9.py -f FILE.score` (exit code 1 on an error; `-k` goes on after errors; `-c "cmd; cmd"` runs commands given on the line). A batch may call another batch (4 deep). Examples: `batches/ladder6_compare.score`, `batches/waves_demo.score`.

---

## 7. Making a new kind with no program: `make`

```
make bump add 5 xor arg shl 1 then sum
make flip not
make top16 shr 16 then max
```
Steps: `add sub xor and or shl shr not`, each with a number or `arg`; an optional ending `then sum|xor|or|and|min|max`. `make` writes the assembly program and its Python answer, checks both on the instruction-set simulator, and keeps the kind in `programs/made/` for later sessions. **A made kind is never changed: use a new name.** `code KIND` shows the assembly of any made, library or registered kind.

---

## 8. Your own program (the language)

The language is **RV32I assembly**, the plain 32-bit RISC-V integer instructions. There is no compiler on the card side: you write assembly (or copy a library program and change a few lines). *Read* from `PROGRAMS.md`; the full guide with a line-by-line example is there.

### 8.1 The shape of every program

| part | what | you change it? |
|---|---|---|
| 1. `push ra` | saves the way back | no |
| 2. `call lib_io_in` | gives `a0` = byte address of your inputs, `a1` = how many | no |
| 3. `call lib_io_out` | gives `a0` = where answers go, `a1` = how many fit | no |
| 4. the loop | takes inputs one at a time | **yes: your idea** |
| 5. `call lib_io_done` (or `lib_io_fail`), `pop ra`, `ret` | reports finished OK (or refused) | no |

`programs/template.s` is the empty version; `programs/vmax.s` is a real one; `vmin.s` was made from `vmax.s` by changing three lines.

### 8.2 The rules

- RV32I only: add, sub, and, or, xor, shifts, compare, branches, `lw`, `sw`. **No multiply, no divide.** (`vgain.s` multiplies by shifting and adding.)
- **Word loads and stores only** (`lw`, `sw`). No `lb lh sb sh`.
- Touch only your window (inputs and outputs) and your own small stack (16 words by default). Anything else is a trap on the card.
- Keep your values in `t2..t6` and `a2..a7`: the four library calls change only `t0 t1 a0 a1`.
- All programs of one batch together fit in the code store (128 words by default including the library; **1024 on the `hk...i1024` builds**, set by `use`).
- `main` ends with `ret`, returning 1 in `a0` for ok. Error codes are 2 and above (2 = output area too small).
- The job's extra number `arg` is read with `li t0,0x10000` then `lw t5,24(t0)`.
- `lib_io_done` takes the number of output words you produced in `a0`.

### 8.3 Register a program

```
register vmin programs/vmin.s expect=programs.examples_v2:vmin_ref out=1
```
`expect=` names a Python function that computes the right answer (`expect=iss` means: check only that the card did what the instructions say, which proves the card is right but not that your idea is). `out=` = how many answer words to reserve (a number, or `same`). It is checked at once: it assembles, fits the code store, runs on the instruction-set simulator, finishes with status 1 and agrees with your Python answer. A program that breaks a rule is refused with a message before it reaches the card.

In a job file:
```json
{"programs": [{"name": "vmin", "source": "programs/vmin.s",
               "expect": "programs.examples_v2:vmin_ref", "out": 1}],
 "jobs": [{"kind": "vmin", "inputs": [900, 42, 17000, 42, 5]}]}
```

### 8.4 The instruction-set simulator (`jobiss.py`)

The host has a Python simulator that runs one job instruction by instruction against its window, the way the card does. It is the independent reference for programs without a Python answer, and an early bug catcher: a load or store outside the window, a fetch outside the code region, a runaway loop (over 2,000,000 steps) are traps. It does **not** model byte or halfword access or multiply and divide. It checks that a program does what *the instructions say*, not what you *meant*: a wrong program that the simulator and the card run the same way still passes.

---

## 9. The window (browser)

`scwin_v18.py` is the shell with panels. The prompt (left) takes the same commands; the line is coloured as you type, **Tab** completes, **Up/Down** is the history. Pasting several commands at once sends them one line at a time. The right column is four fixed-height panels, so nothing jumps:

| panel | shows |
|---|---|
| **Builds** | the store's builds with fit and timing; buttons `use` and `load` type the same commands as the prompt, so every check applies; the chosen build first |
| **Cores** | one row per block asked for, one square per slice, always the same size. Dark = idle, yellow = taken and waiting, green = running, dim green = used (see below), red = error. Fused cores touch. The bar at the left of a row is green when that block's sequencer finished with steps run |
| **Jobs / Plan** | the jobs with their expected answers and verdicts; the batches of the plan |
| **Settings** | the settings |

Plus the **Batch box** (a collapsible text area, "run batch", a keep-going tick, a file chooser).

**What the Cores panel can and cannot show over JTAG.** A square turns green only if a status check catches that core busy. A status read takes 3 to 9 ms over JTAG and the first one lands about 22 to 24 ms after the start, but short runs finish in 0.14 to 0.43 ms, so nothing is caught (*measured*, #1548: "polls that found it busy: 0"). v11 therefore shows every square of a block that ran steps as "used" after the run. That is block-level knowledge: **it does not say which cores did the work** (a `lw 0` run on a 32-slice block lights all 32). Seeing individual cores needs a run long enough to be caught, or a hardware latch that records slices used (not built). *Not yet seen in a browser:* the "used" squares and the v10/v11 fix for a log line showing twice (page-text and state tests only).

---

## 10. Settings

`settings` lists them; `set NAME VALUE` changes one. `use BUILD` sets the build's own values.

| name | default | meaning |
|---|---|---|
| `blocks` | 1 | how many blocks of the card to use (it must be the number of blocks in the loaded build: the host does not ask the board) |
| `lw` | none | width for every job: 0..5 (2**lw slices fused), `auto`, or none (each job keeps its own) |
| `order` | auto | submit order inside a batch: auto (widest first when widths differ), kind, width |
| `profile`, `estimate`, `margin` | none, off, 0.1 | card profile and per-job width choice for `lw auto` |
| `dsh` | none | shared RAM words per block (none = ask the card on run; 256 for plan) |
| `far-words` | none | far RAM words (65,536 on the card builds; set smaller to force waves, as in #1548) |
| `slices` | none | slices per block (for plan with auto width; a real run asks the board) |
| `unit-lw` | none | log2 of the lanes of the unit on the loaded build (5 on hk8s32) |
| `imem` | none | code words per block (the planner assumes 128 if none; `use` sets it) |
| `loader` | none | path of openFPGALoader; none = the nix one, then PATH |
| `port` | jtag | the link: jtag, or a serial device |
| `out` | shell_results.json | where run writes the results |

---

## 11. Where the "interpreter" stands

Today there are three things that could be called an interpreter; none runs a high-level language.

1. **The instruction-set simulator** (`jobiss.py`, chapter 8.4): runs RV32I job programs on the host as the independent check. Built and used on every `register` and `make`.
2. **The host's expected-answer layer** (`Task.expected()`, per-kind Python functions): the reference for built-in and library kinds.
3. **`make` recipes** (chapter 7): a tiny step language (`add 5 xor arg shl 1 then sum`) that is turned into assembly. This is the nearest thing to a higher-level language that exists.

Not built (a plan only): an interpreter or compiler that takes a higher-level description and produces job programs, windows and stages itself. If you pursue it, the natural first step is to grow the recipe language of `make` (more steps, conditions, loops over windows) and let it emit `from=` pipelines, because the shell already runs those on the card (#1548). That is a suggestion, not a design.

---

## 12. Limits and what a failure looks like

| limit | value | what you see |
|---|---|---|
| code store per block | 128 words default; 1024 on `hk...i1024` (with `use`) | a program that does not fit is refused at `register` / `plan` |
| shared RAM per block | 256 words (`dsh`) | a job's window = header + inputs + outputs; about 247 data words |
| far RAM | 65,536 words (16-bit far addresses) | "far-RAM area ends" from the planner: the front end then runs waves |
| jobs per batch | 16 | the host packs automatically |
| widths | `lw` 0..5 (unit 32 lanes); `lw 5` needs a build with a 32-lane unit | the host refuses a width the build cannot give (checked against the board) |
| program length above the code store of the build | not yet tried above 128 words in a real run (to-do) | |
| blocks | 8 on the biggest hk build | `blocks` must match the loaded build |

Failure signs: `DIFFERENT` on a job (answer wrong); a program status code 2 or above (refused or output too small); a wave refused with the far-RAM message (halved and retried); `load` refusing because timing failed or the board does not match the build; the old failures of this project were silent wrong answers from the wrong build line (`hd` built in Vivado: every shared-RAM read returned 0) and a unit that got one instruction per S clocks. If a result is wrong: reload the build, run `first-read`, run the one-job ladder, then bisect.

Known open items (see `S_CORE_TODO.md`): a design that really exceeds the card; a stage that reads several jobs; per-wave timing; the Plan panel during waves; keeping earlier waves' answers on disk if a wave fails; programs over 128 words in a real run; scale tests T1 to T10 (`USAGE_MANUAL_AND_SCALE_TESTS_PLAN_v1.md`).

---

## 13. JTAG now, PCIe later

Everything above goes over JTAG. *Measured over JTAG (#1548 and earlier):* the card computes a 43-job wave in 0.43 ms; a status read takes 3 to 9 ms; loading far RAM takes about 2 s per wave (earlier runs). So the host time of a big design is dominated by the cable, not the card, and the number of waves costs real seconds. A PCIe link (a new PC and card) would change that: far-RAM loads and status reads would be orders of magnitude faster, so waves would cost almost nothing and polls could catch cores running. The plan, wave splitting, stage feeding and checking all happen on the PC side; whether a PCIe access can sit behind the same calls is **not yet checked**, and nothing in the S-Core code talks to the card by PCIe today.

---

## 14. File map

| file | what |
|---|---|
| `score_shell_v9.py`, `SHELL_v9.md` | the shell and its generated command list (`--write-help`) |
| `openocd_path_v1.py` | chooses one named openocd and puts it first on PATH |
| `link_check_v2.py` | the link check: adapter on USB, dropped since last check, ping, plain-words advice for link errors |
| `card_label_v1.py` | the label in the card's far RAM, the block-count probe, and the one-off reload test |
| `scwin_v18.py` | the browser window |
| `score_store_v1.py` | the build store: finds builds, timing verdict, fit, load, first-read |
| `scwaves_v1.py` | the wave planner and stage feeder |
| `scblocks.py`, `scbatch.py`, `jobcomp_v2.py`, `batch.py` | the host chain: jobs, tasks, batches, scripts, run |
| `jobiss.py` | the instruction-set simulator |
| `programs/` (`*.s`, `made/`) | job programs: template, library, made kinds |
| `k7/` | builds: `make_mb_v13.py`, `stage_mb_v12.sh`, `run_builds_v1.sh`, `vivado/run_vivado_v5.tcl`, manifests |
| `make_manifest_v2.py`, `targets_v1.json`, `builds_measured_v1.json` | size model, board profiles, measured numbers |
| `LADDER.md`, `PROGRAMS.md`, `BATCH_FORMAT.md`, `K7_BUILDS_AND_LOADING_v1.md`, `README.md` | the older guides (read them for detail; this manual links them in one story) |
| `S_CORE_TODO.md`, `latest.md`, `points/` | to-do, live state, the append-only ledger |

**Standing conventions of the project.** Proven files are never edited: a new version is a clone with the number incremented. The ledger (`points/`) is numbered and append-only. Measurements beat claims: a result is logged with where it came from.

---

## 15. What this draft has not been checked against

It was written from the files and the ledger. It has not been read through by Alan. Chapter 4.4 (the build commands) follows the scripts as they are; the 8 x 32 build was run by Alan with `run_builds_v1.sh`, but this exact command sequence was not re-run for this manual. Chapter 9's description of "used" squares is from tests of the page state, not from a browser. Chapter 13 is a view of what changes, not a measurement.
