// Testbench for rtl/hexn_speech_chain_v1.v. Reads prog.hex (16-bit words: bit 14 = start, bit 15 = window end, else event address in [7:0]; first x word ends the program),
// feeds one word per clock, waits for out_valid after each window end and prints "R <win> <cls> <pred> <gap> <stop>". LOAD=1: the config is written through the cfg_ port instead of being preloaded.
`timescale 1ns/1ps
module tb #(parameter LOAD = 0);
    reg clk = 0, rst = 1;
    reg cfg_we = 0; reg [2:0] cfg_sel = 0; reg [15:0] cfg_addr = 0; reg [79:0] cfg_data = 0;
    reg start = 0, ev_valid = 0, win_end = 0; reg [7:0] ev_idx = 0;
    wire out_valid, out_stop; wire [2:0] out_win; wire [3:0] out_cls, out_pred; wire signed [16:0] out_gap;
    hexn_speech_chain_v1 #(.WFILE(LOAD ? "" : "wrom.hex"), .TFILE(LOAD ? "" : "thr.hex"), .LFILE(LOAD ? "" : "lp.hex"), .CFILE(LOAD ? "" : "cfg.hex")) dut (
        .clk(clk), .rst(rst), .cfg_we(cfg_we), .cfg_sel(cfg_sel), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .start(start), .ev_valid(ev_valid), .ev_idx(ev_idx), .win_end(win_end),
        .out_valid(out_valid), .out_win(out_win), .out_cls(out_cls), .out_pred(out_pred), .out_gap(out_gap), .out_stop(out_stop));
    always #5 clk = ~clk;
    reg [15:0] prog [0:65535];
    reg [19:0] tw [0:959]; reg [79:0] tt [0:4]; reg [79:0] tl [0:604]; reg [15:0] tc [0:5];
    integer i, k, rec, wait_n;
    initial begin
        for (i = 0; i < 65536; i = i + 1) prog[i] = 16'hxxxx;
        $readmemh("prog.hex", prog);
        if (LOAD) begin
            $readmemh("wrom.hex", tw); $readmemh("thr.hex", tt); $readmemh("lp.hex", tl); $readmemh("cfg.hex", tc);
        end
        repeat (4) @(posedge clk); rst <= 0; @(posedge clk);
        if (LOAD) begin
            for (i = 0; i < 960; i = i + 1) begin cfg_we <= 1; cfg_sel <= 0; cfg_addr <= i; cfg_data <= {60'd0, tw[i]}; @(posedge clk); end
            for (i = 0; i < 5; i = i + 1) begin cfg_we <= 1; cfg_sel <= 1; cfg_addr <= i; cfg_data <= tt[i]; @(posedge clk); end
            for (i = 0; i < 605; i = i + 1) begin cfg_we <= 1; cfg_sel <= 2; cfg_addr <= i; cfg_data <= tl[i]; @(posedge clk); end
            for (i = 0; i < 6; i = i + 1) begin cfg_we <= 1; cfg_sel <= 3; cfg_addr <= i; cfg_data <= {64'd0, tc[i]}; @(posedge clk); end
            cfg_we <= 0; @(posedge clk);
        end
        k = 0; rec = 0;
        while (prog[k] !== 16'hxxxx) begin
            start <= 0; ev_valid <= 0; win_end <= 0;
            if (prog[k][14]) begin start <= 1; @(posedge clk); start <= 0; @(posedge clk); end
            else if (prog[k][15]) begin
                repeat (3) @(posedge clk);
                win_end <= 1; @(posedge clk); win_end <= 0;
                wait_n = 0; while (!out_valid && wait_n < 200) begin @(posedge clk); wait_n = wait_n + 1; end
                $display("R %0d %0d %0d %0d %0d", out_win, out_cls, out_pred, out_gap, out_stop);
                repeat (2) @(posedge clk);
            end else begin ev_valid <= 1; ev_idx <= prog[k][7:0]; @(posedge clk); ev_valid <= 0; end
            k = k + 1;
        end
        $display("DONE");
        $finish;
    end
endmodule
