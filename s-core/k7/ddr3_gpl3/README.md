# ddr3_gpl3 — GPL-3.0 code lives ONLY in this folder

**Everything under `upstream/` is NOT ours and is NOT under this project's MIT or CERN OHL licences.**
It is the UberDDR3 DDR3 memory controller by Angelo Jacobo, licensed **GNU GPL version 3** (full text in `upstream/LICENSE`).

## Decision (Alan, 2026-11-16)
Option 1: use UberDDR3 for the Kintex card's DDR3, keep it in this one folder, keep our own code in separate files, label everything.
The rest of the repository stays MIT (software) and CERN OHL-2 Permissive (hardware).

## Provenance
- Upstream: https://github.com/AngeloJacobo/UberDDR3
- Commit copied: `79d8fd3` ("Merge pull request #45 from jirgais/arty_a7_demo"), the commit sirmick tested on this card.
- Copied verbatim from upstream: `LICENSE`, `rtl/` (controller, PHY, top, AXI wrapper, ECC, SPD, ECP5 PHY), `README.md` (as `README-upstream.md`).
- No upstream file has been edited. If we ever must change one, copy it next to it with a new name and a header saying what changed and when (GPL requires modified files to carry notice of the change); never edit in place.

## What is ours, and what is GPL
| Where | Licence |
|---|---|
| `upstream/**` | GPL-3.0 (Angelo Jacobo) |
| Anything we write that is derived from, or is a modified copy of, `upstream/**` | GPL-3.0, put it in this folder and mark it |
| Our own wrapper / glue written against only the controller's ports | Our intent: keep it in this folder too, marked GPL-3.0 where it instantiates the controller, so the boundary is plain |
| The rest of `s-core/` (pool, sequencer, JTAG link, `farram_bram_v1.v`, scripts) | MIT / CERN OHL-2 as before |

## What this means for a bitstream or design that contains it
A build that includes `upstream/` is a combined work. If it is ever given to someone else, it has to be offered with its source under GPL-3.0.
Using it only on our own card does not trigger that. Not legal advice; if the project is ever sold or licensed commercially, get this checked by someone qualified.

## Keeping the boundary clean
- Our far-RAM interface (`req/ack`, same as `sdram_ctl` and `farram_bram_v1`) is the only thing the pool sees. The pool never includes a file from this folder.
- Builds that need DDR3 are separate top files (named `*_ddr3`) and are labelled GPL-3.0 in their header and in their Makefile. The existing BRAM build (`sc_k7_v1`) has no GPL code in it.
- Every file we add in this folder starts with a header naming this decision and the upstream commit.
