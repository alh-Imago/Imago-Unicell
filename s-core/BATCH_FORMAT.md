# Batch data: how jobs, batches and widths are stored (S-Core)

Written 2026-11-19 (ledger #1404) from the code (`scbatch.py`, `jobcomp.py`, `batch.py`, `scblocks.py`, `sc_calibrate_v1.py`) and a real plan printed from it.
If the code and this page disagree, the code is right: fix the page and log it.

## 1. The chain, in one line
job file (JSON) -> `Task` objects -> split over blocks (`scblocks.split`) -> packed into batches (`jobcomp.pack`) -> one script per batch (`batch.Script`, 4-word steps) -> one far-RAM image per block (scripts, code, windows, then status and results areas) -> the on-card sequencer runs the scripts -> results are read back from far RAM and checked.

Nothing about batches is stored in the job file. The batches are worked out again on every run, the same way each time (deterministic: same jobs, same sizes, same result).

## 2. The job file (`jobs_*.json`)
```
{ "programs": [ {"name": "crc32", "source": "programs/crc32.s", "expect": "programs.examples:crc32_ref", "out": 1}, ... ],     (optional: extra programs; source paths are relative to the job file's folder)
  "jobs":     [ {"kind": "vgain", "inputs": [5061658, ...], "arg": 63, "out_len": 13, "lw": 2}, ... ] }
```
- `kind`: a program name (built-in vsum, vscale, vstress, or one registered in `programs`). `inputs`: a list of 32-bit words, or `{"seq": [start, count, step]}`. `arg` (default 0), `out_len` (default: the program's default) are optional.
- `lw` (optional, default 0): the width of this job, 2**lw slices fused (0 = one slice; 0..4, or the text "auto"). The command line `--lw N|auto` overrides every job's `lw`.
- Job numbers are the order in the file (0, 1, 2, ...). Results always come back in this order.

## 3. In memory (`jobcomp.Task`)
`kind, inputs, arg, out_len, lw`; `window_words = HDR + len(inputs) + out_len` is the job's size in the shared data RAM. `scblocks.cost()` = window words x a weight per kind (crc32 counts about 19 times a vector job per word; a rough guide from #1350, not a measurement).

## 4. How jobs become batches (`jobcomp.pack`)
- Blocks first: `scblocks.split` gives each block jobs, most expensive first, each to the block with the least total so far.
- Per block, `pack`: first fit, biggest window first. A batch is closed when it would exceed the code store (`imem`, 128 words: library + one copy of each program), the shared data RAM (`dsh`, 256 words: one window per job; jobs of the same program share code and have their own window, padded to the largest of that program in the batch) or 16 jobs.
- Inside a batch the jobs are sorted by (kind, job number). Task ids inside a batch are 0..n-1, reused by every batch (each batch waits for its jobs before the next starts).
- The width does not change the packing.

## 5. The script of a batch (`batch.py`): 4 words per step, `w0` opcode, `w1..w3` arguments
| op | name | w1 | w2 | w3 |
|---|---|---|---|---|
| 0 | END | tag | | |
| 1 | LOAD_CODE | near (code word) | far (word address) | count |
| 2 | LOAD_DATA | near (shared word) | far | count |
| 3 | SAVE | near (shared word) | far | count |
| 4 | SUBMIT | tid \| code<<16 (code = entry word) | prog \| **lw<<8** \| crit<<12 | |
| 5 | WAIT | timeout/1024 clocks | | |
| 6 | JUMP | far address of the next script | | |
| 7 | REGION | prog \| cbase<<16 | clen \| dlen<<16 | |
| 8 | WINDOW | prog | base \| len<<16 | |
| 9 | LIBRARY | base \| len<<16 | | |

A batch = LIBRARY, REGION + WINDOW per program, LOAD_CODE, LOAD_DATA per job, **one SUBMIT per job**, WAIT, SAVE (status and output of every job), then JUMP to the next batch's script (END with tag 0x600D after the last). Rules: jobs are submitted, never preempted; code/region changes are refused while jobs are in flight (error 7), which is why every batch ends in a WAIT.

**Where the width lives: the `lw` field of each SUBMIT step (4 bits, bits 8..11 of w2). So the format already holds one width per job, and a batch can mix widths.** (`crit`, bit 12, puts the job in the dispatcher's critical queue. Since #1406 the host can set it: `"crit": 1` in the job file, or `scblocks.py --crit wide`. The compiler is `jobcomp_v2.py` (a copy of `jobcomp.py` with the crit flag and the submit order; `jobcomp.py` is unchanged).)

**Submit order (the order of the SUBMIT steps inside a batch; since #1410 `scblocks.py --submit-order auto` is the default):** a batch whose jobs have different widths is submitted widest first (the dispatcher does not skip a head that does not fit, #1405), a batch of equal widths in the old order (identical image). `--submit-order kind` gives the old order for every batch, `width` always widest first. Measured on the card: wide-first 36,230 clocks against wide-last 51,962 (#1408, #1409).

Real example (4 jobs of `jobs_telemetry.json`: jobs 3, 2, 1, 0 given widths 3, 2, 0, 0; printed with `batch.decode`):
```
batches [[0], [1, 2], [3]]   (batch 0: the vgain job at lw 3; batch 1: crc32 at lw 2 and vprefix at lw 0 together; batch 2: vgain at lw 0)
script 0 at far 0x2000:  LIBRARY base=0 length=20 | REGION prog=0 cbase=20 clen=41 dlen=16 | WINDOW prog=0 base=0 length=208 | LOAD_CODE near=0 far=0x2090 count=61
                         LOAD_DATA near=0 far=0x20cd count=208 | SUBMIT tid=0 code=20 prog=0 lw=3 crit=0 | WAIT timeout_k=0xffff | SAVE near=4 far=0x238b count=2
                         SAVE near=108 far=0x2393 count=100 | JUMP far=0x2028
script 1 at far 0x2028:  ... SUBMIT tid=0 code=20 prog=0 lw=2 crit=0 | SUBMIT tid=1 code=58 prog=1 lw=0 crit=0 | WAIT ... (two SAVE pairs) | JUMP far=0x2068
script 2 at far 0x2068:  ... SUBMIT tid=0 code=20 prog=0 lw=0 crit=0 | WAIT | SAVE x2 | END tag=0x600d
```
Script 1 is a mixed batch: two jobs, widths 2 and 0.

## 6. Far RAM layout of one block's plan (`jobcomp.compile`)
scripts first (the sequencer reads them directly; the first is the entry, here 0x2000), then the code images and the window images, then the status block (2 words per job: status, n_out, in job order) and the results block (every job's output words, in job order, whichever batch ran it). Each block gets its own area (`scblocks.plan_blocks`); the areas do not overlap. The host loads the image over JTAG, starts the entry, polls the sequencer, reads status and results back, and checks them against the Python answer.

## 7. The profile file (`profiles/<name>.json`, format `sc_profile_v1`, `sc_calibrate_v1.py`)
`card` (version, slices, blocks, unit_lw, units, bitstream), `widths`, `speedup` (one job, per width), `at_once` (jobs running at once per width >= 1), `measured_best` (best width per job count that was run), `fit` (runs, files, max_err, mean_err), `lw0_clocks_per_word_crc32`, `raw` (the sweep: [length, jobs, [clocks per width]]), `note`, `date`. The raw sweep lines are saved next to it as `<name>.raw.txt`.

## 8. How the dispatcher places the jobs of a batch (read from `sc_sys_v17.v`, 2026-11-19, ledger #1405; READ from the code, not measured)
- A job of width w needs a free ALIGNED group of 2**w slices (start a multiple of the size). `BESTFIT = 1` (the default): it takes the smallest free aligned group that holds it, which keeps big groups free for wide jobs.
- Two queues: critical and bulk. The host sends every job as bulk today (`crit` = 0). The dispatcher takes the head of a queue; **if the head does not fit anywhere it does not skip it: it tries the head of the other queue once, then sleeps until a job finishes and frees slices.** So a wide bulk job at the head of the bulk queue with no free aligned group holds back every bulk job behind it ("head-of-line blocking"); the idle slices are counted by `waste_blocked` (idle slice-clocks while work waited) in the pool; whether the card's host link reads that counter was not checked.
- Critical jobs go first; after `GUARD` (8) critical launches in a row a waiting bulk job gets a turn; and after `MAXPASS` (8) bulk launches past a blocked critical head, bulk is held back so the critical job can get its group. This is the existing way to stop a wide job from being starved by narrow ones; nothing sets `crit` yet.
- **CORRECTION (#1415): `LONGEST = 1` in every card build** (the module default is 0, but `sc_top_k7_v10.v` and `sc_block_v3.v`, which all the card tops use, set 1; the n3 top does not override it). The bulk queue is 8 buckets by predicted duration: a class (program number in the batch and width) whose duration is not yet known goes to the highest bucket and is served first (to learn it), known ones follow longest first (whole octaves of the learned clocks: bucket = log2(duration) - 8, 0..6); the duration is kept per (program number, width) and is averaged with every new run (new = half old + half measured). **The learned values survive a reset (only a power-up or a reload of the bitstream clears them), so the clocks of a run can depend on the runs before it.** Earlier text in this section describing the bulk queue as plain first-in first-out is the cold state only.
- The order jobs reach the queue is the order of the SUBMIT steps: by (kind, job number) with `--submit-order kind`; by default (`auto`, since #1410) a batch with mixed widths is written widest first (then biggest window), as `--submit-order width` does for every batch. Alphabetical kinds put crc32 first, which is why the crc32-wide tests of #1394 and #1395 had the wide jobs at the front.

## 9. Not stored, not known
- Batch composition and the widths chosen by `--lw auto` are not saved anywhere; the plan output of `scblocks.py --plan` shows them.
- Not measured: the cost of head-of-line blocking on the card, and whether `crit` on the wide jobs or a wide-first submit order helps (test prepared in #1406: `order_test_v1.sh`).
- Measured since (#1408, #1409): wide-first submit order helps when a long wide job would otherwise be submitted last; `crit` on the wide job adds nothing on top of wide-first.
- Not in the hardware: reserved cores for critical jobs and preemption. A critical job is served first and can hold bulk back after MAXPASS launches; it cannot take slices from running jobs.
