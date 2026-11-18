"""Harness for test_mb_sim.py: like test_k7_harness.py but builds fpga/tb_k7mb.v with the multi-block Kintex top (sc_top_k7_v8, sc_block, far_arb, host_bridge_v11,
jtag_link_v2, sc_sys_v15).  NB blocks of S slices.  Cloned from test_k7_harness.py (left as proven)."""
import os, sys, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
FPGA = os.path.join(HERE, 'fpga')
import test_k7_harness as K
Script = K.Script
def build(tag='mb', NB=2, S=2):
    if not shutil.which('iverilog'): print('SKIP: iverilog not installed'); sys.exit(1)
    exe = os.path.join(HERE, tag + '.vvp')
    files = ['tb_k7mb.v', 'sc_top_k7_v8.v', 'sc_block.v', 'far_arb.v', 'jtag_link_v2.v', 'host_bridge_v11.v', 'farram_bram_v1.v', 'batch_seq_v2.v', 'far_copy.v']
    srcs = [os.path.join(FPGA, f) for f in files] + [os.path.join(HERE, f) for f in ('sc_sys_v15.v', 'fit_search_tree.v', 'uc_core_v2v.v')]
    subprocess.run(['iverilog', '-g2012', '-Ptb_k7mb.NB=%d' % NB, '-Ptb_k7mb.S=%d' % S, '-o', exe] + srcs, check=True)
    return exe
def run(exe, sc, tag='mb', maxcyc=60_000_000): return K.run(exe, sc, tag=tag, maxcyc=maxcyc)
