# Loading a precompiled design into an FPGA from an ESP32: a separate method

*Written 17 Oct 2026 (ledger #1177) at Alan's request of 16 Oct: keep this apart from the UniCell architecture.*

**Status: a PROPOSED ROUTE. It is NOT built and NOT tried.** Everything below under "What the repo records" comes from reading the Tang Nano 20K schematic and our own notes (#1036 addendum 10, `docs/unit_bringup_guide.md`), not from running anything.

## 1. What the method is

A small microcontroller (the ESP32) keeps one or more precompiled FPGA bitstreams (on an SD card or in its own flash) and, on request, streams one into the FPGA's configuration port. The FPGA then runs whatever design that bitstream holds.

This has nothing to do with what is inside the bitstream. It would load a UniCell design, a UART blinker or any other design equally well. It is a way to get a bitstream onto an FPGA without a PC and a USB cable, and it should be described that way, with no mention of cells, NOR logic or the UniCell architecture.

## 2. What the repo records (read, not run)

- The Tang Nano 20K has JTAG test points: TP3 = TCK (FPGA pin 6), TP4 = TDO (8), TP5 = TDI (7), TP6 = TMS (5), TP2 = GND, and TP1 = RECONFIG_N (pin 9; pulling it low makes the FPGA reload from its flash).
- The on-board BL616 chip drives the same JTAG nets directly, so there is a contention risk; about 1 kohm series resistors were advised.
- The board's flash sits on the FPGA's own MSPI pins, so the ESP32 cannot touch it. FPGA pins 75/76 are shared with the BL616's SPI port. MODE0/MODE1 are the buttons S1/S2 (pins 88/87).
- The slave-SPI configuration pins (CS 55, SCLK 52, DIN 54, DOUT 53) are on header J5, but which MODE setting selects that route has not been checked against Gowin's configuration guide.
- ESP32 pins IO27, IO14, IO13 and IO4 were left free for a later JTAG loader (`docs/playout_capture_v1.md`).
- The proposed route: (1) the ESP32 reads the new bitstream's blocks from the SD card, keeps the roughly 1 MB file in its own flash; (2) it bit-bangs it into the FPGA over JTAG through TP3-TP6 (SRAM load).

## 3. Not known

Whether the BL616 stays quiet on the JTAG nets while the ESP32 drives them; whether the SSPI route works on this board; how long a load takes; how a failed load is detected and recovered. None of these have been tested.

## 4. Prior art (found 17 Oct by web search; titles and links only, the pages were not read in full)

Microcontrollers loading FPGAs over JTAG or a configuration port is an established technique, including on the ESP32:

- [Efinix AN 038: Programming with an MCU and the JTAG Interface](https://www.efinixinc.com/docs-html/an/an038.html)
- [esp32ecp5: ESP32 JTAG tap walker for ECP5](https://libraries.io/pypi/esp32ecp5)
- [Xilinx XAPP058 (XSVF player for microcontrollers), mirrored at mikrocontroller.net](https://www.mikrocontroller.net/attachment/20584/xapp058.pdf)
- [FPGA configuration with an AVR Butterfly (mikrocontroller.net)](https://www.mikrocontroller.net/articles/FPGA_Konfiguration_mit_AVR_Butterfly)
- [In-system CPLD programming using XSVF files (Big Mess o' Wires)](https://www.bigmessowires.com/2012/03/29/in-system-cpld-programming-using-xsvf-files/)

So nothing here is claimed as new in itself. If anything about our version turns out to be new, it will be in specifics (for example, how designs are chosen and fetched), and only after it exists and has been compared with these.

## 5. Where UniCell touches this (kept as a separate item)

The loader only delivers bytes. Two UniCell-specific uses sit on top of it, and neither is the loader:

- **Reconfiguration stream.** Once a carrier is already loaded in the FPGA, a new wiring (a cell network) can be streamed into it and replace the running program without reloading the bitstream. That depends on the architecture (a program is a wiring), and the carrier does it, not the loader. Confirmed on the card with a standard command cell as the source (#1087-#1089, README table); with the ESP32 as the source it has not been tried.
- **Freeze, save, reload of state** through the ESP32's SD card (#1036 addendum 53): an IDEA, NOT BUILT. The VM already does checkpoint, wipe and reload of a mixed grid; a state read-out port on the flex cells and a freeze driver on the Tang were not found in the repo.

## 6. How to describe it

Use two separate descriptions: (a) the loader method, generic, status as above; (b) the reconfiguration stream, as a feature of the carrier. Do not describe them as one feature.
