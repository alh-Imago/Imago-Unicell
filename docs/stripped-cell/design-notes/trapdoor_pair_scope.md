# Trapdoor pair core -- scoping note (Alan / Claude, 10 Oct 2026)

*Scope only. Nothing is designed or built. Written from reading the notes named below; where something is a guess it says so. The Onion archive has NOT been searched for this yet (the working rule says to do that before any build).*

## The idea (Alan, 15:13 and 15:16, 10 Oct 2026)

A special core that has the same cardinal (N/S/E/W) routing as every other cell and can also tap the command connection: a trapdoor. It sends data to a set point, receives data from one, and passes what it gets out through its cardinal faces. It comes as a PAIR and is strictly time-controlled. One pair can use the command bus directly because nothing else is using it. More than one pair must be time-division controlled (a fixed schedule), and the host's own control traffic uses the same bus, so the host needs a slot too.

## What problem it answers

Data in this system moves only between neighbours, in order, with a handshake. Moving a word between two distant cells means relays across the grid, and there is no addressing to reach a far cell directly. The objection raised (by Alan's son) was that the system is hard to feed and read as a memory. The trapdoor pair would be a deliberate, rare, scheduled shortcut: loading a table, saving or restoring state (see addendum 53), reaching a distant RAM cell. It is not meant for streaming.

## What already exists (read, not run)

- **Full-cell line.** The full cell has an addressed command bus. A cell with `is_command_cell` (`cmd_latch[10]`) drives its stored command word onto the command bus, targeted by `output_address`, instead of a gate result onto the data bus (`docs/full-cell/CELL_INTERNALS.md`, "Command-emit cells"). That is already a one-way trapdoor for commands.
- **Stripped-cell line (the Tang flex and sub cells descend from it).** Addressing is "deliberately absent, not merely disabled"; configuration comes through `cfg_valid` / `cfg_data` and the ID-tagged program path (`docs/shared/SYSTEM_MECHANICS.md`). `command_cell_v4.v` drives one fixed direction, exactly one of N/S/E/W (ledger #881). So **on the Tang there may be no command bus to tap in the sense the full cell has**. Whether the trapdoor means "reuse an existing bus" (full-cell and carrier lines) or "add a small shared channel" (Tang) is the first open question.
- **Prior art on the same problem** (`archeology/full-cell/docs/design-notes/tiled_interconnect.md`, read in full; `island_hierarchy_interconnect.md`, read in full):
  - A single shared bus carries one emission per cycle; two cells firing in the same cycle collide. A timed or serialised shared bus and per-cell arbitration are listed as dead ends **when that bus carries the fabric's traffic**.
  - The island note keeps a global bus but gives it a new role: it carries only sparse inter-island bridge traffic, not compute. That is close to what the trapdoor pair would do, and it states the condition for it to work: crossings must be sparse.
  - Staggering by time (modulo scheduling) is described as the time-axis version of separating by space.
  - Reachability is a security matter. In the tiled note, creating a NEW connection between tiles is the high-authority act, and a tile may not grant itself one; the pond grants it. A trapdoor creates reachability between two distant cells, so by that rule the pair would be set up by the host or pond layer, never by the cells.

## Open questions

1. Which line first: the carrier line (command bus exists), or the Tang flex line (no addressed bus; a new shared channel or a use of the config path)?
2. How is a pair formed and addressed? Fixed at load time (simplest, deterministic) or configurable?
3. What is the schedule? One slot table fixed at compile time, with a reserved host slot. How many pairs per table, and what does each pair's share of the bus give in words per second?
4. Handshake: the flex cells use ack and freeze. Does a trapdoor word wait for ack like any other item, and what happens if the far end is not ready in its slot?
5. Interaction with freeze (addendum 53): can a frozen cell still send or receive on its slot, and could state save and reload use trapdoors?
6. Does it fit the tile model as a bridge, so it can be described with the existing words?
7. Cost: extra logic per cell (a bus tap and a slot counter) against what it saves in relay cells. Nothing measured.

## Decision (Alan, 10 Oct 2026, 15:20): flex first

Question 1 is settled: design it in the **flex family** (v4sa) first, because it is easier. Alan is not sure it fits the **sub** family (v4s), which has no timing control (no ack handshake and no freeze), and a trapdoor pair depends on time control. My reading, as an inference and not checked against the sub RTL: the flex cells' ack and freeze give a pair a way to wait and to stop, which the sub cells lack; whether the sub family could carry a trapdoor with a purely fixed schedule is left open and is not part of the first design. The carrier line stays a later question.

## Revision (Alan, 10 Oct 2026, 15:23 and 15:26): on the Tang it is a "programmed corridor"

On an FPGA the JTAG load goes through the vendor's configuration logic, which the cells cannot reach, so the Tang has no real command bus for a trapdoor to tap (the flex designs are programmed by constants fixed at synthesis plus one shared `cfg_valid` pulse). Alan's answer: how this works differs by card and manufacturer, which is why the card's `.man` file matters, and on the Tang, and realistically on the sub family, the trapdoor becomes **a specified part of the design: a programmed corridor**, a dedicated point-to-point path between the two cells of the pair.

What that changes, as I understand it (an inference, to be checked):
- **No shared medium, so no contention and no time slots.** The time-division schedule, the host slot and the arbitration questions above apply to a real shared bus (the full cell, the silicon) and not to a corridor.
- **Many corridors are possible.** Each is its own wire path, so they do not share capacity.
- **The price is timing.** A longer corridor means longer wires and a longer delay; each one can slow the whole design (a lower maximum clock) if it is not broken up with register stages, and registers add ticks of latency. Nothing is measured; the cost per corridor length on the Tang is a number to get from place-and-route, not to guess.
- **The sub family may fit after all.** A corridor needs no timing control, only a fixed, known latency. Whether it fits is still to be checked against the sub RTL.
- **It is declared in the design, per card.** How a corridor is written down (in the design description, the assembler input or the card's `.man` file) is open.

The earlier sections (a time-controlled pair on a shared command bus) stay as the description of the bus-based version for the full cell and silicon.

## Out of scope for this note

The design, any RTL, a VM model, a throughput figure, and a claim that this beats relays. None of that is known yet.

## Suggested next steps (when Alan wants them)

1. Search the Onion archive and the points ledger for earlier pair or sideband-bus constructions (the working rule).
2. Settle question 1 with Alan.
3. Only then a design note, and a VM model before any RTL.
