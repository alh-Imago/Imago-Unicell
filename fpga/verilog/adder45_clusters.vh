// AUTO-GENERATED: 10 cluster instances + address-decoded bridge wiring
// for the 50-cell adder. Placement respects the same-cluster constraint
// for shared-broadcast address pairs (2026-07-05).

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
    wire        br_0_n_out_valid;
    wire [15:0] br_0_n_out_addr;
    wire [31:0] br_0_n_out_data;
    wire        br_0_s_out_valid;
    wire [15:0] br_0_s_out_addr;
    wire [31:0] br_0_s_out_data;
    wire        br_1_e_out_valid;
    wire [15:0] br_1_e_out_addr;
    wire [31:0] br_1_e_out_data;
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

    // ── cluster 0 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(0),
        .N_ZONE(1), .N_ACTIVE(1'b1), .S_ZONE(2), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
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
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 1 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(1),
        .N_ZONE(0), .N_ACTIVE(1'b1), .S_ZONE(2), .S_ACTIVE(1'b1), .E_ZONE(9), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
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
        .bridge_e_out_valid(br_1_e_out_valid), .bridge_e_out_addr(br_1_e_out_addr), .bridge_e_out_data(br_1_e_out_data),
        .bridge_e_in_valid(br_9_n_out_valid), .bridge_e_in_addr(br_9_n_out_addr), .bridge_e_in_data(br_9_n_out_data),
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
        .N_ZONE(2), .N_ACTIVE(1'b1), .S_ZONE(4), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
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
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
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
        .N_ZONE(4), .N_ACTIVE(1'b1), .S_ZONE(6), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
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
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 6 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(6),
        .N_ZONE(5), .N_ACTIVE(1'b1), .S_ZONE(7), .S_ACTIVE(1'b1), .E_ZONE(8), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
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
        .bridge_e_in_valid(br_8_n_out_valid), .bridge_e_in_addr(br_8_n_out_addr), .bridge_e_in_data(br_8_n_out_data),
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
        .bridge_s_in_valid(br_8_s_out_valid), .bridge_s_in_addr(br_8_s_out_addr), .bridge_s_in_data(br_8_s_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 8 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(8),
        .N_ZONE(6), .N_ACTIVE(1'b1), .S_ZONE(7), .S_ACTIVE(1'b1), .E_ZONE(9), .E_ACTIVE(1'b1), .W_ACTIVE(1'b0)
    ) cluster8 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z8_out_addr), .out_data(z8_out_data), .out_valid(z8_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z8_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_8_n_out_valid), .bridge_n_out_addr(br_8_n_out_addr), .bridge_n_out_data(br_8_n_out_data),
        .bridge_n_in_valid(br_6_e_out_valid), .bridge_n_in_addr(br_6_e_out_addr), .bridge_n_in_data(br_6_e_out_data),
        .bridge_s_out_valid(br_8_s_out_valid), .bridge_s_out_addr(br_8_s_out_addr), .bridge_s_out_data(br_8_s_out_data),
        .bridge_s_in_valid(br_7_s_out_valid), .bridge_s_in_addr(br_7_s_out_addr), .bridge_s_in_data(br_7_s_out_data),
        .bridge_e_out_valid(br_8_e_out_valid), .bridge_e_out_addr(br_8_e_out_addr), .bridge_e_out_data(br_8_e_out_data),
        .bridge_e_in_valid(br_9_s_out_valid), .bridge_e_in_addr(br_9_s_out_addr), .bridge_e_in_data(br_9_s_out_data),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

    // ── cluster 9 ──────────────────────────────────────────
    unicell_zone64_v3 #(.NUM_CELLS(5), .NUM_BRIDGES(1), .ZONE_ID(9),
        .N_ZONE(1), .N_ACTIVE(1'b1), .S_ZONE(8), .S_ACTIVE(1'b1), .E_ACTIVE(1'b0), .W_ACTIVE(1'b0)
    ) cluster9 (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(cpu_addr), .cpu_data(cmd_data), .cpu_valid(cpu_valid),
        .out_addr(z9_out_addr), .out_data(z9_out_data), .out_valid(z9_out_valid),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(z9_emit),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(), .cycle_count(),
        .bridge_n_out_valid(br_9_n_out_valid), .bridge_n_out_addr(br_9_n_out_addr), .bridge_n_out_data(br_9_n_out_data),
        .bridge_n_in_valid(br_1_e_out_valid), .bridge_n_in_addr(br_1_e_out_addr), .bridge_n_in_data(br_1_e_out_data),
        .bridge_s_out_valid(br_9_s_out_valid), .bridge_s_out_addr(br_9_s_out_addr), .bridge_s_out_data(br_9_s_out_data),
        .bridge_s_in_valid(br_8_e_out_valid), .bridge_s_in_addr(br_8_e_out_addr), .bridge_s_in_data(br_8_e_out_data),
        .bridge_e_out_valid(), .bridge_e_out_addr(), .bridge_e_out_data(),
        .bridge_e_in_valid(1'b0), .bridge_e_in_addr(16'h0), .bridge_e_in_data(32'h0),
        .bridge_w_out_valid(), .bridge_w_out_addr(), .bridge_w_out_data(),
        .bridge_w_in_valid(1'b0), .bridge_w_in_addr(16'h0), .bridge_w_in_data(32'h0)
    );

