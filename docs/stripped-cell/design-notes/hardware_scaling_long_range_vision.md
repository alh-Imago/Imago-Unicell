# Long-range note: hardware scaling, beyond the current card

*Captured 2026-08-25, per Alan's own request ("adds to the vision doc
if anywhere") — a real, connected thread of thought-experiment ideas
that came up across one evening conversation, none scoped, none
started. Full reasoning trail for every idea below: `points.md` `#502`.
Same discipline as `general_purpose_programming_long_range_note.md`
and `full_cell_capability_and_cross_card_scheduling.md` — this is a
marker so the ideas survive intact until deliberately picked up, not
a commitment to build any of them.*

## The real, present-day starting point

Two real, already-known limitations on the CURRENT card set the whole
thread in motion:
- **`#412`**: all real BRAM access today runs through ONE shared
  `bram_controller_v1` instance every chain in the grid arbitrates
  for — a genuine single-point contention.
- **`#448`**: all real host↔card data movement today goes over JTAG —
  proven, but slow (~0.75 KB/s). PCIe x8 physically exists on the
  current board but carries no real data traffic yet.

Everything below is a real idea for what a FUTURE card generation
could look like, addressing one or both of these — none of it touches
the current Arria 10 GX board (IEI Mustang-F100-A10).

## Idea 1: many independent memory paths instead of one shared one

Checked directly against Intel's own documentation: Agilex-family
devices allocate two hardened memory controllers per I/O bank, and
larger parts can reach into the mid-teens of independent controllers
— a real, substantial jump over an Arria 10-class device. The real
architectural insight isn't just "more capacity" — it's borrowed
directly from Intel's own current Xeon methodology (Diamond Rapids:
multiple Compute Building Blocks, each reaching a shared pair of
fabric hub tiles fed by 16 independent memory channels, specifically
to avoid many cores contending for one memory path). A future UniCell
card built on a many-controller device could give DIFFERENT REGIONS
of the grid their own independent BRAM path instead of funneling
everything through the one shared, arbitrated port `#412` identified.
Honest caveat: only pays off for workloads with multiple regions
genuinely wanting memory access simultaneously.

**A connected sub-idea**: once real PCIe DMA exists (a real, separate,
substantial engineering effort — nothing built here today, everything
so far uses JTAG), the card's own RAM should sit as an elastic buffer
between PCIe's bursty, packetized nature and the mesh's own steady
one-word-at-a-time consumption — the standard, correct pattern for
that kind of mismatch, and it reuses `bram_controller_v1.v` (already
real, hardware-proven, `#265`) rather than needing anything new. It
should be a DEDICATED instance, separate from whatever the mesh's own
ordinary RAM cells already arbitrate for — otherwise this just
relocates `#412`'s bottleneck rather than solving it.

## Idea 2: a real first step into custom silicon

Real, current, low-cost shuttle service checked directly: **Tiny
Tapeout** (tinytapeout.com). Chips come back in QFN packaging (as few
as 44 balls), mounted on a small standardized breakout board — which
can plug into either Tiny Tapeout's own demo board (RP2040 +
USB-C, for interactive standalone use) or a fully custom PCB designed
to interface with the breakout board directly, per their own
documented support. The real, resolved design implication: a future
"the RISC controller is part of the interface" idea should use the
second route — the tiny taped-out ASIC handles whatever cell-mesh-
adjacent function gets designed into it; a separately-designed carrier
board provides whichever real RISC controller and host interface is
actually wanted, rather than inheriting Tiny Tapeout's own RP2040
choice.

**Real, honest category distinction, worth restating precisely:** this
is a fundamentally different KIND of decision than any FPGA work in
this project. Every RTL file built so far is reprogram-for-free FPGA
work. A real tapeout — even a tiny one — means real mask costs, a real
fabrication run with multi-month turnaround, and mistakes get baked
into physical silicon with no re-flash option. A strategic-level
decision, not an engineering-scope one.

**A related, explicitly ruled-OUT-for-now idea**: matching a UniCell
card's pins to a standard DIMM/RAM socket and actually speaking real
DDR to a host's own memory controller — genuinely a much harder bar
than matching pins (modern DDR requires the host's memory controller
to run real training/calibration sequences assuming genuine DRAM
electrical behavior on the other end). If the real goal is host-
adjacent memory-mapped access, **CXL** is the real, modern, industry-
supported route already built for exactly that — not something to
reverse-engineer from scratch. The DIMM-shaped-connector-with-a-
custom-protocol version (below) is a different, real, separable idea
that doesn't require any of this.

## Idea 3: a RAM-form-factor backplane, scaled with real math

**The real, concrete shape, worked through with real numbers:** small,
cheap, mechanically-standard RAM-style sockets carrying UniCell dies —
not speaking real DDR (see above), just borrowing the connector, run
as a PARALLEL bus (sidestepping DDR training entirely). At 8 dies per
card and 8 cards per backplane: **64 parallel lanes per backplane** —
the arithmetic checks out cleanly. Multiple backplanes would link
through a real switch fabric (a "64×32" aggregator was discussed,
most likely real, standard OVERSUBSCRIPTION — 64 inputs onto 32
trunk lanes, betting traffic is bursty rather than every lane wanting
full simultaneous bandwidth, the same legitimate tradeoff real
InfiniBand/Clos-topology fabrics already make routinely), giving each
backplane dedicated channels to the others as needed, then one
breakout link to a host machine — a pool of cards presenting,
with real caveats around bus contention, as something closer to one
unit.

**The real, honestly-acknowledged ceiling, and why photonics is the
actual answer past it, not just a nicer version of the same thing:**
an electrical crossbar trying to offer genuine full-line-rate,
non-blocking connectivity across all 64 lanes simultaneously needs its
own internal switching fabric to sustain that aggregate bandwidth
INSIDE the switch chip itself — heat, power, and interconnect density
are real physical walls electronic fabrics hit at scale. This is the
same real reason hyperscalers have begun moving toward real optical
circuit switching in their own datacenters (Google's own published
work is the well-known public example) — not because optics are
inherently superior, but because they avoid converting everything back
to electrical and re-switching it at every hop.

**Fiber for aggregation specifically (not DIMM-pin-level optics) is
real and achievable with hardware that exists TODAY**, once one real
constraint is respected: the current Arria 10 board (IEI Mustang-
F100-A10) has NO external transceiver breakout at all — PCIe x8, 12V,
and JTAG only, already confirmed elsewhere in this project's own
multi-card architecture decision. So fiber aggregation today has to
happen at the HOST level, not the card level: each UniCell card stays
on its existing PCIe connection to its own host; hosts carry standard,
off-the-shelf fiber NICs (Ethernet or InfiniBand); a small rack of such
hosts connects through an ordinary network switch. This is a concrete,
real instance of the multi-card architecture's own already-named
"planned smart NIC" path. Native fiber ports ON a future UniCell card
directly would need a genuinely new board with real transceiver
breakout — a separate, later project.

## Real, honest summary of scope

Nothing in this note is built, scoped into steps, or committed to.
Every idea here is real, connects to an already-known limitation in
the current system, and is worth NOT having to re-derive from scratch
whenever a next hardware generation is actually being planned — that
is the entire purpose of this document.
