# Current State (as of 2026-08-04 — see archeology/sessions/archive-2026-08-04.md for the 2026-07-31 narrative this replaces)

Previous narrative (through 2026-07-31) has been moved to
`archeology/sessions/archive-2026-08-04.md`, exactly as it was written. This file starts
fresh as the fast catch-up document, per its own stated purpose. This was a
large, multi-day session (2026-08-01 through 2026-08-04) — see `points.md`
#115-#152 for the full, detailed narrative; this is the compressed version.

## Where things stand

**The STRIPPED cell (`fpga/verilog/unicell_stripped_v1.v`) gained a complete
memory/comparator/branch/programming capability set this session, all
confirmed correct by hand in simulation, and partially confirmed on real
Quartus fits at scale.** The FULL cell (`unicell64_v3.v`) was NOT touched at
all this session — it remains untouched since 2026-07-31, still the separate
"dream" architecture line per #107's original fork.

### Stripped cell: new mechanisms (#115-#120, #123-#126, #140-#144)
- **Memory cell system**: `hold_in` (freeze the first-arrival value across
  multiple fires), `fb_internal_in` (internal self-feedback, no external
  round-trip), `a_reemit_in`/`a_update_in` (pure pass-through vs. genuine
  update of the held value), `a_self_update_in` (self-adjusting threshold).
- **Command mechanism, REDESIGNED TWICE this session, final form confirmed
  cheap and fast**: `program_in`/`program_done` + a genuinely CARDINAL
  (`prog_data_in_n/s/e/w` etc.) dedicated programming channel, separate from
  ordinary data ports (#133, after #131/#132 found sharing the data port and
  a non-directional single wire both cost real Fmax). Programming itself is
  now VARIABLE-LENGTH and ID-TAGGED (#140/#142) — each word is
  `{3-bit field ID, 16-bit data}`, touching only the field it targets ("a
  scalpel, not a hammer"), not a fixed 96-bit overwrite. A reserved
  `COMPLETE` ID triggers `program_done`.
- **Branch mechanism** (#140/#142): ported from the FULL cell's
  `pattern_low/equal/high` + `dynamic_route_en` (same aligned bit positions,
  `[93:76]`/`[94]`), simplified to 4 wired bits per pattern (N/S/E/W). A live
  comparator result (`second_val` vs. held `input_val`) now genuinely picks a
  DIFFERENT routing direction per fire — confirmed: B>A/B<A/B=A route to
  three different, correct directions.
- **Bit `[10]` aligned** with the FULL cell's own `command_cell`/
  `COMMAND_EMIT` concept (#143/#144) — a config-time, fully self-contained
  permanent re-emitter, no external control wire needed.
- **A companion module, `cell_command_v1.v`** (~6 lines of real logic):
  holds one control line on trigger, releases on `program_done`. Genuinely
  separate from a stripped cell — not a mode, a distinct small instance.

### The wrapper, REBUILT for full host/JTAG parity (`cell_wrapper_v2.v`, #127)
Replaces `cell_wrapper_v1.v`'s single opcode with 5: `PROGRAM` (now via the
target's ordinary/dedicated programming port, not `cfg_data`), `COLLECT`,
`SET_CTRL`/`CLR_CTRL` (toggle any of the 6 control lines, persistent latches
inside the wrapper), `DIAG` (reads back `program_done`/`a_arrived`/`ready`/
`pending_ack` — deliberately minimal, not full state). Address field widened
twice this session (5→7→10 bits) to keep pace with cell-count scale-ups.

### Real bugs found and fixed along the way (not glossed over)
- A leftover-reference compile bug and a silently-defaulted `CONSUME_CMD`
  parameter, found by re-verifying "already confirmed" step 1 before
  building on it (#122) — caught two real problems that would have
  contaminated every later measurement.
- `a_reemit_active` never actually required `a_arrived` — a latent bug in
  the ORIGINAL #119 design, exposed only when bit-10's config-driven mode
  removed the external sequencing that had silently masked it (#144).
- A test-driver divide/modulo (#134) and a flat global-broadcast trigger at
  750-cell scale (#151) both turned out to be REAL Fmax-dominating
  artifacts in the TEST HARNESS, not the cell — both found via careful path
  tracing (Report Timing, From clock: `clk_div`) and fixed at the root.
- Several grid-scale test files were found still wired to pre-redesign
  protocols after RTL changes and had to be caught and updated (#145, #148).

### #103 measurement campaign — RE-RUN, complete for the corrected mechanism
Old (relay-chain) design's numbers are SUPERSEDED, not just re-measured:
- Step 1 (plain baseline, complete cell, all new features dormant): 145
  ALMs, 261.44 MHz (#129) — confirms the new capability costs NOTHING when
  unused (register count barely changed vs. #106's original baseline).
- Step 2 (wrapper v2): +264 ALMs (10.6/cell), 190.22 MHz (#135) — cheaper
  AND faster than the old v1 wrapper despite doing far more.
- Step 3 (command-cell, corrected single-hop scope, #122's fix): +163 ALMs
  (6.5/cell), 174.64 MHz (#138) — cheapest mechanism measured.
- Step 4 (both): +302 ALMs (12.08/cell), 188.29 MHz (#143) — genuinely
  BETTER than additive.
- Re-measured against the COMPLETE #140-144 branch/programming redesign
  (#146): 293 ALMs (11.72/cell), 192.75 MHz — cheaper AND faster than the
  old mechanism it replaced, confirming "scalpel not hammer" paid off in
  silicon, not just programming flexibility.

### Zone-scale figures (new this session, #148-#151)
- 50-cell zone (5×10): 813 ALMs (16.26/cell), 171.29 MHz (#149) — a mild
  economies-of-scale effect, cost per cell LOWER than at 25-cell scale.
- 750-cell zone (25×30, Alan's actual per-zone target — 16×750=12,000 cells
  total): 12,295 ALMs (16.39/cell) but Fmax (90.12 MHz) was DOMINATED by a
  test-driver fanout artifact (#151) — fixed at the root (one-hot walking
  sequencer replacing a flat global broadcast, reusing #105's own already-
  proven pattern), NOT YET RE-MEASURED. Expect a substantially higher real
  number once rebuilt.

### RAM / PCIe throughput analysis (#147) — a real, grounded conclusion
On-board DDR4 (Mustang-F100-A10, 8 GB, PCIe Gen3 x8) is a BUFFER AT BEST at
current wrapper throughput: single-chain 771 MB/s, both RAM buses ~1.54
GB/s, vs. PCIe's raw ~7.88 GB/s ceiling — PCIe is ~5x faster than the
wrapper mechanism can currently sustain. Confirms #121's earlier
speculation with real numbers: PCIe direct cell interfacing becomes the
essential lever for real throughput, not a nice-to-have — still blocked on
the parked BAR0 hardware issue.

### Freeze / ward-sentinel connection (#152) — real, and genuinely cheap
Freeze-driven runaway prevention, host-controlled targeting, save/restore,
self-healing relocation, and loader integration all map onto
`archeology/shared/docs/software/VISION.md`'s already-documented "ward/sentinel" layer (systems-level,
explicitly placed LAST in VISION's own dependency order). Key insight:
freezing the LAST cell in a chain (or any point in it) makes the ALREADY-
PROVEN backpressure cascade (#91/#92) stall every upstream cell for free —
no new zone-targeting RTL needed, and it's genuinely MORE granular than a
flat zone-broadcast would have been. Confirmed still working on today's
fully-redesigned cell (`tb_stripped_v1_ring.v` re-run, byte-identical), and
confirmed via the REAL host-driven path (`tb_wrapper_freeze_cascade.v`,
new): freeze B via wrapper `SET_CTRL` before A fires → A offers data to
frozen B → `A_ready` correctly drops to 0 (NOT B's own ready — a real
correction made mid-test) → release B via `CLR_CTRL` → `A_ready` recovers.

## Next steps (explicitly agreed, in order)
1. **DONE (points.md #155).** `freeze_in` now genuinely exercised at all
   three grid scales (25/50/750-cell), sim-confirmed. A real routing-
   corruption bug found and fixed in the 750-cell command walker along
   the way (it was silently zeroing cells' routing_mask as it walked).
2. **DONE (points.md #156).** The armed gate — ported from the FULL
   cell's `start_flag`/`CMD_RELEASE` concept, at Alan's own prompting.
   Scoped to the incremental `program_in` path; reuses `COMPLETE`'s
   previously-unused data LSB. Fixed a ripple effect across 9 driver
   files (all previously sent `COMPLETE` with a zero payload); new
   dedicated test (`tb_stripped_v1_armed.v`) proves the gate itself.
3. **Re-measure the 750-cell zone in Quartus** — now with #151's fanout
   fix, #155's freeze-exercise/routing-fix, and #156's armed gate all
   applied — same project (`Unicell-Q-stripped-zone750`), updated
   `top_stripped_zone750_v1.v`.
4. **Deferred to later, explicitly** (Alan): full state readback for
   genuine save/restore, the ICM-diff file format, and self-healing zone
   relocation. These need at minimum the underlying cell mechanisms to
   exist first — today's session is enough groundwork for now.
5. **Approaching the git-tidy/catchup point** — several methods proven
   this session (the routing self-consistency fix, the armed/COMPLETE-
   LSB convention) are candidates to carry back to or cross-check
   against the FULL cell once the compiler/VM catchup pass (#136) begins.
6. **Archeology sweep underway (Alan, 2026-08-04).** `docs/`+`sessions/`
   reorganized into `current/` (live docs) and `archeology/` (moved,
   not yet re-examined) — see `archeology/README.md`. First piece of the
   actual re-examination done: `docs/SYSTEM_MECHANICS.md` (#158), what's
   genuinely shared between both cell lines, verified directly against
   both RTL files. Model for how the rest of `archeology/` should get
   pulled out and checked, one piece at a time — no next piece chosen yet.
7. **Full archeology triage done (#159).** Checked every remaining doc
   in `archeology/full-cell/docs/` and `archeology/shared/docs/` against
   the "genuine shared idea" test — `ICM_FORMAT.md`/`MIF_FORMAT.md`
   promoted (verified against real code); everything else confirmed
   cell-specific, stale, or a different axis (compiler/VM layer),
   written up in `archeology/TRIAGE.md`. Next: Alan's call between the
   FULL-cell-specific phase or a toolchain-setup doc rewrite.
8. **Stripped cell's first standalone docs written (#160).**
   `docs/stripped-cell/CELL_INTERNALS.md` — built by reading
   `unicell_stripped_v1.v` directly, start to finish: full `cmd_latch`
   field map, every mechanism, port list, known bugs, real silicon
   numbers. `docs/` reorganized into `shared/`/`stripped-cell/` (mirrors
   `archeology/`'s split). Alan flagged the FULL cell will be revisited
   to become functional again, carrying back discoveries from the
   stripped cell (#155's routing fix, #156's armed convention) — this
   doc is preparation for that, not the FULL-cell work itself, which
   hasn't started.
9. **`docs/full-cell/` created (#161), intentionally empty** — matches
   the other two branches' structure, ready for whenever that phase
   starts. Not started. Placeholder flags `V3_COMMAND_CONTRACT.md`/
   `core/CELL_INTERNALS.md` as likely starting points, and notes the
   RTL work + doc phase may need to happen together, not docs-first.
10. **The manual builds again (#162).** `docs/build_manual.py`/
    `manual.html` moved back to `docs/` root (an active tool, not
    archeology holding material) and every doc-path reference fixed.
    Session log index rewritten per Alan's specific ask — dated/archived
    logs now read from `archeology/sessions/`, `current/latest.md`
    pinned first as its own row (it no longer lives inside that folder
    at all). "The Cell" section now points at the new, verified
    `docs/stripped-cell/CELL_INTERNALS.md` instead of the old
    confirmed-stale v2.3-era doc. Ran end to end — builds clean.
11. **The manual now explains the reorg itself (#163).** "Start Here"
    gained three new sub-parts (`docs/README.md`, `current/README.md`,
    `archeology/README.md`) so a reader gets the real orientation, not
    just working links. "Roadmap" gained `archeology/TRIAGE.md`.
    Rebuilt and spot-checked the actual output HTML, not just the
    Python source.
12. **Shared gate-computation core extracted (#164)** into
    `unicell_gate_core.py` — the first concrete piece of Alan's shared-
    core-plus-shells VM architecture. `unicell_v3.py` re-exports the
    same names, zero regression (216/216). Real finding along the way:
    `unicell_automaton_v1.py` (2026-08-02) already exists as the nano
    cell's own precursor VM, cited directly in the RTL's header — but
    stops at roughly #115, missing everything since.
13. **`unicell_automaton_v1.py` rebuilt in place, Phase 2 (#165)** — per
    Alan's direction to reuse, not replace it. Added freeze_in/
    error_frozen/relay-mismatch, same-cycle OR-combine, hold_in/
    a_reemit_in/a_update_in, comparator-driven routing, is_command_cell.
    Three real bugs found and fixed during the rebuild (multi-direction
    ready-wait, relay_fire ready-gating, a frozen cell silently
    absorbing instead of rejecting — the last one would have defeated
    the whole freeze-cascade backpressure mechanism). 254/254 across all
    three affected VM suites. Phase 3 (continuous internal-feedback,
    needs a Grid.tick() architecture change) and Phase 4 (wire-level
    programming protocol) explicitly deferred, not silently skipped.
14. **Phase 3 done (#166): internal feedback.** The one genuinely
    continuous-cycle mechanism — solved with a second dispatch pass in
    Grid.tick() rather than restructuring the whole event-driven model.
    Confirmed against real RTL that internal_fb_active never touches
    pending_ack (private oscillation, invisible to neighbors except via
    a_reemit_in). 47/47 automaton tests, 263/263 total. Only Phase 4
    (wire-level programming protocol) remains on this file.
15. **Phase 4 done (#167): the wire-level ID-tagged programming
    protocol.** `program_word()` + `program_in`/`program_done`, matching
    `cell_wrapper_v2.v`'s exact word format — COMPLETE's LSB genuinely
    arms/disarms via the protocol now, program_in correctly suspends and
    backpressure-retries ordinary operation. **All four phases of
    `unicell_automaton_v1.py`'s own rebuild plan are now complete** — the
    nano cell's precursor VM is genuinely caught up to current RTL.
    50 new tests this session (14→64), 280/280 across all three VM
    suites, zero regressions. Next per Alan's order: the toolchain-setup
    doc rewrite, then the FULL-cell documentation phase.
16. **Toolchain-setup doc rewrite done (#168).** `docs/shared/
    TOOLCHAIN_SETUP.md` replaces the stale `HARDWARE_SETUP.md`. Real
    finding: that file claimed "Linux is the primary platform," which
    reversed — Windows is currently authoritative, Linux still paused on
    this machine despite the usbfs_memory_mb/autosuspend fixes being
    correctly applied. New doc adds the reboot-after-JTAG-reprogram
    rule and the volatile-SRAM-config discipline, neither of which
    existed in any shared doc before. Last item on Alan's list: the
    FULL-cell documentation phase.
17. **FULL-cell documentation phase done (#169).** `docs/full-cell/
    CELL_INTERNALS.md` — built by reading `unicell64_v3.v` directly.
    Real trap caught: the RTL's own HEADER comment is known stale (wrong
    `auth_mask` bit position) — the file's own later "verified current"
    block is authoritative, built from that instead, flagged explicitly
    so nobody reading the RTL fresh repeats the mistake. Covers the
    two-state boot/run addressing model (no STRIPPED-cell equivalent),
    the three-latch field map, command-emit cells, and an opcode
    overview. **This closes Alan's full "proceed in order" list from
    this session.** No specific next item chosen.
18. **750-cell zone real Quartus result came in: 118.91 MHz, 188,075
    ALMs (75% of the whole die, ~250 ALM/cell), 3-hour placement — far
    worse than the 140-160 MHz hoped for.** Alan pulled the actual
    TimeQuest critical-path report. Traced cleanly: neighbor's
    `out_buffer` → OR-combine → **6 LUT levels of the #140 magnitude
    comparator** → relay/consume classification → ack → a 1.57ns
    interconnect round-trip back to the origin cell → `next_pending_ack`
    → `next_ready` → `cmd_latch[13]`. Comparator chain and the
    interconnect round-trip were both real and compounding (43% of the
    8.6ns path was two single interconnect hops).
19. **Comparator gated at compile time (#170), directly targeting the
    measured path.** New `ENABLE_DYNAMIC_ROUTING` module parameter
    (default off) — a `generate` block means the comparator isn't
    instantiated AT ALL for cells built with it off, unlike the existing
    runtime `dynamic_route_en` bit, which static timing analysis can
    never prove stays 0. Every grid-scale top already defaults to off
    (none use dynamic routing) — zero file changes needed there. New
    test proves the gate holds even under deliberately mismatched
    runtime config. Full regression clean (18 testbenches + 4 scale
    tests). **Not yet re-measured in Quartus** — the interconnect
    round-trip portion of the original path is a separate, unaddressed
    placement question. Next: rebuild (25-cell isolation build or the
    750-cell zone directly) and see what actually moves.
20. **25-cell isolation build confirms the fix, dramatically (#171):
    84 ALMs (3.36/cell, was 293/11.72), 280.66 MHz (was 192.75 MHz) —
    a 71% ALM reduction and 46% Fmax increase.** Stronger than "the fix
    worked": this build ALSO carries the freeze exercise (#155) and
    armed gate (#156) on top of the original baseline, and still came in
    below it on both metrics — the comparator really was the dominant
    cost. Rough extrapolation (applying the known ~40% congestion
    overhead from 25→750 cell scale) suggests ~3,500 ALMs for the full
    750-cell zone, versus 188,075 pre-fix — an estimate, not a
    guarantee, since the interconnect round-trip issue from the original
    timing report is untouched by this fix. **Next: rebuild the 750-cell
    zone directly** — the small-scale result is strong enough to skip
    the 500-cell intermediate step.
21. **Modular/composable cell builds concept captured (#172), NOT
    built.** Alan's own reasoning chain from #170's win: if one
    mechanism can be a build-time toggle, more could be — but that makes
    `.icm` files build-specific, which means the compiler needs target
    awareness, which means `.icm` should declare its own requirements
    rather than track compatibility out-of-band. Four real pieces
    identified (per-`.sof` capability manifest, `.icm` `requires` field,
    compiler-side inference — the hard/safety-critical part, loader-side
    validation — the actual payoff), each with genuinely open questions
    recorded honestly in `docs/shared/design-notes/
    modular_cell_builds_and_capability_aware_icm.md`. New
    `docs/shared/design-notes/` subfolder created, explicitly exempted
    from the rest of `docs/`'s verified-against-code bar. Parked idea —
    the 750-cell rebuild remains the active priority.

## Reading order for a new session
`git pull`, then `current/START.md` → `archeology/full-cell/docs/core/ARCHITECTURE.md` (Alan: worth reading
directly for conceptual grounding even though it's known to be behind where
the RTL has progressed) → `points.md` #115 onward for the full detailed
narrative → this file for the compressed version.
