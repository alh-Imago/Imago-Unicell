// tb_v3_rearm_hazard.v — reproduces the back-to-back-rearm hazard confirmed
// on real Arria 10 silicon (points.md #59 follow-up, 2026-07-30): with
// latch_in=1 and NO reset between cases, re-priming the threshold via
// CMD_SWAP_AB before each injection corrupts specifically the EQUAL case
// (extra spurious east bit -- the comparator selects pattern_high instead
// of pattern_equal). Confirmed on silicon with the EXACT same signature
// this test is built to reproduce. Traces a_data/a_arrived every cycle
// around each SWAP_AB + inject pair to find the actual mechanism instead
// of guessing at it.
//
// Same static config as tb_v3_route_latch.v (routing_mask=N|E,
// cardinal_edge=all-local, patterns low=E-only/equal=N-only/high=N|E,
// dynamic_route_en=1), topology=PASS_B+armed+LATCH_IN (this is the
// deliberate difference from the CLEAN version of tb_v3_route_latch.v,
// which never hit this because each case there got a fresh reset).
`timescale 1ns/1ps
module tb_v3_rearm_hazard;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire        brn_v; wire [15:0] brn_a; wire [31:0] brn_d;
    wire        bre_v; wire [15:0] bre_a; wire [31:0] bre_d;
    wire tie_v = 1'b0; wire [15:0] tie_a = 16'h0; wire [31:0] tie_d = 32'h0;
    wire [15:0] z_out_addr; wire [31:0] z_out_data; wire z_out_valid;
    wire [15:0] z_emit;

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

    localparam [7:0] OP_BOOT_COMMIT     = 8'd7;
    localparam [7:0] OP_RECONFIGURE     = 8'd4;
    localparam [7:0] OP_SET_ROUTE_LATCH = 8'd37;
    localparam [7:0] OP_SWAP_AB         = 8'd18;

    task boot_cell; begin
        @(negedge clk); cmd_bus={8'h0,OP_BOOT_COMMIT}; cmd_data=32'h0; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // topology=PASS_B + start_flag(armed) + LATCH_IN + output_set -- LATCH_IN
    // is the one deliberate difference from the clean version of
    // tb_v3_route_latch.v (which never sets it, since each case there gets
    // its own fresh reset+reboot). Real silicon's zone1_route_latch.tcl
    // (no reset between cases) needs latch_in to stay armed across cases at
    // all -- otherwise a single-shot cell would need SWAP_AB to also
    // re-arm it, which it already does (a_arrived<=1'b1 unconditionally).
    // latch_in itself, per cmd_data[17], bit position confirmed from
    // CMD_RECONFIGURE's field map.
    task config_topology_latchin; begin
        @(negedge clk); cmd_bus={8'h0,OP_RECONFIGURE};
        cmd_data = 32'h0002_082C; cmd_valid=1'b1;  // PASS_B, start_flag(11), latch_in(17)
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task config_route_latch; begin
        @(negedge clk); cmd_bus={8'h0,OP_SET_ROUTE_LATCH};
        cmd_data = (32'd5) | (32'd0<<6) | (32'd4<<12) | (32'd1<<18) | (32'd5<<24) | (32'd1<<30);
        cmd_valid=1'b1; @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task prime_threshold; input [12:0] thresh; begin
        @(negedge clk); cmd_bus={8'h0,OP_SWAP_AB}; cmd_data={19'h0, thresh}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task inject; input [31:0] value; begin
        @(negedge clk); inj_addr=16'h0000; inj_data=value; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
    end endtask

    // Per-cycle trace of the exact signals the comparator reads, plus the
    // derived comparator result and effective_routing, for N cycles.
    task trace_cycles; input integer n; input [255:0] label; begin
        integer k;
        for (k=0;k<n;k=k+1) begin
            $display("    [%0s k=%0d] a_data=0x%08h a_arrived=%b bus_data_r=0x%08h bus_valid_r=%b bus_hit=%b new_data=%b effective_routing=0x%02h transit_only=%b bre_v=%b brn_v=%b",
                label, k,
                zone.cells.cell_array[0].cell_inst.a_data,
                zone.cells.cell_array[0].cell_inst.a_arrived,
                zone.cells.cell_array[0].cell_inst.bus_data_r,
                zone.cells.cell_array[0].cell_inst.bus_valid_r,
                zone.cells.cell_array[0].cell_inst.bus_hit,
                zone.cells.cell_array[0].cell_inst.new_data,
                zone.cells.cell_array[0].cell_inst.effective_routing,
                zone.cells.cell_array[0].cell_inst.transit_only,
                bre_v, brn_v);
            @(posedge clk); #1;
        end
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== REARM HAZARD REPRODUCTION: no reset between cases, latch_in=1 (matches silicon zone1_route_latch.tcl) ===");

        boot_cell;
        config_topology_latchin;
        config_route_latch;

        $display("--- CASE LOW (0x10 < 0x50) ---");
        prime_threshold(13'h050);
        trace_cycles(3, "pre-inject");
        inject(32'h0000_0010);
        trace_cycles(8, "post-inject");

        $display("--- CASE EQUAL (0x50 == 0x50) ---");
        prime_threshold(13'h050);
        trace_cycles(3, "pre-inject");
        inject(32'h0000_0050);
        trace_cycles(8, "post-inject");

        $display("--- CASE HIGH (0x90 > 0x50) ---");
        prime_threshold(13'h050);
        trace_cycles(3, "pre-inject");
        inject(32'h0000_0090);
        trace_cycles(8, "post-inject");

        $display(">>> trace complete");
        $finish;
    end
endmodule
