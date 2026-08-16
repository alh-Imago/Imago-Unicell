# Session Start — Imago UniCell

**NOTE (2026-08-04 archeology sweep): this file now lives in `current/`,**
**alongside `PLAN.md` and `latest.md` — the three "live" documents.**
**Everything else has moved to `archeology/`, split into `full-cell/`**
**(the FULL cell / "dream" line, #107's fork — nearly all pre-existing**
**docs), `stripped-cell/` (the active nano line — currently has NO**
**standalone docs yet, see `archeology/stripped-cell/docs/README.md`**
**for why), and `shared/` (genuinely cross-cutting material). All paths**
**below are relative to the REPOSITORY ROOT (run these from a terminal**
**opened at the repo root, not from inside `current/`).**

## Read these first (in order)
```bash
git pull
git submodule update --init --recursive              # NEW (2026-08-16): grabs tools/onion -- appears EMPTY otherwise. See "Onion archival tool" note below before first use each fresh session.
cat fpga/verilog/unicell_stripped_v1.v                # GROUND TRUTH -- the ACTIVE line (#107's "reality" fork). Verilog logic wins every argument.
cat fpga/verilog/cell_wrapper_v2.v                    # host/JTAG path -- full parity with the cell's own internal mechanisms (#127)
cat fpga/verilog/cell_command_v1.v                    # the (tiny) command-cell companion module
cat archeology/full-cell/verilog/unicell64_v3.v       # the FULL cell -- separate "dream" line (#107), untouched since 2026-07-31, moved into archeology 2026-08-04 (#175)
cat archeology/full-cell/docs/core/ARCHITECTURE.md    # overall scheme + design intent (KNOWN OUT OF DATE vs current RTL, still gives conceptual grounding -- Alan, 2026-08-04)
cat archeology/shared/docs/software/VISION.md         # systems-view/ward-sentinel/PTT layers -- read for #152's freeze/ward connection
cat docs/shared/SYSTEM_MECHANICS.md               # NEW (2026-08-04): what's genuinely shared between both cell lines, verified against real RTL -- the first piece of the cleaner re-examined structure
cat docs/stripped-cell/CELL_INTERNALS.md          # NEW (2026-08-04): the nano cell's first standalone documentation -- field map, mechanisms, port list, built by reading unicell_stripped_v1.v directly
cat docs/stripped-cell/CORES_AND_WRAPPERS_REFERENCE.md  # NEW (2026-08-13): living cross-cutting reference table -- every core/wrapper built so far, what's standalone-Quartus-proven vs. aggregate-only vs. sim-only
cat docs/shared/TOOLCHAIN_SETUP.md                # NEW (2026-08-04): current Quartus/JTAG/Arria10 setup -- Windows is currently authoritative (Linux paused on this machine), the reboot-after-JTAG rule, replaces stale HARDWARE_SETUP.md
cat docs/full-cell/CELL_INTERNALS.md              # NEW (2026-08-04): the FULL cell's own field map, built by reading unicell64_v3.v directly -- flags the RTL's own known-stale header comment (wrong auth_mask position)
cat current/VM_CORE_GAP_ANALYSIS.md               # NEW (2026-08-08): full sweep of all 77 root Python files vs the nano cell -- zero target it, 35 target the old format, 8 real gaps mapped against the VM-core rebuild plan (points.md #216/#217)
cat current/latest.md                                 # current state + recent decisions (most recent at TOP) -- READ THE CRITICAL CORRECTION AT THE TOP FIRST (points.md #228)
cat points.md                                         # the FULL detailed narrative, #1 onward -- #115-#157 is this session's entire body of work
cat current/PLAN.md                                   # what needs doing
```

**A large, multi-day session (2026-08-01 through 2026-08-04) rebuilt the
STRIPPED cell almost entirely — memory/comparator mechanisms, a full
command/programming redesign (twice), a branch/routing mechanism ported
from the FULL cell, and real zone-scale measurement up to 750 cells. Read
`current/latest.md` for the compressed summary before diving into
`points.md`'s full narrative.**

## Onion archival tool — setup needed EVERY fresh session (2026-08-16, points.md #332-335)
Legacy/superseded material now gets packed into `.onion` archives in
`archeology/onion/` instead of left scattered live or riskily deleted
(real, working discipline, not aspirational — see `points.md` #332-333
for the first real pass and #334-335 for a real fix already made to
the tool itself). The `git submodule update --init --recursive` above
only gets the SOURCE — in a fresh sandboxed environment the C
extensions and CLI install need rebuilding every session too, they
don't persist:
```bash
cd tools/onion
pip install cryptography --break-system-packages
python3 build_ext.py build_ext --inplace
pip install -e . --break-system-packages
cd ../..
```
Then `onion -c/-d/-i/--search` work as documented in `tools/onion/README.md`.
**Real gotcha already hit once, worth avoiding a repeat:** packing
multiple individually-named files that share a basename (e.g. two
different files both called `fpga_bridge.py`) silently collides on
extraction — only one survives. Stage same-named files into
distinguishing subfolders before packing, or pack a real directory
tree instead (that case works correctly, confirmed on real files).
Always verify a real extract-and-checksum round-trip before deleting
any live original — this exact discipline is what caught the
collision bug the one time it mattered.

## GROUND TRUTH
**`fpga/verilog/unicell_stripped_v1.v` is the ACTIVE line — build everything on it (#107's "reality" fork).**
`fpga/verilog/unicell64_v3.v` remains the FULL cell's own ground truth for that SEPARATE "dream" line
(#107) — untouched since 2026-07-31, not currently being developed, but not abandoned either.
Verilog LOGIC (not comments) wins every argument, on EITHER cell. But ground truth can have bugs:
verify the Verilog's INTERNAL consistency (does the logic match the field map?), not just
contract-vs-Verilog. Two real bugs and a missing-flags error were found this way on the FULL cell
(2026-07); a latent bug (`a_reemit_active` never requiring `a_arrived`) was found the same way on
the stripped cell this session (#144). The FULL cell's header carries an AUTHORITATIVE FIELD MAP —
trust that block, re-verify against logic when in doubt.

Core discipline: sim-first then silicon; smallest-test-first; isolate-the-variable; clone don't
modify proven files; prose over heavy formatting; honest assessment over enthusiasm.

## Canonical STRIPPED-cell stack (active line, #107's "reality" fork)
- `fpga/verilog/unicell_stripped_v1.v`      — THE stripped cell (ground truth, this session's whole focus)
- `fpga/verilog/cell_wrapper_v2.v`          — host/JTAG path, full parity (PROGRAM/COLLECT/SET_CTRL/CLR_CTRL/DIAG)
- `fpga/verilog/cell_command_v1.v`          — command-cell companion (trigger -> hold -> release on program_done)
- `fpga/verilog/top_stripped_grid5x5_*.v`   — 25-cell campaign tops (baseline/wrapper/command/both)
- `fpga/verilog/top_stripped_zone50_v1.v`   — 50-cell zone base figure
- `fpga/verilog/top_stripped_zone750_v1.v`  — 750-cell zone, Alan's actual per-zone target (16 zones x 750 = 12,000 cells)
- `fpga/quartus/Unicell-Q-stripped-*.qsf`   — build from these (one per test above)

## Canonical v3 (FULL cell) stack — separate "dream" line, untouched since 2026-07-31
- `fpga/verilog/unicell64_v3.v`        — THE cell (ground truth)
- `fpga/verilog/unicell_array64_v3.v`  — array
- `fpga/verilog/unicell_zone64_v3.v`   — zone (pass .DEBUG_SELECT(1) for per-cell readback+bank switch)
- `fpga/verilog/top_arria10_zone1_v3.v`— silicon top (has DEBUG_SELECT(1))
- `fpga/quartus/Unicell-Q-zone1-v3.qsf`— build from THIS (references the v3 top, not the old one)

## Sim — STRIPPED cell (primary active line — testbenches are oracles, not smoke tests)
```bash
cd fpga/verilog
iverilog -o /tmp/t.vvp -g2012 tb_stripped_v1_program.v unicell_stripped_v1.v && vvp /tmp/t.vvp          # variable-length ID-tagged programming
iverilog -o /tmp/t.vvp -g2012 tb_stripped_v1_branch.v unicell_stripped_v1.v && vvp /tmp/t.vvp            # comparator-driven routing (branch mechanism)
iverilog -o /tmp/t.vvp -g2012 tb_stripped_v1_commandcell.v unicell_stripped_v1.v && vvp /tmp/t.vvp       # bit-10, config-driven command-emit
iverilog -o /tmp/t.vvp -g2012 tb_wrapper_v2.v cell_wrapper_v2.v unicell_stripped_v1.v && vvp /tmp/t.vvp  # full wrapper (all 5 opcodes)
iverilog -o /tmp/t.vvp -g2012 tb_wrapper_freeze_cascade.v cell_wrapper_v2.v unicell_stripped_v1.v && vvp /tmp/t.vvp  # freeze cascade via SET_CTRL
```

## Sim — FULL cell (v3, separate line, primary verification — testbenches are oracles, not smoke tests)
```bash
cd fpga/verilog
iverilog -o /tmp/t.vvp -g2012 tb_v3_twoslot.v      unicell64_v3.v && vvp /tmp/t.vvp   # 15/15 decoder+compose+auth
iverilog -o /tmp/t.vvp -g2012 tb_v3_auth_relocate.v unicell64_v3.v && vvp /tmp/t.vvp   # 11-bit auth @ [63:53]
iverilog -o /tmp/t.vvp -g2012 tb_v3_bank.v          unicell64_v3.v && vvp /tmp/t.vvp   # op26 bank switch
```
VM tests: `PYTHONPATH=. python3 tests/vm/test_fp_tiles.py` and `tests/vm/test_compiler_int32.py`.

## Sim — the super cell (all 6 cores in one, `#324`/`#336`)
```bash
cd fpga/verilog
iverilog -o /tmp/t.vvp -g2012 tb_unicell_super_v1.v unicell_super_v1.v unicell_stripped_v1.v \
    ram_cell_v1.v adder_cell_v1.v adder_v1.v accumulator_cell_v1.v compare_cell_v1.v latch_cell_v1.v \
    nibble_mask_addon_v1.v shift_lane_addon_v1.v invert_addon_v1.v && vvp /tmp/t.vvp   # all 6 cores + isolation
python3 -m pytest tests/vm/test_icm_v3.py -v   # ICM v3 format (SUPER_LATCH encode/decode), 16/16
python3 -m pytest tests/vm/test_unicell_super_automaton_v1.py -v   # VM dispatch, all 6 cores, 19/19
python3 -m pytest tests/vm/test_super_tile_library_v1.py -v   # Tier 0 tile library + target tagging, 19/19
python3 -m pytest tests/vm/test_composed_tile_library_v1.py -v   # Tier 1: sentinel + dual_threshold_monitor + twin_sentinel, 14/14
python3 -m pytest tests/vm/test_dsl_compiler_v1.py -v   # DSL compiler, first slice, 18/18
python3 -m pytest tests/vm/test_python_frontend_v1.py -v   # backend/frontend split proof, 8/8
python3 -m pytest tests/vm/test_user_tile_loader_v1.py -v   # 'use this model' CLI switch, 10/10
python3 -m pytest tests/vm/test_dsl_compiler_v1.py -v   # includes define/expose/fixed-params/forward-refs, 28/28
python3 -m pytest tests/vm/test_python_ast_frontend_v1.py -v   # real Python-AST frontend, 12/12
python3 -m pytest tests/vm/test_vm_introspection_v1.py -v   # #216's JSON introspection, 7/7
python3 -m pytest tests/vm/test_root_definition_extractor_v1.py -v   # #216's root definition, 12/12
python3 -m pytest tests/vm/test_generic_field_codec_v1.py -v   # #216's generic codec, 8/8
python3 nano/regenerate_root_definition_v1.py --check   # confirm root_definition.json is current
python3 nano/validate_icm_v3_against_rtl_v1.py           # confirm icm_v3.py still matches the RTL
```
Read `docs/stripped-cell/UNICELL_S_DSL_MANUAL.md` for the language
reference -- every example in it is independently verified to compile.
Note (2026-08-16): `iverilog` is NOT preinstalled in a fresh sandboxed
environment -- `apt-get install -y iverilog` first (network allowlist
already covers `archive.ubuntu.com`).

## SILICON — reflash FIRST
Mustang-F100 Arria 10 config is VOLATILE SRAM (PCIe-powered) — any host restart/sleep/PCIe
re-enumeration WIPES it. JTAG IDCODE still enumerates (misleading). Reflash before any quartus_stp test.
- When in doubt, run `fpga/icm64_readstate.tcl` as the KNOWN-GOOD baseline (it authenticates
  correctly, lands config, reads a real latch, and has a cycle-tick snapshot-health check).
- Our test tcl auth framing must MATCH what the bitstream's boot stores (a mismatch = config
  silently auth-rejected — the cause of the long silicon chase; auth GATE works on silicon).
- Debug/readback path (ISSP bridge, DEBUG_SELECT) is a SECURITY DOOR — strip + lock JTAG in production.

## Real fitted numbers — STRIPPED cell (active line, Quartus 25.1, 2026-08-09)
**CRITICAL (points.md #228): the old 25-cell isolated baseline below
("293 ALMs, 11.72/cell") is INVALID as a per-cell figure — confirmed
only 3 of that test's 25 nominal cells were ever genuinely live, the
other 22 fully pruned by Quartus. Do not cite it as "what one cell
costs." Use the real, confirmed reference instead: ~100-106 ALM/cell
for genuinely live cells, consistent across both 240-cell and 750-cell
scale (points.md #209/#224).**

**ALSO CRITICAL (points.md #241, fixed and re-verified #242/#247):
every Fmax/slack figure from the `#176`-`#227` timing arc was measured
against a phantom auto-derived ~1GHz clock — the SDC constraint file
was never actually applied (a project-folder workflow gap, confirmed
via Quartus's own "file not found" message). ALM counts were NOT
affected — confirmed by direct before/after comparison at two
independent scales below. The numbers below are the corrected,
SDC-confirmed-applied figures.**
- 25-cell isolated baseline (retained for history, NOT a per-cell
  figure — see correction above): 293 ALMs, 192.75 MHz (#146).
- 240-cell zone (controlled clone of the 750-cell build, ROWS-only
  change): 28,930 ALMs, 214.87 MHz, **+0.346ns slack — PASSING**
  (#242, SDC confirmed applied; supersedes #223/#224's invalidated
  28,900 ALM/238.66MHz/-3.190ns figure — ALM barely moved, 0.1%
  difference, confirming resource usage was never contaminated).
- 750-cell zone (Alan's actual per-zone target, `top_stripped_zone750_v5`):
  **89,778 ALMs, 210.79 MHz, +0.256ns worst slack — PASSING at the real
  200MHz target** (#247, SDC confirmed applied; supersedes #198's
  invalidated 89,818 ALM/259.61MHz/-2.852ns figure — ALM moved 0.04%,
  same confirmation as the 240-cell case). Genuinely interior cells:
  100.1-106.2 ALM/cell, avg 102.8 (#209, ALM-based, unaffected by the
  SDC issue).
- **Real per-card capacity estimate (#229): ~1500-1700 cells at an 80%
  utilization ceiling — a ~7-8x downward revision from the 16-zone/
  12,000-cell target below.** Extrapolated from two real ALM data
  points (240 cells @ 11%, 750 cells @ 36%); untested above 36%
  utilization, where routing congestion commonly becomes non-linear in
  real FPGA designs — treat as a real estimate, not a confirmed number,
  until a build somewhere in the 1000-1500 range exists. This estimate
  is ALM-based and was never affected by the SDC issue.
- ~464 ALM/cell (FULL cell, below) vs. ~100-106 ALM/cell (stripped,
  genuinely live cells) — the comparison that actually matters for
  #107's fork rationale; the old "~11.7-16.4 ALM/cell" figure
  previously cited here shared the same #171 baseline flaw and should
  not be used either.

## Real fitted numbers — distribution system & sentinel (Quartus 25.1, 2026-08-13)

**Full assembled distribution system** (`top_full_tree_system_v1.v` —
2-level mux tree, 4-stage relay chains, 2 real adders, 2-level combiner
tree, real BRAM round trip): **275 ALM, 192.09 MHz, 655,360 real M20K
bits confirmed inferred** (`points.md #286`). Reaching this number
required fixing THREE separate real Quartus synthesis traps found via
actual builds, not predicted — worth knowing before touching this
design again: constant-propagation on the self-test's own literal
addresses (`#283`), a hierarchy-depth RAM-inference failure fixed by
`bram_controller_v2.v`'s registered read address (`#284`), and
constant-propagation again on the self-test's own literal data values
(`#286`). **`bram_controller_v2.v`, not `v1`, is now the standard
memory core for anything more than ~2 hierarchy levels deep from a
real Quartus instantiation.**

**Sentinel system, first real hardware confirmation** (`Unicell-Q-
sentinel-issp-test-v1`, `points.md #291`): channel-alive over real
JTAG confirmed (cycle counter genuinely advancing), power-on-frozen
state confirmed correct on real silicon, the `chain_length=0`
degenerate-case fix confirmed correct on real silicon. `diff` tracking
and actual error-triggering (as opposed to error-absence) remain
sim-only confirmed — a ready-to-run exercise script exists
(`fpga/sentinel_issp.tcl`'s own `sn_full_exercise`, `#292`) but hasn't
been executed yet.

**A real hierarchy-depth RAM-inference limitation, worth remembering
for ANY future design:** the exact same unmodified Verilog can infer
correctly as real M20K when close to the top of the hierarchy but fail
(silently synthesizing as ~650K plain registers instead) once wrapped
several levels deeper — a documented Intel/Altera Quartus limitation,
not a bug in the RTL itself. The fix is registering the read address
inside the memory module (the canonical Quartus RAM template), not
changing the logic.

- Logic 74% (185,445/251,680 ALMs); 16 zones x 25 = 400 cells; ~4.6% marginal per zone (loaded);
  ~464 ALM/cell. DSP 0/1687, BRAM 0, PLL 0/64, HSSI 0/24 — all hardened silicon IDLE.
- FMAX 56.2 MHz — THE number to watch (>logic%); likely wired-OR-bus-limited; island separation
  should raise it. Card gains packing efficiency when fully loaded (single zone ~6% -> 4.6% loaded).

## Where the project is (2026-07)
Strategic pivot: stop forcing the FPGA to be silicon. TWO versions on a shared foundation:
- PURE-CELL (VM-first, demonstrates the thesis, hosts compiler + Tier-2) — proceeds now.
- HYBRID (card: cells for topology/control, DSP+BRAM for math/storage via bridges) — data prereq
  now closed (see arria10_card_capabilities.md).
Deployment = CAFÉ: 8 cards + 1 SBC (SBC runs host-side ward+PTT; cards compute). Card = a POND
(surfaces via PTT; workbench reads it). BRAM = universal primitive (buffer + PCIe-port + program
store); PCIe DMAs to BRAM direct (no I/O cells). Backpressure = command-cell watchdog freeze (no
interrupts); propagates upstream; keep feedback loops zone-local. Product: uni-lab parallel platform,
EOL GX660 ~£450 café to seed / current GX1150 ~£1050 to sustain (128 models/café).

## NEXT (agreed order, 2026-08-16 -- this is what a fresh session picks up first)

**Read `current/latest.md` first.** 2026-08-16 was ground-clearing
(full `points.md` audit, structural cleanup, Onion tool fix), THEN a
real start on the actual next phase, per `#324`'s own milestone:

1. **ICM v3 format -- DONE (`#336`).** `nano/icm_v3.py` (real
   `SUPER_LATCH[79:0]` encode/decode, core-type-selector + per-core
   field tables, record/file format with a checked `record_hash`),
   `tests/vm/test_icm_v3.py` (16/16), `docs/stripped-cell/
   ICM_V3_FORMAT.md` (the spec). Verified two ways: independent
   bit-position tests, AND a bit-for-bit cross-check against
   `tb_unicell_super_v1.v`'s own proven test vectors (iverilog-compiled
   and run against the real RTL the same session).
2. **VM dispatch -- DONE (`#337`).** `nano/unicell_super_automaton_v1.py`:
   `SuperCell`/`SuperGrid`, generalizing `CAGrid`'s event-driven model
   across all 6 core types. nano is DELEGATED to a real `CACell`
   (composition, not reinvention); the other 5 cores' `deliver()` logic
   is a direct transcription of each core's own real RTL body (not just
   the header field-map). `tests/vm/test_unicell_super_automaton_v1.py`
   (19/19), zero regression on the pre-existing 64-test nano suite.
3. **A compiler path from higher-level cell/core description down to
   real `SUPER_LATCH` bits** -- BLOCKED ON THE LIBRARY, per Alan's own
   explicit call-out (`#338`): "the compiler... will need the library
   before we get there as it uses and touches so many things." Real
   sequence now:
   - **Tier 0 (single-cell primitives) -- DONE (`#338`, target-tagging
     added `#339`).** `nano/super_tile_library_v1.py`: 6 tiles, named
     ports, real placement via `place()` (Unicell-S) and `place_on_nano()`
     (Unicell-n, `target='universal'` tiles only). `docs/stripped-cell/
     design-notes/super_tile_library_scope.md` is the scoping note this
     was built against (read it first if extending the library).
   - **Tier 1 (multi-cell composed tiles, relative placement) --
     started (`#340`), generalized with fan-out (`#341`), and
     generalized AGAIN with nested composition (`#342`).**
     `nano/composed_tile_library_v1.py`: `SubCellPlacement`/
     `ComposedTileSpec`/`place_composed()`. Three tiles: `sentinel`
     (accumulator -> comparator -> latch, verified against the exact
     proven feed/collect/unfreeze sequence from real hardware),
     `dual_threshold_monitor` (fan-out + non-linear L-shaped layout),
     and `twin_sentinel` (a composed tile built from OTHER composed
     tiles -- two independent `sentinel` instances, proving recursion +
     double-namespaced params work, confirmed genuinely independent in
     a real running grid).
   - **The DSL + compiler -- first real slice DONE (`#343`).**
     `nano/dsl_lexer_v1.py`/`dsl_parser_v1.py`/`dsl_compiler_v1.py`/
     `dsl_diagnostics_v1.py`. A real `program { place ... }` grammar
     compiles end to end (lex/parse/resolve/place/emit/reload) for
     Tier-0 AND Tier-1 tiles, including fan-out lists and (nested)
     namespaced params -- every mechanism proven at the Python level
     this session (`#338`-`#342`) now confirmed working correctly
     THROUGH the DSL too. Diagnostics are real: what/problem/why/
     suggestion plus a correct source span, confirmed by tests
     checking actual span values. "Collect every problem, don't stop
     at the first" confirmed directly for resolve/place-stage errors
     across multiple statements -- lex/parse errors are the one
     honest exception (no recovery yet, stops at first syntax error).
     `docs/stripped-cell/design-notes/unicell_s_dsl_and_compiler_scope.md`
     is the design note this was built against.
   - **Backend decoupled from the DSL, proven with a real second
     frontend (`#344`).** `nano/program_ir_v1.py` is now the shared,
     frontend-agnostic target (`ProgramIR`/`PlaceIR`/`FieldIR`);
     `dsl_compiler_v1.compile_program_ir()` is the real backend,
     `compile_source()` is the DSL's own thin wrapper on top of it.
     `nano/python_frontend_v1.py` proves the split really works --
     builds `ProgramIR` from plain Python dicts, never touches the DSL
     lexer/parser, and produces byte-identical output to the DSL
     frontend for the same program. C/Rust frontends explicitly NOT
     attempted -- both need an external parser library first (hand-
     writing either grammar isn't reasonable), flagged for a real
     design conversation before committing to either. A full Python-
     AST frontend (real functions/loops/control-flow, in the spirit of
     `compiler.py`'s own precedent) is a separate, bigger undertaking
     than the dict-based proof-of-concept built here.
   - **"Use this model" -- a real `--model FILE` CLI switch (`#345`).**
     Per Alan's own explicit scope: the full design-your-own-tile
     system is the composer's job (Stage 5, `#20`, later, after
     compiler AND workbench) -- what got built is the narrower thing
     asked for now: `nano/dsl_cli_v1.py`, a real command-line tool,
     `nano/user_tile_loader_v1.py` (JSON -> `ComposedTileSpec`, a
     direct mirror of the existing dataclass shape, not a new format),
     and `ComposedTileLibrary` parent-chaining so a user model shadows
     a same-named built-in without ever mutating the real registry.
     Tested as a real command via `subprocess.run()`, not just its
     Python internals. No persistence/category taxonomy/`use`-`define`-
     `expose` grammar -- `place` already handles a loaded user tile the
     same as any built-in Tier-1 tile.
   - **`define`/`expose` grammar -- DONE (`#346`), internals finished
     (`#347`).** A Unicell-S program can now define its own reusable
     composed tile inline (`define NAME { place ... expose ... }`),
     then `place` it like any built-in or `--model`-loaded Tier-1 tile.
     `#347` closed both real limitations `#346` left open: a sub-cell's
     own param can now be FIXED directly inside `define`
     (`SubCellPlacement.fixed_params`, removed entirely from what the
     defined tile requires from its own caller), and `place` can now
     forward-reference a `define` appearing anywhere in the same file
     (two-pass processing -- all defines first, in their own relative
     order, then all places). A `define` still can't forward-reference
     a LATER `define`, a real, narrower, stated limit.
   - **A real Python-AST frontend -- DONE (`#348`).**
     `nano/python_ast_frontend_v1.py`: parses actual Python syntax (a
     declarative subset -- `place(...)` calls and
     `with define("name"): ...` blocks, every argument a plain literal),
     genuinely distinct from `#344`'s dict-based proof-of-concept.
     Cross-checked against the DSL frontend for the same program,
     byte-identical output. C/Rust frontends remain unattempted -- both
     need an external parser library first.
   - **DSL language manual -- DONE (`#349`), corrected (`#350`).**
     `docs/stripped-cell/UNICELL_S_DSL_MANUAL.md`. Every code example
     independently compiled and confirmed before inclusion (caught two
     real inaccuracies this way, not after publishing); the tile
     catalog tables pulled from the live registries, not written by
     hand. `#350` fixed a real framing error: "no automatic placement"
     was listed as a compiler limitation, but the project already
     settled this architectural boundary for the old full-cell system
     (`model -> ICM (shape-neutral) -> [BINDER] -> placement -> loader
     -> silicon`) -- corrected to state it as a genuine boundary, not a
     gap.
   - **Naming hygiene lint + circular-reference guard -- DONE (`#350`),
     per Alan's own review.** `_lint_names()` in `dsl_compiler_v1.py`:
     real `severity: "warning"` diagnostics for duplicate local names
     (top-level statements, and sub-cells within one `define`), never
     blocking compilation. A REAL circular-reference bug found and
     fixed in `place_composed()` -- a hand-crafted `--model` JSON tile
     could self-reference (or indirectly cycle) with zero protection,
     confirmed as a genuine `RecursionError` before being fixed, not
     assumed. Now a clear `ValueError` naming the exact cycle.
   - **NEXT: open, per `#349`/`#350`'s own remaining "known
     limitations."** Candidates: parser error recovery; a real loader/
     binder stage for Unicell-S (per `#350`'s own corrected framing --
     genuinely new work, not previously scoped at all); C/Rust
     frontends (need external parser tooling first); or the workbench's
     own first scoping conversation (still hasn't had one at all). The
     composer (Stage 5, `#20`) remains explicitly later work, after
     both compiler and workbench.
   - **A genuinely long-range thread, captured not started
     (`#351`/`#352`/`#353`).**
     `docs/stripped-cell/design-notes/general_purpose_programming_
     long_range_note.md` -- real, general-purpose, language-agnostic
     programming compiled onto Unicell-S (not just declarative
     placement). Real prior art surfaced: the old full-cell compiler's
     typed arithmetic/comparisons/if-else-as-MUX, proven on real system
     logic (`sentinel_core.py`/`ward_core.py`/`shore_core.py`, still in
     `bootloader/icm/`). Real open questions: what a variable/loop even
     means on this substrate. "The FPGA design side route" clarified
     (`#352`): lower the compiler's own output past ICM v3 configuration
     to real, synthesizable Verilog generated per-program -- a natural
     extension of the already-proven "many frontends, one shared IR"
     architecture, applied to the backend side instead. A third facet
     added (`#353`, "LEGO for FPGA") -- a snap-in core ecosystem for
     third-party hardware designers, which turns out to be the direct
     fulfillment of a real requirement Alan already stated the day
     before this session began (`#317`), with the RTL's own
     `core_select` field already reserving the headroom for it (values
     6-31). Deliberately deferred, per Alan's own words: "sort after
     all this is sorted." Not scoped for real work yet.
   - **The workbench, real sequencing decided (Alan, 2026-08-16):** do
     `#216`'s VM-core work FIRST, as the real foundation, not the
     workbench itself yet. Going through `#216`'s own items in order,
     per Alan's own instruction.
     - **Item 5, JSON introspection -- DONE (`#354`).**
       `nano/vm_introspection_v1.py`, verified against real running VM
       state (the proven `sentinel` sequence), not just structural
       shape.
     - **Item 1, root definition -- DONE (`#355`).**
       `nano/root_definition_extractor_v1.py` mechanically extracts
       field-map bit positions directly from the RTL's own comments.
       `nano/validate_icm_v3_against_rtl_v1.py` cross-checks
       `icm_v3.py`'s own hand-typed field tables against this
       independent extraction -- PASSED, zero mismatches, a genuine
       positive confirmation of `#336`'s earlier transcription.
       `nano/regenerate_root_definition_v1.py` + `nano/root_definition.
       json` -- the real, re-runnable persisted artifact. Two real
       parser bugs found and fixed during development (wrapped headers/
       descriptions silently losing fields), locked in as regression
       tests. Honest gap: `addon_config`'s own fields aren't covered
       (wired via module ports, not the same comment convention).
     - **Items 2/4, generic field codec -- DONE (`#356`).**
       `nano/generic_field_codec_v1.py` -- pack/unpack driven entirely
       by `root_definition.json`, never consulting `icm_v3.py`'s own
       hand-typed tables. Proven bit-for-bit equivalent to `icm_v3.py`'s
       already-RTL-verified codec across all 6 cores and many values,
       not assumed from matching source data. A real, non-bug caught
       during testing (icm_v3's own direction-list convenience is a
       documented, deliberately-not-re-derived scope boundary, not a
       mismatch) -- fixed the test's comparison, not the module.
     - **NEXT, in `#216`'s own order: item 3 (dual CPU/GPU execution),
       then 6 (AI-interaction port), then 8 (the `core/` folder name).**
       The actual GRID/CELL construction layer using this new generic
       codec (a `SuperCell` built generically rather than hand-coded per
       -core Python classes) is still real, unstarted work -- items 1/2/
       4 provided the field-level foundation, not the full engine.
   - **Two small wins, per Alan's own choice (`#358`).** A real
     registry (`CoreHandler`/`register_core_handler()`) replaced
     `SuperCell`'s if/elif core dispatch -- proven, not just refactored:
     a genuinely new core type registered and run correctly with zero
     edits to `SuperCell`'s own dispatch methods. Root-definition-driven
     validation added to `SuperCell.from_record()`, closing a real gap
     (typo'd `core_config` keys were previously silently ignored, not
     flagged) using `generic_field_codec_v1.field_table()` -- the same
     table `#356` already proved equivalent to `icm_v3.py`'s own.
   - **Item 6, AI-interaction port -- DONE (`#359`).**
     `nano/vm_ai_port_v1.py` (`VMSession`/`CompileFailure`) -- compile
     (DSL or Python-AST) -> real ICM v3 -> real running VM -> real JSON
     introspection, all through one clean object. Deliberately NOT the
     `attach_ai()` precedent directly (no `torch`/`transformers`
     dependency just for the port to exist) -- a real model attachment
     remains a separate, optional, later layer. Building and testing
     this end to end immediately found a REAL, previously-undiscovered
     bug in `SuperGrid.run_to_quiescence()` (checked `_pending` before
     ever calling `tick()` once, silently under-reporting quiescence
     for a continuously-live core with zero prior stimulus) -- fixed
     the same session, regression tests added.
   - **NEXT, per Alan's own call: item 3 (dual CPU/GPU execution),
     saved for next session.** Real precedent found: `gpu_array.py`
     (pattern reusable, not code -- built for the old `UniCellArray`, a
     different cell model).
   - **Real documentation staleness found and fixed (`#357`).**
     `docs/stripped-cell/CELL_INTERNALS.md`/`CORES_AND_WRAPPERS_
     REFERENCE.md` -- neither covered the super carrier shell at all
     (confirmed via git log, not assumed: 11 days and same-day-but-
     before-the-milestone, respectively). New standalone doc built
     (`SUPER_CELL_INTERNALS.md`), every field-position claim in it
     cross-checked against the live code, every real-world figure
     checked against its own `points.md` entry (caught and fixed one
     own mistake -- a rounded timing figure). `docs/README.md`'s own
     index was also stale, missing two already-existing docs entirely.
   - The compiler itself comes after Tier 1, not after Tier 0.
4. **The 77-file root Python sprawl** -- archive this AS PART OF
   starting the real VM/`core/` rebuild above, not before (per `#218`'s
   own "concept survives, code doesn't" discipline, and `#332`/`#333`'s
   own stated priority order).

**Smaller items, whenever convenient:**
- `hardware/Arria10_Programming_Procedure.md` -- needs a human call
  (archive vs. refresh), not mechanical action.
- The `mathtrix` root/community structural question.
- `#323`'s own register-count discrepancy, via Chip Planner.
- A real host/JTAG-wrapped version of the super cell, for a fully
  clean comparison against `#319`'s baseline.
- `latch_in`/`latch_A_dis` (`#310`'s core-shaped pair) -- still
  completely unstarted.
- The RAM-side address-arbitration/retry-loop mechanism (`#301`/
  `#302`) -- needs real testing before trust.
- Wire the sentinel into a real chain; wire `shared_bram_arbiter_v1.v`
  into the full tree system.
- The two long-queued Quartus experiments (`#206`'s OPTIMIZATION_MODE,
  `#200`'s duplication-flags).
- Two small orphaned items from `#331`'s audit (`#10`, `#45`) -- just
  need a conscious keep/drop decision.

**Also queued:** the `#210` programming-delivery decision, the BRAM+
DSP hybrid integration (`#220`), and the longer-horizon FPGA dev-tool
vision (`#305`).

## Git
```bash
git config user.email "session@imago.local"; git config user.name "Imago Session"
git remote set-url origin https://<PAT>@github.com/alh-Imago/Imago-Unicell.git
git ls-remote   # confirm actual remote state ("ahead N" in status is a false alarm)
```
