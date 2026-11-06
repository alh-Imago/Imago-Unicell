# hexn_l1: the layer 1 detector with core v9 on the Kintex card (6 Nov 2026)

Clone of `../hexn` (left untouched) with `hexn_core_v9` (counted detector bank, hold-N-samples counter, exact-match wiring, layer 2 store v5), lattice v18, bank v19, behind the JTAG byte bridge on USER1 (IR 0x02). Same plumbing and pins as `../hexn`.
Build (from `~/ypcb-00338-1p1` inside the openXC7 nix shell; the first line once):

    ln -sfn ~/hexn-wt/fpga/ypcb/hexn_l1 designs/hexn_l1
    mkdir -p /media/alan/InternalHDD/hexn_builds/det_v9_hex7 && ln -sfn /media/alan/InternalHDD/hexn_builds/det_v9_hex7 designs/hexn_l1/build_det_v9_hex7
    HEXN_REPO=$HOME/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=1 BUILD=build_det_v9_hex7 THREADS=4 FPGA_HOST=$(hostname -s) CHIPDB=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin ./fpga build designs/hexn_l1 2>&1 | tee /media/alan/InternalHDD/hexn_builds/det_v9_hex7.log

Host: `python3 tools/hexn_kxlayer1_judge_v1.py classes --core v9 --hold 3 ...` (JTAG USER1, `HEXN_CHAIN=1` is the tool's default for this phase).
Status: NOT built yet (simulation first, tests/vm/test_hexn_kxlayer1_judge_v1.py).
