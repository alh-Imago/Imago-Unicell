"""Python twin of sub/verilog/hexn_ramroute_v5.v for ONE held face (the RAM-routing cell, one-word FIFO). One step() per clock; the order of the updates mirrors the Verilog
non-blocking assignments (everything is computed from the OLD state). Checked against the RTL by tests/vm/test_hexn_ramcell_model_v1.py (random stimulus through iverilog)."""
class RamCell:
    DW = 7
    def __init__(s, mode=1, dly=1):
        s.mode, s.dly = mode, dly
        s.cnt = (1 << s.DW) - 1; s.q = 0; s.rr = 0; s.mem = [0] * 32
    def step(s, din, ws):
        """one clock edge; returns the registered output bit (face hout) that is visible AFTER this edge"""
        M = (1 << s.DW) - 1
        cc = 0 if ws else s.cnt
        out = s.q if s.mode != 0 else None            # fo[hout] <= q (old q); in pass mode the cell routes (caller handles)
        if s.mode == 0:
            s.cnt = M; s.rr = 0
            return None
        dd = (cc - s.dly) & M
        rd = cc >= s.dly and dd < 32
        mem_old = s.mem                                  # read BEFORE the write below, so this is the old contents
        q_n = s.q
        if s.mode == 1:
            q_n = mem_old[dd & 31] if rd else 0
        else:
            q_n = mem_old[s.rr] if cc >= 32 else 0
            s.rr = 0 if cc < 32 else (s.rr + 1) & 31
        if cc < 32:
            s.mem[cc & 31] = din                        # write happens at the same edge; the read above used the old contents
        s.cnt = cc + 1 if cc != M else cc
        s.q = q_n
        return out
