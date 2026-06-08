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
