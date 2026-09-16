# A real pattern library for placement decisions — shape as identifier, a real escalation ladder (Alan/Claude, 2026-09-16)

*Per Alan's own direct proposal, immediately after `#751`'s own real
`priority`-vs-relay-padding finding: a library of known, verified
placement patterns the compiler can recognize and reuse, falling back
to the user when nothing matches. Confirmed directly, not assumed:
this is Tier 1 of the tile library `super_tile_library_v1.py`'s own
docstring already names but hasn't built, and its own escalation
mechanism connects precisely to two things already real and scoped in
this project — the TRIX family's own proven design principle, and the
Composer's own already-confirmed, NP-complete-justified role. A
scoping pass only, nothing built.*

## The real, confirmed starting point: this is Tier 1, already named, not invented fresh

`super_tile_library_v1.py`'s own header states it directly: "Tier 0 of
the super-cell tile library... proving the named-port/placement
contract before Tier 1's [harder multi-cell relative-placement
problem]." `SuperTileSpec`'s own docstring: "Tier 1 (multi-cell,
relative-position composed tiles) is explicitly out of scope here."
Alan's own proposal — a store of known, verified, MULTI-cell patterns
(not just single-cell primitives) the compiler recognizes and reuses
— is precisely that already-anticipated Tier 1, given a real,
concrete shape and a real escalation mechanism for the first time.

## Shape as identifier — the real, direct connection to the TRIX family's own proven principle

**Alan's own real insight: "data is just data, once you take out the
semantics of a thing, what's left is the shape, and... it's the shape
of the design that becomes the identifier."** Checked directly, not
assumed: this is the SAME real, unifying design principle
`mathtrix_mif_connection.md` already states as the TRIX family's own
core idea, in Alan's own words quoted there: *"a way to define and
manipulate specific cases in the native substrate without extra cells
being needed. The boundary was where all the work was done, and the
domain idea spawned from that, so it flowed through — but it worked."*
TRIX's own real, confirmed mechanism: push all domain-specific
complexity to a boundary (the pack/unpack step, paid once per value);
once data is inside the fabric in its own native, already-decomposed
form, computation uses the SAME generic substrate primitives
regardless of whether the original domain was floats, DNA, chemistry,
physics, or finance. The `FormatDefinition` pattern generalized
cleanly across all of them precisely because, once semantics are
stripped at the boundary, what's left — the shape — is the same kind
of thing every time.

**The real, different reference point, exactly as Alan named it:**
TRIX's own shape is about DATA REPRESENTATION (a value's own bit-level
encoding, alphabet, packing). A placement pattern's own shape is about
GRAPH TOPOLOGY (how many real values converge, at what kind of
consumer, in what real arrangement) — a different axis, the same real
principle: strip the semantics (which specific variables, which
specific program, which specific IR instruction names) and what
remains — arity, consumer type, real structural arrangement — is a
genuine, reusable identifier. `#751`'s own two-way integer-add
convergence pattern and a hypothetical future three-way convergence at
a different core type are DIFFERENT shapes by this identifier, even
though both are "DAG convergence" at the semantic level a person
would describe them at.

## The real escalation ladder, per Alan's own direct proposal

**1. A known shape in the local pattern library → a clear winner,
applied directly.** No re-derivation, no risk — exactly `Addendum 2`'s
own real, cited precedent from the old full-cell compiler: premade
artifacts already placed, timed, and verified, composed rather than
re-solved per program. `#750`'s relay-padded two-way convergence and
`#751`'s `priority`-based one are the first two real entries this
library would hold.

**2. More than one equally-valid known pattern for the same shape →
disambiguate by real, measured constraints: SIZE and DEPTH, per Alan's
own direct framing** ("the prompt is over size and depth, both
constraints become important in actual card-based designs"). This is
not an abstract preference question — it's the same real, already-
established currency this whole project already tracks: real cell
count (the MAN-file/ALM-budget discipline, `#734`/`#745`) for size,
and real tick/cycle latency for depth. `#751`'s own real, honest
finding already names exactly this trade-off for the two known
patterns: `priority`-based resolution costs one real, additional cell
and one real, additional tick of latency versus a bare, staggered
adder — the SAME real trade-off this disambiguation step would need to
present concretely, not abstractly, whenever a real card's own real
budget makes the choice matter.

**3. No local match at all → check a real, shared library first**,
per Alan's own direct question ("unless the user can tap into a shared
library system, held in the git?"). A real, separate, git-hosted (or
git-adjacent) repository of community-contributed, verified patterns
— the same real shape-as-identifier lookup, against a broader,
shared corpus rather than just the current project's own local one.

**4. Still no match anywhere → the real fork Alan named directly,
honestly ranked by likelihood:**
- **If the user's own system has a real AI attached, it can provide a
  real, researched candidate model** — directly the same kind of
  reasoning this whole session has been doing by hand (build the
  smallest case, trace it, verify it) applied to a genuinely novel
  shape, rather than a person doing it alone.
- **If not — which Alan names directly as the real, more likely
  position for most users** — the system's own real job becomes
  describing the problem precisely enough for a person to design a
  candidate answer themselves, and directing them to the Composer.

## The Composer connection — confirmed real and already scoped, not a new idea grafted on

**Checked directly, not assumed: `composer_scope.md` already
establishes exactly this role, for a real, load-bearing reason, not a
convenience.** Its own real premise: "a visual, human-in-the-loop tool
for PLACING and ROUTING an already-compiled model." Its own real
justification, confirmed rather than argued: "the underlying
placement/connection problem is CONFIRMED NP-complete (`#385`,
Numberlink). No algorithm guarantees an optimal answer as connection
count grows. Humans are genuinely good at this class of puzzle in
practice, despite its proven worst-case hardness." **This is the exact
real reason a human fallback belongs in this ladder at all** — not
because automated pattern-matching is incomplete today (though it is),
but because the underlying problem is provably one no algorithm can
always solve, meaning a human-in-the-loop step is a structural
necessity of the domain, not a stopgap for a compiler that isn't
finished yet.

**A real, already-written addendum to `composer_scope.md` names this
exact use case directly, confirmed by reading it, not remembered
vaguely:** "a second, narrower, genuinely different real use case
(browse/understand/compose-around an existing library)... a real
candidate for a FUTURE scoping pass of its own, once there's a real
tile library substantial enough... to make it worth doing." **Real,
honest assessment: that threshold may now be close to met** — a real
tile library exists (`super_tile_library_v1.py`, `vix_tile_library_
v1.py`), and two real, verified placement patterns for one real shape
now exist (`#750`, `#751`) — genuinely the first real content a Tier-1
pattern library, and a Composer surfacing it, would have to show.

## Real, honest, open questions — not resolved here

- **What exactly is "the shape," concretely, as data?** A real,
  precise schema is needed — something like `(arity, consumer_core,
  operand_commutativity, ...)` — not yet designed. Getting this wrong
  in either direction (too coarse, missing real distinctions the VM
  cares about; too fine, fragmenting what should be one reusable
  pattern into many near-duplicates) is a real, consequential design
  choice.
- **How does a "shared library held in the git" actually work
  mechanically?** A real, separate repository? A subdirectory of this
  one, with its own contribution/review process? How is a
  community-contributed pattern verified before being trusted as a
  real "clear winner" rather than an unverified guess? Real, unbuilt,
  possibly substantial infrastructure.
- **What does "describe the problem in enough detail" actually mean
  as a concrete artifact?** A real, structured problem description
  (something like "N real values of type X need to reach a consumer
  of type Y, here are the real, current constraints") the Composer
  could consume directly, versus a free-form text description a
  person has to parse themselves — a real, meaningful difference in
  how useful the hand-off actually is.
- **Does a confirmed, human- or AI-resolved answer feed back into the
  library automatically?** Alan's own proposal implies a growing
  library over time; the real mechanism for capturing and validating
  a new entry (confirmed correct how, by whom, before being trusted as
  a future "clear winner") is real, separate, unscoped work.

## Real, honest status

A scoping pass, connecting a real, new proposal to real, existing
architecture already present in this project (Tier 1 of the tile
library, the TRIX family's own shape-over-semantics principle, the
Composer's own NP-complete-justified human fallback) — not inventing
new concepts, recognizing that three separately-scoped ideas are
actually one real system once connected. No RTL, no schema, no code,
no shared-library infrastructure. The real, concrete first step,
whenever this is picked up: design the real shape schema precisely
enough to register `#750`'s and `#751`'s own two known patterns as
its first real entries — everything else in this ladder (shared
library, AI research, the Composer hand-off) depends on that schema
existing first.
