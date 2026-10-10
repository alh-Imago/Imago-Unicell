# points.md — ACTIVE part (currently entries #1037 onward)

**This is the real, currently-open tail of the single, canonical
points.md ledger — the file new entries get appended to.** Split
across multiple files purely because GitHub won't render a file over
~512KB in the browser (the single combined file had grown past 2MB);
no entry content was changed, reworded, or reordered. See `points/
INDEX.md` for the full real map of which part holds which entries,
and `points.md` (repo root) for the short, canonical pointer every
session should still start from.

**Naming convention, for future-me:** this file keeps the stable name
`points_active.md` (no entry range in the filename) for as long as
it's still being appended to, so appending never requires a rename.
Once it approaches ~350KB, seal it — rename to `points_NN_XXX-YYY.md`
with its real final range, start a fresh, empty `points_active.md`
for continued work, and add the sealed file's own row to `points/INDEX.md`.

---

## #1037 -- THE LEDGER IS SEALED THROUGH #1036 (part 12), AND A TEACHING USE FOR UNICELL IS PLANNED (Alan's decision, 10 Oct 2026, evening)

**The seal.** Alan: "close out the points and start a new one." `points_active.md` (349,195 bytes, #946-#1036 with addenda 1-69 under #1036, 90 distinct entry numbers) is now `points_12_946-1036.md`, and this file starts fresh at #1037. Proof it is lossless: everything after the part's header line is byte-for-byte the body of the old active file (body 348,209 bytes, sha256 `3c5103d996292ef1141a9e2a717817514417e7029f7e4d5859bd57391434308f`; the old whole file was sha256 `e8a1c2a9a1afe0b13e6c090b1148a438250352f0918f5e31fd68f5770314a243`). Only a header was added, in the same words as the earlier parts. The old file is also recoverable from git (the commit before this one). Numbering notes for this range, recorded and NOT fixed: #990 physically follows #991-#998 (already recorded in the INDEX); #1002 was never used (recorded in #1003 and #1006); the heading style drifts between `##`, `###` and bold paragraphs, so the INDEX's `grep '^## N\.'` finds only some of them.

**The decision.** After the close-out of 10 Oct (addendum 69), Alan asked whether the project could have a second life as a teaching aid rather than a platform: showing logic, timing and routing, and refocusing some of the work that way. He said plainly that the design is complete and is not to be added to; the existing tools (the composer and the VM) and the cell-like structure are to be used to teach computing from the base up, with UniCell as the backdrop rather than the subject. He chose the flex nano as the cell to use, and said a magnified view that exposes everything inside a cell may be needed. He asked for a simple intro, a change to the README, and the main manual left as it is, because it is specifically for UniCell itself; the teaching side needs its own separate documents.

**What was checked (read-only, run from Python on 10 Oct 2026; not run in the browser page).**
- The step simulator (`tools/flex_layout_sim_v1.py`, the composer's step-through) runs the library adder: 7 + 5 = 12, output at tick 18, settled after 21 ticks, because the values walk through relay cells.
- The flex nano (`sub/verilog/nano_cell_v4sa.v`) is ten NOR gates, `g0` to `g9`, with a `topology` setting that only selects which one's output comes out, plus a held operand, an output buffer and `armed`/`pending`/`ack` flags. `nano/unicell_gate_core.py` (`_gate_tree`) already returns `g0`-`g9` for any inputs, so a magnified view could show all ten with live values and change nothing in the design.
- The gate core's truth tables are right for NOR, NOT, OR, AND, NAND, XOR and XNOR (width 1).
- A nano between three `ram` port cells in the composer layout gave AND = 0,0,0,1 and XOR = 0,1,1,0 at width 1 when the two operands arrive one after the other. If both arrive on the same tick nothing comes out and nothing reports an error: the first arrival is held and the second triggers the gate. `hold_in` on a flex nano is refused at width 1.
- NOT YET CHECKED: the two hierarchical example files (relay chain, reduction tree) in the step viewer; the sequencer and ram state; the floating-point adder as a lesson (1,712 cells, probably too big to start with); whether the VM exposes the nano's `armed`/`pending`/`ack` flags; the whole thing in the browser with a person who has never seen the project.

**What changed (documents only; no design, test or tool touched).** New `docs/teaching/README.md`, a plain intro with a proposed seven-rung ladder (one NOR gate, other gates from NOR, waiting for both inputs, moving data costs time, combining in parallel, remembering and sequencing, non-whole numbers), each rung marked checked or not yet checked, and a "what this does not claim" section. One paragraph added to the root `README.md` under the status banner, saying this is a plan only and does not change the status. Pushed to main as `bd26c2c`. Then this seal: `points/INDEX.md`, the root `points.md` pointer, `current/START.md` (two catch-up lines), `CLAUDE.md` (the ledger line), and `current/latest.md`.

**Deliberately NOT done.** `docs/manual.html` was not rebuilt, at Alan's instruction. `README.md` is one of the manual's inputs (`docs/build_manual.py`), so the manual is now one paragraph behind the README until someone rebuilds it; `CLAUDE.md` says to rebuild after editing such a doc, and Alan's instruction takes precedence. The magnified cell view and any lesson text beyond the intro are not built. The GitHub archive setting, the public gh-pages site and the other items left open in addendum 69 are unchanged and still Alan's call. This entry does not alter the status in addendum 69: UniCell is still an unconfirmed idea, and the teaching use claims nothing about it that the measurements do not support.

---

## #1038 -- A SEPARATE TEACHING MANUAL BUILDER (Alan's decision, 10 Oct 2026, late evening)

Alan, on the manual: leave the main manual as it is, clone its build so it writes a separate teaching manual, same style, slightly different content, and use the newer file from here on. Done as a clone, not a change: `docs/build_teaching_manual.py` is `docs/build_manual.py` with the same renderer, page and style, but its own `SECTIONS` list (two tabs for now: the teaching plan `docs/teaching/README.md`, and the repository `README.md` as "The Backdrop") and its own output, `docs/teaching_manual.html`. The output sits beside `manual.html` on purpose, because the builder's link rewriting assumes the output is exactly one level below the repo root. The headings and page title say "Teaching Manual" instead of "Field Manual". To add a lesson, write it as markdown, add one dict to `SECTIONS`, and re-run `python3 docs/build_teaching_manual.py` (the file's docstring says so).

Checked: it builds (2 sections, 56,709 bytes), the page has 2 tabs and 2 panels, no "Field Manual" text remains, and the rewritten links point one level up as in the main manual. `docs/build_manual.py` and `docs/manual.html` are byte-identical to before. NOT checked: how the page looks in a browser; I read the generated HTML only. The main manual is still one paragraph behind the README (see #1037); that is unchanged and still Alan's call. No lessons exist yet beyond the plan, so the teaching manual is a frame, not a course.

Next entry: #1039.
