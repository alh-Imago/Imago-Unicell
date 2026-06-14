# Trix Ecosystem — Current State

*Updated: June 2026*

A family of domain-specific frontends that compile to `.icm` via a common
`FormatDefinition` pattern. Each frontend speaks a domain language; the
fabric executes the same cell network regardless of which Trix produced it.

---

## Core mechanism: FormatDefinition

All Trix frontends are built on `cell_format.py`'s `FormatDefinition` base
class. A format definition declares:

- **Alphabet** — the finite symbol set (4 DNA bases, 20 amino acids, 118
  elements, 9 D2Q9 distribution functions, …)
- **Encoding** — how symbols pack into cell words (bits per symbol, words
  per cell, pack order)
- **Valid tiles** — the tile names legal in this domain
- **Produces/consumes** — typed data flow contracts between tiles
- **Constants** — domain constants preloaded into cells at configure time
  (CODATA 2018 physical constants, lattice weights, genetic code table, …)
- **Operations** — reference implementations for validation

The pattern generalises MIF: MIF was always a format definition; `cell_format.py`
formalises that so any finite-alphabet domain can do the same thing.

---

## Active frontends

### MathTrix — parallel stencil and physical simulation

The reference implementation. Maps equations, PDEs, and stencils onto the
cell fabric via the MIF (MathTrix Internal Float) tile family.

**Format:** MIF (compact floating-point, 64 bits per value pair)
**Tile family:** MIF_ADD/SUB/MUL/DIV/SQRT/MADD/ABS/NEG/MIN/MAX/CMP_*/
  MIF_MUX/MIF_RECIP/MIF_RSQRT/MIF_PACK/MIF_UNPACK (20 tiles)
**System models (10):** boids, conway, fast_marching, gray_scott, ising,
  laplacian_1d, laplacian_2d, nbody, pagerank, wave
**Runner:** `mathtrix.py` — Grid1D, Grid2D, MathTrix domain classes
**Animation:** `mathtrix_animate.py` — MP4/GIF/PNG/live via matplotlib+ffmpeg
**Tests:** 242/242 fp_tiles, 157/157 compiler_int32

### FlowTrix — Lattice Boltzmann fluid simulation

**Format:** FlowTrix_D2Q9 — 9 distribution functions, D2Q9 lattice weights
and velocity vectors as preloaded constants (from cell decode table, same
mechanism as topology preset opcodes).
**Key structural properties:**
- Streaming IS the topology: one hop per direction, no streaming tile exists
- Ternary velocities (e ∈ {-1,0,+1}): all moment sums are pure add/subtract
  — zero MIF_MUL in the moment computation
- Reciprocal once: ux,uy share 1/ρ → 1 MIF_RECIP + 2 MIF_MUL, not 2 MIF_DIV
**Tile implementation:** `flowtrix_lbm_mif.py` — LBM_COLLIDE as composed
  MIF tiles. Predicted: **1,714 ticks/update** (reciprocal-optimised).
**Demo:** `flowtrix_cylinder.py` — flow past cylinder at Re=100-200. Strouhal
  number validated against Williamson correlation (St=0.167 unbounded).
  Blockage 0.10 → St=0.160 (4.2% error); correct shedding physics confirmed.
**Cost:** `flowtrix_cost.py` — honest comparison vs NASA/Boeing 777 PowerFLOW
  (6.5B cells, 5000 cores, Pleiades). Solid vs projected numbers separated.
**Tests:** 27/27 flowtrix, 13/13 flowtrix_collide, 18/18 flowtrix_cylinder
**Hardware run:** first real Arria 10 workload once USB Blaster arrives.
  Predicted-vs-measured ticks is the primary validation metric.

### NeuroTrix — Spiking neural networks

**Format:** NeuroTrix_LIF — Leaky Integrate-and-Fire neuron model
**Tile implementation:** `neurotrix_lif_mif.py` — one LIF tick as composed
  MIF tiles. Predicted: **353 ticks/update** (~7× shallower than LBM collide).
  Division-free: dominated by two MADDs (leak + integrate). β and input gain
  are preloaded multiply constants; threshold is a preloaded comparator
  constant. Matches `LIFNeuron.step()` exactly over 300-tick runs.
**Runner:** `neurotrix_lif.py`
**Tests:** 28/28 neurotrix_lif, 14/14 neurotrix_lif_mif

### MidiTrix — MIDI events to spiking neurons (iteration 1)

**Format:** MidiTrix — finite alphabet: pitch 0-127, velocity 0-127, on/off.
  Constants: A4=440Hz, equal temperament divisor 12 (`note_to_hz()`).
**Architecture:** Tonotopy IS topology — pitch→neuron is wiring, so there is
  deliberately no MIDI_ROUTE tile. Same principle as FlowTrix having no
  LBM_STREAM tile.
**Runner:** `miditrix_lif.py` — plays a MIDI event stream to a tonotopic
  LIF bank. Per-update cost: 92 (MIF_MUL gain + MIF_MUX gate) + 353 (LIF) = 445 ticks.
**Scope:** Iteration 1 — notes, velocity, timing only. Timbre, harmony, and
  consonance need a spectral (FFT/filterbank) front-end, left open by design.
  `note_to_hz()` is the tonotopic anchor that front-end would bridge onto.
**Tests:** 19/19 miditrix

---

## Format definitions (cell_format.py)

9 format definitions across 6 domains — all registered in `FormatRegistry`:

| Format | Domain | Alphabet | Bits/symbol |
|--------|---------|----------|-------------|
| MIF | MathTrix | ∞ (float) | 64 (pair) |
| FlowTrix_D2Q9 | FlowTrix | 9 directions | — |
| NeuroTrix_LIF | NeuroTrix | continuous | — |
| MidiTrix | MidiTrix | 128 pitches + vel | 16 |
| DNA_4Base | BioTrix | A/T/G/C | 2 |
| RNA_4Base | BioTrix | A/U/G/C | 2 |
| Amino20 | BioTrix | 20 residues | 5 |
| Chemistry_Element | ChemTrix | 118 elements | 8 |
| SI_Physics | PhysTrix | continuous | — |
| Finance_Currency | FinTrix | currencies | — |
| BCD | General | 0-9 | 4 |
| FixedPoint | General | fixed-pt | — |

---

## Bridge system

`cell_format.py` includes a `BridgeContract` base class and 9 fundamental
bridges connecting domains:

- **Hawking bridge** (PhysTrix ↔ thermal): T = ℏc³/8πGMk_B,
  `semantic_confidence = 1.0` (exact physical identity, not analogy)
- DNA→Amino20 (codon decoding), DNA→RNA (transcription), RNA→Amino20
  (translation), Chem→Bio (mutagen probability), and others

`semantic_confidence` encodes the ontological depth of connection: 1.0 = exact
physical identity; lower = analogy or approximation.

Remaining: compiler auto-placement of bridge tiles, SI_CHECK dimensional
analysis integration, design-time confidence-threshold enforcement.

---

## Community contribution space

`community/` provides a structured exchange layer for both Trix and non-Trix
contributions. Two contribution kinds:

**trix-domain** — a full FormatDefinition with format.py, models, bridges.
  Validated by `community_tools.py cmd_validate` (checks domain, format class,
  tile refs against valid_tiles).

**raw-model** — a raw `.icm` or builder library, no FormatDefinition required.
  Validated by `cmd_validate` (checks .icm schema + record_hash canonR).
  Scaffolded by `cmd_new --kind raw-model`.

Current community content:

| Domain | Kind | Models |
|--------|------|--------|
| MathTrix | trix-domain | 10 (all system models) |
| BioTrix | trix-domain | 5 (gc_content, hamming_distance, dna_complement, codon_scan, hydrophobicity_profile) |
| ChemTrix | trix-domain | 3 (molecular_weight, valence_check, electronegativity_delta) |
| PhysTrix | trix-domain | 3 (hawking_temperature, schwarzschild_radius, arrhenius_rate) |
| FinTrix | trix-domain | 0 (format def only) |
| General | trix-domain | 0 (format defs only) |
| PoliticsTrix | trix-domain | 0 (format def only) |

Seed raw-model entries: `examples/tiles/samples/` (committed .icm tile palette).

### Walker — tile .icm authoring tool

`examples/walker/walk_tiles.py` exports any tile or whole builder library to
hashed `.icm` files:

```bash
# Export a single tile
python examples/walker/walk_tiles.py --builder fp_tiles:make_int32_add

# Export a whole user builder library
python examples/walker/walk_tiles.py --module my_tiles.py

# Export the full built-in functional set
python examples/walker/walk_tiles.py
```

Every emitted `.icm` carries `record_hash` matching the composer's canonR
exactly (`{gs,in,init,out}`, no whitespace, SHA-256 hex). The composer
verifies "hash verified ✓"; the strict loader accepts without warning.

The two authoring routes:
- **Route A** — compiler for full programs: Python source → IR → `.icm`
- **Route B** — builder + walker for models/libraries: NORBuilder → walker → hashed `.icm` → raw-model community contribution

---

## Planned / future

- **BioTrix runner** — DNA/RNA/protein sequence execution on VM
- **ChemTrix runner** — molecule computation on VM
- **FlowTrix hardware run** — MLUPS/watt on Arria 10 (hardware-gated)
- **Compiler auto-placement of bridge tiles** — from pipeline `.icm`
- **SI_CHECK dimensional analysis** — compile-time unit enforcement
- **MIF_RSQRT for boids/n-body** — requires depth-aware cost model in those runners first
- **LLVM frontend** — C/C++/Rust/Swift via IR pipeline (deferred)
