`timescale 1ns/1ps
// Checks hexn_det_v1 against hexn_cell_v2 clock by clock: random weights, thresholds and inputs (held or changing every clock). Prints "DET MATCHES CELL: n clocks, m trials" or the first mismatch.
module tb_hexn_det_v1;
    parameter NB = 12, AW = 6, TRIALS = 400;
    localparam N = 24, PL = 10;
    reg clk = 0, rst = 1, phase = 0, ph_start = 0, win_end = 0;
    reg [NB-1:0] rx, wp, wn; reg [AW-1:0] thr;
    reg [N-1:0] cfg_active; reg [2*N-1:0] cfg_dir, cfg_code; reg [N-1:0] crx;
    wire [N-1:0] ctx; wire dtx;
    hexn_cell_v2 #(.FACES(6), .PAIRS(4), .AW(AW)) ucell(.clk(clk), .rst(rst), .phase(phase), .ph_start(ph_start), .win_end(win_end), .rx(crx), .tx(ctx),
        .cfg_active(cfg_active), .cfg_dir(cfg_dir), .cfg_code(cfg_code), .cfg_thr(thr), .bias(16'd0));
    hexn_det_v1 #(.NB(NB), .AW(AW)) udet(.clk(clk), .rst(rst), .phase(phase), .ph_start(ph_start), .win_end(win_end), .rx(rx), .w_pos(wp), .w_neg(wn), .cfg_thr(thr), .tx(dtx));
    integer i, t, w, ph, trial, clocks = 0, bad = 0, hold, bursts = 0;
    always #5 clk = ~clk;
    task setcfg; begin
        cfg_active = 0; cfg_dir = 0; cfg_code = 0;
        for (i = 0; i < NB; i = i + 1) begin
            cfg_active[i] = wp[i] | wn[i]; cfg_dir[2*i +: 2] = 2'd0; cfg_code[2*i +: 2] = wn[i] ? 2'd3 : 2'd1;
        end
        cfg_active[20] = 1; cfg_dir[40 +: 2] = 2'd1; cfg_code[40 +: 2] = 2'd1;
    end endtask
    initial begin
        rx = 0; wp = 0; wn = 0; thr = 0; crx = 0; setcfg;
        repeat (3) @(posedge clk); #1 rst = 0;
        for (trial = 0; trial < TRIALS; trial = trial + 1) begin
            wp = $random; wn = $random & ~wp; thr = $random % (1 << AW); if (trial % 3 == 0) thr = $random % 12;
            hold = (trial % 2); rx = $random; setcfg;
            for (w = 0; w < 3; w = w + 1) for (ph = 0; ph < 2; ph = ph + 1) for (t = 0; t < PL; t = t + 1) begin
                phase = ph; ph_start = (t == 0); win_end = (ph == 1 && t == PL - 1);
                if (!hold) rx = $random;
                crx = 0; for (i = 0; i < NB; i = i + 1) crx[i] = rx[i];
                #2;
                clocks = clocks + 1; bursts = bursts + dtx;
                if (dtx !== ctx[20] || (ctx & ~(24'd1 << 20)) !== 0) begin bad = bad + 1; if (bad < 5) $display("MISMATCH trial %0d w %0d ph %0d t %0d: det %b cell %b", trial, w, ph, t, dtx, ctx[20]); end
                @(posedge clk); #1;
            end
        end
        if (bad == 0) $display("DET MATCHES CELL: %0d clocks, %0d trials, %0d clocks with output on", clocks, TRIALS, bursts); else $display("DET DIFFERS from cell: %0d mismatches", bad);
        $finish;
    end
endmodule
