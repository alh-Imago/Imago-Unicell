# Trix Ecosystem — Vision Document

*Design note — June 2026*
*Status: future direction, not current work*

---

## What it is

A family of domain-specific frontends that all compile to ICM via a
common compiler API. Each frontend speaks a domain language; the
compiler produces the same executable format regardless of source.

---

## The core insight

Every domain expresses computation as:
- input format
- rules and constraints
- calculations
- dependencies between values
- transformations

UniCell is domain-agnostic at the execution level. Therefore the only
domain-specific component is the frontend parser. Everything else —
model building, validation, export, execution — is universal.

---

## The Trix family

| Module | Domain | Status |
|---|---|---|
| MathTrix | Equations, PDEs, stencils, linear algebra | In progress |
| BioTrix | Pathways, reactions, gene networks | Future |
| ChemTrix | Reaction chains, kinetics, molecular graphs | Future |
| AstroTrix | Orbital mechanics, N-body systems | Future |
| DataTrix | Pipelines, transforms, ETL | Future |
| FinanceTrix | Pricing models, risk, time-series | Future |

All emit ICM. All use the same compiler core. All run on the same
VM/FPGA execution layer.

---

## How the API works

A frontend author only needs to know:

1. The compiler API — takes a graph of nodes and edges, returns ICM
2. The available primitive tiles — what operations exist in the library
3. The ICM format — how to describe the model for execution

They do not need to understand UniCell cell internals, the two-arrival
firing model, the command bus, or the FPGA implementation.

If their domain requires operations that don't exist as tiles yet, they
supply the tile models. The compiler is tile-library-aware — domain
experts contribute tiles that match their domain. The API stays stable;
the library grows organically.

---

## Execution workflow

1. User enters domain input (equation, pathway, reaction, pipeline)
2. Frontend parses and validates
3. AST maps to UniCell primitives via compiler API
4. Composer builds the visual model
5. User validates on VM
6. User exports to ICM
7. ICM runs on VM, FPGA, or photonic slab

Full idea-to-execution loop, portable, offline, no cloud dependencies.

---

## Honest caveats

**Domain complexity varies significantly.**

MathTrix maps naturally to UniCell — PDEs, stencils, and linear algebra
are parallel dataflow problems. The tiles mostly exist already.

BioTrix and ChemTrix involve stochastic processes and continuous ODEs.
These need floating point or probabilistic primitives that don't exist yet.

FinanceTrix requires high-precision arithmetic and potentially
regulatory auditability — worth thinking carefully about whether
fixed-point UniCell is the right substrate for financial production use.

**The compiler API is not stable yet.**

Known bugs exist (MUX selector, forward simulation). These need fixing
before the API surface is worth documenting for external use. Publishing
an unstable API creates more work, not less.

**MathTrix is the reference implementation.**

Everything else should wait until MathTrix works end-to-end. A working
reference implementation is what makes the ecosystem concept real rather
than theoretical.

---

## Schema-aware I/O — API requirement

For external frontends to work reliably, the compiler API needs
type-aware input and output schemas. Currently the composer treats
data inputs as essentially untyped.

**What's needed:**

- **Input schemas** — a frontend declares what data it expects and
  in what format. A biologist's reaction rate and a physicist's
  velocity are both numbers at the cell level but they're different
  things at the domain level.
- **Type mapping** — schemas map to UniCell's internal dtype encoding
  (NUMERIC, SIGNED, ALPHA, DATETIME). The mapping is the frontend
  author's responsibility; the compiler validates it.
- **Output schemas** — same in reverse. What the model produces,
  in what format, at what precision.
- **Boundary validation** — reject malformed input before it reaches
  the cells. Errors at the schema boundary are much easier to
  diagnose than errors deep in cell execution.

**Why this is a prerequisite, not optional:**

Without schema-aware I/O, a frontend author has no reliable way to
connect domain data to a model. They'd have to understand cell
addressing and type encoding directly — which defeats the purpose
of the API abstraction.

**Current state:** not implemented. ICM carries some type information
already; the main work is formalising it as a declarable schema and
adding validation in the composer/compiler bridge.

**Explore when:** the compiler API stabilisation work begins.
Not before MathTrix is working — MathTrix will surface what the
schema system actually needs to handle in practice.



- MathTrix working end-to-end, demonstrable on tablet
- Known compiler bugs fixed (especially MUX selector)
- Compiler API surface cleaned up and documented
- ICM format declared stable
- Tile library extension process documented

Realistic timeline: 6-12 months of solid work from current state.

---

## The broader point

The goal is not to build all six Trix modules. The goal is to build
the platform that makes it possible for others to build them — people
who know biology, chemistry, or finance better than we do.

That's a different and more achievable goal. The platform work is
MathTrix plus a clean API. The domain modules follow from others
choosing to build on it.
