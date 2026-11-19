# The S-Core shell (`score_shell_v1.py`): commands

Start: `python3 score_shell_v1.py` (plan and check need no card), or with the card: `nix shell nixpkgs#openocd --command python3 score_shell_v1.py`.
Type `help` inside for this list, `help COMMAND` for one command. Tab completes commands, kinds, settings and file names. With the optional package
`prompt_toolkit` the line is coloured as you type (known command green, unknown red, kinds cyan, numbers yellow, options magenta). `NO_COLOR=1` or `--plain` turns colour off.
Several commands on one line are separated by `;`. A line starting with `#` is a comment. Files of commands: `python3 score_shell_v1.py -f FILE.score`.

*This file is generated: `python3 score_shell_v1.py --write-help`. A test checks it matches the shell.*

## Jobs

### `add KIND DATA [arg=N] [lw=N|auto] [crit]`

add a job. DATA is numbers (hex ok) or `seq START COUNT STEP`. The expected answer is shown at once.
Examples:  add vsum 1 2 3 4     add vmax seq 5 80 3     add vxor 1 2 3 arg=255
Kinds: built in vsum vscale vstress; library crc32 vgain vmax vprefix vmin vxor vcount (brought in by themselves); or your own (register).

### `addbig KIND DATA [arg=N] [chunk=N] [lw=N] [crit] [combine=RULE]`

add a job whose data is longer than one job can hold (about 247 words at 256 shared words): the data is cut into pieces, each piece is an ordinary job, and run puts the answers back together and compares them with the answer for the whole data.
Examples:  addbig vsum seq 1 1000 1     addbig vgain seq 1 500 1 arg=128 chunk=60     addbig mymax seq 5 800 7 combine=max
For per-word kinds the answers are joined; for totals (sum min max xor or and) the totals of the pieces are totalled again; vprefix carries the running sum across. crc32 and recipes with diff / prefix cannot be split.

### `list`

the jobs typed so far, numbered.

### `show`

the jobs with the answers they should give (computed on this computer).

### `remove N`

delete job number N.

### `dup N [TIMES]`

copy job N (once or TIMES times) at the end of the list.

### `clear`

delete all jobs (registered programs stay).

### `new`

start again: no jobs, no registered programs.

### `save FILE.json`

write the jobs as a job file (the same format scblocks.py reads). Checks everything first.

### `open FILE.json`

read a job file (checks it) and replace the current jobs.

## Programs

### `programs`

the kinds you can use: built in, library, yours.

### `make NAME STEP... [then ENDING]`

build a NEW job kind from a recipe, no program to write. Steps: add sub xor and or shl shr (each with a number or arg) and not. Ending (optional): then sum|xor|or|and|min|max.
Examples:  make bump add 5 xor arg shl 1 then sum     make flip not     make top16 shr 16 then max
It writes the program and the right answer, checks both on the interpreter, and keeps the kind (programs/made/) for later sessions. A made kind is never changed: use a new name.

### `code KIND`

show the program (assembly) of a made, library or registered kind.

### `register NAME FILE.s [expect=module:function|iss] [out=N|same]`

make your own program a kind (see PROGRAMS.md). It is checked at once: assembles, fits, runs on the interpreter, agrees with your Python answer.

## Settings

### `settings`

the settings and their values.

### `set NAME VALUE`

change a setting: blocks, lw (0..4 | auto | none), order, profile, estimate on|off, margin, slices, unit-lw, port, out.
Example: set lw auto   set profile example_2x8_nu3_v2   set estimate on

## Run

### `plan`

what the host would do with these jobs and settings: batches, widths, submit order. No card needed.

### `run`

run the jobs on the card (needs the link; start the shell with `nix shell nixpkgs#openocd --command python3 score_shell_v1.py`), then compare with the right answers.

### `check RESULT.json`

compare a result file from the card with the right answers (run does this by itself).

### `profile [NAME]`

list the card profiles, or show one with its length model.

### `load`

how to load a bitstream (done outside this shell).

## Other

### `help [COMMAND]`

this list, or the help for one command.

### `quit`

leave (warns once if the jobs are not saved).

## Settings

| name | default | meaning |
|---|---|---|
| `blocks` | `1` | how many blocks of the card to use |
| `lw` | `none` | width for every job: 0..4 (2**lw slices fused), auto, or none (each job keeps its own) |
| `order` | `auto` | submit order inside a batch: auto, kind or width |
| `profile` | `none` | card profile (sc_calibrate_v1) for auto width, or none |
| `estimate` | `False` | on: choose a width per job from its length (needs profile and lw auto) |
| `margin` | `0.1` | the estimate keeps a mix of widths only if it beats the best single width by this much |
| `dsh` | `none` | shared RAM words per block of the build: none = ask the card on run (256 for plan); set it to plan for a bigger build |
| `far-words` | `none` | far RAM words (65536 on the block-RAM card build): set it to plan for a DDR3 build |
| `slices` | `none` | slices per block (only for plan with auto width; a real run asks the board) |
| `unit-lw` | `none` | log2 of the lanes of a fusion unit on the loaded build (3 on the 2x8) |
| `port` | `jtag` | the link to the card: jtag, or a serial device |
| `out` | `shell_results.json` | where run writes the results |

## A first session

```
add vsum 1 2 3 4
add vmax seq 5 80 3
show
save first.json
set blocks 1
plan
run          # with the card
```
