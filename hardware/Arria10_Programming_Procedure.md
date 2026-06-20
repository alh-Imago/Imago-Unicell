# Imago UniCell — Arria 10 GX660 Programming Procedure
## Repeatable guide for IEI Mustang-F100 cards (2-card and 8-card builds)

**Status:** Verified on Card 1 — 19 June 2026  
**Author:** Alan Hill  
**Hardware:** IEI Mustang-F100-A10 (Arria 10 GX660)

---

## Hardware Required

- IEI Mustang-F100-A10 card (Arria 10 GX660, PCIe Gen3 x8)
- IEI USB Download Cable kit (part `7Z000-00FPGA00`) — supplied by IEI, use as-is
- Host machine with PCIe x8 slot (Gen3), USB 3.0, running Linux
- USB Blaster V2 (clone) — enumerates as `USB-Blaster`, VID:PID `09fb:6001`

**Important:** The Mustang-F100 draws under 60W and is powered entirely from the PCIe slot. No external power connector is required for normal operation. The host machine PSU must have headroom above its existing load. A small form factor (SFF) machine with a 255W PSU is **not recommended** as the host.

---

## Software Required

- Manjaro Linux (or equivalent Arch-based distro) — persistent install, not live USB
- Quartus Prime Standard Edition 25.1 (Windows, for compilation — node-locked licence)
- Quartus Prime Programmer standalone (Linux, free, no licence required)
- Python 3.x
- Git

**Key device string:** `10AX066H2F34E2SG` (use exactly — one common error is adding an extra `2`)

---

## Part 1 — Compile the Bitstream (Windows, one-time per design)

This is done once on the licensed Windows machine. The output `.sof` file is reused for every card.

1. Open Quartus Prime Standard Edition 25.1
2. Compile the project targeting device `10AX066H2F34E2SG`
3. Output files land in the project's `output_files/` directory
4. Confirm `Unicell-Q.sof` exists in that directory
5. Keep this file accessible on a shared or portable drive

**Note:** The Arria 10 IOPLL RST_N cannot be reliably driven in Standard Edition — remove any PLL, use a simple clock divider instead. All five Verilog files must be added manually to the Quartus project. Run Project → Clean Project after any file changes.

---

## Part 2 — Linux Environment Setup (one-time per host machine)

### 2a. Install Manjaro Linux

Install Manjaro to a dedicated drive (not a live USB — changes must persist). During the Manjaro installer:

- On the **Partitions** screen, use the device dropdown to select the correct target drive
- Verify the "After" partition layout shows only that drive before clicking Next
- **Double-check you are not targeting any Windows drive** — the installer defaults to the first detected disk

### 2b. Install Quartus Prime Programmer (Linux, free)

1. Open Firefox and navigate to:  
   `https://www.altera.com/downloads/fpga-development-tools/quartus-prime-standard-edition-design-software-version-25-1-linux`
2. Download the installer: `qinst-standard-linux-25.1std-1129.run` (~71MB)
3. In terminal, navigate to Downloads and run:
   ```bash
   cd ~/Downloads
   chmod +x qinst-standard-linux-25.1std-1129.run
   ./qinst-standard-linux-25.1std-1129.run
   ```
   *(Use Tab key to autocomplete the filename — avoids typos)*
4. In the installer GUI, **uncheck everything except:**
   - Quartus Prime Programmer and Tools (0.41 GB)
   - *(Uncheck Arria 10 device support — not needed for programming)*
5. Install to default location: `/home/alan/altera_standard/25.1std`
6. Click Download & Install

### 2c. Add to PATH

```bash
echo 'export PATH=/home/alan/altera_standard/25.1std/qprogrammer/bin:$PATH' >> ~/.zshrc
echo 'export PYTHONPATH=/home/alan/Imago-Unicell' >> ~/.zshrc
source ~/.zshrc
```

### 2d. USB Blaster udev permissions

```bash
sudo groupadd plugdev
sudo usermod -a -G plugdev alan
sudo nano /etc/udev/rules.d/51-usbblaster.rules
```

Add this single line:
```
SUBSYSTEM=="usb", ATTR{idVendor}=="09fb", ATTR{idProduct}=="6001", MODE="0666", GROUP="plugdev"
```

Save (Ctrl+O, Enter, Ctrl+X), then:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Log out and back in for group membership to take effect.

---

## Part 3 — Verify Card Detection

### 3a. PCIe enumeration

With the card installed and machine booted into Linux:

```bash
lspci | grep -i altera
```

Expected output:
```
08:00.0 Processing accelerators: Altera Corporation Device 2494 (rev 01)
```

The slot address (`08:00.0`) may differ between machines.

### 3b. USB Blaster detection

Plug in the IEI USB Download Cable, then:

```bash
lsusb | grep -i altera
```

Expected output:
```
Bus 003 Device 002: ID 09fb:6001 Altera Blaster
```

---

## Part 4 — Programme the Card

### 4a. Start JTAG daemon and verify chain

```bash
cd /home/alan/altera_standard/25.1std/qprogrammer/bin
sudo ./jtagd
sudo ./jtagconfig
```

Expected output:
```
1) USB-Blaster [3-2]
   02E250DD   10AX066H1(.|ES)/10AX066H2/..
```

The IDCODE `02E250DD` and device string `10AX066H1/H2` confirm the Arria 10 GX660 is visible on the JTAG chain. If you see "Insufficient port permissions", the udev rule has not taken effect — log out and back in.

### 4b. Copy .sof to a path without spaces

The `.sof` file may be on a Windows-formatted drive with spaces in the path. Copy it first:

```bash
cp "/run/media/alan/Fast Data/Quarttus/output_files/Unicell-Q.sof" /home/alan/Unicell-Q.sof
```

*(Note: the Windows Quartus directory is spelled "Quarttus" with double-t)*

### 4c. Programme the card

```bash
sudo ./quartus_pgm -c "USB-Blaster [3-2]" -m JTAG -o "p;/home/alan/Unicell-Q.sof"
```

Expected output (success):
```
Info: Using programming cable "USB-Blaster [3-2]"
Info: Using programming file /home/alan/Unicell-Q.sof with checksum 0x1F70323B for device 10AX066H2F34@1
Info (209060): Started Programmer operation at ...
Info (209016): Configuring device index 1
Info (209017): Device 1 contains JTAG ID code 0x02E250DD
Info (209007): Configuration succeeded -- 1 device(s) configured
Info (209011): Successfully performed operation(s)
Info (209061): Ended Programmer operation at ...
Info: Quartus Prime Programmer was successful. 0 errors, 0 warnings
```

**Programming time:** approximately 54 seconds elapsed, 6 seconds CPU.

---

## Part 5 — Clone the Repository

```bash
cd /home/alan
git clone https://github.com/alh-Imago/Imago-Unicell.git
cd Imago-Unicell
```

The repository is currently public — no authentication required.

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Unable to lock chain — Insufficient port permissions` | udev rule not active | Log out and back in |
| `Programming hardware cable not detected` | jtagd not running, or wrong cable name | Run `sudo ./jtagd` first; use exact name from jtagconfig output |
| `File does not exist or can't be read` | Space in path, or drive not mounted | Copy .sof to `/home/alan/` first |
| `Can't scan JTAG chain. Error code 86` | jtagd timed out between commands | Restart jtagd immediately before quartus_pgm |
| `ShellExecuteEx failed: File not found` (Wine) | Windows Quartus binaries won't run under Wine | Use Linux Quartus Programmer instead |
| Quartus Programmer crashes on Windows | Known Windows issue on this machine | Use Linux path — do not attempt Windows programmer |

---

## Notes for 8-Card Build

- Each card programmes identically — same `.sof`, same procedure
- The USB Blaster cable moves from card to card during initial programming
- For permanent deployment, each card will require its own programming cable or a shared JTAG chain daisy-chained between cards
- The PCIe slot address (`08:00.0` etc.) will differ per card — use `lspci` to identify each
- Wrong-card loading of a card-tailored ICM produces silent timing corruption — a refuse-to-load guard must be implemented before multi-card deployment
- Card PSU headroom: each card draws under 60W from the PCIe slot; plan host PSU budget accordingly (8 cards = up to 480W from PCIe slots alone)

---

## Next Steps (Post First Silicon)

1. Write Arria 10 PCIe host interface (`fpga_bridge_arria10.py`) — the Mustang-F100 communicates over PCIe, not UART
2. Validate `shift_in_en` on Arria 10 silicon — unlocks packed Kogge-Stone adder (~25× cost reduction for INT32 tiles)
3. Re-cost all INT32/OptiTrix/SensorTrix tiles after shift_in_en confirmation
4. Programme second Mustang-F100 card using this procedure
5. Two-node deployment

---

*Document generated: 20 June 2026*  
*Verified hardware: IEI Mustang-F100-A10, Arria 10 GX660, Quartus Prime Standard 25.1*
