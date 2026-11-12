`timescale 1ns/1ps
// Testbench for sc_sys_v3.  +prog=<imem hex> +tasks=<3 words per task: arrival, code word addr, lw|crit<<8>
// +ntasks=<n> +nevents=<m> +out=<file>.  Synthetic peripheral events are injected on lines 64..255.
module tb_sys3;
    parameter S = 32;
    parameter PRIO = 1;
    parameter BESTFIT = 1;
    parameter GUARD = 8;
    parameter MAXPASS = 8;
    parameter LONGEST = 0;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;

    reg        h_push = 0;
    reg [15:0] h_tid = 0, h_code = 0;
    reg [5:0]  h_prog = 0;
    reg [2:0]  h_lw = 0;
    reg        h_crit = 0;
    reg        ev_pl_we = 0, ev_set = 0;
    reg [7:0]  ev_pl_id = 0, ev_set_id = 0;
    reg [31:0] ev_pl_data = 0;

    sc_sys_v3 #(.S(S), .PRIO(PRIO), .BESTFIT(BESTFIT), .GUARD(GUARD), .MAXPASS(MAXPASS), .LONGEST(LONGEST)) dut (
        .clk(clk), .rst(rst), .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_prog(h_prog), .h_lw(h_lw), .h_crit(h_crit),
        .ev_pl_we(ev_pl_we), .ev_pl_id(ev_pl_id), .ev_pl_data(ev_pl_data),
        .ev_set(ev_set), .ev_set_id(ev_set_id));

    reg [31:0] tl [0:3*256-1];
    integer NT, NE, nxt, i, fd;
    reg [1023:0] progname, taskname, outname;

    always @(posedge clk) if (!rst) begin
        h_push <= 0;
        if (nxt < NT && tl[3*nxt] <= dut.cyc) begin
            h_push <= 1; h_tid <= nxt; h_code <= tl[3*nxt+1]; h_lw <= tl[3*nxt+2][2:0]; h_crit <= tl[3*nxt+2][8]; h_prog <= tl[3*nxt+2][14:9];
            nxt <= nxt + 1;
        end
    end

    // synthetic peripheral events: payload first, line raised on the next cycle
    reg [31:0] evt_time [0:255], evt_data [0:255], evt_setcyc [0:255];
    reg [7:0]  evt_line [0:255];
    integer en, ecur;
    reg epend;
    reg [7:0] epend_id;
    always @(posedge clk) if (!rst) begin
        ev_pl_we <= 0; ev_set <= 0;
        if (en < NE && dut.cyc >= evt_time[en]) begin
            ev_pl_we <= 1; ev_pl_id <= evt_line[en]; ev_pl_data <= evt_data[en];
            epend <= 1; epend_id <= evt_line[en]; ecur <= en; en <= en + 1;
        end else if (epend) begin
            ev_set <= 1; ev_set_id <= epend_id; evt_setcyc[ecur] <= dut.cyc; epend <= 0;
        end
    end

    reg [1023:0] profname;
    reg [24:0] proftmp [0:511];
    initial begin
        nxt = 0; en = 0; epend = 0; ecur = 0; NE = 0;
        if (!$value$plusargs("prog=%s", progname))   begin $display("need +prog");   $finish; end
        if (!$value$plusargs("tasks=%s", taskname))  begin $display("need +tasks");  $finish; end
        if (!$value$plusargs("ntasks=%d", NT))       begin $display("need +ntasks"); $finish; end
        if (!$value$plusargs("out=%s", outname))     begin $display("need +out");    $finish; end
        void'($value$plusargs("nevents=%d", NE));
        for (i = 0; i < NE; i = i + 1) begin
            evt_time[i] = 400 + i * 733;
            evt_line[i] = 64 + ((i * 37) % 192);
            evt_data[i] = 32'hA5A50000 + i * 17;
        end
        for (i = 0; i < 8192; i = i + 1) dut.imem[i] = 32'h0;
        $readmemh(progname, dut.imem);
        $readmemh(taskname, tl);
        repeat (4) @(posedge clk);
        rst <= 0;
        if ($value$plusargs("profin=%s", profname)) begin
            @(negedge clk);
            $readmemh(profname, proftmp);
            for (i = 0; i < dut.PROF; i = i + 1) dut.prof[i] = proftmp[i];
        end
        while ((dut.done_count < NT || dut.ev_cnt < NE) && dut.cyc < 50000000) @(posedge clk);
        repeat (2) @(posedge clk);
        fd = $fopen(outname, "w");
        $fdisplay(fd, "total_cycles %0d", dut.cyc);
        $fdisplay(fd, "busy_slice_cycles %0d", dut.busy_slice_cycles);
        $fdisplay(fd, "waste_blocked %0d", dut.waste_blocked);
        $fdisplay(fd, "waste_tail %0d", dut.waste_tail);
        $fdisplay(fd, "search_cycles %0d", dut.search_cycles);
        $fdisplay(fd, "launch_err %0d", dut.launch_err);
        $fdisplay(fd, "dispatches %0d", dut.dispatches);
        $fdisplay(fd, "S %0d", S);
        $fdisplay(fd, "completed %0d", dut.done_count);
        $fdisplay(fd, "events %0d", dut.ev_cnt);
        for (i = 0; i < NT; i = i + 1)
            $fdisplay(fd, "c %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d", i, dut.t_lw[i], dut.t_crit[i], dut.t_arr[i],
                      dut.t_start[i], dut.t_end[i], dut.t_a0[i], dut.t_trap[i], dut.t_state[i], dut.t_slot[i], dut.t_pred[i]);
        for (i = 0; i < dut.ev_cnt; i = i + 1)
            $fdisplay(fd, "e %0d %0d %0d", dut.ev_id[i], dut.ev_data[i], dut.ev_cyc[i]);
        for (i = 0; i < NE; i = i + 1)
            $fdisplay(fd, "x %0d %0d %0d", evt_line[i], evt_data[i], evt_setcyc[i]);
        for (i = 0; i < dut.PROF; i = i + 1) $fdisplay(fd, "p %0d %0d", i, dut.prof[i]);
        $fclose(fd);
        $finish;
    end
endmodule
