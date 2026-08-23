# Physical placement data

Real, per-instance physical bounding boxes, merging real Quartus
post-fit placement into a SHAPE file — closes the "no physical
placement" gap in `docs/shapes/README.md` (`points.md` #456/#457).

## Real, honest history of how this was found

Two earlier approaches were tried and found insufficient before this
one, recorded here so nobody repeats the same dead ends:

1. **Back-Annotate Assignments (Device, or Pin & Device)** — the
   obvious-looking GUI feature. Result: only 8 nodes written, "No
   location assignments were back-annotated" reported three times.
   Real reason, confirmed against Intel's own docs: this feature
   *preserves already-assigned locations across future recompiles* —
   it does not export a full floorplan of everything the Fitter
   actually placed.
2. **Back-Annotate Assignments (Advanced type)** — checked for a
   separate "Cell" or "Routing" category that might give per-primitive
   placement. In Quartus Prime 25.1 Standard Edition, the Advanced
   dialog only offers "Device" and "LogicLock regions" — no such
   option exists in this edition/version.
3. **The real answer: Quartus's own Control Signals report** (a
   section of the real Fitter Report) — see below.

## How to generate the input file

After a completed Fit, open the **Compilation Report → Fitter →
Control Signals** section. This lists every real primitive that
drives some kind of control role (clock, clock-enable, synchronous or
asynchronous clear/load, write-enable) in the design, along with its
real physical location. Export or copy it as tab-separated text.

**Real, honest coverage caveat:** this is not literally every register
in the design — only ones driving a control role somewhere. In
practice this is substantial coverage (confirmed: spans every sub-core
in every super-carrier cell, every fixed connection-point cell, and
the host bridge's own internal ISSP hierarchy), but not 100%
exhaustive by construction.

## How to run the extractor

```
python3 tools/placement_extract_v1.py <control_signals.tsv> --shape <shape.json> [-o output.json]
```

The real command used for the file checked into this directory:

```
python3 tools/placement_extract_v1.py \
    docs/shapes/placement/top_sentinel_gather_shared_bram_v3.control_signals.tsv \
    --shape docs/shapes/top_sentinel_gather_shared_bram_v3.shape.json \
    -o docs/shapes/placement/top_sentinel_gather_shared_bram_v3.placement.json
```

## What it computes, and what it deliberately does NOT claim

A real RTL instance (e.g. `unicell_super_v1:H1`) is built from dozens
of real primitives that Quartus scatters across many separate LAB/
MLABCELL locations — confirmed directly from Alan's own real report:
the super carrier shell places all 6 of its possible cores
simultaneously (accumulator, adder, RAM, compare, latch, nano), even
though only one is active via `core_select` at runtime, so a single
cell's own real footprint is genuinely wide, not one point.

So this tool does **not** try to give one X/Y per instance. For each
known SHAPE instance, it computes the real **bounding box** — min/max
X, min/max Y — across every primitive found under that instance's own
hierarchy prefix in the Control Signals report.

**A real, important caveat, stated plainly rather than left implicit:
a bounding box is a range between real observed points, not a claim
that every coordinate inside it is occupied.** `H1`'s own real x-range
(101–114) happens to span across real DSP/M20K columns at x=102 and
x=108 (per `docs/man/mustang-f100-a10.man.json`'s own real device
data) — but none of `H1`'s own actual sample points land there. The
box means "this instance's real primitives were found somewhere
inside this rectangle," never "this instance fills the whole
rectangle."

## Output schema

```
{
  "placement_version": "1.0",
  "source_control_signals_file": "...",
  "source_shape_file": "...",
  "card_id": "...",                  // from the merged SHAPE file
  "real_rows_parsed": 104,           // real fabric-grid rows successfully parsed
  "pin_rows_skipped": 1,             // rows with a PIN_ location (e.g. CLK_100M itself) — not part of the internal placement grid, not an error
  "unparsed_rows": [ ... ],          // any row that couldn't be parsed, flagged honestly, never silently dropped
  "coverage_note": "...",
  "instances": {
    "H1": {
      "status": "real_partial_coverage",  // or "no_data" if zero rows matched this instance
      "sample_count": 18,                 // how many real primitives contributed to this box
      "x_range": [101, 114],
      "y_range": [2, 13],
      "block_types_seen": ["LABCELL", "MLABCELL"]
    }
  }
}
```

An instance with `"status": "no_data"` means zero rows in this
specific report matched that instance's hierarchy prefix — reported
explicitly rather than assumed to have zero footprint. This can happen
for a real instance whose own primitives happen not to drive any
control-role signal captured in this particular report.

## Real result, `top_sentinel_gather_shared_bram_v3`

All 13 SHAPE instances got real coverage (zero `no_data`), 104/105
real rows parsed cleanly, zero unparsed rows. `H1`, `H2`, `H3`, and
`QUEUE` (the `programmable_substrate` cells) each show a genuinely wide
real footprint (dozens of LAB columns, several rows), consistent with
each one placing all 6 possible cores simultaneously — a real, direct,
independent confirmation of something already known architecturally,
not just an assumption.
