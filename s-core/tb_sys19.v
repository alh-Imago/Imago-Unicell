`timescale 1ns/1ps
// tb_sys19.v - pool-level testbench for sc_sys_v16 (ledger #1386): tasks with a width (lw) on a block of S slices with one fusion unit.
// +prog=<imem hex> +tasks=<3 words/task: arrival clock, code word address, lw|crit<<8|prog<<9> +ntasks=<n> +out=<file>
// out: done, launch_err, per task: a0 trap cause start end leader-slot
module tb_sys19;
    parameter S = 8;
    parameter IMW = 4096;
    parameter FZ = 1;
    parameter ULW = 2;
    parameter NU = 2;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;
    reg h_push = 0; reg [15:0] h_tid = 0, h_code = 0; reg [5:0] h_prog = 0; reg [2:0] h_lw = 0; reg h_crit = 0;
    reg imem_we = 0; reg [15:0] imem_wa = 0; reg [31:0] imem_wd = 0;
    reg [15:0] q_tid = 0;
    reg rs_we = 0, dh_we = 0; reg [15:0] dh_a = 0; reg [31:0] dh_wd = 0; wire dh_busy;
    sc_sys_v19 #(.S(S), .DMW(1024), .DSH(256), .QD(64), .IMEM_WORDS(IMW), .FZ(FZ), .ULW(ULW), .NU(NU)) dut (
        .clk(clk), .rst(rst), .hold(1'b0), .rg_we(1'b0), .rg_prog(6'd0), .rg_cbase(16'd0), .rg_clen(16'd0), .rg_dlen(16'd0),
        .lb_we(1'b0), .lb_base(16'd0), .lb_len(16'd0),
        .rs_we(rs_we), .rs_prog(6'd0), .rs_base(16'd0), .rs_len(16'd64),
        .dh_we(dh_we), .dh_rd(1'b0), .dh_a(dh_a), .dh_wd(dh_wd), .dh_busy(dh_busy),
        .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_prog(h_prog), .h_lw(h_lw), .h_crit(h_crit),
        .imem_we(imem_we), .imem_wa(imem_wa), .imem_wd(imem_wd), .q_tid(q_tid),
        .ev_pl_we(1'b0), .ev_pl_id(8'd0), .ev_pl_data(32'd0), .ev_set(1'b0), .ev_set_id(8'd0));
    reg [31:0] img [0:IMW-1];
    reg [31:0] tl [0:3*64-1];
    integer NT, i, fd, nxt;
    reg [1023:0] progname, taskname, outname;
    reg setup_done = 0;
    always @(posedge clk) if (!rst) begin
        h_push <= 0;
        if (setup_done && nxt < NT && tl[3*nxt] <= dut.cyc) begin
            h_push <= 1; h_tid <= nxt; h_code <= tl[3*nxt+1]; h_lw <= tl[3*nxt+2][2:0]; h_crit <= tl[3*nxt+2][8]; h_prog <= tl[3*nxt+2][14:9];
            nxt <= nxt + 1;
        end
    end
    initial begin
        nxt = 0;
        if (!$value$plusargs("prog=%s", progname))  begin $display("need +prog");  $finish; end
        if (!$value$plusargs("tasks=%s", taskname)) begin $display("need +tasks"); $finish; end
        if (!$value$plusargs("ntasks=%d", NT))      begin $display("need +ntasks"); $finish; end
        if (!$value$plusargs("out=%s", outname))    begin $display("need +out");   $finish; end
        for (i = 0; i < IMW; i = i + 1) img[i] = 32'h0;
        $readmemh(progname, img); $readmemh(taskname, tl);
        repeat (4) @(posedge clk);
        for (i = 0; i < IMW; i = i + 1) begin imem_we <= 1; imem_wa <= i; imem_wd <= img[i]; @(posedge clk); end
        imem_we <= 0; @(posedge clk);
        rst <= 0; repeat (4) @(posedge clk);
        rs_we <= 1; @(posedge clk); rs_we <= 0;                       // shared window of program class 0: words 0..63
        for (i = 0; i < 16; i = i + 1) begin dh_we <= 1; dh_a <= i; dh_wd <= 3*i + 1; @(posedge clk); dh_we <= 0; @(posedge clk); while (dh_busy) @(posedge clk); end
        repeat (4) @(posedge clk);
        setup_done = 1;
        while (dut.done_count < NT && dut.cyc < 30000000) @(posedge clk);
        repeat (8) @(posedge clk);
        fd = $fopen(outname, "w");
        $fdisplay(fd, "done %0d launch_err %0d", dut.done_count, dut.launch_err);
        for (i = 0; i < NT; i = i + 1) $fdisplay(fd, "t %0d %0d %0d %0d %0d %0d %0d", i, dut.t_a0[i], dut.t_trap[i], dut.t_cause[i], dut.t_start[i], dut.t_end[i], dut.t_slot[i]);
        for (i = 0; i < 32; i = i + 1) $fdisplay(fd, "m %0d %0d", i, dut.shd[i]);
        $fclose(fd); $finish;
    end
endmodule
