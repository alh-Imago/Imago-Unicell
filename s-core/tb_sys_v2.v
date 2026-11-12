`timescale 1ns/1ps
// System testbench.  +prog=<imem hex> +tasks=<3 words per task: arrival, code word addr, lw>
// +ntasks=<n> +out=<file>.  Optional +S is fixed by parameter.
module tb_sys;
    parameter S = 32;
    parameter LA = 1;
    parameter MAXPASS = 8;
    parameter RESERVE = 0;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;

    reg        h_push = 0;
    reg [15:0] h_tid = 0, h_code = 0;
    reg [2:0]  h_lw = 0;
    reg        h_crit = 0;

    sc_sys_v2 #(.S(S), .LA(LA), .MAXPASS(MAXPASS), .RESERVE(RESERVE)) dut (.clk(clk), .rst(rst), .h_push(h_push),
                         .h_tid(h_tid), .h_code(h_code), .h_lw(h_lw), .h_crit(h_crit));

    reg [31:0] tl [0:3*256-1];
    integer NT, nxt, i, fd;
    reg [1023:0] progname, taskname, outname;

    always @(posedge clk) if (!rst) begin
        h_push <= 0;
        if (nxt < NT && tl[3*nxt] <= dut.cyc) begin
            h_push <= 1; h_tid <= nxt; h_code <= tl[3*nxt+1]; h_lw <= tl[3*nxt+2][2:0]; h_crit <= tl[3*nxt+2][8];
            nxt <= nxt + 1;
        end
    end

    initial begin
        nxt = 0;
        if (!$value$plusargs("prog=%s", progname))   begin $display("need +prog");   $finish; end
        if (!$value$plusargs("tasks=%s", taskname))  begin $display("need +tasks");  $finish; end
        if (!$value$plusargs("ntasks=%d", NT))       begin $display("need +ntasks"); $finish; end
        if (!$value$plusargs("out=%s", outname))     begin $display("need +out");    $finish; end
        for (i = 0; i < 8192; i = i + 1) dut.imem[i] = 32'h0;
        $readmemh(progname, dut.imem);
        $readmemh(taskname, tl);
        repeat (4) @(posedge clk);
        rst <= 0;
        while (dut.cq_wr < NT && dut.cyc < 50000000) @(posedge clk);
        repeat (2) @(posedge clk);
        fd = $fopen(outname, "w");
        $fdisplay(fd, "total_cycles %0d", dut.cyc);
        $fdisplay(fd, "busy_slice_cycles %0d", dut.busy_slice_cycles);
        $fdisplay(fd, "S %0d", S);
        $fdisplay(fd, "completed %0d", dut.cq_wr);
        for (i = 0; i < dut.cq_wr; i = i + 1)
            $fdisplay(fd, "c %0d %0d %0d %0d %0d %0d %0d", dut.cq_tid[i], dut.cq_lw[i],
                      tl[3*dut.cq_tid[i]], dut.cq_start[i], dut.cq_end[i], dut.cq_a0[i], dut.cq_trap[i]);
        $fclose(fd);
        $finish;
    end
endmodule
