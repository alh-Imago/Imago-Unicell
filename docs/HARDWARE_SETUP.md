# Hardware Backend Setup

## Overview

UniCell hardware backends use the UART bridge (`uart_bridge.v`) as the
universal host interface. The same setup process works for any UniCell
hardware — iCEBreaker, Arria 10, or future cards.

Once set up, the backend appears automatically in the server at
`GET /api/hardware` and can be selected per-job.

---

## iCEBreaker (iCE40UP5K)

### 1. Build the UART bridge bitstream

On FPGA1 (Debian, OSS CAD Suite installed):

```bash
cd ~/Imago-Unicell/fpga/verilog
make uart_bridge   # or manually:
yosys -p "synth_ice40 -top uart_bridge -json uart_bridge.json" uart_bridge.v
nextpnr-ice40 --up5k --package sg48 --json uart_bridge.json \
              --pcf icebreaker.pcf --asc uart_bridge.asc
icepack uart_bridge.asc uart_bridge.bin
```

### 2. Flash to iCEBreaker

```bash
iceprog uart_bridge.bin
```

The iCEBreaker will enumerate as `/dev/ttyUSB0` (or similar).

### 3. Find the serial port

```bash
# Linux
ls /dev/ttyUSB*    # typically /dev/ttyUSB0

# Windows  
# Device Manager → Ports (COM & LPT) → look for USB Serial Port
```

### 4. Configure the server

```bash
# Via API (server running)
curl -X POST http://localhost:5000/api/hardware \
  -H 'Content-Type: application/json' \
  -d '{"backend":"icebreaker","port":"/dev/ttyUSB0"}'

# Or edit hardware_config.json directly
{"icebreaker_port": "/dev/ttyUSB0"}
```

### 5. Restart the server

```bash
python unicell_server.py
```

The server startup will show:
```
  ✓ iCEBreaker (iCE40UP5K)  [/dev/ttyUSB0]
```

---

## Arria 10 GX660 (Mustang-F100)

### 1. Build the UART bridge bitstream (Quartus)

Open Quartus on the Windows machine:
- New project → target device: 10AX066H2F34E2SG
- Add `fpga/verilog/uart_bridge.v`
- Compile (Analysis & Synthesis → Fitter → Assembler)
- Output: `uart_bridge.sof`

### 2. Program via Waveshare USB Blaster V2

Connect Waveshare to PC, JST SH cable to 10-pin JTAG header on card.

```
Quartus → Tools → Programmer → Hardware Setup → USB-BlasterII
Add File → uart_bridge.sof
Program/Configure → Start
```

### 3. Find the serial port

The UART bridge exposes a serial port after programming:
```bash
# Linux (FPGA1 via Samba share)
ls /dev/ttyUSB*    # typically /dev/ttyUSB1 (if iCEBreaker is ttyUSB0)

# Windows
# Device Manager → Ports → new COM port appears after programming
```

### 4. Configure the server

```bash
curl -X POST http://localhost:5000/api/hardware \
  -H 'Content-Type: application/json' \
  -d '{"backend":"arria10","port":"/dev/ttyUSB1"}'
```

---

## Arria 10 — Compiling and Programming on Linux (Quartus, native)

As of July 2026, Linux (not Windows) is the primary development platform for
Imago-Unicell — Quartus Prime 25.1std runs natively on Linux, which gives
direct `/dev` access to the JTAG/USB-Blaster hardware that Windows abstracts
away. This section covers Linux-specific setup and gotchas not covered above.

### 1. Install Quartus Prime Standard Edition (Linux)

```bash
chmod +x qinst-standard-linux-25.1std-*.run
./qinst-standard-linux-25.1std-*.run
```

- Install as your normal user (e.g. into `~/intelFPGA/25.1`), not as root.
- Node-locked licenses are tied to the machine's NIC/MAC address, not the OS —
  a dual-boot machine with the same physical NIC validates the same license
  fine on Linux as it did on Windows.
- Missing shared libraries are common on modern/rolling distros. On Manjaro/Arch:
  ```bash
  sudo pacman -S libxcrypt-compat   # fixes: libcrypt.so.1: cannot open shared object file
  ```
  (Ubuntu/Debian: `libcrypt1` or `libcrypt1:amd64`; Fedora: `libxcrypt-compat`)

### 2. USB-Blaster JTAG permissions

Quartus needs raw USB access to the Blaster cable via usbfs. Without this,
`jtagconfig` fails with "Insufficient port permissions":

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

Unplug and replug the USB-Blaster after this (rules apply on next enumeration,
not to an already-connected device).

### 3. `usbfs_memory_mb` — the critical, easy-to-miss fix

**Symptom:** `quartus_stp` scripts that use `start_insystem_source_probe` /
`read_probe_data` (e.g. `icm64_readstate.tcl`) crash with
`ERROR: An internal Tcl interpreter error occurred`, often failing before
even the first read completes. `jtagconfig` still sees the device fine, and
programming (`quartus_pgm`) may even succeed — only the ISSP/SignalTap-style
JTAG data transfers are affected.

**Root cause:** Linux's default `usbfs_memory_mb` kernel parameter is **16 MB**
— far too small for the buffer sizes `quartus_stp`/`jtagd`'s libusb-based
transfers want to allocate for ISSP reads. Windows imposes no equivalent cap,
which is why an identical `.sof` and identical script run cleanly there while
crashing on Linux with no other symptom.

**Fix:**
```bash
# Immediate (until next reboot):
echo 1000 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb

# Persistent (survives reboots):
echo 'options usbcore usbfs_memory_mb=1000' | sudo tee /etc/modprobe.d/usbfs_memory.conf
```

Do this **before** troubleshooting anything else JTAG/ISSP-related on a fresh
Linux install — this single kernel parameter caused a full day of apparently
unrelated symptoms (readstate crashes, what looked like design/clock bugs,
false leads) before being identified as the actual root cause. Check the
current value with:
```bash
cat /sys/module/usbcore/parameters/usbfs_memory_mb
```

### 4. `jtagd` staleness after reconnects/reprograms

If `jtagconfig` sees the device but `quartus_stp` reports
`No In-System Sources and Probes instance was found` right after a fresh
program cycle or a cable/port change, restart the JTAG daemon before assuming
a design problem:
```bash
killall jtagd
jtagd
jtagconfig
```

### 5. Compile and program from the command line

```bash
cd fpga/quartus
quartus_sh --flow compile Unicell-Q-zone1-v3          # or open in GUI
quartus_pgm -c "USB-Blaster [3-1]" -m jtag -o "p;output_files/Unicell-Q-zone1-v3.sof"
quartus_stp -t ../icm64_readstate.tcl
```

Note: `.qpf` project files and `issp.qsys` (the In-System Sources and Probes
IP, regenerated per build via IP Catalog — Source Port Width 66, Probe Port
Width 113, Use Source Clock enabled) are **not committed to git** — they are
local/regenerated build artifacts. A fresh clone will show `.qsf` files with
no matching `.qpf`; create one manually (same base filename, e.g.
`Unicell-Q-zone1-v3.qpf`) with:
```
QUARTUS_VERSION = "25.1"
PROJECT_REVISION = "Unicell-Q-zone1-v3"
```
then regenerate `issp.qsys` via Tools → IP Catalog before compiling.

### 6. `CLK_100M` is single-ended, not LVDS

Despite the RTL comment describing `CLK_100M` (pin E23) as a "diff pair,
p-leg on E23," the board's clock reference is driven **single-ended**. This
has been re-confirmed by direct measurement (`cycle_count` ticking in
`icm64_readstate.tcl`) on both the original bring-up and the Linux migration.
Forcing `IO_STANDARD LVDS` on `CLK_100M` is a known-wrong dead end that was
tried and ruled out during the Linux migration — leave the `.qsf` with no
explicit `IO_STANDARD` override on this pin (default single-ended applies).

---

## Adding a future card

Any UniCell card with a UART bridge follows the same process:

1. Synthesise `uart_bridge.v` for the target device
2. Flash the bitstream
3. Find the serial port
4. Add to `hardware_config.json`:
   ```json
   {"my_new_card_port": "/dev/ttyUSB2"}
   ```
5. Add the backend entry to `unicell_server.py` → `detect_backends()`
6. Restart server

The REST API, frontend, and all client code stay unchanged.

---

## Verifying hardware is working

```bash
# Check backend status
curl http://localhost:5000/api/hardware

# Run a test model on hardware
curl -X POST http://localhost:5000/api/run/laplacian_1d \
  -H 'Content-Type: application/json' \
  -d '{"size": 8, "steps": 5, "backend": "icebreaker"}'

# Poll for result
curl http://localhost:5000/api/job/<job_id>
```

---

## Troubleshooting

**Backend shows as unavailable after setting port:**
- Check cable is connected and card is powered
- Verify port with: `ls -la /dev/ttyUSB*`
- Check permissions: `sudo chmod 666 /dev/ttyUSB0`
- Try a different USB port on the host machine

**jtagconfig shows no hardware (Arria 10):**
- Waveshare USB Blaster not detected — check Windows Device Manager
- Driver may need manual install from `F:\Q\quartus\drivers\usb-blaster\`

**Serial port found but communication fails:**
- Baud rate mismatch — check `uart_bridge.v` BAUD_RATE parameter
- Card not fully powered — check SATA auxiliary power connector
- Wrong port — may be COM3/COM4 on Windows, /dev/ttyUSB1 on Linux

---
*See also: fpga_bridge.py (Python host interface), uart_bridge.v (Verilog)*
