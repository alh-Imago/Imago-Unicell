#!/usr/bin/env python3
"""hexn_rtl_probe_v1: run one of the serial cores (branch / merge / prio / seq) in iverilog on a clock-by-clock stimulus and return what comes out.
A stimulus is {data_port: [(start_clock, word), ...]}; a word is driven LSB first for 32 clocks with its start flag on the first.  Clocks are counted as in the testbenches: an input applied at clock n is seen by the core at the edge of clock n; an output register that changed at that edge is read at clock n+1.
The result is a list (out_port, start_clock, word): start_clock is the clock at which the start flag is READ on the output."""
import os, shutil, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = lambda f: os.path.join(ROOT, "sub", "verilog", f)

# core -> (module, files, config ports with widths, data ports [(name, flagname)], outputs [(data, flag)])
CORES = {
    "branch": ("hexn_branch_core_v1", ["hexn_join_core_v2.v", "hexn_branch_core_v1.v"], [("route_lt", 2), ("route_eq", 2), ("route_gt", 2), ("emit", 2), ("fixed", 32)], [("a", "wsa"), ("b", "wsb")], [("o1", "o1s"), ("o2", "o2s")]),
    "merge":  ("hexn_merge_core_v1", ["hexn_join_core_v2.v", "hexn_merge_core_v1.v"], [("mode", 2)], [("a", "wsa"), ("b", "wsb")], [("r", "rs")]),
    "prio":   ("hexn_prio_core_v1", ["hexn_join_core_v2.v", "hexn_prio_core_v1.v"], [("mask", 4), ("ranks", 8), ("mode", 2), ("len", 3), ("order", 8)], [("dn", "wsn"), ("ds", "wss"), ("de", "wse"), ("dw", "wsw")], [("r", "rs")]),
    "seq":    ("hexn_seq_core_v1", ["hexn_seq_core_v1.v"], [("vals", 128), ("len", 3)], [("adv", None)], [("r", "rs")]),
}


def probe(core, cfg, stim, nclk=500, keep=False):
    mod, files, cports, dports, oports = CORES[core]
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="hexnprobe_")
    try:
        dyn = [p for pair in dports for p in pair if p]       # dynamic inputs, in order
        lines = []
        for n in range(nclk):
            bits = {}
            for (dn, fn) in dports:
                v, f = 0, 0
                for (s, w) in stim.get(dn, []):
                    if s <= n < s + 32: v = (w >> (n - s)) & 1; f = 1 if n == s else 0
                    if dn == "adv" and s == n: v = 1
                bits[dn] = v
                if fn: bits[fn] = f
            lines.append("".join(str(bits[p]) for p in dyn))
        open(os.path.join(d, "stim.txt"), "w").write("\n".join(lines) + "\n")
        decl = "".join("    reg [%d:0] %s = %d;\n" % (w - 1, n, cfg.get(n, 0)) for n, w in cports)
        decl += "    reg cfgload = 0;\n" if core in ("prio", "seq") else ""
        decl += "".join("    reg %s = 0;\n" % p for p in dyn)
        decl += "".join("    wire %s;\n" % p for pair in oports for p in pair)
        conn = [".clk(clk)"] + [".%s(%s)" % (n, n) for n, w in cports] + ([".cfgload(cfgload)"] if core in ("prio", "seq") else []) + [".%s(%s)" % (p, p) for p in dyn] + [".%s(%s)" % (p, p) for pair in oports for p in pair]
        outs = [p for pair in oports for p in pair]
        assign = "".join("        %s = bitsv[%d];\n" % (p, len(dyn) - 1 - i) for i, p in enumerate(dyn))
        tb = """`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
%s    %s dut (%s);
    integer fd, n, rc; reg [%d:0] bitsv;
    initial begin
        fd = $fopen("stim.txt", "r");
        repeat (2) @(negedge clk);
        %s
        for (n = 0; n < %d; n = n + 1) begin
            @(negedge clk);
            rc = $fscanf(fd, "%%b", bitsv);
%s            #4; $display("O %%0d %%b", n, {%s});
        end
        $finish;
    end
endmodule
""" % (decl, mod, ", ".join(conn), len(dyn) - 1, ("cfgload = 1; @(negedge clk); cfgload = 0; @(negedge clk);" if core in ("prio", "seq") else ""), nclk, assign, ", ".join(outs))
        open(os.path.join(d, "tb.v"), "w").write(tb)
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", "o.vvp", "tb.v"] + [V(f) for f in files], capture_output=True, text=True, cwd=d)
        assert c.returncode == 0, c.stderr
        out = subprocess.run(["vvp", "o.vvp"], capture_output=True, text=True, timeout=600, cwd=d).stdout
        # parse: per clock the output vector (first listed output is the leftmost bit)
        cur = {}; res = []
        for ln in out.splitlines():
            if not ln.startswith("O "): continue
            _, n, b = ln.split(); n = int(n)
            vals = dict(zip(outs, b))
            for (dpn, fpn) in oports:
                if vals[fpn] == "1": cur[dpn] = [n, 0, 0]       # [start, bits seen, word]
                if dpn in cur and cur[dpn][1] < 32:
                    st = cur[dpn]; st[2] |= (1 if vals[dpn] == "1" else 0) << st[1]; st[1] += 1
                    if st[1] == 32: res.append((dpn, st[0], st[2])); del cur[dpn]
        return sorted(res, key=lambda x: (x[1], x[0]))
    finally:
        if not keep: shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    import random
    rnd = random.Random(1)
    A, B = rnd.randrange(1 << 32), rnd.randrange(1 << 32)
    print("merge single A (mode 0)", probe("merge", {"mode": 0}, {"a": [(10, A)]}))
    print("seq adv at 10", probe("seq", {"vals": A | (B << 32), "len": 2}, {"adv": [(10, 0)]}))
