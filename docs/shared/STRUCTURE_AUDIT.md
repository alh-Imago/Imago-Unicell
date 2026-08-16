# Full Structural Audit — 2026-08-16

**Purpose: an honest answer to "how much of a mess are we in," ahead of
the VM/ICM/compiler/PCIe/AI-system phase. Every top-level file and
folder checked directly, not assumed. Builds on and cross-references
two pieces of real prior work that already covered part of this
ground — `archeology/TRIAGE.md` (docs only, 2026-08-04) and
`current/VM_CORE_GAP_ANALYSIS.md` (root Python files, already fully
mapped, 2026-08-08) — rather than redoing what's already done.**

**The honest headline: it's not chaos, but it is genuinely disorganized
in a way that would look bad to anyone new, and it will get worse, not
better, once new subsystem work starts landing files without a
structure to land them into.**

---

## 1. The root-level Python sprawl — already fully mapped, not new work

`current/VM_CORE_GAP_ANALYSIS.md` already did this precisely: 77
root-level `.py` files, **zero target the current nano/stripped cell**,
35 explicitly target the old full-cell format. Categorized there into
core VM/cell-sim, OS/Pond layer, domain/Trix apps, LLVM/frontend, old
hardware bridge, and misc/support. This audit adds nothing new here —
just confirms the finding stands and flags it as the single largest
piece of the reorganization, by file count.

**Action: this is the biggest single onion-archival candidate.** Per
`#218`'s own already-established discipline ("concept survives, code
doesn't" — the same move already proven once on the RTL side, `#153`),
none of this should be preserved as live code once the real Python
rebuild starts. Pack whole, with real metadata citing the gap analysis
as the reason.

---

## 2. `pcie/` — confirmed entirely legacy, zero current references

Checked directly: none of `pcie/`'s files (testbenches, `top_arria10*.v`,
XDMA Python tooling) reference `unicell_stripped_v1.v`, `cell_wrapper_
v2.v`, or anything from the current active RTL line. This is entirely
FULL-cell-era PCIe integration work, superseded by whatever real PCIe
work eventually happens against the nano line (not yet started —
`current/START.md`'s own item).

**Action: onion-archive the whole directory as one unit.**

---

## 3. Duplicate `fpga_bridge.py` — two different files, same name, both stale

Confirmed by direct diff: `fpga_bridge.py` (root) and `fpga/fpga_bridge.py`
are **genuinely different files** (1,368 lines of diff), not copies of
each other. Worse than a simple duplicate — the root version targets
"iCEBreaker... v3 architecture" (the FULL-cell era), the `fpga/` version
targets "Protocol v2.3... `unicell.v` v2.3" (an even OLDER generation).
**Neither targets current architecture.** Anyone new opening either one
by that filename would reasonably assume it's the real bridge script —
it isn't, for either one.

**Action: both are onion-archival candidates.** If a real Python bridge
to the current hardware is ever needed, it gets written fresh against
current architecture, not recovered from either of these.

---

## 4. `PAPERS.md` (root) vs `papers/PAPERS.md` — near-duplicate

Confirmed by diff: 24 lines different out of a ~20K file — one is a
stale near-copy of the other, not a meaningful fork.

**Action: keep `papers/PAPERS.md` (it lives with its own actual
content — `paper_bridges`, `paper_main`, etc.), remove the root-level
copy.** Low-risk, quick win, no onion archival needed — this one's
just a straightforward duplicate to delete once confirmed which is
current.

---

## 5. `hardware/` at the repo root — never covered by any prior triage

**A real gap: `archeology/TRIAGE.md`'s own pass only covered
`archeology/{full-cell,shared}/docs/` — this root-level `hardware/`
folder was never touched by it at all.** Two files, checked directly:

- **`Arria10_Programming_Procedure.md`** (dated 19 June 2026) — genuinely
  real, Mustang-F100/Arria 10 content, but predates most of this
  session's own hard-won hardware lessons (SDC discipline, JTAG-wipes-
  BAR0 reboot rule, `usbfs_memory_mb`/autosuspend fixes) — likely stale
  in the same way `TRIAGE.md` already found `HARDWARE_SETUP.md` to be.
- **`YPCB_00338_bringup_findings.md`** — a completely different board
  (Kintex-7 480T, YPCB-00338), from before the Arria 10 was even
  settled on as the target hardware. Clearly, entirely historical.

**Action:** `YPCB_00338_bringup_findings.md` is a clean onion-archive
candidate. `Arria10_Programming_Procedure.md` needs a human judgment
call — worth a quick check against current knowledge before deciding
archive vs. rewrite-fresh (same treatment `TRIAGE.md` already
recommended for `HARDWARE_SETUP.md` and never got done).

---

## 6. `mathtrix` split (root `.py` files vs. `community/mathtrix/`) — checked, NOT a true duplicate

Verified directly: `community/mathtrix/format.py` is the community-
facing FORMAT REGISTRY layer (imports root-level `cell_format.py`,
references `docs/FORMAT_DEFINITION_GUIDE.md`) — a genuinely different
layer from the root-level `mathtrix.py`/`mathtrix_*_mif.py` files,
which are the actual domain-simulation logic. **Not literally the same
content in two places — two real, different layers of the same
ecosystem, both currently living at different points in the tree.**
Worth a conscious decision on whether they should live together once
the real Python rebuild starts, but this is a structural question, not
a "delete the duplicate" cleanup.

---

## 7. Dead backup files — confirmed and already proven archivable

`composer/unicell_composer.html.bak` and `.bak2` — abandoned backups,
already used as the real proof-of-concept for the onion-archival
workflow (see `points.md`, same session). Round-trip already verified
byte-for-byte identical via checksum and `diff`. Ready to actually
archive for real, not just tested.

---

## 8. Smaller items, checked, low concern

- `block_defs` — a single small text file (not a directory, despite
  the name reading like one). Low priority, not investigated further.
- `models/`, `data/`, `sketches/`, `examples/`, `tests/` — each
  contains real, purposeful content matching its name, no obvious
  scatter or duplication found in this pass. Not flagged for action.

---

## Proposed structure going forward

**The principle Alan set directly: each new subsystem gets its own
clean subfolder from the start (VM rebuild, ICM v3, compiler, PCIe,
AI-system integration) — not more loose root-level files.** Concretely:

```
core/           -- the real VM rebuild (#216's own intended location)
icm/            -- ICM v3 format + tooling, once real work starts
compiler/       -- compiler rebuild, once real work starts
pcie/           -- REPLACES the current legacy pcie/ after archival,
                   real work only, targeting current architecture
ai/             -- the AI-interaction port work (#57's own long-
                   standing "first-class, per-subsystem" requirement)
```

Legacy material that any of these replace gets packed whole into
`.onion` archives (internal structure preserved, not flattened),
stored in `archeology/`, with real descriptive metadata — proven
working this session, not theoretical.

---

## Priority order for actually doing this

1. **Quick, low-risk wins first:** delete the confirmed-duplicate root
   `PAPERS.md`; onion-archive the two confirmed-dead backup files for
   real (not just the test).
2. **`pcie/` and both `fpga_bridge.py` files** — high-confidence
   archival candidates, clearly superseded, low risk since nothing
   current references them (confirmed by direct search).
3. **The 77-file root Python sprawl** — the big one. Should wait until
   the real `core/`/VM rebuild actually starts, so the archival
   happens as part of "replacing" rather than "deleting speculatively"
   — matching `#218`'s own stated discipline precisely.
4. **`hardware/Arria10_Programming_Procedure.md`** — needs a human call
   (archive vs. refresh), not a mechanical archive.
5. **`mathtrix` root/community split** — a real structural decision,
   not an archival one, best made once the Trix domain-model rebuild
   is actually in scope.
