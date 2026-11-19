# Writing your own program for S-Core (a plain guide)

A **job** is one program plus one set of data. The programs that come with the host (crc32, vsum, vgain, vmax, vprefix, vscale) need no writing: you name the kind and give the data. This guide is for the other case, a program that is not in that list.

You never write a whole program from nothing. You **copy a working one and change the part that computes**. Everything around it (reading the inputs, finding the output area, reporting that the job finished) stays the same.

## 1. The five parts of every program

Every program in `programs/` has the same shape. `programs/template.s` is the empty version with comments; `programs/vmax.s` is a real one.

| part | what it does | you change it? |
|---|---|---|
| 1. `push ra` | saves the way back (the library is called from `main`) | no |
| 2. `call lib_io_in` | asks "where are my inputs and how many?": address in `a0`, count in `a1` | no |
| 3. `call lib_io_out` | asks "where do I write my answers and how many fit?" | no |
| 4. the loop (`loop:` ... `j loop`) | takes the inputs one at a time | **this is where your idea goes** |
| 5. `call lib_io_done` / `lib_io_fail`, `pop ra`, `ret` | reports "finished OK" or "refused", returns | no |

If your program does not fit in the loop (it needs a different shape), copy the nearest example instead of the template: `vmax.s` is the shape for "many inputs, one answer", `vprefix.s` and `vgain.s` for "many inputs, many answers".

## 2. The rules the core imposes

Check these before you write; the host checks them again before anything reaches the card.

| rule | why |
|---|---|
| Only the basic RV32I instructions: add, sub, and, or, xor, shifts, compare, branches, `lw` / `sw` | that is what the core has |
| **No multiply, no divide** | the core has none (`vgain.s` multiplies by shifting and adding) |
| **Word loads and stores only** (`lw`, `sw`): no `lb`, `lh`, `sb`, `sh` | the shared memory is word-wide |
| Touch only your window (the inputs and outputs) and your own small stack | anything else is a trap on the board |
| Keep your own values in `t2..t6` and `a2..a7`; the four library calls change only `t0 t1 a0 a1` | otherwise the library overwrites your values |
| All the programs of one batch together fit in about 100 instructions | the code store is 128 words including the library |
| `main` ends with `ret` and gives back 1 in `a0` for "ok" (the example programs do `li a0,1`, or the number of words produced) | the host reads the status |

The job's extra number, `arg` (one 32-bit word per job), is read from word 6 of the header: `li t0,0x10000` then `lw t5,24(t0)`. `vgain.s` and `vxor.s` do this.

## 3. A worked example: `vmax.s`, line by line, in words

```
main:
  push ra                  # save the way back
  call lib_io_in           # a0 = where the inputs start, a1 = how many
  mv t2,a0                 # t2 = pointer into the inputs
  mv t3,a1                 # t3 = how many are left
  li t4,0                  # t4 = the biggest so far (start at 0)
loop:
  beqz t3,fin              # none left: go to the end
  lw t0,0(t2)              # t0 = the next input word
  bgeu t4,t0,skip          # if the biggest so far is at least this one, keep it
  mv t4,t0                 # else this one is the new biggest
skip:
  addi t2,t2,4             # move the pointer to the next word
  addi t3,t3,-1            # one fewer left
  j loop                   # round again
fin:
  call lib_io_out          # a0 = where my answer goes, a1 = how many answers fit
  beqz a1,bad              # no room at all: refuse
  sw t4,0(a0)              # write the answer
  li a0,1                  # tell the library I produced 1 word
  call lib_io_done         # finished OK
  li a0,1                  # my own return value: ok
  j end
bad:
  li a0,2                  # error code 2 = output area too small
  call lib_io_fail
  li a0,0
end:
  pop ra                   # get the way back
  ret
```

## 4. Making a new program from an old one: `vmin.s`

`vmin` (the smallest input) was made from `vmax` by changing **two things**:

1. the start value: `li t4,-1` (all ones, the largest possible word) instead of `li t4,0`;
2. the comparison: `bgeu t0,t4,skip` (input not smaller than the best, keep the best) instead of `bgeu t4,t0,skip`;

plus one line for the empty case (`beqz t3,none`, answer 0). The whole change is three lines; the other twenty-odd are the same as `vmax`.

`vxor` (each input XOR the job's `arg`) was made from `template.s`: the `YOUR CODE` line became `xor t0,t0,t5`, and four lines at the top read `arg` into `t5`.

## 5. The three steps to use a new program

**Step 1: write the program** as a `.s` file in `programs/` by copying one of the above.

**Step 2: write the answer you expect, in Python, one line.** The host uses it to check the card's result. For `vmin`:

```python
def vmin_ref(inputs, arg, out_len): return [min(inputs) if inputs else 0]
```

(If you cannot write it, use `"expect": "iss"`: then the host only checks that the card did what the instructions say, which proves the card is right, not that your idea is.)

**Step 3: name it in a job file.**

```json
{"programs": [ {"name": "vmin", "source": "programs/vmin.s",
                "expect": "programs.examples_v2:vmin_ref", "out": 1} ],
 "jobs": [ {"kind": "vmin", "inputs": [900, 42, 17000, 42, 5]} ] }
```

`out` is how many answer words to reserve: a number, or `"same"` for as many as inputs. Then the same commands as for any job file:

```
python3 scblocks.py --plan jobs_own_examples2.json --blocks 1        # what the host will do, no card needed
python3 scblocks.py jtag jobs_own_examples2.json --blocks 1          # run it on the card
```

When the file is loaded the host already checks, with no card: the program assembles, fits the code store, runs on the host's interpreter and finishes with status 1, and agrees with your Python answer. A program that breaks a rule is refused with a message at that point, before it goes near the card.

## 6. What the host then does for you

Once registered, your program is a job kind like the built-in ones: it can be batched with other kinds, split over blocks, and given a width automatically (`--lw auto --profile NAME --estimate`). The estimate counts your program's instructions on the host, so a new program is sized without being measured. It assumes your program runs at the same clocks per instruction as crc32 (133.5) unless its own value is measured; the four library kinds have measured values (`python3 lengthest_v1.py show --profile NAME`), a new program does not yet (ledger #1411, #1412).

## 7. The examples in the repository

| program | file | answers | made from | answer in Python |
|---|---|---|---|---|
| copy (template) | `programs/template.s` | as many as inputs | (the empty template) | `"expect": "iss"` |
| vmax | `programs/vmax.s` | 1 | | `examples.py: vmax_ref` |
| vprefix (running total) | `programs/vprefix.s` | as many as inputs | | `examples.py: vprefix_ref` |
| vgain (gain by shift and add; uses `arg`) | `programs/vgain.s` | as many as inputs | | `examples.py: vgain_ref` |
| crc32 | `programs/crc32.s` | 1 | | `examples.py: crc32_ref` |
| **vmin** (new, #1418) | `programs/vmin.s` | 1 | vmax, 3 lines changed | `examples_v2.py: vmin_ref` |
| **vxor** (new, #1418; uses `arg`) | `programs/vxor.s` | as many as inputs | template, 1 line + `arg` | `examples_v2.py: vxor_ref` |

Job files: `jobs_own_example.json` (vmax, vprefix, copy), `jobs_own_examples2.json` (vmin, vxor). Tests: `python3 test_progs.py`, `python3 test_own_examples_v1.py` (no board); `python3 test_ownprog_sim.py FILE.json` runs the whole board in simulation (needs iverilog).

## The short way: `make` (no assembly)

If what you want is "do this to every word, and maybe add them up", you do not need to write a program. In the shell:

    make bump add 5 xor arg shl 1 then sum
    add bump 1 2 3 arg=255

Steps: `add sub xor and or shl shr` (each with a number or `arg`, the job's own arg) and `not`. Ending (optional): `then sum|xor|or|and|min|max` gives one word out; without an ending you get one word out per word in. All arithmetic is 32-bit and wraps; `shr` is a logical shift; a shift by `arg` uses its low 5 bits; a summing-up over no inputs gives 0.
`make` writes `programs/made/NAME.s` (the program), `NAME.py` (the right answer) and `NAME.json` (the recipe), checks the program on the interpreter against the right answer (12 runs, 0 to 17 words, random data and args), and keeps the kind for later sessions. A made kind is never changed (use a new name for a new recipe). `code NAME` shows the program; you can copy it and edit it by hand as in the sections above. Anything that is not "the same steps on every word" (loops that depend on neighbouring words, tables, early exit) still needs a hand-written program.

### More steps in `make` (ledger #1428)

Besides add sub xor and or shl shr not, a recipe can use: `min N` / `max N` (clamp, unsigned), `gt N` / `lt N` / `eq N` / `ne N` (the word becomes 1 or 0), `rol N` / `ror N` (rotate), `sra N` (shift keeping the sign), `mul N` (a number built from shifts and adds, at most 12 shifts and adds; `mul arg` is a slow loop), `diff` (this word minus the one before it, at that point of the recipe), `prefix` (running total). Start a recipe with `pair OP` to work on two arrays: the data is two equal halves a and b and the recipe starts from `a[i] OP b[i]` (an odd last word is ignored), e.g. a dot product: `make dot pair mul then sum`. Compares and min / max are unsigned. A recipe can have one `diff` and one `prefix`, and constants that need a register are limited to 6 minus the extra state used (the shell says so if there are too many).

### Data longer than one job holds: `addbig`

A job has at most 247 data words at 256 shared words (all the jobs of a batch share that RAM). `addbig KIND DATA` cuts longer data into pieces, each piece is an ordinary job, and after `run` the shell combines the pieces' answers and compares them with the answer for the whole data. Per-word kinds are joined; totals (sum min max xor or and) are totalled again; `vprefix` carries its running sum from piece to piece. crc32 and recipes with `diff` / `prefix` cannot be split. `chunk=N` sets the piece size (default about a quarter of the shared RAM); `combine=RULE` says how the answers of a kind the shell does not know combine.

