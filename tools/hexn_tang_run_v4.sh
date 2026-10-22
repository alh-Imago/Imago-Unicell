# (v4: new file; loads a bitstream, then runs a training script exported by the Hex-N Explorer page with tools/hexn_tang_script_v1.py. tools/hexn_tang_run_v3.sh is left untouched.)
# Usage:  sudo sh tools/hexn_tang_run_v4.sh BITSTREAM.fs SCRIPT.txt [PORT] [extra options of hexn_tang_script_v1.py]
# e.g.    sudo sh tools/hexn_tang_run_v4.sh hexn_w18_hex7_noalu.fs docs/hex-n/frontend/example_sensors_script_v1.txt /dev/ttyUSB1 --cells 7 --wires 18 --aw 7
# The script's classes, wires and accumulator bits must match the bitstream (hex7 = 7 detectors, hex19 = 19; w18 = 18 wires, AW 7; 12-wire builds = 12 wires, AW 6). The bitstream goes to SRAM only; the flash is not touched.
FS=$(realpath "$1" 2>/dev/null || echo "$1"); SC=$(realpath "$2" 2>/dev/null || echo "$2")
[ -f "$FS" ] || { echo "NOFILE: cannot find bitstream $1"; exit 1; }
[ -f "$SC" ] || { echo "NOFILE: cannot find script $2"; exit 1; }
cd "$(dirname "$0")/.." || exit 1
PORT=${3:-/dev/ttyUSB1}; [ $# -ge 3 ] && shift 3 || shift $#
openFPGALoader -b tangnano20k "$FS" || { echo "NOLOAD: the loader could not program the board"; exit 1; }
sleep 3
python3 tools/hexn_tang_script_v1.py "$SC" --port "$PORT" "$@"
