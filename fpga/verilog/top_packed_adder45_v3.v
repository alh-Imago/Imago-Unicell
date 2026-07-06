// STALE (2026-07-06): generated against the OLD zone-parameter routing
// (N_ZONE/N_ACTIVE etc.), which unicell_zone64_v3.v no longer has -- routing
// moved to per-cell routing_mask (see points.md #4). This file will NOT
// compile until the adder's placement/config generation is redone to use
// routing_mask instead of the shared-address relay-chain approach. Left in
// place as reference for that next step, not as working code.

// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// top_packed_adder45_v3.v — the verified-in-Python 50-cell packed shift-adder
// (docs/design-notes/packed_adder_cluster_mesh.md) on 10 five-cell clusters,
// wired per the computed plus-pentomino-derived bridge plan.
//
// STATUS (2026-07-05): loads and primes correctly (all 50 cells + 32 priming
// steps confirmed via emit_count). Does NOT yet compute the correct SUM --
// a real, precisely-diagnosed placement/routing conflict remains: the
// shared-broadcast-address fan-out trick (a relay cell listens at its
// "natural" sibling's address to catch a shared broadcast) is incompatible
// with the zone bridge's new address-decode routing (each address routes
// to only the ONE cluster that owns it by CELL_BASE) whenever the sharing
// pair lands in different clusters. Real fix: a placement constraint
// keeping any address-sharing pair in the same cluster -- not yet applied.
// See tb_packed_adder45_v3.v's trailing comment and the design note.
`default_nettype none
`timescale 1ns / 1ps

module top_packed_adder45_v3 (
    input  wire clk,
    input  wire rst,
    input  wire start_load,

    // Host stimulus: inject A and B (two-arrival, shared external address
    // both G0 and P0 listen at -- see adder45_config.vh, EXTERNAL_ADDR=1000)
    input  wire [31:0] host_cmd_bus,
    input  wire [31:0] host_cmd_data,
    input  wire        host_cmd_valid,

    output wire [31:0] sum_result,
    output wire         sum_valid_pulse,
    output wire         loader_done
);

    localparam NCELLS = 85;
    localparam NPRIME = 68;
    localparam NCLUSTERS = 18;
    localparam [15:0] RESULTS_ADDR = 16'd2000;

    // ── config tables (generated) ──────────────────────────────────────────
    wire [15:0] cfg_target[0:NCELLS-1], cfg_input_addr[0:NCELLS-1], cfg_output_addr[0:NCELLS-1];
    wire [31:0] cfg_c1_bus[0:NCELLS-1], cfg_c1_data[0:NCELLS-1], cfg_c2_bus[0:NCELLS-1], cfg_c2_data[0:NCELLS-1];
    wire [7:0]  cfg_cluster[0:NCELLS-1];
    wire [15:0] prime_target[0:NPRIME-1];
`include "adder45_config.vh"

    // ── loader/host bus arbitration ────────────────────────────────────────
    wire [31:0] ldr_cmd_bus, ldr_cmd_data; wire ldr_cmd_valid, ldr_cpu_valid;
    wire [15:0] ldr_cpu_addr;
    wire [15:0] emit_count[0:NCLUSTERS-1];

    wire preload_act = (host_cmd_bus[18:17] != 2'b00);
    wire host_cmd_valid_w = host_cmd_valid && (host_cmd_bus[7:0]!=8'd1)
                          && ((host_cmd_bus[7:0]!=8'd0) || preload_act);
    wire [15:0] host_cpu_addr = (host_cmd_bus[7:0]==8'd1) ? host_cmd_data[31:16] : host_cmd_data[15:0];

    wire [31:0] cmd_bus   = !loader_done ? ldr_cmd_bus  : host_cmd_bus;
    wire [31:0] cmd_data  = !loader_done ? ldr_cmd_data : host_cmd_data;
    wire        cmd_valid = !loader_done ? ldr_cmd_valid: host_cmd_valid_w;
    wire [15:0] cpu_addr  = !loader_done ? ldr_cpu_addr : host_cpu_addr;
    wire        cpu_valid = !loader_done ? ldr_cpu_valid: host_cmd_valid;

    adder_loader_v3 #(.NCELLS(NCELLS), .NPRIME(NPRIME), .NCLUSTERS(NCLUSTERS)) loader (
        .clk(clk), .rst(rst), .start(start_load),
        .cfg_target(cfg_target), .cfg_input_addr(cfg_input_addr), .cfg_output_addr(cfg_output_addr),
        .cfg_c1_bus(cfg_c1_bus), .cfg_c1_data(cfg_c1_data), .cfg_c2_bus(cfg_c2_bus), .cfg_c2_data(cfg_c2_data),
        .cfg_cluster(cfg_cluster), .prime_target(prime_target),
        .cmd_bus(ldr_cmd_bus), .cmd_data(ldr_cmd_data), .cmd_valid(ldr_cmd_valid),
        .cpu_addr(ldr_cpu_addr), .cpu_valid(ldr_cpu_valid),
        .emit_count(emit_count), .done(loader_done)
    );

`include "adder45_clusters.vh"

    assign emit_count[0]=z0_emit;
    assign emit_count[1]=z1_emit;
    assign emit_count[2]=z2_emit;
    assign emit_count[3]=z3_emit;
    assign emit_count[4]=z4_emit;
    assign emit_count[5]=z5_emit;
    assign emit_count[6]=z6_emit;
    assign emit_count[7]=z7_emit;
    assign emit_count[8]=z8_emit;
    assign emit_count[9]=z9_emit;
    assign emit_count[10]=z10_emit;
    assign emit_count[11]=z11_emit;
    assign emit_count[12]=z12_emit;
    assign emit_count[13]=z13_emit;
    assign emit_count[14]=z14_emit;
    assign emit_count[15]=z15_emit;
    assign emit_count[16]=z16_emit;
    assign emit_count[17]=z17_emit;

    // ── results capture: SUM_XOR lives in cluster9, output_address=RESULTS_ADDR ──
    reg [31:0] sum_reg; reg sum_valid_r;
    always @(posedge clk) begin
        if (rst) begin sum_reg <= 32'h0; sum_valid_r <= 1'b0; end
        else begin
            sum_valid_r <= 1'b0;
            if (z9_out_valid && z9_out_addr==RESULTS_ADDR) begin
                sum_reg <= z9_out_data; sum_valid_r <= 1'b1;
            end
        end
    end
    assign sum_result = sum_reg;
    assign sum_valid_pulse = sum_valid_r;

endmodule
