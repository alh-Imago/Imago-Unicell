// STALE (2026-07-06): generated against the OLD zone-parameter routing
// (N_ZONE/N_ACTIVE etc.), which unicell_zone64_v3.v no longer has -- routing
// moved to per-cell routing_mask (see points.md #4). This file will NOT
// compile until the adder's placement/config generation is redone to use
// routing_mask instead of the shared-address relay-chain approach. Left in
// place as reference for that next step, not as working code.

// AUTO-GENERATED: 18 cluster instances + address-decoded bridge wiring.

    wire        z0_out_valid; wire [15:0] z0_out_addr; wire [31:0] z0_out_data; wire [15:0] z0_emit;
    wire        z1_out_valid; wire [15:0] z1_out_addr; wire [31:0] z1_out_data; wire [15:0] z1_emit;
    wire        z2_out_valid; wire [15:0] z2_out_addr; wire [31:0] z2_out_data; wire [15:0] z2_emit;
    wire        z3_out_valid; wire [15:0] z3_out_addr; wire [31:0] z3_out_data; wire [15:0] z3_emit;
    wire        z4_out_valid; wire [15:0] z4_out_addr; wire [31:0] z4_out_data; wire [15:0] z4_emit;
    wire        z5_out_valid; wire [15:0] z5_out_addr; wire [31:0] z5_out_data; wire [15:0] z5_emit;
    wire        z6_out_valid; wire [15:0] z6_out_addr; wire [31:0] z6_out_data; wire [15:0] z6_emit;
    wire        z7_out_valid; wire [15:0] z7_out_addr; wire [31:0] z7_out_data; wire [15:0] z7_emit;
    wire        z8_out_valid; wire [15:0] z8_out_addr; wire [31:0] z8_out_data; wire [15:0] z8_emit;
    wire        z9_out_valid; wire [15:0] z9_out_addr; wire [31:0] z9_out_data; wire [15:0] z9_emit;
    wire        z10_out_valid; wire [15:0] z10_out_addr; wire [31:0] z10_out_data; wire [15:0] z10_emit;
    wire        z11_out_valid; wire [15:0] z11_out_addr; wire [31:0] z11_out_data; wire [15:0] z11_emit;
    wire        z12_out_valid; wire [15:0] z12_out_addr; wire [31:0] z12_out_data; wire [15:0] z12_emit;
    wire        z13_out_valid; wire [15:0] z13_out_addr; wire [31:0] z13_out_data; wire [15:0] z13_emit;
    wire        z14_out_valid; wire [15:0] z14_out_addr; wire [31:0] z14_out_data; wire [15:0] z14_emit;
    wire        z15_out_valid; wire [15:0] z15_out_addr; wire [31:0] z15_out_data; wire [15:0] z15_emit;
    wire        z16_out_valid; wire [15:0] z16_out_addr; wire [31:0] z16_out_data; wire [15:0] z16_emit;
    wire        z17_out_valid; wire [15:0] z17_out_addr; wire [31:0] z17_out_data; wire [15:0] z17_emit;
    wire        br_0_e_out_valid;
    wire [15:0] br_0_e_out_addr;
    wire [31:0] br_0_e_out_data;
    wire        br_0_n_out_valid;
    wire [15:0] br_0_n_out_addr;
    wire [31:0] br_0_n_out_data;
    wire        br_0_s_out_valid;
    wire [15:0] br_0_s_out_addr;
    wire [31:0] br_0_s_out_data;
    wire        br_0_w_out_valid;
    wire [15:0] br_0_w_out_addr;
    wire [31:0] br_0_w_out_data;
    wire        br_1_n_out_valid;
    wire [15:0] br_1_n_out_addr;
    wire [31:0] br_1_n_out_data;
    wire        br_1_s_out_valid;
    wire [15:0] br_1_s_out_addr;
    wire [31:0] br_1_s_out_data;
    wire        br_2_e_out_valid;
    wire [15:0] br_2_e_out_addr;
    wire [31:0] br_2_e_out_data;
    wire        br_2_n_out_valid;
    wire [15:0] br_2_n_out_addr;
    wire [31:0] br_2_n_out_data;
    wire        br_2_s_out_valid;
    wire [15:0] br_2_s_out_addr;
    wire [31:0] br_2_s_out_data;
    wire        br_3_e_out_valid;
    wire [15:0] br_3_e_out_addr;
    wire [31:0] br_3_e_out_data;
    wire        br_3_n_out_valid;
    wire [15:0] br_3_n_out_addr;
    wire [31:0] br_3_n_out_data;
    wire        br_3_s_out_valid;
    wire [15:0] br_3_s_out_addr;
    wire [31:0] br_3_s_out_data;
    wire        br_4_n_out_valid;
    wire [15:0] br_4_n_out_addr;
    wire [31:0] br_4_n_out_data;
    wire        br_4_s_out_valid;
    wire [15:0] br_4_s_out_addr;
    wire [31:0] br_4_s_out_data;
    wire        br_5_e_out_valid;
    wire [15:0] br_5_e_out_addr;
    wire [31:0] br_5_e_out_data;
    wire        br_5_n_out_valid;
    wire [15:0] br_5_n_out_addr;
    wire [31:0] br_5_n_out_data;
    wire        br_5_s_out_valid;
    wire [15:0] br_5_s_out_addr;
    wire [31:0] br_5_s_out_data;
    wire        br_6_e_out_valid;
    wire [15:0] br_6_e_out_addr;
    wire [31:0] br_6_e_out_data;
    wire        br_6_n_out_valid;
    wire [15:0] br_6_n_out_addr;
    wire [31:0] br_6_n_out_data;
    wire        br_6_s_out_valid;
    wire [15:0] br_6_s_out_addr;
    wire [31:0] br_6_s_out_data;
    wire        br_7_n_out_valid;
    wire [15:0] br_7_n_out_addr;
    wire [31:0] br_7_n_out_data;
    wire        br_7_s_out_valid;
    wire [15:0] br_7_s_out_addr;
    wire [31:0] br_7_s_out_data;
    wire        br_8_e_out_valid;
    wire [15:0] br_8_e_out_addr;
    wire [31:0] br_8_e_out_data;
    wire        br_8_n_out_valid;
    wire [15:0] br_8_n_out_addr;
    wire [31:0] br_8_n_out_data;
    wire        br_8_s_out_valid;
    wire [15:0] br_8_s_out_addr;
    wire [31:0] br_8_s_out_data;
    wire        br_9_n_out_valid;
    wire [15:0] br_9_n_out_addr;
    wire [31:0] br_9_n_out_data;
    wire        br_9_s_out_valid;
    wire [15:0] br_9_s_out_addr;
    wire [31:0] br_9_s_out_data;
    wire        br_10_n_out_valid;
    wire [15:0] br_10_n_out_addr;
    wire [31:0] br_10_n_out_data;
    wire        br_10_s_out_valid;
    wire [15:0] br_10_s_out_addr;
    wire [31:0] br_10_s_out_data;
    wire        br_11_e_out_valid;
    wire [15:0] br_11_e_out_addr;
    wire [31:0] br_11_e_out_data;
    wire        br_11_n_out_valid;
    wire [15:0] br_11_n_out_addr;
    wire [31:0] br_11_n_out_data;
    wire        br_11_s_out_valid;
    wire [15:0] br_11_s_out_addr;
    wire [31:0] br_11_s_out_data;
    wire        br_12_e_out_valid;
    wire [15:0] br_12_e_out_addr;
    wire [31:0] br_12_e_out_data;
    wire        br_12_n_out_valid;
    wire [15:0] br_12_n_out_addr;
    wire [31:0] br_12_n_out_data;
    wire        br_12_s_out_valid;
    wire [15:0] br_12_s_out_addr;
    wire [31:0] br_12_s_out_data;
    wire        br_13_e_out_valid;
    wire [15:0] br_13_e_out_addr;
    wire [31:0] br_13_e_out_data;
    wire        br_13_n_out_valid;
    wire [15:0] br_13_n_out_addr;
    wire [31:0] br_13_n_out_data;
    wire        br_13_s_out_valid;
    wire [15:0] br_13_s_out_addr;
    wire [31:0] br_13_s_out_data;
    wire        br_14_n_out_valid;
    wire [15:0] br_14_n_out_addr;
    wire [31:0] br_14_n_out_data;
    wire        br_14_s_out_valid;
    wire [15:0] br_14_s_out_addr;
    wire [31:0] br_14_s_out_data;
    wire        br_15_e_out_valid;
    wire [15:0] br_15_e_out_addr;
    wire [31:0] br_15_e_out_data;
    wire        br_15_n_out_valid;
    wire [15:0] br_15_n_out_addr;
    wire [31:0] br_15_n_out_data;
    wire        br_15_s_out_valid;
    wire [15:0] br_15_s_out_addr;
    wire [31:0] br_15_s_out_data;
    wire        br_16_n_out_valid;
    wire [15:0] br_16_n_out_addr;
    wire [31:0] br_16_n_out_data;
    wire        br_16_s_out_valid;
    wire [15:0] br_16_s_out_addr;
    wire [31:0] br_16_s_out_data;
    wire        br_17_e_out_valid;
    wire [15:0] br_17_e_out_addr;
    wire [31:0] br_17_e_out_data;
    wire        br_17_n_out_valid;
    wire [15:0] br_17_n_out_addr;
    wire [31:0] br_17_n_out_data;
    wire        br_17_s_out_valid;
    wire [15:0] br_17_s_out_addr;
    wire [31:0] br_17_s_out_data;

    // ── cluster 0 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(0),
        .N_ZONE(1), .N_ACTIVE(1'b1), .S_ZONE(2), .S_ACTIVE(1'b1), .E_ZONE(9), .E_ACTIVE(1'b1), .W_ZONE(11), .W_ACTIVE(1'b1)
    ) cluster0 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z0_out_addr), .out_data(z0_out_data), .out_valid(z0_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z0_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_0_n_out_valid), .bridge_n_out_addr(br_0_n_out_addr), .bridge_n_out_data(br_0_n_out_data),
        .bridge_n_in_valid(br_1_n_out_valid), .bridge_n_in_addr(br_1_n_out_addr), .bridge_n_in_data(br_1_n_out_data),
        .bridge_s_out_valid(br_0_s_out_valid), .bridge_s_out_addr(br_0_s_out_addr), .bridge_s_out_data(br_0_s_out_data),
        .bridge_s_in_valid(br_2_n_out_valid), .bridge_s_in_addr(br_2_n_out_addr), .bridge_s_in_data(br_2_n_out_data),
        .bridge_e_out_valid(br_0_e_out_valid), .bridge_e_out_addr(br_0_e_out_addr), .bridge_e_out_data(br_0_e_out_data),
        .bridge_e_in_valid(br_9_n_out_valid), .bridge_e_in_addr(br_9_n_out_addr), .bridge_e_in_data(br_9_n_out_data),
        .bridge_w_out_valid(br_0_w_out_valid), .bridge_w_out_addr(br_0_w_out_addr), .bridge_w_out_data(br_0_w_out_data),
        .bridge_w_in_valid(br_11_n_out_valid), .bridge_w_in_addr(br_11_n_out_addr), .bridge_w_in_data(br_11_n_out_data)
    );

    // ── cluster 1 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(1),
        .N_ZONE(0), .N_ACTIVE(1'b1), .S_ZONE(2), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster1 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z1_out_addr), .out_data(z1_out_data), .out_valid(z1_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z1_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_1_n_out_valid), .bridge_n_out_addr(br_1_n_out_addr), .bridge_n_out_data(br_1_n_out_data),
        .bridge_n_in_valid(br_0_n_out_valid), .bridge_n_in_addr(br_0_n_out_addr), .bridge_n_in_data(br_0_n_out_data),
        .bridge_s_out_valid(br_1_s_out_valid), .bridge_s_out_addr(br_1_s_out_addr), .bridge_s_out_data(br_1_s_out_data),
        .bridge_s_in_valid(br_2_s_out_valid), .bridge_s_in_addr(br_2_s_out_addr), .bridge_s_in_data(br_2_s_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 2 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(2),
        .N_ZONE(0), .N_ACTIVE(1'b1), .S_ZONE(1), .S_ACTIVE(1'b1), .E_ZONE(3), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster2 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z2_out_addr), .out_data(z2_out_data), .out_valid(z2_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z2_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_2_n_out_valid), .bridge_n_out_addr(br_2_n_out_addr), .bridge_n_out_data(br_2_n_out_data),
        .bridge_n_in_valid(br_0_s_out_valid), .bridge_n_in_addr(br_0_s_out_addr), .bridge_n_in_data(br_0_s_out_data),
        .bridge_s_out_valid(br_2_s_out_valid), .bridge_s_out_addr(br_2_s_out_addr), .bridge_s_out_data(br_2_s_out_data),
        .bridge_s_in_valid(br_1_s_out_valid), .bridge_s_in_addr(br_1_s_out_addr), .bridge_s_in_data(br_1_s_out_data),
        .bridge_e_out_valid(br_2_e_out_valid), .bridge_e_out_addr(br_2_e_out_addr), .bridge_e_out_data(br_2_e_out_data),
        .bridge_e_in_valid(br_3_n_out_valid), .bridge_e_in_addr(br_3_n_out_addr), .bridge_e_in_data(br_3_n_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 3 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(3),
        .N_ZONE(2), .N_ACTIVE(1'b1), .S_ZONE(4), .S_ACTIVE(1'b1), .E_ZONE(13), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster3 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z3_out_addr), .out_data(z3_out_data), .out_valid(z3_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z3_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_3_n_out_valid), .bridge_n_out_addr(br_3_n_out_addr), .bridge_n_out_data(br_3_n_out_data),
        .bridge_n_in_valid(br_2_e_out_valid), .bridge_n_in_addr(br_2_e_out_addr), .bridge_n_in_data(br_2_e_out_data),
        .bridge_s_out_valid(br_3_s_out_valid), .bridge_s_out_addr(br_3_s_out_addr), .bridge_s_out_data(br_3_s_out_data),
        .bridge_s_in_valid(br_4_n_out_valid), .bridge_s_in_addr(br_4_n_out_addr), .bridge_s_in_data(br_4_n_out_data),
        .bridge_e_out_valid(br_3_e_out_valid), .bridge_e_out_addr(br_3_e_out_addr), .bridge_e_out_data(br_3_e_out_data),
        .bridge_e_in_valid(br_13_n_out_valid), .bridge_e_in_addr(br_13_n_out_addr), .bridge_e_in_data(br_13_n_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 4 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(4),
        .N_ZONE(3), .N_ACTIVE(1'b1), .S_ZONE(5), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster4 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z4_out_addr), .out_data(z4_out_data), .out_valid(z4_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z4_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_4_n_out_valid), .bridge_n_out_addr(br_4_n_out_addr), .bridge_n_out_data(br_4_n_out_data),
        .bridge_n_in_valid(br_3_s_out_valid), .bridge_n_in_addr(br_3_s_out_addr), .bridge_n_in_data(br_3_s_out_data),
        .bridge_s_out_valid(br_4_s_out_valid), .bridge_s_out_addr(br_4_s_out_addr), .bridge_s_out_data(br_4_s_out_data),
        .bridge_s_in_valid(br_5_n_out_valid), .bridge_s_in_addr(br_5_n_out_addr), .bridge_s_in_data(br_5_n_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 5 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(5),
        .N_ZONE(4), .N_ACTIVE(1'b1), .S_ZONE(6), .S_ACTIVE(1'b1), .E_ZONE(15), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster5 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z5_out_addr), .out_data(z5_out_data), .out_valid(z5_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z5_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_5_n_out_valid), .bridge_n_out_addr(br_5_n_out_addr), .bridge_n_out_data(br_5_n_out_data),
        .bridge_n_in_valid(br_4_s_out_valid), .bridge_n_in_addr(br_4_s_out_addr), .bridge_n_in_data(br_4_s_out_data),
        .bridge_s_out_valid(br_5_s_out_valid), .bridge_s_out_addr(br_5_s_out_addr), .bridge_s_out_data(br_5_s_out_data),
        .bridge_s_in_valid(br_6_n_out_valid), .bridge_s_in_addr(br_6_n_out_addr), .bridge_s_in_data(br_6_n_out_data),
        .bridge_e_out_valid(br_5_e_out_valid), .bridge_e_out_addr(br_5_e_out_addr), .bridge_e_out_data(br_5_e_out_data),
        .bridge_e_in_valid(br_15_n_out_valid), .bridge_e_in_addr(br_15_n_out_addr), .bridge_e_in_data(br_15_n_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 6 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(6),
        .N_ZONE(5), .N_ACTIVE(1'b1), .S_ZONE(7), .S_ACTIVE(1'b1), .E_ZONE(17), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster6 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z6_out_addr), .out_data(z6_out_data), .out_valid(z6_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z6_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_6_n_out_valid), .bridge_n_out_addr(br_6_n_out_addr), .bridge_n_out_data(br_6_n_out_data),
        .bridge_n_in_valid(br_5_s_out_valid), .bridge_n_in_addr(br_5_s_out_addr), .bridge_n_in_data(br_5_s_out_data),
        .bridge_s_out_valid(br_6_s_out_valid), .bridge_s_out_addr(br_6_s_out_addr), .bridge_s_out_data(br_6_s_out_data),
        .bridge_s_in_valid(br_7_n_out_valid), .bridge_s_in_addr(br_7_n_out_addr), .bridge_s_in_data(br_7_n_out_data),
        .bridge_e_out_valid(br_6_e_out_valid), .bridge_e_out_addr(br_6_e_out_addr), .bridge_e_out_data(br_6_e_out_data),
        .bridge_e_in_valid(br_17_n_out_valid), .bridge_e_in_addr(br_17_n_out_addr), .bridge_e_in_data(br_17_n_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 7 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(7),
        .N_ZONE(6), .N_ACTIVE(1'b1), .S_ZONE(8), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster7 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z7_out_addr), .out_data(z7_out_data), .out_valid(z7_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z7_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_7_n_out_valid), .bridge_n_out_addr(br_7_n_out_addr), .bridge_n_out_data(br_7_n_out_data),
        .bridge_n_in_valid(br_6_s_out_valid), .bridge_n_in_addr(br_6_s_out_addr), .bridge_n_in_data(br_6_s_out_data),
        .bridge_s_out_valid(br_7_s_out_valid), .bridge_s_out_addr(br_7_s_out_addr), .bridge_s_out_data(br_7_s_out_data),
        .bridge_s_in_valid(br_8_n_out_valid), .bridge_s_in_addr(br_8_n_out_addr), .bridge_s_in_data(br_8_n_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 8 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(8),
        .N_ZONE(7), .N_ACTIVE(1'b1), .S_ZONE(9), .S_ACTIVE(1'b1), .E_ZONE(17), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster8 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z8_out_addr), .out_data(z8_out_data), .out_valid(z8_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z8_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_8_n_out_valid), .bridge_n_out_addr(br_8_n_out_addr), .bridge_n_out_data(br_8_n_out_data),
        .bridge_n_in_valid(br_7_s_out_valid), .bridge_n_in_addr(br_7_s_out_addr), .bridge_n_in_data(br_7_s_out_data),
        .bridge_s_out_valid(br_8_s_out_valid), .bridge_s_out_addr(br_8_s_out_addr), .bridge_s_out_data(br_8_s_out_data),
        .bridge_s_in_valid(br_9_s_out_valid), .bridge_s_in_addr(br_9_s_out_addr), .bridge_s_in_data(br_9_s_out_data),
        .bridge_e_out_valid(br_8_e_out_valid), .bridge_e_out_addr(br_8_e_out_addr), .bridge_e_out_data(br_8_e_out_data),
        .bridge_e_in_valid(br_17_s_out_valid), .bridge_e_in_addr(br_17_s_out_addr), .bridge_e_in_data(br_17_s_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 9 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(9),
        .N_ZONE(0), .N_ACTIVE(1'b1), .S_ZONE(8), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster9 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z9_out_addr), .out_data(z9_out_data), .out_valid(z9_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z9_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_9_n_out_valid), .bridge_n_out_addr(br_9_n_out_addr), .bridge_n_out_data(br_9_n_out_data),
        .bridge_n_in_valid(br_0_e_out_valid), .bridge_n_in_addr(br_0_e_out_addr), .bridge_n_in_data(br_0_e_out_data),
        .bridge_s_out_valid(br_9_s_out_valid), .bridge_s_out_addr(br_9_s_out_addr), .bridge_s_out_data(br_9_s_out_data),
        .bridge_s_in_valid(br_8_s_out_valid), .bridge_s_in_addr(br_8_s_out_addr), .bridge_s_in_data(br_8_s_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 10 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(10),
        .N_ZONE(11), .N_ACTIVE(1'b1), .S_ZONE(12), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster10 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z10_out_addr), .out_data(z10_out_data), .out_valid(z10_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z10_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_10_n_out_valid), .bridge_n_out_addr(br_10_n_out_addr), .bridge_n_out_data(br_10_n_out_data),
        .bridge_n_in_valid(br_11_s_out_valid), .bridge_n_in_addr(br_11_s_out_addr), .bridge_n_in_data(br_11_s_out_data),
        .bridge_s_out_valid(br_10_s_out_valid), .bridge_s_out_addr(br_10_s_out_addr), .bridge_s_out_data(br_10_s_out_data),
        .bridge_s_in_valid(br_12_n_out_valid), .bridge_s_in_addr(br_12_n_out_addr), .bridge_s_in_data(br_12_n_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 11 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(11),
        .N_ZONE(0), .N_ACTIVE(1'b1), .S_ZONE(10), .S_ACTIVE(1'b1), .E_ZONE(12), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster11 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z11_out_addr), .out_data(z11_out_data), .out_valid(z11_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z11_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_11_n_out_valid), .bridge_n_out_addr(br_11_n_out_addr), .bridge_n_out_data(br_11_n_out_data),
        .bridge_n_in_valid(br_0_w_out_valid), .bridge_n_in_addr(br_0_w_out_addr), .bridge_n_in_data(br_0_w_out_data),
        .bridge_s_out_valid(br_11_s_out_valid), .bridge_s_out_addr(br_11_s_out_addr), .bridge_s_out_data(br_11_s_out_data),
        .bridge_s_in_valid(br_10_n_out_valid), .bridge_s_in_addr(br_10_n_out_addr), .bridge_s_in_data(br_10_n_out_data),
        .bridge_e_out_valid(br_11_e_out_valid), .bridge_e_out_addr(br_11_e_out_addr), .bridge_e_out_data(br_11_e_out_data),
        .bridge_e_in_valid(br_12_s_out_valid), .bridge_e_in_addr(br_12_s_out_addr), .bridge_e_in_data(br_12_s_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 12 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(12),
        .N_ZONE(10), .N_ACTIVE(1'b1), .S_ZONE(11), .S_ACTIVE(1'b1), .E_ZONE(13), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster12 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z12_out_addr), .out_data(z12_out_data), .out_valid(z12_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z12_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_12_n_out_valid), .bridge_n_out_addr(br_12_n_out_addr), .bridge_n_out_data(br_12_n_out_data),
        .bridge_n_in_valid(br_10_s_out_valid), .bridge_n_in_addr(br_10_s_out_addr), .bridge_n_in_data(br_10_s_out_data),
        .bridge_s_out_valid(br_12_s_out_valid), .bridge_s_out_addr(br_12_s_out_addr), .bridge_s_out_data(br_12_s_out_data),
        .bridge_s_in_valid(br_11_e_out_valid), .bridge_s_in_addr(br_11_e_out_addr), .bridge_s_in_data(br_11_e_out_data),
        .bridge_e_out_valid(br_12_e_out_valid), .bridge_e_out_addr(br_12_e_out_addr), .bridge_e_out_data(br_12_e_out_data),
        .bridge_e_in_valid(br_13_s_out_valid), .bridge_e_in_addr(br_13_s_out_addr), .bridge_e_in_data(br_13_s_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 13 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(13),
        .N_ZONE(3), .N_ACTIVE(1'b1), .S_ZONE(12), .S_ACTIVE(1'b1), .E_ZONE(14), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster13 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z13_out_addr), .out_data(z13_out_data), .out_valid(z13_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z13_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_13_n_out_valid), .bridge_n_out_addr(br_13_n_out_addr), .bridge_n_out_data(br_13_n_out_data),
        .bridge_n_in_valid(br_3_e_out_valid), .bridge_n_in_addr(br_3_e_out_addr), .bridge_n_in_data(br_3_e_out_data),
        .bridge_s_out_valid(br_13_s_out_valid), .bridge_s_out_addr(br_13_s_out_addr), .bridge_s_out_data(br_13_s_out_data),
        .bridge_s_in_valid(br_12_e_out_valid), .bridge_s_in_addr(br_12_e_out_addr), .bridge_s_in_data(br_12_e_out_data),
        .bridge_e_out_valid(br_13_e_out_valid), .bridge_e_out_addr(br_13_e_out_addr), .bridge_e_out_data(br_13_e_out_data),
        .bridge_e_in_valid(br_14_n_out_valid), .bridge_e_in_addr(br_14_n_out_addr), .bridge_e_in_data(br_14_n_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 14 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(14),
        .N_ZONE(13), .N_ACTIVE(1'b1), .S_ZONE(15), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster14 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z14_out_addr), .out_data(z14_out_data), .out_valid(z14_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z14_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_14_n_out_valid), .bridge_n_out_addr(br_14_n_out_addr), .bridge_n_out_data(br_14_n_out_data),
        .bridge_n_in_valid(br_13_e_out_valid), .bridge_n_in_addr(br_13_e_out_addr), .bridge_n_in_data(br_13_e_out_data),
        .bridge_s_out_valid(br_14_s_out_valid), .bridge_s_out_addr(br_14_s_out_addr), .bridge_s_out_data(br_14_s_out_data),
        .bridge_s_in_valid(br_15_s_out_valid), .bridge_s_in_addr(br_15_s_out_addr), .bridge_s_in_data(br_15_s_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 15 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(15),
        .N_ZONE(5), .N_ACTIVE(1'b1), .S_ZONE(14), .S_ACTIVE(1'b1), .E_ZONE(16), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster15 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z15_out_addr), .out_data(z15_out_data), .out_valid(z15_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z15_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_15_n_out_valid), .bridge_n_out_addr(br_15_n_out_addr), .bridge_n_out_data(br_15_n_out_data),
        .bridge_n_in_valid(br_5_e_out_valid), .bridge_n_in_addr(br_5_e_out_addr), .bridge_n_in_data(br_5_e_out_data),
        .bridge_s_out_valid(br_15_s_out_valid), .bridge_s_out_addr(br_15_s_out_addr), .bridge_s_out_data(br_15_s_out_data),
        .bridge_s_in_valid(br_14_s_out_valid), .bridge_s_in_addr(br_14_s_out_addr), .bridge_s_in_data(br_14_s_out_data),
        .bridge_e_out_valid(br_15_e_out_valid), .bridge_e_out_addr(br_15_e_out_addr), .bridge_e_out_data(br_15_e_out_data),
        .bridge_e_in_valid(br_16_n_out_valid), .bridge_e_in_addr(br_16_n_out_addr), .bridge_e_in_data(br_16_n_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 16 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(16),
        .N_ZONE(15), .N_ACTIVE(1'b1), .S_ZONE(17), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster16 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z16_out_addr), .out_data(z16_out_data), .out_valid(z16_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z16_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_16_n_out_valid), .bridge_n_out_addr(br_16_n_out_addr), .bridge_n_out_data(br_16_n_out_data),
        .bridge_n_in_valid(br_15_e_out_valid), .bridge_n_in_addr(br_15_e_out_addr), .bridge_n_in_data(br_15_e_out_data),
        .bridge_s_out_valid(br_16_s_out_valid), .bridge_s_out_addr(br_16_s_out_addr), .bridge_s_out_data(br_16_s_out_data),
        .bridge_s_in_valid(br_17_e_out_valid), .bridge_s_in_addr(br_17_e_out_addr), .bridge_s_in_data(br_17_e_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 17 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(17),
        .N_ZONE(6), .N_ACTIVE(1'b1), .S_ZONE(8), .S_ACTIVE(1'b1), .E_ZONE(16), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster17 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z17_out_addr), .out_data(z17_out_data), .out_valid(z17_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z17_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_17_n_out_valid), .bridge_n_out_addr(br_17_n_out_addr), .bridge_n_out_data(br_17_n_out_data),
        .bridge_n_in_valid(br_6_e_out_valid), .bridge_n_in_addr(br_6_e_out_addr), .bridge_n_in_data(br_6_e_out_data),
        .bridge_s_out_valid(br_17_s_out_valid), .bridge_s_out_addr(br_17_s_out_addr), .bridge_s_out_data(br_17_s_out_data),
        .bridge_s_in_valid(br_8_e_out_valid), .bridge_s_in_addr(br_8_e_out_addr), .bridge_s_in_data(br_8_e_out_data),
        .bridge_e_out_valid(br_17_e_out_valid), .bridge_e_out_addr(br_17_e_out_addr), .bridge_e_out_data(br_17_e_out_data),
        .bridge_e_in_valid(br_16_s_out_valid), .bridge_e_in_addr(br_16_s_out_addr), .bridge_e_in_data(br_16_s_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

