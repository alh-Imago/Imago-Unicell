#!/usr/bin/env python3
"""flex_stop_run_v1.py -- ledger #1097: build (assemble + freeze net + wrapper + generated testbench) and run the self-stopping looped CORDIC in iverilog. `build(workdir)` then `run(workdir, mode=, dly=, n=, m=, lag=)`
returns the simulator output: "R step value" per result, "STOP ..." after the first stop (steps counted, held word, whether the loop-closing register still holds it, number of grid cells still holding a word)
and "BUSY cell" for each of those cells, then the host releases, the counter is re-armed for m more steps, and "STOP2 ..." after the second stop. mode bit0 = back pressure, bit1 = freeze.
"""
import re, os, sys, subprocess, shutil, tempfile
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')
sys.path.insert(0,ROOT+'/tools'); sys.path.insert(0,ROOT+'/nano')
import flex_freeze_net_v1 as F
import looped_cordic_v1 as L
def build(work):
    shutil.copy(ROOT+'/nano/examples/looped_cordic_v1_open.icm-hier.json', work+'/open.icm-hier.json')
    out=work+'/rtl'
    subprocess.run([sys.executable,ROOT+'/tools/project_assemble_v1.py','-s','flex','--icm',work+'/open.icm-hier.json','--output',out,'--top','icm_open_flex'],check=True,capture_output=True)
    F.make(out,'icm_open_flex')
    top=open(out+'/icm_open_flex.v').read()
    inst=re.findall(r"^(adder|ram|branch|merge)_cell_v4sa #\(\.CELL_ID\(16'd\d+\)\) (c_\w+) \(",top,re.M)
    busy=[]
    for k,nm in inst:
        g='dut.grid.'+nm
        if k=='ram': busy.append('if (%s.fixed_mode==0 && %s.pending) begin nb=nb+1; $display("BUSY %s"); end'%(g,g,nm))
        elif k=='branch': busy.append('if (%s.pending_1|%s.pending_2) begin nb=nb+1; $display("BUSY %s"); end'%(g,g,nm))
        else: busy.append('if (%s.pending) begin nb=nb+1; $display("BUSY %s"); end'%(g,nm))
    tb='''`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1; always #5 clk=~clk;
  reg cfg_grid=0, cfg_acc=0, load_valid=0, rel=0; reg [15:0] n=0; reg [1:0] mode=0; reg [2:0] dly=4; reg [4:0] lag=0; integer LAG; reg [31:0] ld=0;
  wire stopped, held_valid, take; wire [15:0] steps; wire [31:0] held, td;
  looped_cordic_stop_wrapper_v1 dut(.clk(clk),.rst(rst),.cfg_grid(cfg_grid),.cfg_acc(cfg_acc),.n_steps(n),.mode(mode),.feed_delay(dly),.trig_lag(lag),.load_valid(load_valid),.load_data(ld),
     .release_pulse(rel),.stopped(stopped),.steps_done(steps),.held_word(held),.held_valid(held_valid),.take_o(take),.take_data(td));
  integer nb, N, M, MODE, DLY;
  always @(posedge clk) if (take) $display("R %0d %0d", steps+1, $signed(td));
  initial begin
    if (!$value$plusargs("N=%d",N)) N=3; if (!$value$plusargs("M=%d",M)) M=3; if (!$value$plusargs("MODE=%d",MODE)) MODE=1; if (!$value$plusargs("DLY=%d",DLY)) DLY=4;
    if (!$value$plusargs("LAG=%d",LAG)) LAG=0; mode=MODE; dly=DLY; lag=LAG;
    repeat(4) @(posedge clk); rst<=0; @(posedge clk); cfg_grid<=1; n<=N; cfg_acc<=1; @(posedge clk); cfg_grid<=0; cfg_acc<=0;
    repeat(30) @(posedge clk); load_valid<=1; ld<=50000; @(posedge clk); load_valid<=0;
    wait(stopped); repeat(300) @(posedge clk);
    nb=0; ''' + ' '.join(busy) + '''
    $display("STOP steps=%0d held=%0d valid=%0d busy=%0d", steps, $signed(held), held_valid, nb);
    n<=M; cfg_acc<=1; @(posedge clk); cfg_acc<=0; rel<=1; @(posedge clk); rel<=0;
    wait(stopped); repeat(300) @(posedge clk);
    $display("STOP2 steps=%0d held=%0d valid=%0d", steps, $signed(held), held_valid);
    $finish;
  end
  initial begin #20000000; $display("TIMEOUT"); $finish; end
endmodule
'''
    open(work+'/tb.v','w').write(tb)
    srcs=[out+'/'+f for f in os.listdir(out) if f.endswith('.v')]+[ROOT+'/sub/verilog/looped_cordic_stop_wrapper_v1.v',ROOT+'/sub/verilog/accumulator_cell_v4sa.v',ROOT+'/sub/verilog/latch_cell_v4sa.v',work+'/tb.v']
    srcs=list(dict.fromkeys(srcs))
    subprocess.run(['iverilog','-g2012','-o',work+'/s.vvp']+srcs,check=True)
def run(work,**kw):
    args=['vvp',work+'/s.vvp']+['+%s=%s'%(k.upper(),v) for k,v in kw.items()]
    return subprocess.run(args,capture_output=True,text=True).stdout
if __name__=='__main__':
    w=tempfile.mkdtemp(); build(w)
    for kw in (dict(mode=1,dly=4,n=3,m=3),dict(mode=2,dly=4,n=3,m=3),dict(mode=2,dly=0,n=3,m=3),dict(mode=3,dly=0,n=3,m=3),dict(mode=2,dly=0,n=3,m=3,lag=12),dict(mode=2,dly=0,n=3,m=3,lag=25),dict(mode=1,dly=0,n=3,m=3,lag=25)):
        o=run(w,**kw); print(kw); 
        lines=o.splitlines(); print([l for l in lines if l.startswith(('STOP','TIMEOUT'))], 'R:',[l.split()[2] for l in lines if l.startswith('R ')][:10], 'model',L.model(10)[:8])
        print('busy cells:', [l.split()[1] for l in lines if l.startswith('BUSY')][:12])
