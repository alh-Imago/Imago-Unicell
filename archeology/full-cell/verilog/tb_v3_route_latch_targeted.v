// tb_v3_route_latch_targeted.v — verifies CMD_SET_ROUTE_LATCH_AT (points.md
// #62, 2026-07-30): the targeted counterpart to the broadcast
// CMD_SET_ROUTE_LATCH, config_match-gated so heterogeneous per-cell routing
// latches are actually buildable -- same exclusion property zone_target.tcl
// already proved on silicon for CMD_LOAD_AT vs. broadcast CMD_RECONFIGURE.
//
// Two cells, CELL_ID 0 and 1. Target cell0 -> routing_mask=E-only(4).
// Target cell1 -> routing_mask=N-only(1). Confirm each cell's routing latch
// holds ONLY its own targeted value -- cell1's write must not touch cell0's,
// and vice versa (the exact same "config a cell, target another, confirm
// exclusion" pattern used throughout this project for CMD_LOAD_AT).
`timescale 1ns/1ps
module tb_v3_route_latch_targeted;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;

    unicell_array64_v3 #(.NUM_CELLS(2), .CELL_BASE(0)) arr (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(inj_addr), .cpu_data(inj_data), .cpu_valid(inj_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .out_routing(), .out_transit(),
        .obs_bus_valid(), .obs_bus_addr(), .obs_bus_data(),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(),
        .cycle_count()
    );

    integer errors=0;
    task check6; input [5:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%02h)", msg, got);
        else begin $display("  FAIL: %0s got=0x%02h want=0x%02h", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_BOOT_COMMIT         = 8'd7;
    localparam [7:0] OP_SET_ROUTE_LATCH_AT  = 8'd38;

    task boot_all; begin
        @(negedge clk); cmd_bus={8'h0,OP_BOOT_COMMIT}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Establish bus_addr_r=target (the address-lane hold; a plain harmless
    // dummy injection, since neither cell is armed yet at setup time).
    task hold_target; input [15:0] target; begin
        @(negedge clk); inj_addr=target; inj_data=32'h0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task set_route_latch_at; input [2:0] cell_id; input [5:0] routing_mask; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_SET_ROUTE_LATCH_AT};
        cmd_data = {26'h0, routing_mask};  // cmd_data[5:0]=routing_mask, rest 0
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== CMD_SET_ROUTE_LATCH_AT: per-cell targeting, exclusion proof (points.md #62) ===");

        boot_all;

        set_route_latch_at(3'd0, 6'b000100);  // cell0 -> E-only (4)
        $display("  after targeting cell0: cell0.routing_mask=0x%02h cell1.routing_mask=0x%02h",
            arr.cell_array[0].cell_inst.cmd_latch[69:64],
            arr.cell_array[1].cell_inst.cmd_latch[69:64]);
        check6(arr.cell_array[0].cell_inst.cmd_latch[69:64], 6'b000100, "cell0 got its own targeted value");
        check6(arr.cell_array[1].cell_inst.cmd_latch[69:64], 6'b000000, "cell1 UNTOUCHED by cell0's targeted write");

        set_route_latch_at(3'd1, 6'b000001);  // cell1 -> N-only (1)
        $display("  after targeting cell1: cell0.routing_mask=0x%02h cell1.routing_mask=0x%02h",
            arr.cell_array[0].cell_inst.cmd_latch[69:64],
            arr.cell_array[1].cell_inst.cmd_latch[69:64]);
        check6(arr.cell_array[1].cell_inst.cmd_latch[69:64], 6'b000001, "cell1 got its own targeted value");
        check6(arr.cell_array[0].cell_inst.cmd_latch[69:64], 6'b000100, "cell0 STILL holds its earlier value (exclusion)");

        if (errors==0) $display(">>> ROUTE_LATCH_AT PASS: two cells, two genuinely different routing latches, no cross-contamination");
        else           $display(">>> ROUTE_LATCH_AT FAIL: %0d errors", errors);
        $finish;
    end
endmodule
