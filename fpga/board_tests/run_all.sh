#!/bin/sh
# run_all.sh -- ledger #1023 (Linux): load each self-checking test bitstream onto the Tang Nano 20K, read its result line from the
# board's USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
#
# Needs: openFPGALoader, python3 with pyserial (sudo apt install openfpgaloader python3-serial), the board plugged in by USB-C, and
# permission for the USB devices: add yourself to the dialout group once (sudo usermod -aG dialout $USER, then log out and in),
# or run this with sudo.
# Usage:  ./run_all.sh              (auto-detects the serial port)
#         ./run_all.sh /dev/ttyUSB1 (name it yourself: the board shows two ports, the FPGA UART is the second)
cd "$(dirname "$0")" || exit 1
python3 board_run.py "$1"
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
