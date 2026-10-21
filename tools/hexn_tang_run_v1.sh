# Hex-N on the Tang Nano 20K: load the bitstream and run the tests, in one go (the same sequence as fpga/board_tests/run_one.sh).
# Usage:  sudo sh tools/hexn_tang_run_v1.sh BITSTREAM.fs [PORT] [extra host-script options]
# e.g.    sudo sh tools/hexn_tang_run_v1.sh hexn_tang_hex7.fs /dev/ttyUSB1 --cells 7 --seeds 0-4 --test-noise 0.05,0.15,0.25
# Needs openFPGALoader and pyserial (docs/shared/TOOLCHAIN_SETUP.md). The bitstream goes to SRAM only (gone at power-off); the flash is not touched. --cells must match the bitstream (hex7 = 7, rhombus4 = 4, par16 = 16, hex19 = 19).
cd "$(dirname "$0")/.." || exit 1
FS=$1; PORT=${2:-/dev/ttyUSB1}; [ $# -ge 2 ] && shift 2 || shift $#
openFPGALoader -b tangnano20k "$FS" || { echo "NOLOAD: the loader could not program the board"; exit 1; }
sleep 3          # the loader re-attaches the USB port for about 2 s after loading
python3 tools/hexn_tang_host_v1.py --port "$PORT" "$@"
