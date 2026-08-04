// top_zone_synth.v — one-zone synthesis harness for measuring REAL zone-level
// fmax and fit, with registered I/O so the critical path is fabric-internal
// (flop -> zone -> flop), not the I/O-dominated path that distorts a raw
// standalone cell synth. Minimal top pins; all wide outputs reduced to one
// registered bit so the fitter cannot optimise the fabric away.
//
//   CELL64 = 1  -> zone of unicell64 (the variant)   <-- default, the thing to measure
//   CELL64 = 0  -> zone of unicell   (the proven cell, for an apples-to-apples baseline)
//
// Files needed: top_zone_synth.v unicell_zone.v unicell_array.v unicell.v unicell64.v
// Set top-level entity = top_zone_synth. Same device/settings for both CELL64 values;
// the DELTA in fmax/ALMs is the honest zone-level cost of the cut.
`timescale 1ns/1ps
module top_zone_synth #(
    parameter NUM_CELLS = 25,
    parameter NUM_BRIDGES = 2,
    parameter CELL64 = 1
) (
    input  wire clk,
    input  wire rst,
    input  wire in_bit,     // serial stimulus — keeps inputs live, registered
    output reg  out_bit     // reduced result — registered
);
    // ── registered input driver: a small LFSR seeded by in_bit feeds the wide
    //    zone inputs, so every zone input toggles through a flop (no I/O path).
    reg [31:0] lfsr = 32'h1;
    always @(posedge clk) begin
        if (rst) lfsr <= 32'h1;
        else     lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]^in_bit};
    end
    reg [31:0] cmd_bus_r, cmd_data_r, cpu_data_r;
    reg [15:0] cpu_addr_r;
    reg        cmd_valid_r, cpu_valid_r;
    always @(posedge clk) begin
        cmd_bus_r   <= lfsr;
        cmd_data_r  <= {lfsr[15:0], lfsr[31:16]};
        cpu_addr_r  <= lfsr[15:0];
        cpu_data_r  <= ~lfsr;
        cmd_valid_r <= lfsr[3];
        cpu_valid_r <= lfsr[7];
    end

    // ── zone outputs (wide) ──
    wire [15:0] out_addr, armed_count, arrived_count, output_set_count, emit_count;
    wire [31:0] out_data, dbg0_cmd_latch, dbg0_input_addr, dbg0_output_addr, dbg0_a_data, cycle_count;
    wire        out_valid;
    wire [NUM_BRIDGES-1:0]    bn_ov, bs_ov, be_ov, bw_ov;
    wire [NUM_BRIDGES*16-1:0] bn_oa, bs_oa, be_oa, bw_oa;
    wire [NUM_BRIDGES*32-1:0] bn_od, bs_od, be_od, bw_od;

    localparam BV = {NUM_BRIDGES{1'b0}};
    localparam BA = {(NUM_BRIDGES*16){1'b0}};
    localparam BD = {(NUM_BRIDGES*32){1'b0}};

    generate if (CELL64) begin : gz64
    unicell_zone64 #(.NUM_CELLS(NUM_CELLS), .NUM_BRIDGES(NUM_BRIDGES), .ZONE_ID(0)) z (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus_r), .cmd_data(cmd_data_r), .cmd_valid(cmd_valid_r),
        .cpu_addr(cpu_addr_r), .cpu_data(cpu_data_r), .cpu_valid(cpu_valid_r),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .armed_count(armed_count), .arrived_count(arrived_count),
        .output_set_count(output_set_count), .emit_count(emit_count),
        .dbg0_cmd_latch(dbg0_cmd_latch), .dbg0_input_addr(dbg0_input_addr),
        .dbg0_output_addr(dbg0_output_addr), .dbg0_a_data(dbg0_a_data), .cycle_count(cycle_count),
        .bridge_n_in_valid(BV), .bridge_n_in_addr(BA), .bridge_n_in_data(BD),
        .bridge_n_out_valid(bn_ov), .bridge_n_out_addr(bn_oa), .bridge_n_out_data(bn_od),
        .bridge_s_in_valid(BV), .bridge_s_in_addr(BA), .bridge_s_in_data(BD),
        .bridge_s_out_valid(bs_ov), .bridge_s_out_addr(bs_oa), .bridge_s_out_data(bs_od),
        .bridge_e_in_valid(BV), .bridge_e_in_addr(BA), .bridge_e_in_data(BD),
        .bridge_e_out_valid(be_ov), .bridge_e_out_addr(be_oa), .bridge_e_out_data(be_od),
        .bridge_w_in_valid(BV), .bridge_w_in_addr(BA), .bridge_w_in_data(BD),
        .bridge_w_out_valid(bw_ov), .bridge_w_out_addr(bw_oa), .bridge_w_out_data(bw_od)
    );
    end else begin : gz32
    unicell_zone #(.NUM_CELLS(NUM_CELLS), .NUM_BRIDGES(NUM_BRIDGES), .ZONE_ID(0)) z (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus_r), .cmd_data(cmd_data_r), .cmd_valid(cmd_valid_r),
        .cpu_addr(cpu_addr_r), .cpu_data(cpu_data_r), .cpu_valid(cpu_valid_r),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .armed_count(armed_count), .arrived_count(arrived_count),
        .output_set_count(output_set_count), .emit_count(emit_count),
        .dbg0_cmd_latch(dbg0_cmd_latch), .dbg0_input_addr(dbg0_input_addr),
        .dbg0_output_addr(dbg0_output_addr), .dbg0_a_data(dbg0_a_data), .cycle_count(cycle_count),
        .bridge_n_in_valid(BV), .bridge_n_in_addr(BA), .bridge_n_in_data(BD),
        .bridge_n_out_valid(bn_ov), .bridge_n_out_addr(bn_oa), .bridge_n_out_data(bn_od),
        .bridge_s_in_valid(BV), .bridge_s_in_addr(BA), .bridge_s_in_data(BD),
        .bridge_s_out_valid(bs_ov), .bridge_s_out_addr(bs_oa), .bridge_s_out_data(bs_od),
        .bridge_e_in_valid(BV), .bridge_e_in_addr(BA), .bridge_e_in_data(BD),
        .bridge_e_out_valid(be_ov), .bridge_e_out_addr(be_oa), .bridge_e_out_data(be_od),
        .bridge_w_in_valid(BV), .bridge_w_in_addr(BA), .bridge_w_in_data(BD),
        .bridge_w_out_valid(bw_ov), .bridge_w_out_addr(bw_oa), .bridge_w_out_data(bw_od)
    );
    end endgenerate

    // ── reduce every output to one registered bit (forces real fabric paths) ──
    always @(posedge clk) begin
        out_bit <= ^{ out_addr, out_data, out_valid,
                      armed_count, arrived_count, output_set_count, emit_count,
                      dbg0_cmd_latch, dbg0_input_addr, dbg0_output_addr, dbg0_a_data, cycle_count,
                      bn_ov, bs_ov, be_ov, bw_ov, bn_oa, bs_oa, be_oa, bw_oa,
                      bn_od, bs_od, be_od, bw_od };
    end
endmodule
