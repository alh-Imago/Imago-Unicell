# Mutability test 2 (Tang Nano 20K) -- ledger #1088

**The question (Alan, 12 Oct 2026):** test 1 rewrote the carrier through its direct configuration word. Test 2 adds a **standalone `command_cell_v4`** and a **standalone `sequencer_cell_v4`** on the same card, so that the command cell reconfigures the carrier through the carrier's *live programming channel*, a sequencer feeds the carrier, and **clocks are counted** to see the speed. Mixing cell families on one card is not something a normal build would do; here it is the test.

**What is in the bitstream (`mutability2.fs`):**
- the VIX carrier **v1d** (`fpga/verilog/unicell_vix_carrier_v1d.v`, with live add-on programming), cut down to adder, accumulator and mul (`tools/make_carrier_subset_v2.py`, a clone of the v1 script; the carrier file itself is untouched). Its `cfg_valid` is **tied to 0 for the whole run**: the only thing that ever configures it is the command cell.
- a standalone **`command_cell_v4`** in programmer mode (drive east, toggle pattern 7 = the 3-bit COMPLETE), wired exactly as `tb_vix_carrier_select_redirect_v1.v` wires the carrier's own command core: freeze, program, data, arrived out; prog_ack back.
- a standalone **`sequencer_cell_v4`** offering south into the carrier's north face (four 8-bit values, so it streams operand pairs).
- a wrapper: serial link, operand source for single shots, result consumer, and clock counters.

| File | What it is |
|---|---|
| `mutability2.fs` | The bitstream (git-ignored; `*.fs`). |
| `mutability2_host.py` | The test: runs 7 reconfiguration phases and two 64-result streams, writes `mutability2_results.txt` and `mutability2_results.json`. **Keep a copy of both.** `--selftest` checks the framing with no board. `--mhz` sets the clock period used for the nanosecond column (27 by default). |
| `run_mutability2.sh` | Linux: load the bitstream, wait, run the script (`sudo ./run_mutability2.sh [PORT]`). On Windows: `openFPGALoader -b tangnano20k mutability2.fs`, then `python mutability2_host.py COM7` (needs `pip install pyserial`). |
| `mutability2.json` | The phase table (the command words, expected results), the simulation lines, and the build numbers. |
| `mutability2.v`, `unicell_vix_carrier_v1dm.v`, `mutability2.cst` | What is inside. |

## The phases (same operands every time: A = 0x12345600 then B = 0x78)

Each phase is one `W` frame (the command words), then one `D` frame (the data). The configurations are the same seven as test 1, so the two tests can be compared: adder add; subtract; add + invert; add + shift right 8; add + nibble mask 03; the core itself changed to mul; back to the adder. Then two streams: the **adder** and the **mul**, 64 results each, fed by the sequencer (pairs 0x12,0x34 and 0x56,0x78 alternately).

Every phase sends **ten words** to the command cell: two sessions, each beginning with one harmless no-op word, then the core select (or the add-on address word 11), the field words, and the **COMPLETE word 0x00700001**, which the command cell recognises to release the carrier.

## A carrier finding (this is why each session starts with a no-op word)

The carrier reads the first word of a programming session as the core select **only if it has already seen the session's program line rise**. After reset it is armed. After a session ends it is **not** re-armed until the *next* session's first word has already arrived, because the rising edge and the first word come on the same clock. So the first word of every session after the first is read in the old state: as an ordinary field word for the current core (or as an add-on word if the add-on block was just addressed), and the real select word that follows is then consumed as an ordinary word. Seen in simulation as a stall and reproduced in a directed simulation that printed the carrier's select state word by word. Workaround used here: one word with PROG_ID 6 (unused by the adder, mul and the add-on block, so it does nothing) at the start of every session, and a priming session at power-up. This is a property of the carrier, not of this test; `tb_vix_carrier_select_redirect_v1.v` only ever starts one session after reset, which is why it passed.

## Frames (115200 8N1)

`W` n w1..wn -> `K` + clocks (the command cell relayed the words and went quiet); `D` A B -> `R` + result + latency (clocks from B in to the result out); `S` cfg64 n -> `U` + first-result clock + n-th-result clock + first value + last value. `T` = timed out. All clock figures are counted on the card.

## What was checked, and what was not

- **Simulated (iverilog, serial bit time shrunk, a testbench plays the PC with the same frames):** all seven phases and both streams pass. Four deliberate breaks are caught: the command words never sent after phase 0; one expected word wrong; the command cell never configured; the sequencer never enabled.
- **Counted in simulation (not yet on the board):** reprogramming a core and the add-on block through the command cell takes **40 clocks** for ten words; operand-in to result-out is **3 clocks** for both the adder and the mul; a stream gives one result every **4 clocks** (first result at clock 6, 64th at 258) for both. The 4 is set by the sequencer, which offers one operand every 2 clocks, and the wrapper; it is a floor on this test setup and not a claim about the cores. At 27 MHz, 40 clocks is 1.48 us and 4 clocks is 148 ns.
- **Fit (yosys `synth_gowin -nowidelut` + nextpnr, one seed, 27 MHz target; Fmax is nextpnr's static figure, not a measurement):**

| Cores in the carrier | LUT4 | of chip | ALU | FF | Fmax |
|---|---|---|---|---|---|
| adder, mul | 6,128 | 29.6% | 464 | 1,530 | 125.9 MHz |
| **adder, accum, mul (the bitstream)** | **6,345** | **30.6%** | 574 | 1,632 | **112.3 MHz** |
| + compare, branch, latch, ram | 6,792 | 32.8% | 642 | 1,886 | 106.0 MHz |
| all 15 cores | 8,144 | 39.3% | 692 | 2,443 | 66.3 MHz |

  The other rows were run through the same flow in the fit mode; an earlier build of the same bitstream source came out at 6,276 LUT4 and 109.5 MHz (the tools' result moved slightly when the file names given to yosys changed), so treat the figures as good to a percent or so. Asked for 150 MHz, nextpnr reached 109.5 and failed the target. Measured on their own with yosys, the command cell is 321 LUT4 and the sequencer 385; the rest of the difference from test 1 (4,553 LUT4) has not been broken down. Because the carrier's direct `cfg_valid` is tied off, the tools can simplify the paths that only that input used; the live programming paths are all real. The fit rows are for this command-only-configured card.
- **NOT checked: anything on the physical board.** The first run on silicon will also be the first time the command cell, the sequencer and the live programming channel run on the card. The clock counts come from the card; the nanosecond column is clocks times the period of the 27 MHz clock (the card runs at 27 MHz; a faster clock is not part of this bitstream, so the static Fmax above stays a tool estimate).
- **What a pass will show:** the standalone v4 command cell, through its programmer mode and the carrier's live channel, reconfigures a running carrier (core setting, the shared add-on chain, the choice of core) with no re-synthesis and with the direct configuration word never used; a standalone sequencer can stream operands through the carrier; and exact clock counts for each. **What it does not show:** the full carrier with all its cores in use, 32-bit streaming (the sequencer carries 8 bits; a stack of RAM cells would carry full words), several carriers on a grid, or the accumulator being exercised.
