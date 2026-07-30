// tb_v3_cardinal_edge.v — verifies the PER-EDGE cardinal_edge primitive
// (points.md #42, 2026-07-30), the genuine capability the old single global
// transit_only bit could not express.
//
// Cell routes to TWO directions at once (routing_mask = N|E). The new
// cardinal_edge[3:0] field lets each of those directions independently
// decide whether it's cardinal-only (no local join) or still allows the
// fire to also present on the local cluster bus.
//
//   Run 1 (the new case): cardinal_edge = E-only (bit2=1, bit0=0).
//     E is cardinal-only; N is NOT. Expect: EAST bridge fires, NORTH bridge
//     fires, AND the local bus STILL fires (because N, one of the active
//     routing directions, doesn't want cardinal-only). This is exactly the
//     "pure conduit on some edges, still a normal local participant through
//     others" case the old global bit structurally could not produce --
//     with one bit, transit_only=1 would have suppressed local for BOTH
//     active directions at once, transit_only=0 would have suppressed
//     local for NEITHER. Neither setting of the old bit can reproduce
//     "cardinal-only on E, local-joining on N" simultaneously.
//
//   Run 2 (continuity control): cardinal_edge = N|E (both bits set) --
//     every active routing direction marked cardinal-only. Expect: both
//     bridges fire, local bus suppressed -- the legacy transit_only=1
//     result, now reached via the granular field instead of the single
//     global bit (tb_v3_transit.v already proves METH_SET_TRANSIT's
//     legacy-convenience path separately; this run proves the underlying
//     derived-transit_only logic collapses correctly when all active
//     edges agree, not just when only one edge is active).
`timescale 1ns/1ps
module tb_v3_cardinal_edge;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire [15:0] z_out_addr; wire [31:0] z_out_data; wire z_out_valid;
    wire [15:0] z_emit;

    // Bridge N and E out -- both real this time (two simultaneous active
    // routing directions is the point of this test).
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

    localparam [7:0] OP_LOAD_AT             = 8'd23;
    localparam [7:0] METH_SET_ROUTING       = 8'd34;
    localparam [7:0] METH_SET_CARDINAL_EDGE = 8'd36;

    reg saw_bridge_n, saw_bridge_e, saw_local_bus;

    task boot_cell;  // topology=PASS_B, boot into RUN
        begin
            @(negedge clk); cmd_bus={8'h0,8'd7}; cmd_data=32'h0000_0000; cmd_valid=1'b1;
            @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
        end
    endtask

    // Configure cell0: PASS_B + start_flag(armed) + latch_in, routing_mask=N|E
    // (bit0=N=1, bit2=E=4 -> 5), cardinal_edge per the argument. Same two-step
    // LOAD_AT + bank-2 methodology pattern as tb_v3_transit.v: one LOAD_AT
    // carrying METH_SET_ROUTING, one carrying METH_SET_CARDINAL_EDGE.
    task config_cell; input [3:0] cardinal_val; begin
        // Step 1: LOAD_AT + bank2 METH_SET_ROUTING(payload N|E = 5).
        // cmd_bus: bit16=1 (bank2 valid), [15:8]=METH_SET_ROUTING(34=0x22), [7:0]=LOAD_AT(23=0x17)
        // cmd_data: bit11=start_flag, bit17=latch_in, [9:0]=PASS_B(0x02C),
        //           [26:23]=routing payload = 5 (N|E). 5<<23.
        @(negedge clk);
        cmd_bus  = 32'h0001_2217;
        cmd_data = 32'h0000_082C | (32'h1<<11) | (32'h1<<17) | (32'd5 << 23);
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;

        // Step 2: LOAD_AT + bank2 METH_SET_CARDINAL_EDGE(payload = cardinal_val).
        // cmd_bus: bit16=1, [15:8]=METH_SET_CARDINAL_EDGE(36=0x24), [7:0]=LOAD_AT(0x17)
        @(negedge clk);
        cmd_bus  = 32'h0001_2417;
        cmd_data = 32'h0000_082C | (32'h1<<11) | (32'h1<<17) | (cardinal_val << 23);
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Fire mechanism (same proven pattern as tb_v3_transit.v): CMD_SWAP_AB
    // primes a_arrived, then a real value delivered to the cell's
    // input_address (default = CELL_ID = 0) triggers the fire.
    task prime_and_watch; begin
        saw_bridge_n=1'b0; saw_bridge_e=1'b0; saw_local_bus=1'b0;
        @(negedge clk); cmd_bus={8'h0,8'd18}; cmd_data=32'h0000_0000; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
        @(negedge clk); inj_addr=16'h0000; inj_data=32'h0000_00F0; inj_valid=1'b1;
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
        $display("=== CARDINAL_EDGE PRIMITIVE: per-direction local-vs-cardinal-only (points.md #42) ===");

        // ---- Run 1: cardinal_edge = E-only (bit2=1,bit0=0 -> 4'b0100=4) ----
        // E is cardinal-only; N is not -- local should STILL present because
        // N (one of the two active routing directions) doesn't want cardinal-only.
        boot_cell;
        config_cell(4'b0100);
        prime_and_watch;
        $display("  [cardinal=E-only] bridge_n=%b bridge_e=%b local_bus=%b", saw_bridge_n, saw_bridge_e, saw_local_bus);
        check1(saw_bridge_n,  1'b1, "N: value crossed the NORTH bridge");
        check1(saw_bridge_e,  1'b1, "E: value crossed the EAST bridge");
        check1(saw_local_bus, 1'b1, "local cluster bus STILL driven (N keeps it, E alone can't suppress)");

        // ---- Run 2: cardinal_edge = N|E (both cardinal-only -> legacy result) ----
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        boot_cell;
        config_cell(4'b0101);
        prime_and_watch;
        $display("  [cardinal=N|E]    bridge_n=%b bridge_e=%b local_bus=%b", saw_bridge_n, saw_bridge_e, saw_local_bus);
        check1(saw_bridge_n,  1'b1, "N: value crossed the NORTH bridge");
        check1(saw_bridge_e,  1'b1, "E: value crossed the EAST bridge");
        check1(saw_local_bus, 1'b0, "local cluster bus suppressed (every active edge cardinal-only)");

        if (errors==0) $display(">>> CARDINAL_EDGE PASS: per-edge granularity proven -- one active edge can stay local while another goes cardinal-only on the SAME fire");
        else           $display(">>> CARDINAL_EDGE FAIL: %0d errors", errors);
        $finish;
    end
endmodule
