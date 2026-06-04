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

## Prerequisites before opening to others

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
