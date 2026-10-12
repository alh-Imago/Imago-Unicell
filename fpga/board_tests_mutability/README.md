# Mutability test 1 (Tang Nano 20K) -- ledger #1086

**The question (Alan, 12 Oct 2026):** can one bitstream be reconfigured while running, with no re-synthesis, so that the *same input data* gives a *different result* because the core's configuration changed?

**What is in the bitstream:** the VIX carrier cut down to the maths cores (adder, accumulator, mul; `tools/make_carrier_subset_v1.py` removes the other twelve cores from a copy, the original file is untouched), and a small serial-port front end. Operands go in on the **north** face and the result comes out of the **east** face.

| File | What it is |
|---|---|
| `mutability1h.fs` | **The real test.** Host-driven: the PC sends every configuration and the data over the USB serial port. Nothing about the configuration is in the bitstream. |
| `mutability1.fs` | A weaker smoke test: the board runs the same seven phases by itself and prints one line. Its seven configurations are *inside* the bitstream, so the synthesis tool trims the carrier to those values (it came out at 1,296 LUT4 against 4,553 for the host-driven one). Use it to check the board and the serial line, not as the proof. |
| `mutability_host.py` | Runs the seven phases against `mutability1h.fs` and writes `mutability_results.txt`. Also `--cfg HEX40 [--a HEX --b HEX]` sends one configuration of your own. |
| `run_mutability.sh` / `.bat` | Load a bitstream, wait, run the host script. |
| `mutability1.json` | The phase table: configuration words, add-on settings, expected results, build numbers. |
| `unicell_vix_carrier_v1m.v`, `*.v`, `*.cst` | What is inside. |

## The seven phases (same operands every time: A = 0x12345600, then B = 0x78)

| # | Configuration sent | Expected (worked out from A and B in Python) |
|---|---|---|
| 0 | adder, add (**the first core on its own**) | 12345678 |
| 1 | adder, subtract mode | 12345588 |
| 2 | adder, add, add-on **invert** | EDCBA987 |
| 3 | adder, add, add-on **shift right 8** | 00123456 |
| 4 | adder, add, add-on **nibble mask 03** (nibbles 0 and 1 zeroed) | 12345600 |
| 5 | the **core itself changed to mul** | 88885000 (low word of A x B) |
| 6 | back to adder, add | 12345678 (same as phase 0: reversible) |

## Run it

Linux: `sudo ./run_mutability.sh host` (add the serial port as a second argument if it is not the highest `/dev/ttyUSB*`).
Windows: `run_mutability.bat host COM7` (needs `pip install pyserial`).
Smoke test: `./run_mutability.sh self` should print `UCM mutability1 res=P ok=7F ...`.
A pass of the real test prints `RESULT: PASS ...`; any other result prints which phase was wrong and what came back (`timeout` means nothing came out of the carrier in 60,000 clocks).
The board has been seen to stop answering after about 5 loads in a row (#1024): unplug and replug the USB cable.

## What was checked, and what was not

- **Simulated (iverilog, real UART bit timing shrunk):** both bitstreams' wrappers pass; for the host-driven one a testbench plays the PC and sends the same frames the script sends. Two deliberate breaks are caught (the configuration never rewritten after phase 0: phases 1 to 5 all return 12345678; one expected word wrong).
- **Built:** `mutability1h` 4,553 LUT4 + 474 ALU + 916 flip-flops (about 22% of the LUT4s, 24% counting the ALUs), Fmax 81.5 MHz at the 27 MHz target; `mutability1` 1,296 LUT4 + 856 ALU, 143.1 MHz. One placement seed each; these are nextpnr's figures, not a measurement on the board.
- **NOT checked:** **anything on the physical board.** In particular the serial *receive* line (pin 70) has never been used by any earlier test here (only transmit has); if the host script gets no reply at all, try `mutability1.fs` first: if that prints its line the board and transmit line are fine and the receive line is the suspect.
- **What a pass shows:** the carrier's own configuration word (`cfg_valid` + 160 bits, the same path the carrier testbenches use) can be rewritten while the board is running and the next data through it follows the new setting, for a core setting, the shared add-on chain, and the choice of core. **What it does not show:** the live programming channel (`program_in`), the command core, several cells working together on a grid, speed, or anything with the full carrier.
