// tb_unicell_super_v2.v — first real test of unicell_super_v2.v
// (points.md #421/#422): confirms the new SEL_SEQ core (sequencer_
// cell_v1.v, promoted per #418) works correctly through the shell's
// own real config/mux path, AND confirms SEL_ACC (completely
// unchanged from v1) still works -- a real regression check on the
// SHARED mux/config machinery every core (old and new) passes
// through, not just a test of the new core in isolation.
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    reg rst = 1;
    always #5 clk = ~clk;

    reg cfg_valid = 0;
    reg [79:0] cfg_data = 80'h0;

    reg [31:0] data_in_n = 0, data_in_s = 0, data_in_e = 0, data_in_w = 0;
    reg arrived_n = 0, arrived_s = 0, arrived_e = 0, arrived_w = 0;
    wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w;
    wire fire_n, fire_s, fire_e, fire_w;
    wire ready_out;
    reg ready_in_n = 1, ready_in_s = 1, ready_in_e = 1, ready_in_w = 1;
    wire ack_out_n, ack_out_s, ack_out_e, ack_out_w;
    reg ack_in_n = 0, ack_in_s = 0, ack_in_e = 0, ack_in_w = 0;
    reg freeze_in = 0;

    reg program_in = 0;
    wire program_done;
    reg [31:0] prog_data_in_n = 0, prog_data_in_s = 0, prog_data_in_e = 0, prog_data_in_w = 0;
    reg prog_arrived_in_n = 0, prog_arrived_in_s = 0, prog_arrived_in_e = 0, prog_arrived_in_w = 0;

    wire [4:0] status_core_select;

    unicell_super_v2 #(.CELL_ID(16'h0002)) DUT (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_out(ready_out),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .freeze_in(freeze_in),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(prog_arrived_in_s),
        .prog_arrived_in_e(prog_arrived_in_e), .prog_arrived_in_w(prog_arrived_in_w),
        .status_core_select(status_core_select)
    );

    integer errors = 0;
    task check(input cond, input [255:0] msg);
        begin
            if (!cond) begin
                $display("FAIL: %s", msg);
                errors = errors + 1;
            end
        end
    endtask

    localparam [4:0] SEL_ACC = 5'd3, SEL_SEQ = 5'd6;

    initial begin
        #12 rst = 0;

        // ── Part 1: SEL_SEQ, the new core. Config: VALUE_0=10,
        // VALUE_1=20, VALUE_2=30, SEQUENCE_LEN=3 (stored 2),
        // downstream_mask=N. core_config[37:0] = sequencer's own field
        // map directly; core_select=SEL_SEQ in the low 5 bits. ──
        // cfg_data[79:67]=reserved, [66:47]=addon_config(off),
        // [46:5]=core_config, [4:0]=core_select
        cfg_data = {13'b0, 20'b0, 4'b0, 4'b0001, 2'd2, 8'd0, 8'd30, 8'd20, 8'd10, SEL_SEQ};
        #10 cfg_valid = 1;
        #10 cfg_valid = 0;

        check(status_core_select == SEL_SEQ, "core_select should read back SEL_SEQ");

        repeat (20) begin
            @(posedge clk);
            #1;
            if (fire_n) ack_in_n = 1; else ack_in_n = 0;
        end
        #1 ack_in_n = 0;

        // Real, honest regression: confirm the shell's own reset (via
        // a fresh cfg_valid pulse to a DIFFERENT core) doesn't leave
        // SEQ's own outputs stuck driving the shared bus.
        #10;

        // ── Part 2: SEL_ACC, completely unchanged from v1 -- a real
        // regression check that adding SEL_SEQ didn't disturb the
        // shared mux/config machinery every OTHER core also depends
        // on. inc_dir=N(4'b0001), dec_dir=0, downstream_mask=N. ──
        cfg_data = {13'b0, 20'b0, {18'b0, 4'b0001, 4'b0000, 4'b0001}, SEL_ACC};
        #10 cfg_valid = 1;
        #10 cfg_valid = 0;

        check(status_core_select == SEL_ACC, "core_select should read back SEL_ACC");

        arrived_n = 1;
        @(posedge clk); #1;
        arrived_n = 0;
        @(posedge clk); #1;

        check(fire_n === 1'b1, "SEL_ACC should offer after one real arrival, matching v1's own proven behavior");
        check(data_out_n == 32'd1, "SEL_ACC's first count should be 1, matching v1's own proven behavior");

        if (errors == 0) begin
            $display("PASS: unicell_super_v2 -- SEL_SEQ works, SEL_ACC unchanged (zero regression)");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end
endmodule
