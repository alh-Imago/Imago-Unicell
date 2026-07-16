# Second Linux Machine — Fresh Bring-Up Runbook

Purpose: a known-good Linux JTAG rig, independent of the first Linux machine,
to isolate whether the July 2026 JTAG instability (see `HARDWARE_SETUP.md`)
was machine-specific or a genuine Quartus/Linux/USB-Blaster class issue. Set
up card 2 + a new USB-Blaster on this machine and follow this in order — it
folds in every gotcha hit on the first machine so this one doesn't repeat
a full day of debugging.

Do the steps in this order. Do not skip the GRUB step or defer it "for
later" — on the first machine, deferring it caused a full day of apparently
unrelated JTAG failures before it was traced back to this.

---

## 0. Before plugging anything in

- [ ] Second Mustang-F100-A10 card seated in a PCIe slot (x8 Gen2 electrical,
      even if only using JTAG for now — don't rely on a cheap riser rated
      below x4 if PCIe bring-up is planned on this machine later)
- [ ] Second USB-Blaster (Waveshare clone or genuine Intel) — **do not**
      reuse the first machine's Blaster; this needs to be a fully
      independent chain for the comparison to mean anything
- [ ] Note this machine's OS/distro and kernel (`cat /etc/os-release`,
      `uname -r`) — Manjaro vs. Ubuntu/Debian/Fedora changes a couple of
      package names below

## 1. Install Quartus Prime Standard Edition 25.1std

```bash
chmod +x qinst-standard-linux-25.1std-*.run
./qinst-standard-linux-25.1std-*.run
```
- Install as a normal user (e.g. `~/intelFPGA/25.1`), not root.
- License: node-locked to NIC/MAC. If this is a genuinely different physical
  machine (different NIC) from the Windows box, this will need a **new**
  license file from Intel's licensing portal — the existing one won't
  validate here. Confirm this before spending time on anything else.
- Missing shared libs are common on modern distros:
  - Arch/Manjaro: `sudo pacman -S libxcrypt-compat`
  - Ubuntu/Debian: `sudo apt install libcrypt1` (or grab the `.deb` from an
    older Ubuntu archive if not in current repos)
  - Fedora: `sudo dnf install libxcrypt-compat`

## 2. USB-Blaster udev permissions

```bash
sudo tee /etc/udev/rules.d/92-usbblaster.rules << 'EOF'
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6001", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6002", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6003", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6010", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6810", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6020", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6022", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6024", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6025", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6026", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="602C", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="602D", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="602E", MODE="0666"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger
```
Unplug/replug the Blaster after this.

## 3. Kernel USB parameters — via GRUB, not live `echo` (do this now, not later)

**Why GRUB and not `echo ... | sudo tee /sys/module/...`:** on the first
machine, `usbcore` turned out to be built into the kernel (not a loadable
module), so `/etc/modprobe.d/` had zero effect, and `usbfs_memory_mb`
specifically could not be changed live at all post-boot on that kernel —
only `autosuspend` accepted a live change, and it silently reverted anyway
after the next reboot since it was never made truly persistent. Check
whether that applies here too:
```bash
lsmod | grep -i usbcore
```
If nothing prints, `usbcore` is built-in on this machine too — go straight
to the GRUB method below rather than losing time on live `echo` attempts.

```bash
sudo nano /etc/default/grub
```
Add to the `GRUB_CMDLINE_LINUX_DEFAULT="..."` line:
```
usbcore.usbfs_memory_mb=1000 usbcore.autosuspend=-1
```
Then:
```bash
sudo grub-mkconfig -o /boot/grub/grub.cfg
sudo reboot
```
After reboot, confirm both actually took:
```bash
cat /proc/cmdline
cat /sys/module/usbcore/parameters/usbfs_memory_mb   # want 1000
cat /sys/module/usbcore/parameters/autosuspend        # want -1
```
Do not proceed past this point until both show the correct values.

## 4. Clone the repo

```bash
git clone https://<fresh-PAT>@github.com/alh-Imago/Imago-Unicell.git
```

Remember: `.qpf` project files and `issp.qsys` are **not committed** —
local/regenerated build artifacts by design (see `HARDWARE_SETUP.md`).
You will need to recreate them on this machine (steps 5-6).

## 5. Fix `.qsf` paths for this machine's clone layout

The committed `Unicell-Q-zone1-v3.qsf` already has correct **relative**
paths (fixed on the first machine, commit `7fc700f`) — this step should
only be needed if this machine's clone lives at a different relative depth
than `<repo>/fpga/quartus/`. Sanity-check first:
```bash
cd Imago-Unicell/fpga/quartus
grep "VERILOG_FILE\|SDC_FILE\|QSYS_FILE" Unicell-Q-zone1-v3.qsf
```
Expected (already correct if paths are relative and files resolve):
```
VERILOG_FILE ../verilog/unicell64_v3.v
VERILOG_FILE ../verilog/unicell_array64_v3.v
VERILOG_FILE ../verilog/unicell_zone64_v3.v
SDC_FILE "Unicell-Q.sdc"
VERILOG_FILE ../../pcie/unicell_issp_bridge.v
VERILOG_FILE ../verilog/uart_bridge.v
QSYS_FILE issp.qsys
VERILOG_FILE ../verilog/top_arria10_zone1_v3.v
```
If any of these don't resolve (`find .. -iname <filename>` to check), fix
the specific line(s) with `sed`, same pattern as the first machine.

## 6. Create the `.qpf` and regenerate `issp.qsys`

```bash
cat > Unicell-Q-zone1-v3.qpf << 'EOF'
QUARTUS_VERSION = "25.1"
PROJECT_REVISION = "Unicell-Q-zone1-v3"
EOF
```

Open in Quartus (File → Open Project → this `.qpf`). Then Tools → IP
Catalog → "In-System Sources and Probes":
- Instance name: `issp`
- Source Port Width: **66**
- Probe Port Width: **113**
- Use Source Clock: **enabled**
- Save as `issp.qsys` in `fpga/quartus/` (same dir as the `.qsf`)

## 7. Compile

```bash
quartus_sh --flow compile Unicell-Q-zone1-v3
```
Expect ~0 errors. `CLK_100M` (pin E23) should compile as **single-ended**
(no `IO_STANDARD` override needed) — do NOT set it to LVDS; that was a
confirmed dead end on the first machine despite the RTL comment describing
a "diff pair." Sanity-check after compile:
```bash
grep -i "CLK_100M" output_files/*.pin
```
Should show plain `1.8 V`, not `LVDS`.

## 8. Program and verify — this is the actual test

```bash
jtagconfig                                          # confirm chain, note IDCODE
quartus_pgm -c "USB-Blaster [X-Y]" -m jtag -o "p;output_files/Unicell-Q-zone1-v3.sof"
quartus_stp -t ../icm64_readstate.tcl
```

**What "clean" looks like** (this is the actual pass/fail bar for the
machine-isolation test):
- `quartus_pgm` completes in ~50-60s, reports "Configuration succeeded" on
  the first attempt, no retries needed
- `jtagconfig` sees the device consistently across several repeated checks
  a minute or two apart, no "chain broken" / "insufficient permissions"
- `icm64_readstate.tcl` runs to completion with **zero** `(retry N/5: ...
  glitch)` lines printed — the retry wrapper (added 2026-07-16, commit
  `58a3cc4`) is a workaround for confirmed USB/JTAG instability, not
  something that should be firing on a healthy connection
- `cycle_count` ticks between the two snapshot reads (clock alive)
- Final `cmd_latch`/`a_data`/output fields show real configured values
  (not all-zero, not all-`F`) — the known-good sequence in the script
  (`docs/V3_COMMAND_CONTRACT.md` section 7) boots and configures the whole
  zone, routes east, and injects a value that should fire

If this machine passes all of the above cleanly with no retries firing at
all, that's a strong signal the first machine's instability was specific to
that machine (USB controller, motherboard, or a marginal cable/cable path)
rather than a general Quartus/Linux/USB-Blaster problem. If this machine
shows the *same* instability pattern, that's a different and more useful
finding — point back to `HARDWARE_SETUP.md` and treat it as a genuine class
issue worth escalating (Intel support / Quartus forums) rather than a local
setup mistake.

---
*See also: `HARDWARE_SETUP.md` (general Linux Quartus/JTAG setup + the two
confirmed root causes from the first machine), `V3_COMMAND_CONTRACT.md`
(the command/auth protocol), `icm64_readstate.tcl` (the test script itself).*
