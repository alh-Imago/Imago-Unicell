#!/usr/bin/env python3
"""tests/test_flexsub_family_equivalence_v1.py -- is `flex` (default 32-bit WIDTH, handshake tied off) the same as `sub`?

Run: python3 tests/test_flexsub_family_equivalence_v1.py     (needs iverilog, yosys)
Alan asked (4 Oct 2026): "in some ways the sub flex supersedes the sub, as it falls back to the 32 bit version when no
size is given? Double check that." This pins the answer down with evidence, three ways:
  1. CELL level   -- every flex cell declares WIDTH = 32, so an unsized instance IS 32-bit.
  2. FUNCTION     -- for each of the 12 cells that exist in both families, a flex cell (no WIDTH given, freeze_in low, ack_in high)
                     and its sub twin are driven with IDENTICAL stimulus (isolated items, 1000 per run) and compared every cycle:
                     valid, and data when valid, and the cycle of the first valid (= latency). They must be identical.
  3. THROUGHPUT   -- the one place they differ: offered a new item EVERY cycle with the handshake honoured, flex accepts one
                     item per two cycles; sub accepts one per cycle. Recorded as a finding (measured on the adder).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flexsub_assemble_v1 as fsa  # noqa: E402

SUBV = ROOT + "/sub/verilog"
common = sorted(set(fsa.cells_for("flex")) & set(fsa.cells_for("sub")))
CFGS = [0xA5C35A3C, 0x13572468, 0xFEDCBA98]
BRANCH_RAW = [0x396, 0x24D, 0x3FE, 0x000, 0x2C5, 0x0B1]
BRANCH_FREE_RUNNING = 0x3FF     # both inputs fixed: the cell fires EVERY cycle on its own -- the throughput case, asserted separately
passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def mult_stubs(path):
    out = ["`timescale 1ns/1ps"]
    for f, mod in (("tb_mul_cell_v4sa_dsp.v", "MULT36X36"), ("tb_mul_cell_v4s_dsp3.v", "MULT18X18")):
        out.append(re.search(rf"module {mod}\b.*?endmodule", open(os.path.join(SUBV, f)).read(), re.S).group(0))
    open(path, "w").write("\n\n".join(out) + "\n")


def build(base, cfgw, raw=False):
    sh=fsa.SHAPES[base]
    mods={f: fsa.cell_module(base,f) for f in ("flex","sub")}
    if sh.get('cfg')=='live' and not raw: cfgw=(cfgw | sh.get('cfg_or',0)) & ~sh.get('cfg_clr',0) & 0xFFFFFFFF
    L=["`timescale 1ns/1ps","module tb;","  reg clk=0, rst=1, cfg_valid=0; always #5 clk=~clk;",
       "  reg [31:0] l1=32'hACE11234, l2=32'h13579BDF, l3=32'h2468ACE0;",
       "  always @(posedge clk) begin l1<={l1[30:0],l1[31]^l1[21]^l1[1]^l1[0]}; l2<={l2[30:0],l2[31]^l2[27]^l2[1]^l2[0]}; l3<={l3[30:0],l3[31]^l3[25]^l3[3]^l3[0]}; end",
       "  reg [3:0] ph=0; always @(posedge clk) ph<=ph+1; wire tick=(ph[2:0]==0); wire [31:0] din=l1, sd0=l2, sd1=l3; wire vin=tick; wire [7:0] sc={8{tick}} & {l1[3],l2[5],l3[9],l1[12],l2[14],l3[2],l1[19],l2[8]};"]
    outs=[]
    for fam in ("flex","sub"):
        real_in,real_out,_=fsa.real_ports(f"{SUBV}/{mods[fam]}.v", mods[fam])
        c=[]
        for p in fsa.STD_PORTS:
            if p in real_in:
                c.append((p, {"clk":"clk","rst":"rst","freeze_in":"1'b0","cfg_valid":"cfg_valid","cfg_data":f"32'h{cfgw:08X}"}[p]))
        if sh.get("in_data"): c.append((sh["in_data"],"din"))
        for k,p in enumerate(sh.get("stim_data",[])): c.append((p,f"sd{k}"))
        for p in sh.get("opt_stim_data",[]):
            if p in real_in: c.append((p,f"32'h{cfgw:08X}"))   # #971: the flex comparator's threshold has its own port; the sub cell reads the same word from cfg_data
        for k,p in enumerate(sh.get("stim_ctrl",[])): c.append((p,f"sc[{k}]"))
        if sh.get("in_valid"): c.append((sh["in_valid"],"vin"))
        for p,v in sh.get("consts",{}).items():
            if raw and base == "branch" and p == "in2_valid": v = "vin"   # a held in1 + an always-valid in2 would fire EVERY cycle (the throughput case, not isolated items)
            c.append((p,v))
        ack = fam=="flex"
        if ack and sh.get("ack_out"): L.append(f"  wire {fam}_ackout;"); c.append((sh["ack_out"],f"{fam}_ackout"))
        L.append(f"  wire [31:0] {fam}_d; wire {fam}_v;"); c.append((sh["out"][0],f"{fam}_d")); c.append((sh["out"][1],f"{fam}_v"))
        if ack and sh.get("ack_in"): c.append((sh["ack_in"],"1'b1"))
        for k,(d,v,a) in enumerate(sh.get("side",[])):
            L.append(f"  wire [31:0] {fam}_s{k}d; wire {fam}_s{k}v;"); c.append((d,f"{fam}_s{k}d")); c.append((v,f"{fam}_s{k}v"))
            if ack: c.append((a,"1'b1"))
        params=[".CELL_ID(16'd0)"]+[f".{k}({v.replace('i','0') if k=='SHIFT_AMT' else v.replace('i','0')})" for k,v in sh.get("params",{}).items()]
        missing=[p for p in real_in if p not in {x for x,_ in c}]
        assert not missing,(base,fam,missing)
        L.append(f"  {mods[fam]} #({', '.join(params)}) {fam[0].upper()} ("+", ".join(f".{p}({e})" for p,e in c)+");")
        outs.append(fam)
    cmp_pairs=[("flex_d","sub_d"),("flex_v","sub_v")]+[(f"flex_s{k}d",f"sub_s{k}d") for k in range(len(sh.get("side",[])))]+[(f"flex_s{k}v",f"sub_s{k}v") for k in range(len(sh.get("side",[])))]
    vpairs=[p for p in cmp_pairs if p[0].endswith("v")]; dpairs=[p for p in cmp_pairs if p[0].endswith("d")]
    vmis=" | ".join(f"({a} !== {b})" for a,b in vpairs)
    dmis=" | ".join(f"({a} !== {b})" for a,b in dpairs)
    dmis_v=" | ".join(f"(({a[:-1]}v && {b[:-1]}v) && ({a} !== {b}))" for a,b in dpairs)
    L+=["  integer n=0, vm=0, dm=0, dmv=0, first=-1, nv=0, fv_first=-1, sv_first=-1, sv=0;",
        "  always @(posedge clk) if (!rst && cfg_done) begin",
        f"    n=n+1; if ({vmis}) begin vm=vm+1; if (first<0) first=n; end",
        f"    if ({dmis}) dm=dm+1;  if ({dmis_v}) dmv=dmv+1;",
        "    if (FANY) begin nv=nv+1; if (fv_first<0) fv_first=n; end if (SANY) begin sv=sv+1; if (sv_first<0) sv_first=n; end end",
        "  reg cfg_done=0; integer c;",
        "  initial begin repeat(4) @(posedge clk); #1 rst=0; @(posedge clk); #1 cfg_valid=1; @(posedge clk); #1 cfg_valid=0;",
        "    repeat(6) @(posedge clk); #1 cfg_done=1; repeat(8000) @(posedge clk);",
        '    $display("RES cycles=%0d valid_mismatch=%0d data_mismatch_any=%0d data_mismatch_when_valid=%0d first_valid_mismatch_cycle=%0d flex_pulses=%0d sub_pulses=%0d first_flex_valid@%0d first_sub_valid@%0d", n, vm, dm, dmv, first, nv, sv, fv_first, sv_first); $finish; end',
        "endmodule"]
    fany=" | ".join(["flex_v"]+[f"flex_s{k}v" for k in range(len(sh.get("side",[])))]); sany=" | ".join(["sub_v"]+[f"sub_s{k}v" for k in range(len(sh.get("side",[])))])
    return "\n".join(L).replace("FANY",fany).replace("SANY",sany)
def run(base, cfgw, raw=False):
    d=f"{TMP}/{base}_{cfgw:08x}"; os.makedirs(d,exist_ok=True)
    open(f"{d}/tb.v","w").write(build(base,cfgw,raw))
    sh=fsa.SHAPES[base]
    files=[f"{SUBV}/{fsa.cell_module(base,'flex')}.v", f"{SUBV}/{fsa.cell_module(base,'sub')}.v", f"{ROOT}/fpga/verilog/adder_v1.v", f"{ROOT}/fpga/verilog/bitwise_multiplier_32bit.v", f"{ROOT}/fpga/verilog/nibble_mask_addon_v1.v"]
    if base.startswith("mul_dsp"): files.append(TMP + "/mult_stubs.v")
    files=[f for f in files if os.path.exists(f)]
    if base=="shift_stage": files=[f"{SUBV}/shift_stage_v4sa.v", f"{SUBV}/shift_stage_v4s.v"]
    c=subprocess.run(["iverilog","-g2012","-o",f"{d}/t.vvp",f"{d}/tb.v",*files],capture_output=True,text=True)
    if c.returncode: return "ELAB FAIL "+c.stderr.strip()[:160]
    out=subprocess.run(["vvp",f"{d}/t.vvp"],capture_output=True,text=True).stdout
    m=re.search(r"RES (.*)",out); return m.group(1) if m else "no result: "+out[-100:]

if not (shutil.which("iverilog") and shutil.which("yosys")):
    print("SKIP: iverilog and yosys are both needed")
    sys.exit(0)
TMP = tempfile.mkdtemp(prefix="famEq_")
try:
    mult_stubs(TMP + "/mult_stubs.v")
    print("1. cell level: every flex cell's WIDTH defaults to 32")
    cells = [f for f in os.listdir(SUBV) if not f.startswith("tb_") and re.match(r"(\w+_cell_v4sa|shift_stage_v4sa|mul_cell_v4sa_dsp)\.v$", f)]
    bad = [f for f in cells if not re.search(r"parameter\s+WIDTH\s*=\s*32\b", open(os.path.join(SUBV, f)).read())]
    check(f"all {len(cells)} flex cell files declare `parameter WIDTH = 32`", len(cells) >= 13 and not bad, str(bad))

    print("2. function: flex (default width, handshake tied off) == sub, cycle for cycle, isolated items")
    for base in common:
        cfgs = [(c, False) for c in (CFGS if fsa.SHAPES[base].get("cfg") == "live" else CFGS[:1])]
        if base == "branch":     # raw words (no pinning): fixed-reference modes, every emit_source, every routing combination
            cfgs += [(w, True) for w in BRANCH_RAW]
        for cfg, raw in cfgs:
            res = run(base, cfg, raw)
            m = re.search(r"valid_mismatch=(\d+) data_mismatch_any=\d+ data_mismatch_when_valid=(\d+) first_valid_mismatch_cycle=(-?\d+) "
                          r"flex_pulses=(\d+) sub_pulses=(\d+) first_flex_valid@(-?\d+) first_sub_valid@(-?\d+)", res)
            silent_ok = base == "branch" and raw and cfg == 0           # cfg 0 routes every outcome to neither: identical SILENCE is the expected result
            ok = bool(m) and m.group(1) == "0" and m.group(2) == "0" and m.group(4) == m.group(5) and (int(m.group(4)) > 0 or silent_ok) and m.group(6) == m.group(7)
            check(f"{base} cfg={cfg:#010x}: identical valid, identical data when valid, identical latency ({m.group(4) if m else '?'} items)", ok, res[:200])

    print("2b. a branch with BOTH inputs fixed is a free-running comparator (fires every cycle): the throughput difference again")
    res = run("branch", BRANCH_FREE_RUNNING, True)
    m = re.search(r"flex_pulses=(\d+) sub_pulses=(\d+)", res)
    fp, sp = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    check(f"both-fixed branch: flex fires {fp}, sub fires {sp} over the same cycles (sub = one per cycle, flex = one per two)",
          m is not None and fp > 0 and 1.8 <= sp / fp <= 2.2, res[:160])

    print("3. throughput: the one difference (measured on the adder)")
    tb = """`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, cfg_valid=0; always #5 clk=~clk;
  reg [31:0] cnt=0; wire fv, sv_; wire [31:0] fd, sd; wire fack;
  adder_cell_v4sa #(.CELL_ID(16'd0)) F (.clk(clk),.rst(rst),.freeze_in(1'b0),.cfg_valid(cfg_valid),.cfg_data(32'h0),
      .in_a(cnt),.in_b(32'd1),.valid_in(1'b1),.ack_out(fack),.data_out(fd),.valid_out(fv),.ack_in(1'b1));
  adder_cell_v4s  #(.CELL_ID(16'd0)) S (.clk(clk),.rst(rst),.cfg_valid(cfg_valid),.cfg_data(32'h0),
      .in_a(cnt),.in_b(32'd1),.valid_in(1'b1),.data_out(sd),.valid_out(sv_));
  integer acc_f=0, vf=0, vs=0, go=0;
  always @(posedge clk) if (!rst && go) begin if (fack) acc_f<=acc_f+1; if (fv) vf<=vf+1; if (sv_) vs<=vs+1; end
  always @(posedge clk) if (!rst && fack) cnt<=cnt+1;
  initial begin repeat(4) @(posedge clk); #1 rst=0; @(posedge clk); #1 cfg_valid=1; @(posedge clk); #1 cfg_valid=0; repeat(6) @(posedge clk); go=1;
    repeat(1000) @(posedge clk); $display("TPUT %0d %0d %0d", acc_f, vf, vs); $finish; end
endmodule
"""
    open(TMP + "/tput.v", "w").write(tb)
    c = subprocess.run(["iverilog", "-g2012", "-o", TMP + "/tput.vvp", TMP + "/tput.v", SUBV + "/adder_cell_v4sa.v", SUBV + "/adder_cell_v4s.v", ROOT + "/fpga/verilog/adder_v1.v"], capture_output=True, text=True)
    m = re.search(r"TPUT (\d+) (\d+) (\d+)", subprocess.run(["vvp", TMP + "/tput.vvp"], capture_output=True, text=True).stdout)
    acc, vf, vs = (int(x) for x in m.groups()) if m else (None, None, None)
    check(f"offered an item every cycle: flex accepts {acc}/1000 (one per two cycles), sub emits {vs}/1000 (one per cycle)",
          m is not None and 450 <= acc <= 550 and 950 <= vs <= 1050 and abs(vf - acc) <= 5, f"acc={acc} flex_valid={vf} sub_valid={vs}")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
