// tb_stripped_v2_dynroute_gate.v — points.md #170: confirms the
// compile-time ENABLE_DYNAMIC_ROUTING gate actually does what it claims.
// A cell built with the parameter at its default (0) must ignore
// dynamic_route_en entirely -- even if that runtime bit somehow gets
// set to 1 -- and always use the plain static routing_mask. This is the
// "compiler/loader contract" the RTL's own comment describes: nothing
// enforces it at runtime once the comparator hardware doesn't exist,
// so this test is the only thing standing between "the parameter works"
// and "silently wrong routing on a mismatched build."
`timescale 1ns / 1ps

module tb_stripped_v2_dynroute_gate;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg [255:0] cfg_data = 0;
    reg         cfg_valid = 0;

    reg  [31:0] din_n = 0, din_s = 0;
    reg         arr_n = 0, arr_s = 0;
    wire [31:0] dout_n, dout_e;
    wire        fire_n, fire_e;

    // NOTE: no ENABLE_DYNAMIC_ROUTING override -- uses the default (0/OFF).
    unicell_stripped_v2 #(.CELL_ID(16'h00B1)) T (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(din_n), .data_in_s(din_s), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arr_n), .arrived_s(arr_s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(dout_e), .data_out_w(),
        .fire_n(fire_n), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0), .hold_in(1'b0), .fb_internal_in(1'b0),
        .a_reemit_in(1'b0), .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    integer passed = 0, failed = 0;
    task check(input cond, input [255:0] name);
        begin
            if (cond) begin passed = passed + 1; $display("  [PASS] %0s", name); end
            else begin failed = failed + 1; $display("  [FAIL] %0s", name); end
        end
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        // Static routing_mask = North only. dynamic_route_en=1 (SET
        // ANYWAY, deliberately mismatched with this build's
        // ENABLE_DYNAMIC_ROUTING=0). pattern_high = East only -- if the
        // comparator were live, a HIGH result should route East instead.
        cfg_data = 128'h0;
        cfg_data[9:0]   = 10'h02C;              // TOPO_PASS_B
        cfg_data[69:64] = 6'b000001;            // routing_mask = North only
        cfg_data[94]    = 1'b1;                 // dynamic_route_en = 1 (should be IGNORED)
        cfg_data[93:88] = 6'b000100;            // pattern_high = East only
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;

        din_n = 32'h00000064;  // 100 -- first arrival (A)
        arr_n = 1; @(posedge clk); #1; arr_n = 0;
        din_s = 32'h000000C8;  // 200 -- second arrival, 200 > 100 -> would be HIGH
        arr_s = 1; @(posedge clk); #1; arr_s = 0;
        @(posedge clk); #1;

        check(fire_n === 1'b1, "fired North -- static routing_mask, exactly as configured");
        check(fire_e === 1'b0, "did NOT fire East -- comparator/pattern_high genuinely has no effect on this build");

        $display("\n=== Results ===\n");
        $display("Results: %0d passed, %0d failed out of %0d tests", passed, failed, passed+failed);
        if (failed > 0) begin
            $display("FAILED");
            $finish;
        end
        $display("ALL TESTS PASSED");
        $finish;
    end

endmodule
