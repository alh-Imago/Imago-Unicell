# IP Reference Files

Generated Quartus IP configuration and component files, checked in deliberately.

**Why these are here.** Generated IP output normally isn't versioned, and this
repo previously followed that convention -- `pcie_a10_hip_0` and `pio_bridge_0`
were referenced only by instance name in `pcie/pcie_hip_wrapper.v`. During the
PCIe bring-up of 2026-07-24/26 that cost real hours: port directions and widths
that could have been read directly off a `.cmp` file were instead inferred,
twice incorrectly. These files are small, plain text, and answer those questions
offline without needing the Quartus machine.

None of this is the actual generated RTL -- that stays out of the repo. These
are the interface descriptions and configuration, which is what's useful to
read.

## Files

| File | What it is | What it answers |
|---|---|---|
| `pio_bridge_0.cmp` | Component declaration for the PIO Avalon-ST-to-Avalon-MM bridge | Exact port names, directions, widths. Settled that `pld_core_ready` is an **output** of the bridge (so it is driven), and that every conduit width in `pcie_hip_wrapper.v` matches. |
| `pcie_example_design.qsys` | Intel's own generated PIO example design system | The known-good reference wiring. Diffing against it found the `hip_ctrl` divergence (see below). |
| `pcie_example_design.cmp` | Component declaration for that example system | Confirmed the exported ports Intel expects the level above to drive: `hip_ctrl_test_in[31:0]`, `hip_ctrl_simu_mode_pipe`, `pcie_rstn_npor`, `pcie_rstn_pin_perst`. |
| `pcie_a10_hip_0.qsys` | Our PCIe Hard IP configuration | Device/Subsystem IDs, BAR setup, link parameters. Reading this found the identity fields left at `0`. |
| `pio_bridge_0.qsys` | Our PIO bridge configuration | Avalon-ST interface width. |
| `issp.qsys` | In-System Sources and Probes configuration | JTAG debug path. |
| `altera_pcie_win_driver.inf.original` | Intel's shipped Windows driver INF | Contains a genuine packaging bug -- see below. |
| `altera_pcie_win_driver.inf.fixed` | Corrected version | The one that actually installs. |

## The two findings worth remembering

**The driver INF bug.** Intel's shipped `.inf` maps the device to install
section `Altera_Device` in its `[ALTERA.NTamd64]` Models section, but every
actual DDInstall section in the file is named `AltPCI_Inst`. Windows finds no
matching section -- including no `AddService` directive -- and fails with Code
39 / `STATUS_PNP_FUNCTION_DRIVER_REQUIRED` (`0xC0000494`). The `.fixed` version
renames the five section headers. Since that changes the file, it no longer
matches the signed `.cat`, so Test Mode must be active to install it. Diff the
two files to see the whole change.

**`hip_ctrl` is exported, not connected.** In `pcie_example_design.qsys`, every
DUT<->APPS conduit is wired internally *except* `hip_ctrl`:

```xml
<interface name="hip_ctrl" internal="DUT.hip_ctrl" type="conduit" dir="end" />
```

Intel expects the level above the Qsys system to drive `test_in[31:0]` and
`simu_mode_pipe`. `pcie_hip_wrapper.v` originally left both unconnected, so
synthesis tied them to zero -- the only structural divergence from a
configuration known to work on silicon. See the wrapper's own comment block for
the value used and where it comes from.

## Not included

Intel's Design Example User Guide (UG-20039, doc 683065) is the source for the
`test_in` typical values and the SignalTap `build_stp.tcl` route described in
`docs/PCIE_ARRIA10_NOTES.md`. It's Intel's copyrighted documentation, so it
isn't checked in -- download it from Intel if needed.

Likewise `Alt_Test.exe`, `AlteraPCILibraryDll.dll` and the driver binaries
(`.sys`, `.cat`, `WdfCoinstaller01011.dll`) are Intel-distributed binaries and
stay out of the repo. The host-side test tool built against that DLL's API is
ours and lives separately.

## Keeping these current

These are snapshots. If the IP is regenerated with different parameters, they go
stale silently -- nothing checks them. Re-copy after any IP Catalog change that
alters ports, widths, or identity fields, and note what changed.
