# The real road ahead, in order — a consolidated roadmap (Alan/Claude, 2026-09-15)

*Alan's own direct sequencing, captured before it's lost, checked
against what actually exists rather than assumed from scratch. Each
piece below is genuinely substantial — its own session, at minimum,
matching Alan's own framing ("a whole other session by itself") for
the first item alone. Nothing built here; a real, ordered map of what
comes next and what each piece can actually build on.*

## The real order, as given

1. LLVM IR work (its own session)
2. Compiler design
3. The loader mechanism
4. The save mechanism
5. The frontend system (including an "open MAN file" concept)
6. Workbench expansion (cell inspection, freeze, slow, connections)
7. Separate chains loaded and run
8. User data entry and results attachments
9. *Then*, LaTeX and Trix — explicitly after all of the above

## Real, checked status against each item — what already exists, what's a genuine gap

**1. LLVM IR.** Real, existing scope: `llvm_ir_compiler_scope.md`,
`llvm_ir_frontend_completion_scope.md` (the more current of the two,
per its own header). Both just updated with `#742`'s own real,
hard-won placement constraints (`#743`). A real frontend
(`nano/llvm_ir_frontend_v1.py`) already exists and handles real
constructs (counting loops, `select`, `icmp eq`/`ne`) — but none of it
targets the VIX Carrier lineage or the hierarchical ICM format at all
yet (`#732`'s own status table: "not yet wired in"). Real, substantial,
standalone work, exactly as sized.

**2. Compiler design.** Real, existing scope:
`unicell_s_dsl_and_compiler_scope.md` — also just updated with the
same `#742` constraints. A real, concrete next step is already named
there (one real program end to end, with a deliberately-broken variant
proving diagnostics work) — not started.

**3. The loader mechanism.** Real, honest status: what exists today
(`nano/examples/hierarchical_icm_prototype_loader.py`) is explicitly a
prototype, built to test the hierarchical ICM design against a real
VM, not a production loader (stated plainly in its own docstring and
in `#740`-`#742`'s own notes). A real, production loader needs: `NC`
handling (never implemented in the prototype), nested-pattern support
(never needed by any of the three real examples built so far), and a
real answer to the `VixCarrierGrid` preload gap `#742` found (its own
`__init__` never runs the real freeze/preload/unfreeze logic at all —
recorded, not fixed).

**4. The save mechanism.** Real, already-resolved design, per `#737`
and confirmed via Alan's own direct restatement just now: the original
structure ICM stays unchanged, and a save is a real, separate
reference to that structure PLUS a diff file holding only the runtime
values that differ — keyed by the real, already-existing, stable
`cell_id` field. `#742`'s own prototype demonstrated a real
`cell_id`-keyed snapshot, but never a full, real round-trip (write a
diff file, then reload the original structure and REPLAY the diff back
onto a fresh grid) — that round-trip is real, remaining, concrete work,
not yet attempted.

**5. The frontend system, including "open a MAN file, arbitrary size,
no extras." Real, honest correction, checked directly rather than
re-asserted: this was already decided back at `points.md` #19/#23**
(2026-07-08 — genuinely early, exactly as Alan recalled), and the real
mechanism already exists, not a new requirement as this note first,
wrongly, claimed. `tools/man_generate_v1.py`'s own `build_man()`
already treats almost every field as real, optional data — `part`,
`family`, `jtag_idcode`, `dsp_total`, `m20k_bits`, `clk_pin`, `led0_
pin`, `led1_pin` all accept `None` cleanly, with the schema's own
other fields (package, board name, PCIe, DDR4) already defaulting to
`null`/empty regardless. Confirmed directly, not assumed: calling
`build_man(card_id="unconstrained-virtual", alm_total=1_000_000, ...
everything else None)` produces a real, valid, loadable "just cells"
MAN file, and it loads and checks cleanly through the existing
`load_man()`/`check_against_man()` (`#741`) machinery with zero
changes needed. **The one real, narrow, genuine gap:** `man_generate_
v1.py`'s own CLI marks several of these as `required=True` (`--part`,
`--alm-total`, `--dsp-total`, `--clk-pin`, `--led0-pin`, `--led1-pin`)
— a real, deliberate choice for a human hand-authoring a REAL card's
own MAN file (forcing explicit values rather than silent defaults),
but a genuine, minor obstacle to generating an "arbitrary size" MAN
file directly from the command line today. The underlying mechanism
needs no new design at all — a small, real CLI relaxation (or a
dedicated `--arbitrary-size ALM_TOTAL` convenience flag) is the only
real, remaining work here, not a genuine, un-scoped requirement.

**6. Workbench expansion (cell inspection, freeze, slow, connections)
— genuinely less green-field than it might look, checked directly
against `nano/workbench_v1.py` and `nano/vm_ai_port_v1.py` rather than
assumed.** Real, already-existing, exposed `WorkbenchController`
methods: `load_icm`/`save_icm`, `step`/`start_run`/`pause_run` (with a
real `ticks_per_sec` — this IS "slow," already built), `inject`/
`deliver` (real data entry), `state` (real, current results). A real,
underlying `describe_cell(row, col)` already exists too (`vm_ai_port_
v1.py`), giving genuine per-cell inspection — but `WorkbenchController`
itself doesn't expose it as its own real, named, HTTP-facing method
yet. **The real, genuine gaps, narrower than "needs the same
functionality as the earlier iteration" might suggest:** (a) `freeze`/
`unfreeze` exist at the real VM level (`SuperGrid.freeze_all()`/
`unfreeze_all()`) but aren't exposed through the workbench controller
at all; (b) no real "show connections" capability exists anywhere
checked so far — genuinely new, not found, not just unexposed; (c)
none of this — inspection, freeze, or connections — has been checked
against the NEW hierarchical ICM format's own real shape (patterns,
`(row,col,face)` links) at all, only the old, flat lineage.

**7. Separate chains loaded and run.** Real, existing, substantial
groundwork: `load_region`/`load_icm_region`/`list_regions`/
`clear_region` already let multiple, independently-named regions
coexist in one real workbench session — this is genuinely most of what
"separate chains" needs already. Real, honest, unchecked question: do
these regions support genuinely independent RUN control (pause one,
step another, freeze a third) or only independent LOADING into a
shared, single-stepped grid? Not verified either way here — real,
concrete follow-up before assuming this item is further along than it
is.

**8. User data entry and results attachments.** Real, existing
building blocks: `inject`/`deliver` (entry), `state` (results) — the
real, open question is what "attachments" means beyond reading current
state: a saved, named result set? A real export format? Genuinely
unscoped, not found described anywhere else in this project's own
notes.

**9. LaTeX and Trix — explicitly and correctly last.** Real, existing
scope already recorded separately (`mathtrix_mif_connection.md`, the
LaTeX-parser mentions across earlier ledger entries) — Alan's own
explicit ordering here (after everything above) is a real, useful,
recorded prioritization, not a new scoping decision, worth keeping on
record precisely as stated.

## Real, honest status

A consolidated roadmap, not a build plan for any one item. Every
number above is its own, real, separately-sized piece of work — item 1
alone was named by Alan as "a whole other session by itself," and nothing
here suggests any of the rest is smaller. Two real findings from
checking rather than assuming, both corrections to this note's own
first draft: item 5 ("open a MAN file, arbitrary size") is NOT a new
requirement — it was already decided at `points.md` #19/#23, and the
real mechanism (`man_generate_v1.py`'s own `build_man()`, almost every
field genuinely optional) already exists and was confirmed working
directly, with only a small, real CLI convenience gap remaining. Item
6 (workbench expansion) is genuinely less green-field than "needs the
same functionality as the earlier iteration" implies — most of the
real infrastructure already exists; freeze-exposure, connection-
visualization, and hierarchical-format compatibility are the real,
narrower, named gaps, not a full rebuild.
