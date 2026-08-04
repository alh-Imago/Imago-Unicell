# Security, Portability & Licensing — design note

Status: DESIGN / reasoning trail (2026-06-28). Captures the layered model so the
loader/format work builds to a settled spec. Honest current-state recorded; most of
this is horizon (full-hardware era), with ONE near-term buildable piece called out.

The governing tension: the portable-`.icm` invariance claim (same file runs byte-identical
across VM/FPGA/silicon) and a real security model must REINFORCE each other, not trade off.
They do — IF integrity, authenticity, authorisation, and licensing are kept as SEPARATE
layers with different keys and different homes. Conflating them breaks portability.

## Current state (honest)

program_builder.py `_write_image` computes `hashlib.sha256(json_text)` and RETURNS it
(into the ProgramImage object + log) — it is NOT written into the `.icm`, and `load_image`
does NOT verify it. So the integrity LOOP is not closed: a hash is computed and discarded.
It also hashes JSON TEXT (whitespace/`_note`-sensitive), not the packed records.
controller.py has a `_machine_key` (64-bit, SHA'd for a machine-key id) — the keystore
concept exists. So: foundation present (a SHA call, a machine key, atomic write); the
enforcement loop and the right hash-input are missing.

## REJECTED: machine-keyed HMAC as the file's integrity field

First instinct was HMAC the file with the machine key. REJECTED — it breaks sharing: a
file made on machine A won't verify on machine B (B lacks A's secret), killing the
community/portability story. A secret-keyed check is only verifiable by secret-holders,
so it cannot be the PORTABLE integrity field. (It survives only as the local authorisation
layer below, where local-only is the point.)

## The four layers (opt-in by trust level; only the bottom is machine-bound)

1. INTEGRITY — "has this file been altered since it was made?"
   Universally verifiable by ANYONE on ANY machine. => PLAIN HASH (SHA-256) over the
   CANONICAL PACKED RECORD STREAM (the `(cmd_bus, cmd_data)` sequence the loader emits),
   with auth bits zeroed and the hash field excluded from its own input. Lives IN the file.
   Community-safe: download, recompute, know it arrived intact. This is the portable layer.
   *** This is the one NEAR-TERM buildable piece: close the loop in program_builder.py —
   hash the records (not text), embed in the .icm, verify on load, hard-REFUSE on
   missing/malformed/mismatch (all three identical, no warn-and-continue). ***

2. AUTHENTICITY — "did this really come from this author, unaltered?"
   Portable AND provenance-bearing. => ASYMMETRIC SIGNATURE (NOT HMAC): producer signs
   with a private key, ANYONE verifies with the producer's PUBLIC key. Publicly verifiable
   => still portable. Foundation of a trusted shared library: verify provenance without
   trusting every uploader. Optional, opt-in per file.

3. AUTHORISATION — "is this file allowed to RUN on MY system?"
   Inherently LOCAL and secret-keyed — only my system answers it, with my key, at MY
   loader, at load time. NOT stored in the file (so it never blocks sharing — it was never
   part of the artifact). This is the local keyed gate; this is where the machine key lives.

4. LICENSING (hard lock) — boot-ROM root of trust. See below.

## Layer 4: boot-ROM 64-bit key — the hard licensing lock (full-hardware era)

Early spec, for the FULL hardware system (boot ROM built into the backplane, local + server
systems). The ROM has several jobs; one is a 64-bit key FUSED into it, UNREADABLE by anything
but the ROM itself, with the ROM as the gateway all loads/unloads pass through.

Flow: purchase -> download the PORTABLE file (you're entitled to) -> the ROM SEALS a
machine-local LICENSED file using its fused key -> only THIS machine can load that copy.

KEY CONSISTENCY POINT (this is what stops it collapsing into the rejected HMAC trap):
licensing produces a DIFFERENT FILE, not a different hash on the same file. The portable
`.icm` keeps its plain hash (+ optional signature), travels freely, verifies anywhere —
UNTOUCHED. The licensed copy is a downstream, ROM-sealed, machine-bound DERIVATIVE. Share
the portable original all you like; the licensed copy is inert elsewhere; the original was
never locked. Portability preserved; the lock lives in a separate sealed artifact + the ROM.

Trust spectrum, opt-in: community (plain hash, runs anywhere that accepts community files)
-> signed (adds portable provenance) -> licensed (ROM-sealed local derivative, zero
portability BY DESIGN — the point, for paid/private content).

### Two hardware caveats to confirm against the device (cheap now, brutal to retrofit)
- UNREADABLE must be real at silicon level: fused, NO register read-back path, ROM uses it
  only internally. "A register the ROM promises not to expose" is NOT a root of trust. On
  Arria 10 this leans on device security features, not pure RTL — know early what the part
  offers.
- PERMANENCE across the volatile-config reality: the GX660 reloads its bitstream every power
  cycle. The ROM + key must be authoritative ACROSS reflashes, not evaporate with the SRAM
  config. If the key's permanence depends on the volatile fabric, it is not a root. Answer
  "where does the root actually live" before the spec hardens.

## Consequence: PARTIAL / FEATURE LICENSING (a capability monolithic software can't offer)

Because a program is a bundle of ICM records and a "feature" is a named SUBSET (subgraph),
and the loadable unit is already the per-cell record, the LICENSABLE unit can be the FEATURE.
"Data is just data": the fabric doesn't distinguish a feature boundary from any record
boundary, so composing features from different products is just loading two record-bundles
side by side. The ROM seals per-MODULE, not per-program (same seal mechanism — records are
uniform). => Corporate model: license the 30% of features you use, not a suite that's 70%
dead weight. Monolithic binaries CAN'T do this (features fused at compile); this can
(features never fused). Genuinely novel, and it's the natural grain of the system.

Rests on EXISTING foundations: relocatable root+offset modules (place independently-compiled
features without collision), anchor-first placement (loader-as-linker), per-cell streaming
load (subset loading is native).

Edges that make it non-trivial (disciplines this imposes):
- CLEAN feature boundaries: a feature is licensable only if it's a self-contained subgraph
  with a defined in/out ADDRESS CONTRACT. No shared cells / cross-wiring across feature
  lines, or you can't license one without the other. Composer must emit features as
  relocatable modules with explicit interfaces.
- DEPENDENCY closure: feature X may consume feature Y; licensing X without Y leaves it
  inert. Needs a dependency graph + "you hold the closure" enforcement (package-mgmt).
- PLACEMENT-collision at compose time: independently-compiled features mustn't claim the
  same slots/outputs; loader resolves via root placement (loader becomes a linker).

## Build order
NEAR-TERM (buildable now): Layer 1 — close the plain-hash-over-records integrity loop in
program_builder.py (hash records not text, embed, verify, hard-refuse). Every producer
(composer, compiler, saves) emits it — NO bypass, or it's not a boundary.
PREREQUISITE for enforcement-at-a-chokepoint: split the compiler and loader (currently one
program) so the loader is the SINGLE door where verify-or-refuse lives. A chokepoint with a
bypass is not a chokepoint.
HORIZON (full-hardware era): Layers 2-4 — signatures, local authorisation gate, boot-ROM
licensing + feature-licensing — with the two hardware caveats confirmed against the device.

## ICM direct-viewer (related, near-term-friendly)
Opcodes are standardised, so a viewer is a pure function bytes->text: walk the file, unpack
each opcode's known fields, print readable lines on the fly. NO stored second representation
(no drift). MUST read the SAME shared opcode/field table the loader uses (not a copy), or the
view drifts from the truth. Auth fields render blanked/`****` (never present in a file).
Ground truth stays the packed words; readability is a non-authoritative VIEW. A
`--disassemble` emits text for inspection; the file the loader parses stays number-exact.
