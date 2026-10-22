# Hex-N: load the SAVE AND RECALL bitstream (tools/hexn_tang_build_v16.sh) onto the Tang Nano 20K and run the memory test (tools/hexn_tang_mem_v1.py).
# Usage:  sudo sh tools/hexn_tang_mem_run_v1.sh BITSTREAM.fs [PORT] [options of hexn_tang_mem_v1.py]
# e.g.    sudo sh tools/hexn_tang_mem_run_v1.sh /home/alan/Downloads/hexn_mem16_w18_hex7_nc7_noalu.fs /dev/ttyUSB1
FS=$(realpath "$1" 2>/dev/null || echo "$1")
[ -f "$FS" ] || { echo "NOFILE: cannot find bitstream $1"; exit 1; }
cd "$(dirname "$0")/.." || exit 1
PORT=${2:-/dev/ttyUSB1}; [ $# -ge 2 ] && shift 2 || shift $#
openFPGALoader -b tangnano20k "$FS" || { echo "NOLOAD: the loader could not program the board"; exit 1; }
sleep 3
python3 tools/hexn_tang_mem_v1.py --port "$PORT" "$@"
