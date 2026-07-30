// tb_v3_route_latch.v — verifies the COMPARATOR + DYNAMIC ROUTING LATCH
// primitive (points.md #49/#51, 2026-07-30).
//
// One cell, ONE static configuration (routing_mask=N|E open, cardinal_edge=
// all-local, dynamic_route_en=1, patterns loaded via the new whole-latch
// CMD_SET_ROUTE_LATCH opcode), fired three times against the SAME stored
// threshold (a_data, re-primed via CMD_SWAP_AB before each injection so the
// three cases are independent) with three different incoming values:
//
//   pattern_low   = E-only (4)   -- selected when incoming < threshold
//   pattern_equal = N-only (1)   -- selected when incoming == threshold
//   pattern_high  = N|E    (5)   -- selected when incoming > threshold
//
// effective_routing = selected_pattern & routing_mask (both open in this
// test, so the AND is a no-op here -- confirms the comparator selection
// itself, not the openness gate; tb_v3_cardinal_edge.v already covers the
// openness/local-vs-cardinal layering separately).
//
// Threshold = 0x50. Three injected values: 0x10 (LOWER), 0x50 (EQUAL),
// 0x90 (HIGHER). Same static config throughout -- only the comparator
// result changes which bridges fire, proving genuinely data-dependent
// routing on real, unchanged cell configuration.
`timescale 1ns/1ps
module tb_v3_route_latch;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire [15:0] z_out_addr; wire [31:0] z_out_data; wire z_out_valid;
    wire [15:0] z_emit;

    wire        brn_v; wire [15:0] brn_a; wire [31:0] brn_d;
    wire        bre_v; wire [15:0] bre_a; wire [31:0] bre_d;
    wire tie_v = 1'b0; wire [15:0] tie_a = 16'h0; wire [31:0] tie_d = 32'h0;

    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(0)) zone (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(inj_addr), .cpu_data(inj_data), .cpu_valid(inj_valid),
        .out_addr(z_out_addr), .out_data(z_out_data), .out_valid(z_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(brn_v), .bridge_n_out_addr(brn_a), .bridge_n_out_data(brn_d),
        .bridge_n_in_valid(tie_v), .bridge_n_in_addr(tie_a), .bridge_n_in_data(tie_d),
        .bridge_s_out_valid(), .bridge_s_out_addr(), .bridge_s_out_data(),
        .bridge_s_in_valid(tie_v), .bridge_s_in_addr(tie_a), .bridge_s_in_data(tie_d),
        .bridge_e_out_valid(bre_v), .bridge_e_out_addr(bre_a), .bridge_e_out_data(bre_d),
        .bridge_e_in_valid(tie_v), .bridge_e_in_addr(tie_a), .bridge_e_in_data(tie_d),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(tie_v), .bridge_w_in_addr(tie_a), .bridge_w_in_data(tie_d)
    );

    integer errors=0;
    task check1; input got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (%b)", msg, got);
        else begin $display("  FAIL: %0s got=%b want=%b", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_BOOT_COMMIT     = 8'd7;
    localparam [7:0] OP_RECONFIGURE     = 8'd4;
    localparam [7:0] OP_SET_ROUTE_LATCH = 8'd37;
    localparam [7:0] OP_SWAP_AB         = 8'd18;

    reg saw_bridge_n, saw_bridge_e, saw_local_bus;

    task boot_cell; begin
        @(negedge clk); cmd_bus={8'h0,OP_BOOT_COMMIT}; cmd_data=32'h0000_0000; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // topology=PASS_B(0x02C) + start_flag(armed) + latch_in, output_set=1.
    // No auth targeting needed: auth_mask stays 0 after boot (BOOT_COMMIT
    // above stored cmd_data[23:16]=0), so auth_boot stays true -- these are
    // plain broadcast opcodes (auth_ok-gated only, no config_match), the
    // same reason tb_v3_cardinal_edge.v's simpler cases needed no address
    // targeting either.
    task config_topology; begin
        @(negedge clk); cmd_bus={8'h0,OP_RECONFIGURE}; cmd_data=32'h0002082C; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Whole routing latch in one word: routing_mask=N|E(5), cardinal_edge=0
    // (all local), pattern_low=E-only(4), pattern_equal=N-only(1),
    // pattern_high=N|E(5), dynamic_route_en=1.
    task config_route_latch; begin
        @(negedge clk); cmd_bus={8'h0,OP_SET_ROUTE_LATCH};
        cmd_data = (32'd5)          // [5:0]   routing_mask
                 | (32'd0   << 6)   // [11:6]  cardinal_edge
                 | (32'd4   << 12)  // [17:12] pattern_low
                 | (32'd1   << 18)  // [23:18] pattern_equal
                 | (32'd5   << 24)  // [29:24] pattern_high
                 | (32'd1   << 30); // [30]    dynamic_route_en
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Re-prime the threshold: a_data <= thresh, a_arrived <= 1. Independent
    // of whatever latch_in did on the previous fire -- makes each of the
    // three comparator cases start from the same known threshold.
    task prime_threshold; input [12:0] thresh; begin
        @(negedge clk); cmd_bus={8'h0,OP_SWAP_AB}; cmd_data={19'h0, thresh}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task inject_and_watch; input [31:0] value; begin
        saw_bridge_n=1'b0; saw_bridge_e=1'b0; saw_local_bus=1'b0;
        @(negedge clk); inj_addr=16'h0000; inj_data=value; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
        begin : watch
            integer k;
            for (k=0;k<20;k=k+1) begin
                if (brn_v) saw_bridge_n=1'b1;
                if (bre_v) saw_bridge_e=1'b1;
                if (k>=2 && zone.cells.bus_valid) saw_local_bus=1'b1;
                @(posedge clk); #1;
            end
        end
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== COMPARATOR + DYNAMIC ROUTING LATCH (points.md #49/#51) ===");

        // ---- Case LOW: incoming 0x10 < threshold 0x50 -> pattern_low (E-only) ----
        boot_cell; config_topology; config_route_latch;
        prime_threshold(13'h050);
        inject_and_watch(32'h0000_0010);
        $display("  [LOW  0x10<0x50] bridge_n=%b bridge_e=%b local=%b", saw_bridge_n, saw_bridge_e, saw_local_bus);
        check1(saw_bridge_n,  1'b0, "LOW: north did NOT fire (pattern_low=E-only)");
        check1(saw_bridge_e,  1'b1, "LOW: east fired (pattern_low=E-only)");
        check1(saw_local_bus, 1'b1, "LOW: local bus fires (cardinal_edge=all-local)");

        // ---- Case EQUAL: incoming 0x50 == threshold 0x50 -> pattern_equal (N-only) ----
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        boot_cell; config_topology; config_route_latch;
        prime_threshold(13'h050);
        inject_and_watch(32'h0000_0050);
        $display("  [EQ   0x50=0x50] bridge_n=%b bridge_e=%b local=%b", saw_bridge_n, saw_bridge_e, saw_local_bus);
        check1(saw_bridge_n,  1'b1, "EQUAL: north fired (pattern_equal=N-only)");
        check1(saw_bridge_e,  1'b0, "EQUAL: east did NOT fire (pattern_equal=N-only)");
        check1(saw_local_bus, 1'b1, "EQUAL: local bus fires");

        // ---- Case HIGH: incoming 0x90 > threshold 0x50 -> pattern_high (N|E) ----
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        boot_cell; config_topology; config_route_latch;
        prime_threshold(13'h050);
        inject_and_watch(32'h0000_0090);
        $display("  [HIGH 0x90>0x50] bridge_n=%b bridge_e=%b local=%b", saw_bridge_n, saw_bridge_e, saw_local_bus);
        check1(saw_bridge_n,  1'b1, "HIGH: north fired (pattern_high=N|E)");
        check1(saw_bridge_e,  1'b1, "HIGH: east fired (pattern_high=N|E)");
        check1(saw_local_bus, 1'b1, "HIGH: local bus fires");

        if (errors==0) $display(">>> ROUTE_LATCH PASS: same static config, three different injected values took three genuinely different routes");
        else           $display(">>> ROUTE_LATCH FAIL: %0d errors", errors);
        $finish;
    end
endmodule
