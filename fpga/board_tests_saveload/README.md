# Save / load / retarget proof, part 1: the Tang Nano 20K stops itself, takes a VM state, runs on (ledger #1098)

**Alan's rule (12 Oct 2026):** there is no exact way to say where the Tang is or how many calculations it has done, and the host link is slow, so the card must not be stopped by time or by a host command. Here **the card stops itself at a programmed step count** (a counter built from the family's own accumulator cell, setting a latch cell), raises a `stopped` flag, and waits. The host reads it afterwards.

**What is on the card (`saveload.fs`):** the looped CORDIC (4 stages + a drift adder + a 20-relay way back, 57 cells after the assembler, from `nano/examples/looped_cordic_v1_open.icm-hier.json` through the flex assembler), every cell's `freeze_in` joined to one freeze line, a `busy` signal (any non-constant cell holding a word), a one-word loop-closing register (the place a state is loaded and read), the step counter and the stop latch, and the serial front end. Two ways to stop, together or alone: **back pressure** (the loop stops being fed; the design runs itself down) and **freeze** (the latch drives every cell's freeze pin).

| File | What it is |
|---|---|
| `saveload.fs` | The bitstream (git-ignored; `*.fs`). |
| `saveload_host.py` | `--sanity` (4 short checks), `--state FILE --steps 300 --label A` (load the VM's state and run on), `--from-zero`, `--selftest` (no board). |
| `run_saveload.sh` | Linux: load the bitstream and run the host (`sudo ./run_saveload.sh [PORT] [sanity\|state\|zero]`). Windows: `openFPGALoader -b tangnano20k saveload.fs`, then `python saveload_host.py COM7 --sanity` (needs `pip install pyserial`). |
| `vm_save_step300.json` | The VM's save at step 300 (design model + running state by cell name + words in flight + tick), made by `tools/flex_tang_bridge_v1.py vm-save 300`. |
| `tang_state_step300.json` | What the card is loaded with: the loop word (8138) and its step (300), made by `... make-state`. |
| `saveload.v`, `saveload.cst`, `saveload.json` | What is inside, the pin file, and the simulated results and build numbers. |

## Do this, in this order
1. `sudo ./run_saveload.sh <PORT> sanity` -- four short checks of the stop, release, freeze and save/fresh-card/load mechanics (3 + 3 steps). Keep the output.
2. `sudo ./run_saveload.sh <PORT> state` -- the card is reset, loaded with the VM's step-300 word, runs 300 steps by itself and stops. **Pass back `tang_result_A.json`** (and the text on screen).
3. I run the VM from its step-300 save to the same step (600) and compare: `python3 tools/flex_tang_bridge_v1.py compare vm_save_step300.json tang_result_A.json`.
Optional: `... zero` runs 300 steps from the loop's first value (50000) on the card alone, as a cross-check of the card against the Python model.

## The cut point, and what a state is
Step k = the k-th result delivered to the loop's exit relay. The VM save is taken at that event, where (measured) the only non-constant cell holding a word is the exit relay, the adders' waiting first operands are constants, and the merge turn flags are not decisive for this one-item loop (the arbiter only decides when two sources are valid at once, which this loop never does). So the whole running state the card needs is **one word and the step number**; the rest of the save is the design (loaded first, in the card's case by the bitstream) and bookkeeping. A VM state that is not of that kind is refused by `make-state` with the reason.

## Frames (115200 8N1)
`X` reset -> `K`; `C` mode N(2) dly lag -> `K`; `L` word(4) -> `K`; `G` -> `K`; `Q` -> `Q` flags steps(2) word(4) run_clocks(4). flags: bit0 stopped, bit1 busy, bit2 held_valid.

## What was checked, and what was not
- **Simulated (iverilog; a testbench plays the PC with the same frames):** the four sanity scenarios pass: back pressure; freeze; freeze with the word inside the grid then resume; save, reset, load into the fresh card, run on. A deliberate break (the load path flips a bit) is caught (7 failures reported).
- **The loop on the card, in simulation:** each step takes about 46 clocks including the 4-clock wait in the closing register (3 steps = 137 clocks counted by the design in simulation); at 27 MHz that is 1.7 us per step, so 300 steps is about 0.5 ms.
- **Fit (yosys + nextpnr, one seed, 27 MHz target; Fmax is nextpnr's static figure, not a measurement):** LUT4 2,076 of 20,736; ALU 584; flip-flops 2,098; static Fmax 129.1 MHz.
- **Host script:** `--selftest` checks the frames against a software model (it proves framing and parsing only, not the hardware).
- **NOT checked: anything on the physical board.** The first run on silicon will also be the first time the freeze line, the accumulator-to-latch stop and the flex loop run on the card. A state in which the word is inside the grid (freeze mid-flight) is held but not read out; reading and loading it needs the scan path, which is not built. The carrier (non-mirrored) version and the retarget into a full VM are later steps.
