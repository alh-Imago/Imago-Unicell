# Hex-N: load the LEAKY CELLS bitstream (tools/hexn_tang_build_v15.sh, NCELL=7) onto the Tang Nano 20K and run the leak test (tools/hexn_tang_leak_v1.py).
# Usage:  sudo sh tools/hexn_tang_leak_run_v1.sh BITSTREAM.fs SCRIPT.txt [PORT] [options of hexn_tang_leak_v1.py]
# e.g.    sudo sh tools/hexn_tang_leak_run_v1.sh /home/alan/Downloads/hexn_leak15_w18_hex7_nc7_noalu.fs docs/hex-n/frontend/example_sensors_script_v1.txt /dev/ttyUSB1
FS=$(realpath "$1" 2>/dev/null || echo "$1"); SC=$(realpath "$2" 2>/dev/null || echo "$2")
[ -f "$FS" ] || { echo "NOFILE: cannot find bitstream $1"; exit 1; }
[ -f "$SC" ] || { echo "NOFILE: cannot find script $2"; exit 1; }
cd "$(dirname "$0")/.." || exit 1
PORT=${3:-/dev/ttyUSB1}; [ $# -ge 3 ] && shift 3 || shift $#
openFPGALoader -b tangnano20k "$FS" || { echo "NOLOAD: the loader could not program the board"; exit 1; }
sleep 3
python3 tools/hexn_tang_leak_v1.py "$SC" --port "$PORT" "$@"
