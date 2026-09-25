# Hex-N

**This branch is not intended to be merged into `main`.**

Hex-N is a separate project that shares lineage and some core concepts with
Imago UniCell, but is a distinct architecture with its own direction. It lives
on this branch for convenience (shared history, shared repo access) rather
than as a feature under development for UniCell itself. If GitHub prompts you
to open a pull request comparing this branch to `main`, that prompt can be
ignored — there is no plan to reconcile the two.

## What it is

A hex-cell neuron design: a 6-face cell, 16 individually-configurable
in/out lines per face (96 lines total), each line gated through one of four
selectable logic functions (AND / OR / XOR / NOT). Lines pair directionally
between neighbouring cells (an `out` on one cell wired to a matching `in` on
the next) rather than sharing a physical bidirectional wire, avoiding the bus
contention problems the original UniCell "full fat" cell design hit.

Each face accumulates its active input lines over a timer-gated window and
compares the result against a threshold to decide whether to fire — a trained,
frozen threshold rather than one that keeps adapting after deployment.
Feedback lines currently share the same accumulator as forward input
(simplest version, not separately weighted).

## Relationship to Imago UniCell

- Concept-linked: same "topology is computation" thinking, same style of
  cardinal/point-to-point wiring, same instinct to compose from small proven
  pieces before adding new hardware.
- Architecturally separate: different cell design, different resource profile
  (this is a heavier per-cell cost — closer to a small ALU than a pure logic
  mesh), different training method (discrete parameters — lane active/inactive,
  gate-per-lane, threshold — so evolutionary/genetic search or simulated
  annealing rather than backprop).
- Separate hardware target in mind: Tang Nano 20K (Gowin GW2AR-18), with a
  BL616-based link out to a front-end (originally scoped as an ESP32) over a
  direct GPIO link — see `esp32-bl616-link-protocol-v0.1.md` for that protocol
  draft.

## Status

Scoping stage. No RTL or VM work started yet — waiting on the Tang Nano 20K
board to arrive before BL616 firmware and cell design work begins in earnest.
