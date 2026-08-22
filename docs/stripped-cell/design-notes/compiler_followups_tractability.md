# Compiler/frontend follow-ups — where each one actually sits on the tractable-to-open-research spectrum

*Short note, 2026-08-20. Captures a real distinction drawn out of a
speculative AI conversation (Gemini) Alan flagged honestly as
speculative -- not a build, a placement of two follow-up ideas
relative to each other and to what already exists.*

## What's already real and done

`nano/python_ast_frontend_v1.py` (`#348`, verified) parses genuine
Python syntax via `ast.parse()` -- but only a DECLARATIVE subset:
`place(...)` calls and `define(...)` blocks. Loops, conditionals,
variables, and arithmetic are explicitly rejected with real
diagnostics, by design. This is Python syntax used AS a DSL, not
Python-the-algorithm-language. Solid, finished ground.

## Two real follow-ups, genuinely different distances away

**Closer: lowering the carrier ABI directly to Verilog.** Already
captured as a real idea at `#405`
(`docs/stripped-cell/design-notes/icm_to_verilog_generator.md`) --
`IcmV3Record`'s own row/col + core + config already carries everything
needed to generate synthesizable Verilog wiring (instantiate
`unicell_super_v1` per cell, wire cardinal ports via grid adjacency,
exactly as `SuperGrid.neighbor_pos()` already does for VM simulation).
The real, honest gap `#405` already flagged: static SHAPE only, not
sequence-of-events stimulus -- but the shape-generation part is a
direct, mechanical lowering from data already sitting in a proven
format. Real engineering effort, not open research.

**Further: compiling arbitrary Python algorithms to spatial hardware.**
This is high-level synthesis (HLS) for spatial/dataflow architectures
-- a real, decades-old open research area well-funded EDA and academic
groups have worked on for years with partial, not complete, success.
Not a modest step past the existing declarative frontend; a different
category of problem. The real difficulty driver, worth stating
precisely since it's easy to misjudge: NOT vocabulary size (how many
keywords/builtins/stdlib functions exist) but CONTROL-FLOW complexity
-- loops, recursion, data-dependent branching. A three-line function
with a data-dependent loop is harder to compile to a spatial circuit
than fifty lines of straight-line arithmetic. Scheduling and
resource-sharing for arbitrary control flow is the actual open
problem.

**One piece of the HLS conversation that ISN'T speculative, worth
keeping separate:** running a phase, snapshotting results, reprogramming
the tree, and feeding results back in (to fit large programs into a
limited cell budget) rests on real, already-built capability -- the
incremental, ID-tagged reprogramming path and armed/COMPLETE marker
already exist. That idea is sound and buildable independent of
whether general HLS ever gets solved.

## Status

Not started, either one. Recorded so "declarative frontend, done" and
"general HLS, genuinely open research" don't get blurred together
later, and so the ABI-to-Verilog lowering is understood as the nearer,
more tractable of the two real follow-ups.
