`timescale 1ns/1ps
// Stress testbench for the shared data RAM of sc_sys_v10: the host hammers the RAM (reads of one word, every other clock) while slices run.
// +prog=<imem hex> +tasks=<3 words/task: arrival, code addr, lw|crit<<8|prog<<9> +ntasks=<n> +shared=<hex pairs addr,data> +nshared=<n>
// +regions=<hex triples prog,base,len> +nregions=<n> +hammer=<word>  (reads that word continuously; every reply must equal +hval=<value>)
// +out=<file>: shared words 0..255 and per-task a0/trap, plus the number of hammer reads and mismatches.
module tb_sys10;
    parameter S = 4;
    parameter IMW = 256;
    parameter DSH = 256;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;
    reg h_push = 0; reg [15:0] h_tid = 0, h_code = 0; reg [5:0] h_prog = 0; reg [2:0] h_lw = 0; reg h_crit = 0;
    reg imem_we = 0; reg [15:0] imem_wa = 0; reg [31:0] imem_wd = 0;
    reg rs_we = 0; reg [5:0] rs_prog = 0; reg [15:0] rs_base = 0, rs_len = 0;
    reg dh_we = 0, dh_rd = 0; reg [15:0] dh_a = 0; reg [31:0] dh_wd = 0;
    wire [31:0] dh_q; wire dh_qv, dh_busy;
    sc_sys_v10 #(.S(S), .DMW(16), .DSH(DSH), .QD(32), .IMEM_WORDS(IMW), .LONGEST(1)) dut (
        .clk(clk), .rst(rst), .hold(1'b0), .rg_we(1'b0), .rg_prog(6'd0), .rg_cbase(16'd0), .rg_clen(16'd0), .rg_dlen(16'd0),
        .rs_we(rs_we), .rs_prog(rs_prog), .rs_base(rs_base), .rs_len(rs_len),
        .dh_we(dh_we), .dh_rd(dh_rd), .dh_a(dh_a), .dh_wd(dh_wd), .dh_q(dh_q), .dh_qv(dh_qv), .dh_busy(dh_busy),
        .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_prog(h_prog), .h_lw(h_lw), .h_crit(h_crit),
        .imem_we(imem_we), .imem_wa(imem_wa), .imem_wd(imem_wd), .q_tid(16'd0),
        .ev_pl_we(1'b0), .ev_pl_id(8'd0), .ev_pl_data(32'd0), .ev_set(1'b0), .ev_set_id(8'd0));
    reg [31:0] img [0:IMW-1];
    reg [31:0] tl [0:3*64-1];
    reg [31:0] shv [0:2*256-1];
    reg [31:0] rgv [0:3*64-1];
    integer NT, NSH, NRG, i, fd, HAM, HVAL, hread, hbad, nxt;
    reg [1023:0] progname, taskname, outname, shname, rgname;
    reg hon;
    // hammer: a read request every other clock; the reply (dh_qv) must carry the expected value
    reg hwait = 0;
    always @(posedge clk) begin
        dh_rd <= 1'b0;
        if (hon && !rst) begin
            if (!hwait && !dh_busy) begin dh_rd <= 1'b1; dh_a <= HAM; hwait <= 1'b1; end
            if (dh_qv) begin hwait <= 1'b0; hread = hread + 1; if (dh_q !== HVAL[31:0]) hbad = hbad + 1; end
        end
    end
    reg setup_done = 0;
    always @(posedge clk) if (!rst) begin
        h_push <= 0;
        if (setup_done && nxt < NT && tl[3*nxt] <= dut.cyc) begin
            h_push <= 1; h_tid <= nxt; h_code <= tl[3*nxt+1]; h_lw <= tl[3*nxt+2][2:0]; h_crit <= tl[3*nxt+2][8]; h_prog <= tl[3*nxt+2][14:9];
            nxt <= nxt + 1;
        end
    end
    initial begin
        nxt = 0; hread = 0; hbad = 0; hon = 0; HAM = 0; HVAL = 0;
        if (!$value$plusargs("prog=%s", progname))  begin $display("need +prog");  $finish; end
        if (!$value$plusargs("tasks=%s", taskname)) begin $display("need +tasks"); $finish; end
        if (!$value$plusargs("ntasks=%d", NT))      begin $display("need +ntasks"); $finish; end
        if (!$value$plusargs("out=%s", outname))    begin $display("need +out");   $finish; end
        void'($value$plusargs("nshared=%d", NSH)); void'($value$plusargs("nregions=%d", NRG));
        if ($value$plusargs("shared=%s", shname))  $readmemh(shname, shv);
        if ($value$plusargs("regions=%s", rgname)) $readmemh(rgname, rgv);
        for (i = 0; i < IMW; i = i + 1) img[i] = 32'h0;
        $readmemh(progname, img); $readmemh(taskname, tl);
        repeat (4) @(posedge clk);
        for (i = 0; i < IMW; i = i + 1) begin imem_we <= 1; imem_wa <= i; imem_wd <= img[i]; @(posedge clk); end
        imem_we <= 0; @(posedge clk);
        rst <= 0; repeat (4) @(posedge clk);
        for (i = 0; i < NRG; i = i + 1) begin rs_we <= 1; rs_prog <= rgv[3*i]; rs_base <= rgv[3*i+1]; rs_len <= rgv[3*i+2]; @(posedge clk); end
        rs_we <= 0;
        for (i = 0; i < NSH; i = i + 1) begin dh_we <= 1; dh_a <= shv[2*i]; dh_wd <= shv[2*i+1]; @(posedge clk); dh_we <= 0; @(posedge clk); while (dh_busy) @(posedge clk); end
        dh_we <= 0; repeat (4) @(posedge clk);
        setup_done = 1;
        if ($value$plusargs("hammer=%d", HAM)) begin
            // value of the hammered word is known from the shared list
            for (i = 0; i < NSH; i = i + 1) if (shv[2*i] == HAM) HVAL = shv[2*i+1];
            hon = 1;
        end
        while (dut.done_count < NT && dut.cyc < 20000000) @(posedge clk);
        hon = 0; repeat (8) @(posedge clk);
        fd = $fopen(outname, "w");
        $fdisplay(fd, "done %0d launch_err %0d", dut.done_count, dut.launch_err);
        $fdisplay(fd, "hammer %0d bad %0d", hread, hbad);
        for (i = 0; i < NT; i = i + 1) $fdisplay(fd, "t %0d %0d %0d", i, dut.t_a0[i], dut.t_trap[i]);
        for (i = 0; i < DSH; i = i + 1) $fdisplay(fd, "m %0d %0d", i, dut.shd[i]);
        $fclose(fd); $finish;
    end
endmodule
