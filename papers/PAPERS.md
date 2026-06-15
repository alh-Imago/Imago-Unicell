# Imago UniCell — Papers Tracking
*Single source of truth for all publication work.*
*Last updated: 2026-06-15*

## Folder structure

```
papers/
  PAPERS.md          ← this file — status tracking for all papers
  paper_main/        ← working drafts, notes, figures for Paper 1 (future)
  paper_timing/      ← working drafts for Paper 2 (future)
  paper_bridges/     ← working drafts for Paper 3 (future)
  paper_hawking/     ← working drafts for Paper 4 (future)
  paper_robotics/    ← working drafts for Paper 5 (future)
  paper_flowtrix/    ← working drafts for Paper 6 (future)
  paper_substrate/   ← working drafts for Paper 7 (future)
```

**Paper 1 draft lives at:** `docs/PAPER_DRAFT.md` (referenced by the manual;
kept in docs/ so the manual section continues to work without change).
Working notes and figures for Paper 1 will go in `papers/paper_main/` as they
accumulate.

This folder is deliberately excluded from the manual build — `docs/build_manual.py`
only pulls in files explicitly listed in SECTIONS. Nothing in `papers/` will
appear in the manual unless deliberately added.

---

## Status key

| Symbol | Meaning |
|--------|---------|
| 🔴 | Not started |
| 🟡 | In progress / partial |
| 🟢 | Done / ready |
| ⏸ | Blocked on hardware or other dependency |

---

## Paper 1 — The Main Paper (PAPER_DRAFT.md)

**Title (working):** Imago UniCell: A NOR-Universal Reconfigurable Fabric with
Two-Arrival Firing and Wired-OR Arbitration

**Target:** Systems / computer architecture venue (FPGA, ISCA, MICRO, or similar)

**Current state:** Draft exists (949 lines). Core argument is present but the
flow is broken — sections 10b/10c/10d are appended after the conclusion rather
than integrated, major features added since the draft was written are absent
entirely, and the structure doesn't lead with the strongest claims.

### Structural problems to fix

- [ ] 🟡 **Flow rewrite** — the argument should be: idea → cell → emergent
      properties → evidence (silicon + predicted timing) → what it enables.
      Currently buries the lead under implementation detail. Sections 10b/10c/10d
      need integrating as proper numbered sections, not appendices-after-conclusion.

- [ ] 🔴 **Timing determinism section** (new §) — this is one of UniCell's
      defining characteristics and is currently a footnote. The compiler knows
      pipeline depth at build time; the silicon confirms it; no cache effects,
      no jitter, no run-to-run variance. Predicted vs measured tick figures
      (LBM: 1,714 ticks/update; LIF: 353 ticks/update) are the first
      predicted-vs-measured checks in the literature for a reconfigurable fabric.
      Deserves a dedicated section, not a passing mention.

- [ ] 🔴 **Format-typed computation section** (integrate 10b) — the
      FormatDefinition / Trix family has grown enormously since the draft.
      Needs to cover: the generalisation from MIF → any finite-alphabet domain;
      the 12 format definitions now live; the bridge system; SI_CHECK dimensional
      analysis; the community contribution layer. Currently scattered.

- [ ] 🔴 **Bridge system + semantic contracts section** (integrate 10c/10d) —
      the compile-time bridge enforcement (check_pipeline_bridges,
      compile_pipeline_icm, dimension_map) is now fully built and tested.
      The semantic confidence scale and its physical grounding is a genuine
      contribution. Currently appended after the conclusion.

- [ ] 🔴 **Use cases section** (new §) — the Trix family now covers enough
      domains that concrete scenarios are compelling:
      - Robotics: SensorTrix → OptiTrix PID → actuator, deterministic latency,
        no scheduler, no interrupt jitter, fits embedded targets
      - Fluid simulation: FlowTrix, Strouhal validated, MLUPS/watt vs CPU/GPU
      - Neural signal processing: NeuroTrix LIF + MidiTrix tonotopic drive
      - Network packet processing: NetTrix, d14 @ 200MHz = 70ns/packet
      - Cross-domain: PhysTrix → FlowTrix viscosity bridge (confidence=0.95)

- [ ] 🔴 **Sensor data + dimensionality section** (new §) — SensorTrix
      introduces (location, amount) as the universal sensor encoding; a sensor
      stack is N readings on N consecutive bus addresses — one stream, one format,
      one bridge. This maps naturally to higher-dimensional sensor arrays (tactile
      skin, IMU, camera arrays) without architectural change. With physical sensors
      arriving this becomes a real-data section.

- [ ] ⏸ **Section 4 update** — Arria 10 silicon results, shift_in_en validation,
      scale test, MLUPS/watt. *Blocked: USB Blaster in transit.*

- [ ] ⏸ **Performance numbers update** — packed adder reduces INT32 tile costs
      ~25×; MIF_ADD via packed shift; updated cell counts throughout.
      *Blocked: shift_in_en silicon validation.*

### Content gaps (things that exist but aren't in the paper)

- [ ] 🔴 SensorTrix — 5 tiles, (location, amount) encoding, sensor stack pattern
- [ ] 🔴 OptiTrix — PID as 6-tile pipeline, state in preloaded registers,
      anti-windup at zero fabric cost
- [ ] 🔴 NetTrix — two-arrival model IS a state machine; TCP FSM as topology
- [ ] 🔴 FlowTrix Strouhal validation result (currently in status, not results)
- [ ] 🔴 NeuroTrix LIF predicted tick figure (353 ticks/update)
- [ ] 🔴 Bridge compiler enforcement — check_pipeline_bridges, compile_pipeline_icm
- [ ] 🔴 SI_CHECK dimensional analysis — unit errors caught at compile time
- [ ] 🔴 Community contribution layer — walker, raw-model kind, REGISTRY
- [ ] 🔴 Onion compression tool (tools/onion/) — mention as ecosystem artifact
- [ ] 🔴 Tile count update (was 86 in draft; now considerably more)
- [ ] 🔴 Test suite count update (was 133/236; now 15+ suites, 700+ tests)

### What can be written now (pre-hardware)

Everything except Section 4 Arria 10 results and the performance numbers
that depend on shift_in_en. The flow rewrite, all missing sections, all
content gaps above — none of these need the card.

---

## Paper 2 — Deterministic Timing in Reconfigurable Fabric

**Title (working):** Compile-Time Timing Guarantees in a NOR-Universal
Reconfigurable Fabric

**Target:** Short paper / workshop — systems, real-time, or embedded venue

**Argument:** In conventional compute, performance is cache-dependent,
varies run-to-run, and cannot be known in advance. In UniCell, pipeline
depth is a compile-time constant — the compiler knows the tick count before
silicon fires a single cell. The silicon confirms it exactly. This is a
qualitatively different kind of performance claim. For embedded, ECU, and
real-time applications this matters more than raw throughput.

**Evidence needed:**
- 🟢 iCEBreaker: predicted depths match silicon (31/31 silicon tests)
- 🟢 LBM collide: 1,714 predicted ticks/update (VM-confirmed)
- 🟢 LIF: 353 predicted ticks/update (VM-confirmed)
- ⏸ Arria 10: predicted-vs-measured on larger fabric (*blocked: cable*)

**Status:** 🔴 Not started. Could be written now for iCEBreaker; Arria 10
results would strengthen it considerably. Short paper — probably 6-8 pages.

**Dependencies:** iCEBreaker results already sufficient for the core claim.
Arria 10 adds the scaling argument.

---

## Paper 3 — Typed Cross-Domain Computation and Semantic Bridge Inference

**Title (working):** Semantic Bridge Inference in a Format-Typed Heterogeneous
Compute Fabric

**Target:** PL / type systems venue, or a broader CS venue (POPL adjacent,
or a systems + semantics workshop)

**Argument:** UniCell's FormatDefinition system is a typed heterogeneous
compute fabric where domains are first-class citizens and cross-domain
connections are formal scientific claims (BridgeContract, semantic_confidence).
The compile-time enforcement (check_pipeline_bridges, dimension_map SI_CHECK)
is a type checker for physical units and ontological depth simultaneously.

The inference extension — surfacing candidate bridges from dimensional
matching without requiring a BridgeContract to have been written — makes this
a *discovery tool*: the system can show researchers domain connections they
hadn't considered, grounded in declared physical relationships rather than
word-matching or embedding similarity.

**Novel contributions:**
- semantic_confidence as a typed confidence annotation on cross-domain edges
- dimension_map as a compile-time SI unit type system
- Bridge inference from dimensional overlap (not yet built — see below)
- The distinction between analogy (confidence < 0.8) and physical identity
  (confidence = 1.0) as a formal type distinction

**What needs building:**
- [ ] 🔴 Bridge inference engine — given two formats with declared
      dimension_maps, find concept pairs where dimensions match and surface
      them as candidate bridges with a confidence floor. Not auto-placing —
      showing the user "these may be connectable, here's the dimensional
      basis." Region Connector UI: "Suggested connections" panel.
- [ ] 🔴 Inference confidence scoring — how to assign a prior confidence
      to an inferred (not declared) bridge. Dimensional match alone gives a
      floor; declared physical formula raises it; literature citation raises
      it further.
- [ ] 🔴 Case studies — Hawking (T = ℏc³/8πGMkB, confidence=1.0);
      LBM viscosity (ν = cs²(τ-0.5)Δt, confidence=0.95); a speculative
      bridge as a negative example

**Status:** 🔴 Not started. The infrastructure (BridgeContract, dimension_map,
check_pipeline_bridges) is fully built. The inference engine is the main new
piece of work.

**Dependencies:** No hardware dependency. Entirely software + theory.

---

## Paper 4 — The Hawking Bridge as a Standalone Result

**Title (working):** A Compute Bridge Between Gravitational and Thermal Domains:
Hawking Radiation as a Fabric Connection

**Target:** Possibly interdisciplinary — physics + CS, or a short note in a
computing + science venue

**Argument:** The Hawking temperature formula T = ℏc³/8πGMkB connects black
hole mass (gravitational domain) to temperature (thermal domain) with
confidence=1.0 — it is derived from first principles, not an approximation.
In UniCell this becomes a typed fabric connection: a PhysTrix computation
feeding a thermal model via a bridge whose dimensional type is verified at
compile time. The bridge contract IS the scientific hypothesis — stated
formally, enforced mechanically, and permanently recorded in the model metadata.

This is a short paper (4-6 pages) making a conceptual point: that formal
computation systems can encode scientific relationships as typed program
constructs, making the physical assumptions of a simulation explicit,
checkable, and reproducible.

**Status:** 🔴 Not started. Largely a writing task — the implementation
is complete. Could be written now.

**Dependencies:** None. All infrastructure exists.

---

## Paper 5 — Robotics: A Complete Sensor-to-Actuator Pipeline in Fabric

**Title (working):** Deterministic Sensor-to-Actuator Pipelines in a
NOR-Universal Reconfigurable Fabric

**Target:** Robotics / embedded systems venue (ICRA, IROS, or embedded
systems workshop)

**Argument:** A complete sensor-to-actuator control loop — SensorTrix
(location, amount) → OptiTrix PID → actuator command — runs entirely in
fabric with deterministic end-to-end latency. No OS scheduler, no interrupt
latency jitter, no cache effects. Pipeline depth is a compile-time constant.
Reconfiguring the controller (changing gains, switching control law) is a
fabric reconfiguration, not a software update.

**What makes this compelling for robotics:**
- Every sensor is (location, amount) — one encoding covers touch arrays,
  IMU, motor encoders, sonar, ADC channels
- PID pipeline: 6 tiles, ~2512c total, state in preloaded registers,
  anti-windup is host-side at zero fabric cost
- Cascade PID (position → velocity) is two OptiTrix pipelines with
  SensorTrix bridging the loops — fits naturally
- With physical sensors arriving: real-data validation possible

**With real sensor hardware (incoming):**
- Actual sensor readings through the pipeline
- Measured latency vs CPU/microcontroller equivalent
- Dimensionality: N-sensor arrays map directly to N consecutive bus
  addresses — the architecture scales with sensor count without redesign

**Status:** 🔴 Not started. Tile infrastructure complete. Significantly
stronger once real sensor data is available.

**Dependencies:** Sensor hardware arriving strengthens this considerably
(real data, real latency measurements). Core argument provable in VM now.

---

## Paper 6 — FlowTrix: Physics Simulation on a Topology-Compute Fabric

**Title (working):** Lattice Boltzmann Fluid Simulation via Fabric Topology:
MLUPS/Watt and Deterministic Timing on a Reconfigurable Fabric

**Target:** HPC / scientific computing venue

**Argument:** LBM is naturally parallel (collision is local arithmetic,
streaming is nearest-neighbour). On UniCell, the streaming step is not
computed — it IS the topology. The cylinder obstacle is fabric wiring, not
a data check. Validated against published Strouhal number for Re~100-200.
MLUPS/watt and MLUPS/dollar comparison vs CPU/GPU, with honest accounting
of temporal-blocking tax.

**Status:** 🟡 VM results exist, Strouhal validated. Hardware run blocked.

**Dependencies:** ⏸ Arria 10 for MLUPS/watt measurement. VM-only results
publishable as a short paper but the hardware numbers are the main event.

---

## Paper 7 — The Universal Symbolic Substrate

**Title (working):** A Universal Symbolic Substrate: Format-Typed Heterogeneous
Computation on a NOR Fabric

**Target:** Broader venue — CACM, IEEE Computer, or a survey/vision track

**Argument:** UniCell's Trix family has grown into something qualitatively
different from what it started as: a typed heterogeneous compute fabric where
any domain with a finite alphabet, compact representation, valid operations,
and fixed constants can be expressed as a FormatDefinition and run on the same
fabric as every other domain. The domains currently defined span:
- Floating point (MIF)
- Genomics / proteomics (DNA, RNA, Amino20)
- Chemistry (periodic table, molecular groups)
- Physics (SI units, CODATA 2018 constants, dimensional analysis)
- Finance (currencies, instruments)
- Fluid dynamics (D2Q9 lattice Boltzmann)
- Neural signal processing (LIF neuron, MIDI tonotopic)
- Sensor arrays (location, amount)
- Control systems (PID, Q16.16 fixed-point)
- Network packet processing (TCP/IP state machine)

And they mix. A single cell map can span SensorTrix → OptiTrix → NeuroTrix
→ PhysTrix with typed bridges at each crossing. The fabric is the commons;
the format is the language.

**Status:** 🔴 Not started. This is a vision/survey paper — more writing
than new implementation, but benefits from having the inference engine (Paper 3)
and real sensor data (Paper 5) as concrete examples.

**Dependencies:** Benefits from Papers 3 and 5 being further along.
Can be started now as a skeleton.

---

## Sensor hardware arrival — impact on papers

Physical sensors arriving changes the evidence base for several papers:

| Paper | Impact |
|-------|--------|
| Paper 1 (main) | Real sensor data in use cases section |
| Paper 2 (timing) | Real measured latency through SensorTrix pipeline |
| Paper 5 (robotics) | Core paper — transforms from VM demo to real system |
| Paper 7 (substrate) | Concrete dimensionality example with real data |

SensorTrix introduces genuine dimensionality: an N-sensor array is N readings
on N consecutive bus addresses. With a real tactile array or IMU this becomes
a statement about how the architecture scales with sensor count — no redesign,
no new addressing scheme, just more bus addresses. That's worth tracking
explicitly as a theme across papers.

---

## Shared infrastructure across papers

These sections/results appear in multiple papers — write once, reuse:

| Item | Papers |
|------|--------|
| Timing determinism claim + evidence | 1, 2, 5 |
| SensorTrix (location, amount) encoding | 1, 5, 7 |
| Bridge confidence scale + SI_CHECK | 1, 3, 4, 7 |
| Strouhal validation result | 1, 6 |
| Predicted vs measured tick figures | 1, 2, 6 |
| Two-arrival model as state machine (NetTrix) | 1, 7 |
| Topology IS computation (obstacle = wiring) | 1, 6, 7 |
| Compile-time pipeline depth | 1, 2, 5 |

---

## Immediate actions (pre-hardware, pre-sensor)

1. **Flow rewrite of Paper 1** — integrate 10b/10c/10d, fix section ordering,
   add timing determinism section, add use cases section. No hardware needed.

2. **Paper 4 (Hawking bridge)** — almost entirely a writing task. Short.
   Could be drafted in one session.

3. **Bridge inference engine** (for Paper 3) — Region Connector "Suggested
   connections" panel based on dimension_map overlap. Adds to Paper 3 and
   feeds back into Paper 1's bridge section.

4. **PAPERS.md kept current** — update status symbols as work progresses.
   Same discipline as PLAN.md.

---

## What not to do

- Don't try to put everything into Paper 1 — it's already too long and
  unfocused. Some material belongs in the satellite papers.
- Don't write sensor results sections before the hardware arrives — leave
  placeholders with clear markers.
- Don't start Paper 6 (FlowTrix) in earnest before Arria 10 is up —
  the VM results exist but the hardware numbers are what makes it publishable.
- Don't let Onion tool work absorb paper-writing sessions.
