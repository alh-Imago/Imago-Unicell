# Toolchain Setup — Arria 10 / Quartus (2026-08-04) and Tang Nano 20K / open Gowin flow (2026-10)

*The Tang Nano 20K section is at the end and covers the current line.*

**Status: written by pulling verified-current facts out of `points.md`
and cross-checking against `archeology/full-cell/docs/hardware/
PCIE_ARRIA10_NOTES.md`, replacing `archeology/shared/docs/hardware/
HARDWARE_SETUP.md` as the living reference. That file is now stale in a
way that matters, not just old-hardware stale — it states outright
"As of July 2026, Linux (not Windows) is the primary development
platform," which was true when written but is NOT true now (see below).
Genuinely shared regardless of which cell architecture is being
built/tested — this is about the board and toolchain, not cell logic.**

## Hardware

- **IEI Mustang-F100-A10**, Arria 10 GX660, part `10AX066H2F34E2SG`
- JTAG IDCODE: `0x02E250DD`
- Config is **volatile SRAM** (PCIe-powered) — any host restart, sleep,
  or PCIe re-enumeration **wipes it**. JTAG IDCODE still enumerates even
  when the fabric config is gone — misleading, don't trust IDCODE alone
  as proof the design is actually loaded.
- Two cards available; the second is a clean unit.
- Programmer: Waveshare USB-Blaster clone (fixed ~6 MHz).

## Toolchain

**Quartus Prime 25.1 Standard Edition.** Node-locked license, tied to
the machine's NIC/MAC address — a dual-boot machine with the same
physical NIC validates the same license on either OS.

## Windows is currently the authoritative path — solid every time

This is the current, session-verified state, and it's worth being
direct about since it reverses what `HARDWARE_SETUP.md` said when
written: **program and test on Windows.** Linux JTAG/Tcl execution on
this same physical machine remains unreliable — `quartus_pgm` sometimes
reports success when programming actually failed; Tcl scripts fail
roughly 9 times out of 10. This is despite the `usbfs_memory_mb` and
USB-autosuspend fixes below being correctly applied and confirmed
resolved for what they specifically target — something else, still
unidentified, is wrong on Linux on this particular machine. Possibly
board-specific, possibly USB-Blaster-clone/driver-timing related,
distinct from the two resolved issues below. **Plan in progress:** move
the second card to a dedicated, separate Linux machine (not this dual-
boot one, and not Manjaro) to isolate whether the instability is
machine-specific or a genuine platform issue — not yet done.

**Practical consequence:** if you're picking up this project fresh,
default to Windows for programming and Tcl-based testing unless/until
that isolation test says otherwise. Don't assume the Linux fixes below
mean Linux is currently reliable on this hardware — they fixed two real,
confirmed problems, and Linux use here is still paused regardless.

## Critical procedural rule: reboot after every reprogram, before any PCIe test

**Rule** (established the hard way, see `PCIE_ARRIA10_NOTES.md` ~line
740): program via JTAG, then **reboot the host**, then run any PCIe
test. JTAG reprogramming wipes config space including BAR0 — Windows
caches the old PCI config space until it re-walks it, which only
happens on a real reboot, not just a reprogram. Skipping the reboot
produces a symptom indistinguishable from a dead/unresponsive card. A
reboot is **not** needed for anything that doesn't touch config space
(e.g. some JTAG-only ISSP captures) — but when in doubt, reboot; it's
cheap insurance against a long, misleading debugging session.

## Known-good baseline

Run `fpga/icm64_readstate.tcl` as the reference test when in doubt about
whether the fabric/card is genuinely alive — it authenticates correctly,
lands config, reads a real latch, and has a built-in cycle-tick
snapshot-health check. If this doesn't pass cleanly, don't trust any
other result until it does.

## Linux JTAG instability — two real, confirmed fixes (still not sufficient on this machine, see above)

Kept because they're genuinely correct fixes for two real Linux-USB-
stack defaults, worth applying on ANY fresh Linux Quartus/JTAG setup
regardless of this machine's own unresolved third issue — and because
the planned dedicated second Linux machine will need them too.

### `usbfs_memory_mb`
Linux defaults this kernel parameter to 16 MB — far too small for
`quartus_stp`/`jtagd`'s libusb-based ISSP transfer buffers. Windows
imposes no equivalent cap. Symptom: `quartus_stp` scripts using
`start_insystem_source_probe`/`read_probe_data` crash with an internal
Tcl interpreter error, often before the first read completes, even
though `jtagconfig` sees the device fine and `quartus_pgm` may succeed.

```bash
# Immediate (until next reboot):
echo 1000 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb

# Persistent:
echo 'options usbcore usbfs_memory_mb=1000' | sudo tee /etc/modprobe.d/usbfs_memory.conf
```

### USB hub-level autosuspend
Even with the fix above, transfers can still drop out **mid-sequence**
(not on the first call, partway through a loop of reads/writes).
Setting the Blaster's own device node to `power/control=on` is not
enough — its **parent hub** (often the root hub) can autosuspend
independently and drop the whole bus mid-transaction. Check every node
in the chain:

```bash
lsusb -t
for f in /sys/bus/usb/devices/*/power/control; do echo "$f: $(cat $f)"; done
```

Fix the specific parent, or disable autosuspend globally (blunt but
reliable):
```bash
echo 'options usbcore autosuspend=-1' | sudo tee -a /etc/modprobe.d/usbfs_memory.conf
```

Both are Linux-USB-stack defaults Windows doesn't impose — worth ruling
out first on any fresh Linux setup before chasing design-level
explanations for intermittent JTAG behavior. Neither is sufficient by
itself to make Linux reliable on the current dual-boot machine (see
above) — a real, separate, unresolved third issue remains there.

## Finding real resource locations (DSP, M20K, etc.) via Chip Planner

**A general METHOD, not just data for this one card** — Alan's own
framing: other Quartus-supported devices, and quite possibly other
vendors' place-and-route GUIs entirely, are likely to expose a similar
diagram/mapping capability. Worth knowing this workflow on its own
merits, independent of which specific card is in front of you.

1. Open a project in Quartus (compiled or not — base floorplan
   resource layout doesn't need a finished fit). **Tools → Chip
   Planner.**
2. **Bulk, type-filtered view:** run `find_resources_of_type
   "<Resource Type Name>"` in the Tcl console (e.g. `"MP DSP"` for DSP
   blocks on Arria 10). Highlights every instance of that type directly
   on the floorplan and lists them in the Report panel tree. The exact
   type-name string is device/family-specific — the Chip Planner's own
   "Report Resource" dialog has a dropdown listing every valid type
   name for the loaded device; check there rather than guessing.
3. **Exact per-block coordinates — the reliable path:** click directly
   on a highlighted block in the floorplan. The "Resource Properties"
   panel shows `Full Name` (e.g. `M20K_X52_Y75_N0`), exact `Coordinate`
   `(X, Y)`, `Resource Type`, `Block Utilization`, `Location
   Assignment`. **This GUI path is more reliable than scripting it** —
   `get_node_info`/`get_info_parameters` (the `::quartus::chip_planner`
   Tcl package) were tried first and left genuinely inconclusive after
   several real, confirmed-syntax attempts (full trace in `points.md
   #274`, kept so nobody re-walks the same dead end). Real per-block
   naming convention observed: `<RESOURCE_TYPE>_X<col>_Y<row>_N<index>`.
4. **Color legend** (Chip Planner's own "Color Legend" tab is
   authoritative — don't assume the mapping below carries to a
   different device/version): on this card, blue = ALM (normal fabric
   logic), salmon/pink = MSDSP, lime/yellow = M20K.

**Real data for THIS card (`10AX066H2F34E2SG`):** 8 DSP columns and 11
M20K columns, confirmed completely disjoint (zero shared X-coordinate)
— full coordinate tables in `points.md #275` (DSP) and `#276` (M20K).



The debug/readback path (ISSP bridge, `DEBUG_SELECT`, the selector-3
latch view used for diagnostics) is a genuine security door — strip it
and lock JTAG in any production build. Fine to leave in for bring-up and
active development; don't ship it.

## What this doc does not cover

Board-specific bring-up notes tied to a specific RTL line (PCIe HIP
config, BAR0 history, pin assignments) stay in
`archeology/full-cell/docs/hardware/PCIE_ARRIA10_NOTES.md` — that's
FULL-cell/PCIe-specific history, not generic toolchain setup. The old
iCEBreaker/Kintex-7/UART-bridge workflow in the superseded
`HARDWARE_SETUP.md` is not carried forward here — that hardware line is
not part of current active work.

---

## Tang Nano 20K — the open Gowin toolchain (added 2026-10-06; current line since `#886`)

Everything above is the Arria 10 / Quartus line. The Tang Nano 20K
(Gowin `GW2AR-LV18QN88C8/I7`, family GW2A-18C) uses a fully open flow
that runs on Linux. That includes this project's cloud sandboxes, where
synthesis and place-and-route are run. Flashing happens on Alan's
machine.

| step | tool | install |
|---|---|---|
| simulate | `iverilog` (12.0 used) | `apt-get install iverilog` |
| synthesise | `yosys` `synth_gowin` (0.33 used); `-nowidelut` is the default for generated designs (`#952`) | `apt-get install yosys` |
| place and route | `nextpnr-himbaechel-gowin` | `pip install yowasp-nextpnr-himbaechel-gowin`. **Not** apt's `nextpnr-gowin`, which only has the GW1N family (`#889`) |
| bitstream | `gowin_pack` from apycula (0.32 used) | `pip install apycula`. Give it the FULL device string; `-d GW2AR-18C` alone has no chip database (`#892`) |
| flash | `openFPGALoader -b tangnano20k FILE.fs` | writes to SRAM by default; see `docs/man/tang-nano-20k-getting-started.md` before writing flash |

End-to-end reference build with a pinned seed:
`tools/gowin_sizing/build_smoke_bitstream.sh`. The committed
`fpga/build/unicell_tang_nano_20k_smoke_v2.fs` is its byte-identical
output.

**Board notes.** The clock is pin 4 at 27 MHz. Do not use the reset
button (`BTN_RST_N`) in a design yet: it held the v1 smoke test in
reset on the real board, for an unknown reason (`#896`). The board's
constraints and facts are in `docs/man/tang-nano-20k.man.json` /
`.cst`, generated by `tools/man_gen/gen_tang_nano_20k_man.py`.

**Version caveat.** The recorded synthesis numbers come from yosys
0.33. A different yosys version may give different counts, so re-measure
before comparing (`#965`).

