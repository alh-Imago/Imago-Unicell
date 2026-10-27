`timescale 1ns/1ps
// tb_hexn_ctxstore_v1.v -- runs an operation file against hexn_ctxstore_v1 + our SDRAM controller + the SDRAM model, prints every RD result and the counters; tools/hexn_ctxstore_rtl_check_v1.py compares them with the bit-true model.
// Plusargs: +OPS=<hex file, one 64-bit word per op: bit 40 = OBS, [38:31] = fid, [30:0] = key> +N=<number of ops>. Parameters BB, CB are set by the script (iverilog -P).
module tb_hexn_ctxstore_v1 #(parameter BB = 8, parameter CB = 4);
    reg clk = 0, rst = 1; always #18.5185 clk = ~clk; wire clk_sdram = ~clk; reg resetn = 0;
    reg cmd_valid = 0, cmd_obs = 0; reg [30:0] cmd_key = 0; reg [7:0] cmd_fid = 0; wire cmd_ready, done, found, ready, err; wire [223:0] slots; reg [3:0] cnt_sel = 0; wire [31:0] cnt_val;
    wire sv, swe, sready, srv, sinit; wire [20:0] sa; wire [31:0] sw, sr;
    hexn_ctxstore_v1 #(.BB(BB), .CB(CB)) dut (.clk(clk), .rst(rst), .cmd_valid(cmd_valid), .cmd_obs(cmd_obs), .cmd_key(cmd_key), .cmd_fid(cmd_fid), .cmd_ready(cmd_ready), .done(done), .found(found), .slots_out(slots), .ready(ready), .err(err),
        .cnt_sel(cnt_sel), .cnt_val(cnt_val), .sd_cmd_valid(sv), .sd_cmd_we(swe), .sd_cmd_addr(sa), .sd_cmd_wdata(sw), .sd_cmd_ready(sready), .sd_rd_valid(srv), .sd_rd_data(sr), .sd_init_done(sinit));
    wire O_clk, O_cke, O_cs, O_ras, O_cas, O_wen; wire [31:0] dq; wire [10:0] O_a; wire [1:0] O_ba; wire [3:0] O_dqm;
    hexn_sdram_v1 #(.FREQ(27_000_000), .CL(3'd2)) sdc (.clk(clk), .clk_sdram(clk_sdram), .resetn(resetn), .rdlat(3'd3), .cmd_valid(sv), .cmd_we(swe), .cmd_addr(sa), .cmd_wdata(sw), .cmd_wmask(4'b1111), .cmd_ready(sready), .rd_valid(srv), .rd_data(sr), .init_done(sinit),
        .O_sdram_clk(O_clk), .O_sdram_cke(O_cke), .O_sdram_cs_n(O_cs), .O_sdram_ras_n(O_ras), .O_sdram_cas_n(O_cas), .O_sdram_wen_n(O_wen), .IO_sdram_dq(dq), .O_sdram_addr(O_a), .O_sdram_ba(O_ba), .O_sdram_dqm(O_dqm));
    sdram_model_v1 #(.CL(3'd2)) model (.CLK(O_clk), .CKE(O_cke), .CS_N(O_cs), .RAS_N(O_ras), .CAS_N(O_cas), .WE_N(O_wen), .A(O_a), .BA(O_ba), .DQM(O_dqm), .DQ(dq));
    reg [63:0] ops [0:262143]; integer n, i, t; reg [1023:0] fn; reg [63:0] v;
    initial begin
        if (!$value$plusargs("OPS=%s", fn)) begin $display("no +OPS"); $finish; end
        if (!$value$plusargs("N=%d", n)) n = 0;
        $readmemh(fn, ops);
        repeat (4) @(posedge clk); rst <= 0; resetn <= 1;
        wait (ready === 1'b1); @(posedge clk);
        for (i = 0; i < n; i = i + 1) begin
            v = ops[i];
            @(posedge clk); cmd_valid <= 1; cmd_obs <= v[40]; cmd_key <= v[30:0]; cmd_fid <= v[38:31];
            @(posedge clk); while (!cmd_ready) @(posedge clk);
            cmd_valid <= 0; t = 0;
            while (!done && t < 100000) begin @(posedge clk); t = t + 1; end
            if (!done) begin $display("TIMEOUT op %0d", i); $finish; end
            if (!v[40]) $display("R %0d %0d %056h", i, found, slots);
        end
        for (i = 0; i < 9; i = i + 1) begin cnt_sel = i; #1; $display("C %0d %0d", i, cnt_val); end
        $display("ERR %0d", err); $display("END"); $finish;
    end
    initial begin #4000000000; $display("TIMEOUT total"); $finish; end
endmodule
