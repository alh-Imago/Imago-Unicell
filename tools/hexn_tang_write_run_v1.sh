# Hex-N: load the memory bitstream (hexn_mem16) and run, in one go: the BIST (built-in self-test of the trainer), then the WRITE RULE test (tools/hexn_tang_write_v1.py).
# Usage:  sudo sh tools/hexn_tang_write_run_v1.sh BITSTREAM.fs [PORT]
# e.g.    sudo sh tools/hexn_tang_write_run_v1.sh /home/alan/Downloads/hexn_mem16_w18_hex7_nc7_noalu.fs /dev/ttyUSB1
FS=$(realpath "$1" 2>/dev/null || echo "$1")
[ -f "$FS" ] || { echo "NOFILE: cannot find bitstream $1"; exit 1; }
cd "$(dirname "$0")/.." || exit 1
PORT=${2:-/dev/ttyUSB1}
openFPGALoader -b tangnano20k "$FS" || { echo "NOLOAD: the loader could not program the board"; exit 1; }
sleep 3
python3 tools/hexn_tang_bist_v1.py --port "$PORT" --cells 7 --wires 18 --aw 7 2>&1 | tail -n 4
python3 tools/hexn_tang_write_v1.py --port "$PORT" --seeds 3
