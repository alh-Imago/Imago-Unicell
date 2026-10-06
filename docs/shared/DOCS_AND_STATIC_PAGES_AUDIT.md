# Docs & static pages — real staleness audit, 2026-09-07

*Captured per Alan's own direct request, extending the `#676`/`#677`
orphaned-work audit to documentation and static HTML output
specifically ("add full doc review and update static html pages to
the list as well, some will be behind and some will not have changed,
but they need completing"). A real audit, not a rewrite — every claim
below checked directly (git dates, keyword searches against actual
file content, cross-referenced against the real ledger), matching the
same method `POINTS_STATUS_AUDIT.md`/`_2.md` already established.
Nothing rewritten in this pass; this is the map, not the fix.*

## Update, 2026-10-06 (ledger #995): what is left

The quick fixes are done: `tests/vm/README.md` was rewritten, `TODO.md`
fixed, and status banners were added to `ICM_FORMAT.md`,
`SYSTEM_MECHANICS.md`, `MIF_FORMAT.md`, `core_creation_guide.md`,
`AUDIT.md` and `STRUCTURE_AUDIT.md`. A full keyword and staleness scan of
every live `.md` outside `archeology/` and the dated design notes finds
nothing else misdescribing the current state. The one remaining gap, a
done/pending map for ledger #593 onward, is now
`POINTS_STATUS_AUDIT_3.md` (#593-#995). **Nothing on this audit's list
is outstanding as of #996.** The one exception is #856's standing
request for another full documentation pass once the fp32 work is
complete.

## Update, 2026-10-06 (ledger #992): static pages

| page | what changed | checked |
|---|---|---|
| `docs/manual.html` | rebuilt with `docs/build_manual.py` after its `SECTIONS` were corrected (intros; new parts: sub/README, ICM-VIX, CELL_GOTCHAS, Tang getting-started, MAN README, TOOLCHAIN_SETUP, tools/README). `current/latest.md` is now linked rather than embedded, and the page went from 746 KB to 515 KB | Chromium, desktop and phone: no script errors, no horizontal scroll, 0 of 88 relative links broken |
| `tools/manual_generate_v1.py` (live `/manual`) | `DEFAULT_SOURCES` gains sub/README, the cores reference, both ICM format docs and the Tang getting-started guide | generates; `tests/tools` 49 passed |
| `tools/explainers/cell_pipeline_explainer.html` | core field tables for core_select 1-9 now generated from `icm_v3.py` (it lacked mul, priority, adder subtract/second output, accumulator step/pulse/threshold, latch toggle); `shift_fine` control added; **existing bug fixed:** the add-on controls never triggered a recompute | 300 random configurations (10 cores x 30) driven through the page in Chromium == `icm_v3.encode_super_latch()`, 0 mismatches |
| `tools/explainers/chaos_topology_demo.html` | unchanged: a captured historical run (2026-09-07 finding stands) | — |
| `gh-pages` site (now 6 pages, with `explainer.html`) | **Published at #994** (fast-forward to `f049875`). |
| `gh-pages` site, #992 detail | Home, Architecture, Status and Docs rewritten for both hardware lines (Tang Nano / sub-flex current, Arria 10 earlier); figures renumbered across pages; Contact unchanged; layout and CSS untouched | Chromium, desktop and phone: no horizontal scroll; tags balanced. **Committed on a local branch made from `gh-pages`, NOT pushed**: publishing waits on Alan's go-ahead |

The site's docs page links to `blob/main/...`, so the updated docs show
there once this branch is merged to `main`.

## Update, 2026-10-06 (ledger #991): second pass — the manual's source docs, and what the generator needs

Alan: the manual page is built by a Python tool from the other docs,
so the docs have to be straight before it is run. This pass covered
every doc the two generators read, plus the rest of the #990
"still behind" list.

| doc | what changed |
|---|---|
| `docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md` | a "four cell generations" table, and a sub/flex section with each flex cell's ports, notes and measured cost at W=18; the VIX status rows that said "no ICM format" and "no compiler" corrected |
| `docs/stripped-cell/UNICELL_S_DSL_MANUAL.md` | **two examples no longer compiled** (§3.5 and §5.2: `step_amount` became a required accumulator param). Fixed; all 5 program examples recompiled OK. The Tier-0 table re-checked against the live registry: 14 tiles, 6 were missing (`subtractor`, `sequencer`, `nano_hold_trigger`, `nano_loop_var`, `nano_loop_ctrl`, `nano_loop_ctrl_desc`); §8 updated, including that sub/flex are reached through ICM files and the assembler. (The 2026-09-07 note below says `select`/`icmp eq` and `branch` were missing; they had already been added.) |
| `docs/stripped-cell/SUPER_CELL_INTERNALS.md`, `CELL_INTERNALS.md` | status banners: accurate for the Arria 10 line, and where the current-line equivalents are |
| `docs/stripped-cell/CELL_GOTCHAS.md` | 14 traps from #875-#986 (signed comparator, single-shot preloaded ram, level-source probing, arrival-order pairing, unstarted nano, forcing harness state, second-port acks, `armed`, mask width, unsupported shifts, measurement collapse, skipping suites) |
| `docs/stripped-cell/CELL_CHEATSHEET.md` | a sub-vs-flex comparison table |
| `docs/shared/TOOLCHAIN_SETUP.md` | the open Gowin flow (iverilog, yosys, nextpnr-himbaechel, apycula, openFPGALoader), with the version caveats |
| `fpga/README_FPGA.md` | a banner: the body describes the archived iCEBreaker line (its core files are in `archeology/`), with a map of what `fpga/` holds now |
| `current/PLAN.md` | a 2026-10-06 block listing the open work recorded in #946-#986 (not an order) |
| `current/latest.md` | header line replaced (it read "as of 2026-09-28") |

**Still not updated:** the points status audits (#1-#592 only).
`docs/shapes/README.md` and `docs/full-cell/` were checked and need
nothing; they are not line-specific.

### Before running the manual generators

**`docs/build_manual.py` (writes `docs/manual.html`).** Its `SECTIONS`
list holds hard-coded intro text and the source list. These are code,
not docs, so they were left for an explicit go-ahead:

- "The Idea" intro: the "two-arrival firing model" sentence describes
  the Arria-era cells (sub/flex cells fire on valid / valid+ack); "If
  the PCIe host-integration work succeeds" is out of date (the planned
  host is an ESP32 over SPI, #888).
- "The Cell" intro: calls the super carrier shell "the active line" and
  says "6 real cores". It has no part for `sub/README.md`.
- "ICM v3" intro: "every one of the 6 cores". There is no part for
  `ICM_VIX_FORMAT.md`.
- "Hardware" intro: Arria 10 figures only. It has no parts for
  `docs/man/tang-nano-20k-getting-started.md` or
  `docs/shared/TOOLCHAIN_SETUP.md`.
- "Roadmap" embeds `current/latest.md` in full. That file is now
  ~940 KB (the whole current `manual.html` is 746 KB), so the rebuilt
  page would be well over 1 MB from that one part. Linking it, or
  embedding only its "Read this first" block, would keep the page usable.
- The "Start" section already pulls `README.md` and `docs/README.md`,
  which are current.

**`tools/manual_generate_v1.py` (the live `/manual` route).** Its
`DEFAULT_SOURCES` has no `sub/README.md`, `ICM_V3_FORMAT.md`,
`ICM_VIX_FORMAT.md` or `CORES_AND_WRAPPERS_REFERENCE.md`.

The 2026-09-07 points about `docs/manual.html` possibly being orphaned
(below) still stand. Decide which of the two generators is the one to
keep before investing in both.

## Update, 2026-10-06 (ledger #990): the Tang Nano / sub-flex catch-up, first pass

The ledger had moved about 100 entries past the docs: the Tang Nano 20K
(#886 onward), the sub and flex cell families (#898-#957), the Flex-Sub
assembler (#921-#957), FlexGrid (#960-#973), and the second ports and
target-agnostic ICM flags (#974-#986). Before this pass, none of the
reference docs below mentioned `v4sa`, `FlexGrid`, `min_bit_width`,
`second_output`, `-nowidelut` or `native_width` (checked by keyword
count). Brought current in this pass, each against the code or the
ledger entry it cites:

| doc | what changed |
|---|---|
| `README.md` (root) | new "Where things stand": the two hardware lines, the sub/flex families, the assembler, the target-agnostic ICM, FlexGrid, fp32 on cells, the board. The Arria 10 sections are kept and relabelled as the earlier line. Quick start covers the toolchain check and the flex/sub suites |
| `docs/README.md` | a "Start here (2026-10)" block pointing at the current-line docs |
| `docs/stripped-cell/ICM_V3_FORMAT.md` | all 10 cores' tables (it showed 6, and said VM dispatch was unbuilt); `shift_fine`; `second_output` / `second_downstream_mask`; the one-number shift per target; the mask at other widths; `min_bit_width`; the capability table |
| `docs/stripped-cell/ICM_VIX_FORMAT.md` | "not built" list corrected (the VIX compiler, tile library and workbench load exist); a section on the need-stating fields |
| `docs/stripped-cell/CORE_CHANGE_IMPACT_MAP.md` | new checklist for changing a sub/flex cell or adding a target-agnostic field |
| `docs/man/README.md` | ESP32 host corrected to the ESP32-D (#888); board result (#896); `native_width`, `native_ff_variants`, `cell_costs` |
| `sub/README.md` | a section for #956-#986 (sequencer, FlexGrid and the four RTL limits, second ports, cascade, sweep, free shift, fp32); Status corrected |
| `tools/README.md` | the Flex-Sub assembler tools and flags, the Gowin measurement tools and their pitfalls, the MAN generator |
| `tests/README.md` | rewritten: it described iCEBreaker UART tests. Now covers the toolchain trap and how each suite runs |
| `current/START.md` | a current reading list and toolchain check above the 2026-08 list |
| `tools/project_assemble_v1.py` `--icm` help | no longer says the flex generator is unbuilt |

**Still behind after this pass (not yet updated). All but the points status audits were done in the #991 pass above:**

- `docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md` and
  `CELL_CHEATSHEET.md`: no sub/flex rows (the merge core, the
  comparator's threshold port, second ports). `sub/README.md` is
  the current reference for those cells until they gain rows.
- `docs/stripped-cell/CELL_GOTCHAS.md`: the traps found since #946 are
  not in it. Examples: the comparator is signed, so bit 31 reads
  negative (#984); a preloaded non-fixed ram is single-shot in the VM
  (#939); an exit cell is not a valid probe of a level source (#938);
  the VM pairs two-operand cells by arrival order (#976); same-tick
  operands OR-combine, so feed two-operand cells from one interleaved
  stream (#883).
- `docs/shared/TOOLCHAIN_SETUP.md`: Quartus / Windows only. It has no
  open Gowin flow (yosys, `yowasp-nextpnr-himbaechel-gowin`, apycula
  `gowin_pack`, flashing). `tests/README.md` and
  `docs/man/tang-nano-20k-getting-started.md` cover parts of it.
- `fpga/README_FPGA.md`: not reviewed in this pass.
- `docs/shared/POINTS_STATUS_AUDIT*.md`: they cover #1-#592 only;
  there is no done/pending map for #593-#986.
- `current/latest.md`'s top-line header still reads "as of 2026-09-28".
  The entries under it are current.
- The earlier static-page findings below (`docs/manual.html`, the
  explainer HTML, the `gh-pages` site) are unchanged and still stand.

## Method

Every live (non-`archeology/`) `.md` doc listed with its real last-
edit date, checked against the most recent major architecture
landmarks not yet reflected anywhere in the "living" reference docs:
the command core (`#644`, 2026-09-04), the VIX Carrier and its 9 real
cardinal shells (`#639`/`#645`-`#647`, 2026-09-04/05), and nano's
loop-routing field extension (`#650`, 2026-09-05). All three live HTML
files and the separate `gh-pages` branch (5 pages) checked the same
way — by direct content inspection, not assumed from their own
generation date alone.

## Canonical/"living" reference docs — confirmed stale, with the
specific evidence, not just a date guess

**`docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md`** (last edited
2026-08-25) — the most stale of the group. Explicitly described in
`current/START.md` as a "living cross-cutting reference table," but
its own real content still says "all 6 cores" for the shell/VM and
lists only the original six core rows (nano/RAM/adder/accumulator/
comparator/latch) — zero mention of `branch`, `sequencer`, `command`,
the VIX Carrier, or shell versions v4 through v8. Three real core
types and the entire 9-core-carrier architecture are simply absent.

**`docs/stripped-cell/ICM_V3_FORMAT.md`** (last edited 2026-08-16) —
stale in a specific, self-documented way: its own "Scope, stated
honestly" section says nano's `dynamic_route_en`/`pattern_low`/
`pattern_equal`/`pattern_high` fields are "out of scope for this first
ICM v3 build... when that support is added to the RTL, the nano field
table gets extended to match." `#650` (2026-09-05) added exactly that
support to `icm_v3.py`'s real field table — the doc's own stated
trigger condition fired three weeks ago and the promised update never
happened.

**`docs/stripped-cell/SUPER_CELL_INTERNALS.md`** (last edited
2026-09-02, closer to current than the two above but still one
generation behind) — its own real content covers "the 8 real cores
(6 in v1, +1 sequencer in v2, +1 branch in v3)" in detail, but has zero
mention of the command core or the VIX Carrier, both landing two days
after this doc's own last edit.

**`docs/PROJECT_PHILOSOPHY.md`** (2026-08-26) and **`docs/README.md`**
(2026-08-16) — both zero mentions of VIX/command core/cardinal shells,
same gap as above, unsurprising given their own dates predate all of
it.

**`README.md`** (root, 2026-09-02) — the most current of the group,
already covering `project_assemble_v1.py`, LogicLock, and the moat
experiment, but still written before the command core/VIX Carrier
(`#644`/`#647`) and the LLVM IR loop-compiler work (`#653`/`#661`),
neither of which appears anywhere in it.

**`docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`** (2026-08-17) — covers
the DSL itself, which hasn't fundamentally changed, but doesn't
reflect the newer Tier-1-promoted compositions (`select`, `icmp eq`)
that landed well after this doc's own last edit, or the fact that
`branch` now has a real Tier-0 tile (`#608`).

**`current/VM_CORE_GAP_ANALYSIS.md`** (2026-08-08) — the oldest doc in
active use, a full sweep of "77 root Python files vs. the nano cell"
from before nearly the entire current session's own work existed.
Given how much of the VM has grown since, this is less "needs updating
in place" and more a real, honest open question: is this gap-analysis
still a useful living document at all, or has it been overtaken enough
that it belongs alongside `archeology/` as a historical snapshot
instead? Not decided here.

**Genuinely NOT flagged, checked directly rather than assumed clean:**
every `docs/stripped-cell/design-notes/*_scope.md` file — these are
explicitly point-in-time design notes, not living references, so
"staleness" doesn't apply to them the same way; each one already
states its own real scope and date plainly, matching this project's
own established discipline.

## Static HTML pages

**`docs/manual.html`** (baked 2026-08-18, via `docs/build_manual.py`'s
own `#376` rewrite) — stale on two independent counts, not one:
1. **Content-stale.** Baked from the doc set as it existed on day 3,
   before nearly everything covered above.
2. **Possibly orphaned entirely, not just stale.** `#558` (2026-08-31)
   built a genuinely separate, LIVE `/manual` route
   (`tools/manual_generate_v1.py`, wired into `nano/frontend_v1.py`)
   that regenerates fresh from the current repo on every real request
   — the actual, current, never-stale mechanism. Checked directly:
   `docs/manual.html` is referenced from nowhere else in the repo (not
   `README.md`, not `docs/README.md`, no GitHub Pages config found —
   the separate `gh-pages` branch is its own, unrelated 5-page site,
   not sourced from `docs/`). This may be a real, dead artifact with
   no live consumer at all, not just a page needing a re-bake — worth
   a conscious decision (re-bake for a genuine offline/file:// use
   case the live route can't serve, or retire `docs/build_manual.py`
   entirely now that `#558`'s mechanism exists) rather than assuming
   either answer.

**`tools/explainers/cell_pipeline_explainer.html`** (last rebuilt
2026-08-24, `#489`) — confirmed stale by direct inspection of its own
embedded `CORES` array: six core entries (nano/ram/adder/accumulator/
comparator/latch), matching the original `unicell_super_v1` shell
exactly — no `branch`, `sequencer`, or `command` entries, and nano's
own field list stops at `cardinal_edge`, missing every loop-routing
field `#650` added (`hold_in`/`fb_internal_in`/`a_reemit_in`/
`a_update_in`/`a_self_update_in`/`dynamic_route_en`/`pattern_low`/
`pattern_equal`/`pattern_high`). A real, concrete completion task:
extend `CORES` with the three missing core entries and nano's missing
fields, re-verified bit-for-bit against `icm_v3.py`'s own current
encoder exactly the way `#489` originally built it — not guessed at.

**`tools/explainers/chaos_topology_demo.html`** (built 2026-08-18,
`#393`) — checked directly and confirmed **NOT stale, needs no
completion.** Its own page text states plainly it's "a genuine
captured run of the VM... generated from a real run of
`tools/chaos_topology_v1.py`... not illustrative." It's a fixed
historical artifact documenting one specific real experiment's actual
output, not a living reference that's supposed to track current
architecture — the one item on this whole list that is genuinely
finished as-is.

## The public `gh-pages` site — confirmed stale, real evidence

Separate branch, 5 pages (`index.html`, `architecture.html`,
`status.html`, `docs.html`, `contact.html`), last touched 2026-08-17
(`#369`'s own full rewrite). Checked `status.html` directly: it states
**"211 tests"** (the real current count is 593 — 592 passed + 1
skipped, `#676`), and presents `unicell_super_v1.v`'s original 6-core
shell as **"the current architecture"** with its own 2026-08-24-era
Quartus figures (213 ALM, 200.76 MHz) — a real snapshot from before
`project_assemble_v1.py`'s own array-scale findings, the LogicLock/moat
investigation, the command core, the VIX Carrier, the LLVM IR loop
compiler, and `select`/`icmp eq` promotion, none of which appear
anywhere on the site. Three weeks and roughly 80 ledger entries behind
`main`. The same real discipline `#369` used originally (read all 5
pages in full, rewrite what's actually stale, verify every figure
against the real ledger, verify every link) is the right method for a
refresh pass — not attempted in this note.

## Real, honest summary — what this changes

**Nothing rewritten here.** Per Alan's own request, this is the map:
a full doc review confirming which "living" references have fallen
behind the actual architecture (all of the docs listed above except
the `*_scope.md` notes and `chaos_topology_demo.html`), which static
pages need real completion work (the two explainers, `gh-pages`), and
one genuine open question worth a conscious decision rather than
silent drift (`docs/manual.html`'s own continued reason to exist,
given `#558`'s live route). The single biggest, most concrete gap
across everything checked: **the command core and the 9-core VIX
Carrier — a full week of real, working RTL and VM code — appear in
precisely zero of this project's own standing reference documentation
or public-facing pages**, only in the ledger itself.
