# S-Core: usage manual gap list and scale-test plan (DRAFT v1, 26 Nov 2026)

Status: a PLAN, not a result. Written after the Vivado line (`hh` builds) started working on the card (ledger #1478 to #1485). Nothing in section 3 has been run.

## 1. What documents exist today (read, not rewritten here)

| file | what it is | gap |
|---|---|---|
| `README.md` | the idea, versions table, quick start for the Tang, K7 mentioned as a "second target", limits | the K7 paragraph still says the far RAM is the DDR3 or block RAM and the open flow only; no word on Vivado, the `hd`/`hh` lines or the dispatcher versions that matter |
| `LADDER.md` | step-by-step from one job to your own program | step 0 loads an old fusion build (`sc_k7_fu2s8u8n3.bit`); does not say which current build to load or how to check the card first |
| `PROGRAMS.md` | writing your own program (five-part shape, rules) | none known for these builds (not re-read in full) |
| `BATCH_FORMAT.md` | job file, batches, far-RAM layout (read from the code) | section 8 is from `sc_sys_v17`; the Vivado line uses v18 (same behaviour in simulation) |
| `SHELL.md` | commands of `score_shell_v1.py` | none known |
| `K7_BUILDS_AND_LOADING_v1.md` (new draft) | which build, how to build, how to load, how to check, limits | needs the 8x8 / 8x16 results and a read-through by Alan |

**There is no single usage manual** that takes a reader from "I have a card" to "my own jobs run, I know what limits I hit and what a failure looks like". That is the next documentation target. Proposed order of chapters (each a short page, written from what has been measured):
1. What S-Core is and what it is for (from README, shortened); 2. What you need (card, cable, loader, tools); 3. Load a build and check the card (section 4 of the builds draft); 4. Run your first jobs (LADDER 1 to 3); 5. Your own program (PROGRAMS); 6. Many jobs, many blocks (plan, far RAM layout, `--blocks`); 7. Limits and what a failure looks like (status codes, refused jobs, the failures of this month and how they showed); 8. Building a new shape (open tools and Vivado); 9. Measured results table (one place, with dates and ledger numbers).

## 2. Open items before the manual can be called complete

- 8x8 and 8x16 builds (running) and their card tests; further shapes if wanted (the size fit says 16x8 about 47 %, 16x16 about 76 % of the LUTs; timing will limit, not LUTs).
- **Fusion on the Vivado line**: the `hh` builds have no fusion unit (width 1 only). The `fu...` build with units has not been built with Vivado or v18.
- **Far RAM**: 64K words now. Options for more: more block-RAM banks (a general N-bank clone of `farram_bram_v2`; 128K to 512K words fit the chip's block RAM by my arithmetic), or the card's DDR3 (UberDDR3, proven earlier in the open flow at 4 slices, #1338; not tried with these builds or with Vivado).
- Whole-top simulation of the `hh` tops (`sc_sys_v18` passes its pool-level test; the whole tops were never simulated; rule #1466 was departed from knowingly).
- Why Vivado mishandles the falling-edge registers (unknown), and why `REQP-1962` trips in some builds only (unknown).
- Optional, parked: sub-arbiters for groups of 4 blocks and the slimmer far-RAM link (to cut wires; unproven that wire count was the open tools' problem); the open-tool builds of the larger shapes.

## 3. Scale tests: load, retrieve, reload (to write and run; none done)

Goal: show that putting data in, running, getting results back and doing it again works across the whole range, not just on one job. Each test is a script that prints one RESULT line.

| test | what it does | what it shows | notes |
|---|---|---|---|
| T1 repeat | run the same job set N = 100 times without reloading the bitstream; compare every answer | nothing leaks from one run to the next (shared RAM, queues, counters) | uses `scblocks.py` in a loop; log clocks per run, they should not drift |
| T2 reload | load the bitstream, run the eight-job set, repeat 10 times (the DDR3 build had 10 clean reloads, #1338) | clean start-up every time | one loader call per cycle |
| T3 far RAM full sweep | `far_ram_check_v1.py` over 0x0000 to 0xFFFF in chunks, all four patterns, plus the 0x7FFF/0x8000 boundary | both banks, every address (only 512 words each at 0x2000 and 0x8000 so far) | 64K words x 4 patterns: slow over JTAG; run in the background in chunks |
| T4 shared RAM all blocks | `shared_ram_check_v1.py pattern` on every block (0 to N-1), all 256 words | each block's own shared RAM (only block 0 tested so far) | quick |
| T5 big results | jobs with many output words (vprefix, vgain, vscale) up to the window limit, and one job over the limit (must be refused with status 2, not corrupt) | retrieve works for long outputs and refusals are clean | compare with the Python answer |
| T6 full batches | 16 jobs in a batch, several batches per block, all blocks busy, mixed kinds, random inputs | packing, queues, far-RAM layout at scale | answers from the Python reference (ISS); log the packing report |
| T7 soak | a job mix on all blocks for an hour, a rolling comparison | no late failures, no drift | stop at the first wrong answer and keep the dumps (`far_dump_v1.py`, `shared_ram_check_v1.py dump`) |
| T8 mixed widths | `--lw` 1 to 4 on a fusion build | only once fusion exists on the Vivado line | blocked until section 2 item 2 |
| T9 multi-stage | stage 1 on the card, read its results back, feed them (with new data) into stage 2 as inputs, then stage 3; check the final answer against the Python reference; repeat with the results of several blocks merged into one next-stage job | results are retrievable and reusable: the "values passed back for another stage of processing" case (Alan, 26 Nov) | today this is a host round trip (read results, build the next job file); whether a stage can use the previous results straight from far RAM without the host is not checked |
| T10 work larger than the card | (a) a program longer than the 128-word code store, split into stages that are loaded one after another; (b) data larger than one block's shared RAM (256 words) and than the far RAM (64K words), processed in chunks with partial results combined at the end | the "design larger than the card can take" case (Alan, 26 Nov): chunking, staging and combining at scale | needs a chunking helper on the host side (not written); the far RAM expansion (512K, DDR3) would raise the limit in (b) |

What "reload" means here (Alan, 26 Nov): not only reloading the bitstream (T2) but also work that is bigger than the card holds, or whose results are needed again for a later stage (T9, T10). Order: T4, T3 (quick wins that also test the two-bank RAM), T1, T2, then T5, T6, T7. Each failure gets the same treatment as this month's: dump the far RAM and the shared RAM, compare with a known-good build, then look at the RTL.

Not claimed here: how long each test takes, or that these tests cover everything; they cover what the author could think of.
