// tb_v3_transit.v — verifies the TRANSIT primitive (2026-07-07, points.md #18).
//
// The two-axis routing model:
//   routing_mask = WHERE a fire goes (N/S/E/W bridge directions)
//   transit_only = WHETHER the local cluster is included
//     0 (default) -> present on local bus AND route across if masked
//     1           -> route across ONLY; do NOT present on the local cluster bus
//
// This test proves the transit==1 case at the substrate level, directly on one
// zone (unicell_zone64_v3): a cell configured PASS_B + armed + routing_mask=E
// + transit_only=1 must:
//   (A) assert its EAST bridge output (the value crosses), AND
//   (B) NOT drive its own zone's local data bus (bus_valid stays low for it).
//
// Then a CONTROL run with transit_only=0 (same cell, same routing) must drive
// BOTH the east bridge AND the local bus -- proving the flag is what gates the
// local path, not some unrelated effect.
`timescale 1ns/1ps
module tb_v3_transit;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    // Zone under test. NUM_CELLS small; we only use cell 0.
    wire [15:0] z_out_addr; wire [31:0] z_out_data; wire z_out_valid;
    wire [15:0] z_emit;

    // Bridge east out (what we watch for the cross-boundary hop)
    wire        bre_v; wire [15:0] bre_a; wire [31:0] bre_d;
    // tie-offs for unused bridge inputs
    wire tie_v = 1'b0; wire [15:0] tie_a = 16'h0; wire [31:0] tie_d = 32'h0;

    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(0)) zone (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(inj_addr), .cpu_data(inj_data), .cpu_valid(inj_valid),
        .out_addr(z_out_addr), .out_data(z_out_data), .out_valid(z_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(), .bridge_n_out_addr(), .bridge_n_out_data(),
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

    localparam [7:0] OP_LOAD_AT       = 8'd23;
    localparam [7:0] METH_SET_ROUTING = 8'd34;
    localparam [7:0] METH_SET_TRANSIT = 8'd35;

    // Observe over a window: did the east bridge fire? did the LOCAL bus fire
    // (for a value that isn't a command)? Watch zone.cells.bus_valid directly.
    reg saw_bridge_e; reg saw_local_bus;
    reg [31:0] bridge_e_data_seen;

    task boot_cell;  // topology=PASS_B, boot into RUN
        begin
            @(negedge clk); cmd_bus={8'h0,8'd7}; cmd_data=32'h0000_0000; cmd_valid=1'b1;
            @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
        end
    endtask

    // Configure cell0: PASS_B + start_flag(armed) + latch_in, routing_mask=E,
    // and transit_only per the argument. Uses LOAD_AT (slot A) with bank-2
    // methodology in two steps: one LOAD_AT carrying METH_SET_ROUTING, one
    // carrying METH_SET_TRANSIT. Topology/arm/latch set on the first.
    task config_cell; input transit_bit; begin
        // Step 1: LOAD_AT + bank2 METH_SET_ROUTING(payload E=bit2 -> 4'b0100=4).
        // cmd_bus: bit16=1 (bank2 valid), [15:8]=METH_SET_ROUTING(34=0x22), [7:0]=LOAD_AT(23=0x17)
        // cmd_data: bit11=start_flag, bit17=latch_in, [9:0]=PASS_B(0x02C),
        //           [26:23]=routing payload = 4 (E). 4<<23 = 0x0200_0000.
        @(negedge clk);
        cmd_bus  = 32'h0001_2217;
        cmd_data = 32'h0202_082C | (32'd4 << 23); // start+latch+PASS_B + routing E
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;

        // Step 2: LOAD_AT + bank2 METH_SET_TRANSIT(payload = transit_bit at cmd_data[23]).
        // cmd_bus: bit16=1, [15:8]=METH_SET_TRANSIT(35=0x23), [7:0]=LOAD_AT(0x17)
        @(negedge clk);
        cmd_bus  = 32'h0001_2317;
        cmd_data = 32'h0202_082C | (32'd4 << 23) | (transit_bit << 23 << 0);
        // NOTE: transit payload is cmd_data[23]; routing already latched, so we
        // just need bit23 = transit_bit. Rebuild cleanly to avoid overlap:
        cmd_data = (32'd4 << 23) | (transit_bit ? (32'h1<<23) : 32'h0) | 32'h0000_082C | (32'h1<<11) | (32'h1<<17);
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Fire mechanism (proven pattern from tb_v3_shl_cell): CMD_SWAP_AB primes
    // a_arrived, then a single real value delivered to the cell's input_address
    // (default = CELL_ID = 0) triggers the fire. In a zone, the local bus is
    // internal, so we inject through the zone's cpu_* port (a data write to
    // address 0). We reg-drive cpu_* by adding them to the instantiation.
    task prime_and_watch; begin
        saw_bridge_e=1'b0; saw_local_bus=1'b0; bridge_e_data_seen=32'h0;
        // Prime: CMD_SWAP_AB to cell 0 sets a_arrived
        @(negedge clk); cmd_bus={8'h0,8'd18}; cmd_data=32'h0000_0000; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
        // Fire: inject value 0xF0 to address 0 via cpu port
        @(negedge clk); inj_addr=16'h0000; inj_data=32'h0000_00F0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
        // watch for the fire and its effects
        begin : watch
            integer k;
            for (k=0;k<20;k=k+1) begin
                if (bre_v) begin saw_bridge_e=1'b1; bridge_e_data_seen=bre_d; end
                // local bus carries THIS cell's fire: bus_valid high with the
                // fired value's address (out_addr default CELL_ID+1 = 1), not
                // the inject we just did. Watch after the inject settles.
                if (k>=2 && zone.cells.bus_valid) saw_local_bus=1'b1;
                @(posedge clk); #1;
            end
        end
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== TRANSIT PRIMITIVE: route-across-only vs route-and-local ===");

        // ---- Run 1: transit_only = 1 (route across only) ----
        boot_cell;
        config_cell(1'b1);
        prime_and_watch;
        $display("  [transit=1] saw_bridge_e=%b saw_local_bus=%b", saw_bridge_e, saw_local_bus);
        check1(saw_bridge_e, 1'b1, "transit=1: value crossed the EAST bridge");
        check1(saw_local_bus, 1'b0, "transit=1: local cluster bus NOT driven (suppressed)");

        // ---- Run 2: transit_only = 0 (route AND local) ----
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        boot_cell;
        config_cell(1'b0);
        prime_and_watch;
        $display("  [transit=0] saw_bridge_e=%b saw_local_bus=%b", saw_bridge_e, saw_local_bus);
        check1(saw_bridge_e, 1'b1, "transit=0: value crossed the EAST bridge");
        check1(saw_local_bus, 1'b1, "transit=0: local cluster bus ALSO driven (control)");

        if (errors==0) $display(">>> TRANSIT PASS: route-only suppresses local, control drives both");
        else           $display(">>> TRANSIT FAIL: %0d errors", errors);
        $finish;
    end
endmodule
