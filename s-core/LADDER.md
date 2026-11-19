# From one command to your own program: a ladder (S-Core)

Each step adds one idea to the step before it. Every step has the same three moves:

1. **Look first, no card needed:** `python3 ladder_show.py FILE.json` prints what the answers should be, and `python3 scblocks.py --plan FILE.json --blocks 1` prints what the host will do.
2. **Run on the card** (needs the card loaded, see step 0) and write the results to a file with `--out`.
3. **Compare:** `python3 ladder_show.py FILE.json RESULT.json` puts the card's numbers next to the right ones and says MATCH or DIFFERENT.

The card also prints `N of N jobs correct` by itself; the compare line shows you the actual numbers.

## Step 0: get the card ready (once)

```
cd ~/Imago-Unicell-score
git pull
cd s-core
```

Load a build (from the openXC7 shell). Any build with the pool works for steps 1 to 3 and 5; step 4 needs a fusion build, so load this one for all steps:

```
cd ~/openFPGALoader/build/demo-projects/sc_k7_sizes
openFPGALoader -c ft232 sc_k7_fu2s8u8n3.bit          # expect "done 1"
cd ~/Imago-Unicell-score/s-core
```

## Step 1: the simplest run, one job

The job file `ladder_1_one_job.json` is one line: add up 1, 2, 3, 4.

```
{"jobs": [ {"kind": "vsum", "inputs": [1, 2, 3, 4]} ]}
```

```
python3 ladder_show.py ladder_1_one_job.json                      # should be [10]
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_1_one_job.json --blocks 1 --out r1.json
python3 ladder_show.py ladder_1_one_job.json r1.json              # card: [10]  MATCH
```

What you learn: a **job** is a kind (`vsum`) and some data (`inputs`). `--blocks 1` uses one block of the card.

## Step 2: several jobs, different kinds, one file

`ladder_2_three_jobs.json` has three jobs: `vsum` (adds up), `vmax` (largest), `vprefix` (running total). `vsum` is built in; `vmax` and `vprefix` are programs from `programs/` that the file names in its `"programs"` part.

```
python3 ladder_show.py ladder_2_three_jobs.json
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_2_three_jobs.json --blocks 1 --out r2.json
python3 ladder_show.py ladder_2_three_jobs.json r2.json
```

You should see 60, 99 and `[1, 3, 6, 10, 15]`. What you learn: different programs go into one batch and the host packs them (`--plan` shows "3 jobs (vmax vprefix vsum)" in one batch).

## Step 3: more data

`ladder_3_more_data.json` uses `{"seq": [start, count, step]}` to make a list without typing it: `[1, 100, 1]` is 1, 2, 3 ... 100. Four jobs: sums and maxima of 60 to 100 numbers.

```
python3 ladder_show.py ladder_3_more_data.json                    # 5050, 134650, 242, 9649
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_3_more_data.json --blocks 1 --out r3.json
python3 ladder_show.py ladder_3_more_data.json r3.json
```

What you learn: the jobs no longer fit the card's memory in one go, so the host splits them into two batches by itself (`--plan` shows `batch 0` and `batch 1`). You do nothing.

## Step 4: how wide (how many slices work on one job)

Same file, three ways. The card prints the time in clocks (`block 0: ... clocks = ... ms`):

```
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_3_more_data.json --blocks 1 --unit-lw 3 --lw 0
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_3_more_data.json --blocks 1 --unit-lw 3 --lw 2
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_3_more_data.json --blocks 1 --unit-lw 3 --lw auto --profile example_2x8_nu3_v2 --estimate
```

`--lw 0` is one slice per job, `--lw 2` is four slices fused per job, the last lets the host choose. **Run each twice and compare the second run:** the first run after a load is slower (ledger #1417). The answers are the same in all three; only the time changes.

## Step 5: your own small program

`programs/vcount.s` counts how many inputs are bigger than a number you give with the job (`arg`). It was made from `vmax.s` by turning the "biggest so far" into a counter. Three jobs in `ladder_5_my_program.json`:

```
python3 ladder_show.py ladder_5_my_program.json                   # 3, 0, 50
nix shell nixpkgs#openocd --command python3 scblocks.py jtag ladder_5_my_program.json --blocks 1 --out r5.json
python3 ladder_show.py ladder_5_my_program.json r5.json
```

The job file names the program and its Python answer:

```
{"programs": [ {"name": "vcount", "source": "programs/vcount.s",
                "expect": "programs.examples_v3:vcount_ref", "out": 1} ], ... }
```

**Make your own (the real step 5):**

1. Copy it: `cp programs/vcount.s programs/mine.s`.
2. Change one thing, for example make it count the inputs that are **smaller** than `arg`: in the loop, swap the comparison `bgeu t5,t0,skip` for `bgeu t0,t5,skip` (see `PROGRAMS.md`, section 4, for why).
3. Write the Python answer next to the others, one line: `def vcountless_ref(inputs, arg, out_len): return [sum(1 for x in inputs if x < (arg & 0xFFFFFFFF))]`.
4. Copy `ladder_5_my_program.json`, change the name and the `source`/`expect` to yours.
5. Run `python3 ladder_show.py` and `--plan` on it first. If the program breaks a rule the host says so at once, before the card.

## Where next

`PROGRAMS.md` explains the five parts of a program and the rules of the core. `README.md` has the rest (calibration, the estimate). The files of this ladder: `ladder_1_one_job.json`, `ladder_2_three_jobs.json`, `ladder_3_more_data.json`, `ladder_5_my_program.json`, `ladder_show.py`, `programs/vcount.s`.
