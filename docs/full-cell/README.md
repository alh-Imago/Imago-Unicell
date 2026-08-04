# docs/full-cell/

**UPDATE (2026-08-04, later same session): no longer empty.**
`CELL_INTERNALS.md` now exists — built by reading `unicell64_v3.v`
directly, following the same pattern as `docs/stripped-cell/
CELL_INTERNALS.md`. A real trap caught and flagged in the process: this
RTL file's own HEADER comment block is known stale (still shows
`auth_mask` at the wrong bit position) — the file's own later "verified
current" block is the one that's actually authoritative, and the new
doc was built from that, not the header.

---

Originally created empty (2026-08-04) to mirror `docs/shared/` and
`docs/stripped-cell/`, ready for whenever the FULL-cell-specific
documentation phase started. `archeology/full-cell/docs/` still holds
everything else moved-but-not-yet-re-examined for the FULL cell —
`V3_COMMAND_CONTRACT.md` remains a good next pull if this phase
continues, for the opcode-level detail `CELL_INTERNALS.md` deliberately
didn't try to be exhaustive about.

Per Alan (2026-08-04): the FULL cell is expected to be revisited and
made functional again, carrying back some of what was discovered on the
stripped cell (`docs/stripped-cell/CELL_INTERNALS.md`) — the routing
self-consistency approach from `points.md` #155 and the armed/`COMPLETE`-
LSB convention from #156 (itself modeled on this cell's own
`start_flag`/`CMD_RELEASE`, now documented explicitly in
`CELL_INTERNALS.md`) are the two candidates already flagged. That RTL
work and this documentation phase may need to happen together — worth
deciding when picked up, not assumed.

