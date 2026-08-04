# Vision

*What this is trying to become.*

---

One cell type. One bus. One program format.

The same `.icm` file that runs a logic gate on the Python VM today runs the
same gate on an iCEBreaker FPGA, on a Kintex-7 in July, on a future ASIC in
some number of years, on whatever comes after that. Nothing changes in the
program. Nothing needs to change. The substrate changes; the program doesn't.

That portability is not a marketing claim about cross-platform compatibility.
It is a structural property of the architecture. The cell doesn't know what it's
running on. The bus doesn't know. The program doesn't know. They don't need to.

---

## What Becomes Possible

**Neural ponds alongside OS ponds.** A spiking neural network occupying 300
cells on a Kintex-7 sits in the same tick cycle as the filesystem index, the
COMPANION OS anchor, and the user's WORKSPACE. No mode-switching. No separate
neural processor. No inter-chip communication overhead. The same bus that
carries a spike carries a file lookup.

**Typed silicon.** Every cell now carries its type — unsigned, signed,
character, datetime — in two bits of its configuration word. The type travels
through the hardware, through the OS layer, through the program file, through
the health monitor. The silicon knows what it holds. That's new.

**A language-agnostic compile target.** Via LLVM IR, any language that LLVM
supports — C, C++, Rust, Swift, Zig — becomes a UniCell frontend. Programs
written in those languages today can run on hardware that doesn't exist yet.

**Reconfigurability at runtime.** Because `gate_state` is a value in a
register that another cell can write, a learning rule is just another cell
cluster that observes spike activity and updates gate configurations. Hebbian
learning, STDP, neuromodulation — all expressible as pond computation, on the
same substrate, in the same tick.

**Scale without architecture change.** 12 neurons on an iCEBreaker. 300 on
a Kintex-7. 100 million on a future ASIC. The same `.icm` file. The same OS
layer. The same programming model. What changes is the cell count, not the
design.

---

## The Constraint Was the Point

The founding decision — every logic function must be one cell, one cycle, from
a NOR gate tree — ruled out a hundred easier paths. It ruled out instruction
sets, decoders, ALUs, separate memory banks, type registers. It forced the
wired-OR bus, the single gate_state word, the complement cell model for 64-bit
types, the PTT as the OS contract.

Every constraint that felt limiting turned out to be generative. The wired-OR
bus makes fan-in free. The single gate_state word made the type system two bits
rather than a parallel type bus. The complement cell model for 64-bit types is
the same model that works for matrix inputs — just a shape declaration.

The architecture is more capable now than it was when it had fewer rules.
That is what constraints do when they're the right ones.

---

## What This Isn't

It is not trying to be faster than a GPU for matrix multiplication.
It is not trying to replace dedicated neuromorphic chips at pure spiking
network throughput.
It is not trying to beat a modern CPU at general-purpose sequential computation.

It is trying to be the substrate on which those things coexist — where neural
computation, symbolic reasoning, filesystem operations, OS services, and
hardware I/O happen in the same tick cycle on the same cells, with no
architectural seams between them.

Whether that turns out to matter depends on what people build with it.
The doors are open. The map is the TODO.

## The Full User Experience — one develop/test/study/share loop (community substrate)

The community side isn't a feature to bolt on — it's already the SHAPE of the parts. They form
a stack that lets someone develop, test, study, and share WITHOUT touching silicon, then deploy
to silicon unchanged:

- **Authoring** — the composer and Trix front-ends build models away from a card.
- **Execution** — the VM runs on the SAME model as the FPGA. So a VM result is a silicon result
  (slow, but unbounded in scale — the right trade for development). This fidelity is the keystone:
  it's what makes everything above it trustworthy.
- **Observability (cell scope)** — the workbench is click-time study: watch a single cell, or the
  WAVE of data propagate, as a faithful picture of the die (the silicon runs too fast/opaque to
  watch a wave). Because the VM mirrors the FPGA, the workbench shows the REAL execution model,
  not an approximation — both a learning tool and a development tool, same fidelity.
- **Artifact + integrity** — ICM files are the portable artifact tying authoring→execution→deploy;
  hash checks make sharing trustworthy. Portability holds across the whole loop because everything
  expands to the same proven primitives.

The loop: author → test at scale in the VM → study in the workbench → verify with hashes → run on
silicon → share the ICM. Barrier to entry drops to "a browser + the VM" — which is exactly what a
community needs. This cell-level loop is largely REAL ALREADY and is the community on-ramp; it
works with the proven cell and does not need the OS layer.

### Two observability scopes (a real distinction)
- **Cell/data workbench** — VM-faithful, for developing models. Meaningful NOW.
- **Systems view** (workbench EXTENSION) — sees the layers ABOVE compute (PTT, ward/sentinel, OS
  structure), and only in the SILICON version, because those are real-deployment layers the
  cell-level VM doesn't model. You don't build the systems view until there's a system to view —
  it depends on the OS layer existing on silicon. Far end.

### Dependency order (the experience deepens as the stack deepens)
1. Prove the adder (composition works at all).
2. Mature the compiler/loader; REWRITE the composer/Trix/VM/workbench against the PROVEN new cell
   (they currently target the old cell model — the same model-rewrite already queued).
3. Community loop solid end-to-end on the new substrate.
4. Systems view as the ward/sentinel/PTT layers come up on silicon.

Held as the FRAME the individual roadmap items serve — so the builds point at one destination
instead of drifting into unconnected features. Most of this is forward of the core; the parts
genuinely point at it, and the work is bringing them onto the proven cell, then extending upward.

NOTE (the tidy): the repo/threads are a mess right now by Alan's own assessment. These threads —
community loop, three-tier capability (primitives/std-lib/user-macros), table-as-RTL-projection,
two observability scopes — get PICKED UP AND TIED TOGETHER into a coherent system during the big
tidy/consolidation, which comes toward the FAR END. This note exists so the threads survive until
then; it is not a now-build.
