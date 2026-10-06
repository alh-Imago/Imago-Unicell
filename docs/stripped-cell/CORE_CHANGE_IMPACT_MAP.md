# Core Change Impact Map — where a real change ripples to

**Purpose:** every time a core's own real capability changes — a new
config field, a new delivery behaviour — that change potentially
touches a whole chain of OTHER files that each independently know
something about that core. This project has now hit that chain for
real twice (`#853`/`#854`, adding `mul`'s `wide_mode`) and found it
runs deeper than it looks the first time. This doc exists so the next
change starts from a checklist, not a rediscovery.

**How to use it:** find the kind of change you're making below, work
the list top to bottom, checking each file even when you're confident
it doesn't apply — `#854`'s own real discovery was specifically that
several of these looked unrelated until a full regression run proved
otherwise.

---

## Adding a new `core_config` field to an existing core

Real, complete checklist, in the order `#853`/`#854` actually hit them:

1. **The RTL core file itself** (`fpga/verilog/<core>_cell_v*.v`, and
   its `_v4c`/`v5c`-style sibling if one exists — a field usually needs
   adding to BOTH, or deliberately to only one, stated explicitly why).
2. **The RTL testbench** (`tb_<core>_cell_v*.v`) — new real checks for
   the new field's behaviour, plus a full re-run of the EXISTING
   testbench for any sibling version left unchanged, confirming zero
   regression.
3. **VM dispatch** (`nano/unicell_super_automaton_v1.py`):
   - The `SuperCell` dataclass field(s) for the new state.
   - The `elif core == "<core>":` config-loading block (`cfg.get(...)`).
   - `_deliver_<core>()`, `_offer_state_<core>()`, and (if the new
     field changes when a value counts as "delivered")
     `_clear_valid_<core>()` — `#854`'s own real case needed all three.
4. **Tile library schema** (`nano/vix_tile_library_v1.py`) — the
   `VixTileSpec`'s own `param_names` (a genuinely REQUIRED list, no
   silent defaults — every existing caller must state the new field
   explicitly, confirmed directly against `_resolve()`'s own
   validation) or `fixed_core_config` if the field is being pinned to
   one value for a whole tile variant, not left runtime-configurable.
5. **JSON field schema** (`nano/root_definition.json`) — a real,
   SEPARATE schema from the tile library, checked independently by
   `SuperCell.from_record()`. Carve the new field out of whatever
   `reserved` range currently covers its real bit position; update
   `source_file` if the field only exists in one RTL variant.
6. **Hand-typed field schema** (`nano/icm_v3.py`'s own `_<CORE>_FIELDS`
   dict) — a real, THIRD, independently-maintained copy of the same
   bit-position knowledge. Easy to miss entirely; caught only because
   `tests/vm/test_generic_field_codec_v1.py` cross-checks it against
   the JSON schema directly — that test existing at all is why this
   layer surfaces instead of silently drifting.
7. **Opcode library** (`nano/vix_opcode_library_v1.py`) — every real
   `LibraryEntry` registration whose `tile=` points at this tile needs
   its `extra_params` updated to include the new field (even just
   `{"new_field": 0}` to preserve existing behaviour) the moment the
   field becomes a REQUIRED param in step 4.
8. **DAG dispatcher placement call sites**
   (`nano/vix_dag_dispatcher_v1.py`) — confirm the actual `vtl.place()`
   call for this tile's `port_style` genuinely passes
   `params=dict(entry.extra_params)` through. `#854` found a real,
   PRE-EXISTING gap here: the "named" port-style branch never passed
   `extra_params` at all, silently harmless for years because every
   "named" tile's own `extra_params` happened to be empty until now.
   Check every `port_style` branch, not just the one your tile uses —
   a gap in one can hide until a totally different tile's own change
   exposes it.
9. **Any direct test-file calls to `vtl.place()`** for this tile,
   outside the dispatcher (`grep -rn "TILE_<CORE>" tests/`) — each
   needs the new required param stated explicitly too.
10. **`docs/stripped-cell/CELL_CHEATSHEET.md`** — the human-readable
    quick reference. Update the affected core's own row; if the new
    field is real hardware-side capability (not just internal
    bookkeeping), it belongs in the "Capability" column, not just
    "Notes".
11. **`command_cell_v4.v`'s own programmer mode** — check whether it
    needs anything at all. Usually it doesn't: it's a pure, generic
    word-relay with zero decode logic of its own (confirmed directly,
    `#854`) — it never knows what any `PROG_ID` means for any target,
    so a new field with its own real `PROG_ID` slot is programmable
    through it automatically, for free. Only reconsider this if the
    new field needs something command_cell doesn't already do (e.g.
    a multi-word atomic write, or a response it needs to interpret).
12. **`composed_tile_library_v1.py` / `dsp_wrapper_tile_library_v1.py`**
    — check whether this tile is used as a sub-component of a composed
    tile, or has a parallel entry in the DSP-wrapper library (a
    genuinely separate mechanism, real FPGA hard-block wrappers, not
    VIX cores at all — `mul`'s own `dsp_mul` entry there is REAL IEEE-
    754 float multiply via hard-block silicon, unrelated to `wide_mode`
    specifically, but worth knowing it exists before assuming "mul" in
    a grep hit means the VIX core).
13. **Full regression** (`python3 -m pytest tests/vm/ tests/tools/`) —
    run it BEFORE writing up the change as done. `#854`'s own real
    number: making one field required broke 29 tests across 6 files on
    the first run, none of them obviously related to `mul` by name.

## Lessons that cost real time (`#864`-`#868`) -- read before concluding anything about the VM

- **Two VM homes exist.** `unicell_super_automaton_v1.py` (`SuperCell`/`SuperGrid`, 8 core types) and
  `vix_carrier_automaton_v1.py` (`VixCarrierCell`/`VixCarrierGrid`, which SUBCLASSES the first and adds
  `command`). A grep against one file is not evidence about the other. `#864` claimed "the VM has no
  command dispatch" from exactly that mistake. Check `CORES_AND_WRAPPERS_REFERENCE.md` first.
- **Constants are not capability.** `PROG_ID_MODE`..`COMMAND_PROG_ID_COMPLETE` sat in the carrier module
  for months; nothing wired them into `program_word()`, which raised on a command cell. `#866` claimed it
  worked from reading them. Call the method before claiming it.
- **Some VM tests are scripts, not pytest functions** (`test_vix_carrier_automaton_v1.py`, `..._mesh_v1.py`,
  `..._slot_v1.py`): plain `pytest` reports "no tests ran". Run them directly
  (`python3 tests/vm/<file>.py`) as part of any regression touching `VixCarrierCell`.
- **A `fixed_mode` `ram` needs `data_valid` set separately** (`cfg_data[13]` / `load_data_valid`) or it
  holds its value and never offers it (`#867`).
- **Never feed a command cell from several neighbours at once.** VM/RTL differ on acking (see the command
  row in `CELL_CHEATSHEET.md`); a serialized `ram` chain is both the design intent and the safe shape.
- **Feed a two-operand cell (`adder`, `mul`, `nano`) from ONE interleaved stream, never two faces.** Two operands arriving on the SAME tick OR-combine into a single operand, silently. My first cadence measurement fed A and B from two faces: it returned "5 of 10 results" and a plausible "4 ticks/output", both wrong (each product had consumed two pairs). A single stream `a0, b0, a1, b1, ...` uses the first-come-first-served capture correctly. Always check the VALUES of a measurement, not just its timing.
- **Never force a `ram` cell empty from a harness.** Setting `valid` to 0 via `program_word` leaves the cell's `pending_ack` set, and the stale offer re-fires on the next tick: it refilled 7 of 8 cleared output cells with old data and silently corrupted a multi-pass run (#885). Give the chain a real consumer instead -- a sink `accumulator` acknowledges and discards -- and tap its `deliver` to read results as they arrive.
- **Check that a test function actually depends on its input.** My first 4-stage function (XOR, AND, OR, XNOR with one constant) returned 0xFFFFFFFF for every item: AND-then-OR collapses to the constant. With a CONSTANT operand every bitwise gate is a one-input function per bit, and the lossless ones (XOR/XNOR/NOT) commute, so an order-sensitive AND information-preserving composition cannot exist; search for a usable one and check it.
- **Stage the next pass only when the source gate has frozen the empty source.** Staging on "results are back" lets the next pass start under the OLD configuration and the reprogram land mid-pass (#885).
- **Mutation-testing gotcha:** editing a file to a same-length variant and restoring it within one second
  can leave a stale `.pyc` that keeps running the MUTATED code. Clear `__pycache__` after restoring.

## Changing a core's delivery/offer PROTOCOL (not just adding a field)

Real, additional steps beyond the checklist above — `mul`'s `wide_mode`
needed both, since the new field also changes WHEN a value counts as
delivered, not just what config exists:

- **`_offer_state_<core>()`** may need to report a DIFFERENT value
  depending on which phase of a multi-phase delivery is active (see
  `mul_captured_hi`/`mul_delivering_hi` in `unicell_super_automaton_v1.py`
  for the real, working shape).
- **`_clear_valid_<core>()`** — the generic hook every single-shot
  core's own drain-detection calls — may need to NOT clear validity on
  every drain anymore, reloading for a further real delivery instead.
  Mirror the real, tested RTL's own `start_hi_phase`/`genuinely_done`
  split exactly rather than re-deriving the logic independently.
- **Capture-blocking** (`capture_now`/`block_for_wide` in the RTL, the
  equivalent guard in `_deliver_<core>()`) may need to cover the WHOLE
  multi-phase window, not just "a result is currently pending" — a
  real, deliberate design decision (`#853`), not automatic.
- **Test construction matters more than usual.** A single dead-end
  sink structurally cannot receive a SECOND delivery from a
  multi-phase source — `ram_flowing`'s own real capture rule
  (`_deliver_ram`) refuses a new value while `ram_data_valid` is still
  set, and nothing drains a dead-end sink to free it. Use a real,
  two-stage relay chain (sink1 -> sink2) so the first sink can
  genuinely empty itself between deliveries — confirmed by tracing
  per-tick state before trusting a passing/failing result either way.

## Changing a sub/flex (v4s/v4sa) cell, or adding a target-agnostic ICM field (`#956`-`#986`)

*Added 2026-10-06. This is the chain the second-output work (`#974`-`#981`) and the
FlexGrid fixes (`#968`-`#973`) actually hit, in order. Items 7-10 overlap the list above;
the rest are new files that did not exist when it was written.*

1. **The cell** (`sub/verilog/<core>_cell_v4sa.v`, and `_v4s` if the change applies to sub).
   If a capability is deliberately flex-only, say so. `#919`/`#920` is the precedent for
   deciding whether a family-local capability creates a cross-target obligation.
2. **Its bench** (`sub/verilog/tb_<core>_cell_v4sa*.v`), including the width-specific
   benches. Mutation-check the new cases: break the RTL on purpose and confirm the bench
   fails (every recent entry did this, and twice it found a weak bench, `#941`/`#956`).
3. **Every instantiation of a changed port list.** That means the hand-built chains and
   tops (`adder_chain_v4sa.v`, `adder_v4sa_top_single.v`), the benches, the ICM flex
   emitter (`tools/flexsub_icm_flex_v1.py`), and the step-1 assembler's shapes
   (`tools/flexsub_assemble_v1.py`; its parsed-port check catches a mismatch). **A new
   output with its own ack must be tied high where unused**, or the cell stalls on an
   unconsumed second word (`#974`).
4. **The planner and emitters.** `tools/flexsub_icm_generate_v1.plan()` decides what each
   family can build and refuses the rest with a reason. `FlexGrid` imports this planner,
   so it is the single source of truth for both. After it come the family emitters
   (`flexsub_icm_flex_v1.py` for flex, `flexsub_icm_generate_v1.py` for sub) and the
   netlist extractor's refusals (`flexsub_icm_netlist_v1.py`).
5. **The VM mirror** (`nano/flex_grid_v1.py`): the flex handler for the core, checked against
   the **generated RTL as the oracle** at several widths (4, 8, 18, 32, 36). If the RTL
   cannot do something at some width, FlexGrid must refuse with the reason, not guess.
6. **The std VM** (`nano/unicell_super_automaton_v1.py`): if a new ICM field is one the std
   cells cannot honour, the std loader must **refuse** it. Do not let it be accepted and
   silently ignored (`#976`'s `carry_mode` refusal, `#981`'s `second_downstream_mask`
   refusal). Keep these edits to the minimum and flag them in the ledger.
7. **The ICM field itself**: `nano/icm_v3.py` (`_<CORE>_FIELDS`, and
   `SECOND_OUTPUT_ALIASES` / `canonical_core_config()` if an old name stays accepted) and
   `nano/root_definition.json`. Renaming a stored key changes `record_hash` for files
   that used the old name (`#980`).
8. **The RTL validator** (`nano/validate_icm_v3_against_rtl_v1.py`): a field that exists
   only in the flex cells goes in `_FLEX_ONLY_FIELDS`. A field the standard RTL calls by
   another name goes in `_RTL_NAME_OF`.
9. **The capability table** (`nano/target_capabilities_v1.py`): which targets (std / flex
   / sub) can meet the new need. `check_records` is what makes the compiler refuse at
   compile time.
10. **The compiler side.** In the tile library (`nano/vix_tile_library_v1.py`), use
    **`optional_params`, not a required param**: making `carry_mode` required broke 40
    tests (`#976`). Then the opcode library, the DAG dispatcher (refuse a flag on a core
    that has no such output: never drop it silently, `#979`), and the VIX backend's
    `place` fields.
11. **Costs.** If area changes, re-run `tools/flex_width_sweep_v1.py` and regenerate the
    Tang MAN (`tools/man_gen/gen_tang_nano_20k_man.py`, apycula pinned to 0.32) so
    `cell_costs` follows. If earlier recorded figures included the change by accident,
    say so in the ledger as a correction (`#976` corrected `#974`/`#975`).
12. **Docs**: `sub/README.md`, `ICM_V3_FORMAT.md` (and `ICM_VIX_FORMAT.md` if the field is a
    stated need), `docs/man/README.md` if the MAN changed, and this map.
13. **Regression with the toolchain present**: `which iverilog yosys` first (the flex/sub
    suites skip and exit 0 without iverilog, `#965`), then `python3 -m pytest tests/vm -q`
    and every `tests/test_*.py` script.

## Adding a genuinely new core type

Out of scope for this doc's own real, checked detail (no core has been
added fresh since this map was written) — expect this checklist's own
items 3-13 to all apply, PLUS real new entries in `CORE_NAMES`
(`icm_v3.py`), the carrier's own `core_select` numbering
(`unicell_vix_carrier_v1[d].v`), and `CELL_CHEATSHEET.md`'s own
core-select table. Treat this section as a stub to fill in properly
the next time it actually happens, not a complete list yet.

---

**Keep this map current.** The moment a real change finds a NEW file
in the chain this doc doesn't already list, add it here in the same
turn — this doc's own value is directly proportional to how honestly
it reflects what's actually been hit, not what seems like it should be
hit in principle.
