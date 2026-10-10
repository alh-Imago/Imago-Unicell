# Learning how computers work, using UniCell as the backdrop

> **Status (10 October 2026): a plan, not a course yet.** Nothing here is finished or tested with real learners. The design of UniCell is frozen and is not being extended for this. The main manual (`docs/manual.html`) stays the manual for UniCell itself; this folder is the separate teaching side.

## The idea

Most people meet computing as a finished thing: a screen, an app, a black box. This folder tries the opposite. It starts from one tiny part and builds upward, so you can watch why logic works the way it does, why timing matters, and why moving data costs something.

UniCell suits this because nothing is hidden. A program is a small grid of cells wired to their neighbours. Each cell does one simple thing. Values move one hop at a time, so you can pause, step forward and look.

UniCell is the **backdrop**, not the subject. Each lesson teaches a general idea first (why one kind of gate is enough, why carry is the hard part of adding). UniCell is just the way to see it. You do not need to care about the architecture to follow along.

## What you can see

The tools already exist and are not being changed:

- **The composer** places cells on a board, sets what each one does, joins them, and steps a design tick by tick while showing every value. Start it with `python3 quickstart.py --composer`.
- **The VM** runs the same designs in Python, so nothing needs hardware.
- **The nano cell** (the flex version) is the starting point. Inside it are ten NOR gates, named `g0` to `g9`, and a setting that picks which one's output comes out. A magnified view that draws those ten gates with live values would be the one new piece worth building, and it would only display what is already there.

## The lesson ladder (proposed)

Each rung is one small circuit, one page of plain writing, and one thing to try. "Checked" means it was run on 10 October 2026 from Python (the step simulator, not the browser page).

1. **One NOR gate.** Why a single kind of gate is enough. *Checked:* the gate core gives the right truth tables for NOR, NOT, OR, AND, NAND, XOR and XNOR.
2. **Making other gates from NOR.** NOT, OR, AND and XOR are all built from the same ten NOR gates inside the nano cell. *Checked:* AND and XOR built by hand in the composer layout gave correct results at width 1.
3. **Waiting for both inputs.** A cell fires only when its second input arrives; the first is held. *Checked:* if both arrive on the same tick, nothing comes out and nothing complains. This is a good lesson and a trap, so every lesson needs to say it.
4. **Moving data costs time.** *Checked:* the library adder took 18 ticks to return 7 + 5 = 12, mostly because values walk through relay cells.
5. **Combining in parallel.** The reduction tree. *Not yet checked in the step viewer.*
6. **Remembering and sequencing.** Memory and the sequencer. *Not yet checked.*
7. **Numbers that are not whole.** The floating-point adder. *Not yet checked, and the library version (1,712 cells) is too big to start with.*

## What this does not claim

- UniCell was tested against hand-written hardware and did not come out ahead (see `docs/measurements/UNICELL_VS_PURE.md`). Teaching with it does not change that.
- Some designs have run on the Tang Nano 20K board. Lessons may say "this also ran on a real board" only for those, and only where the repo's ledger says so.
- The step viewer was checked from Python. It still needs trying in the browser with someone who has never seen the project.

## Next steps

1. Check rungs 5 to 7 and the hierarchical example files in the step viewer.
2. Write rung 1 as a full lesson and show it to one or two people who do not know the project.
3. Only if that goes well, decide whether the magnified cell view is worth building.
