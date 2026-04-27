// lif_neuron_reference.v
// Leaky Integrate-and-Fire (LIF) neuron reference implementation
// Source: Grok analysis, April 2026
// Based on UniCell v1 topology -- see architecture_positioning.md
// for v2 cell-based implementation (~6-8 cells per neuron)
//
// NOTE: This is a standalone Verilog module sitting beside the UniCell
// fabric. For a pond-native implementation using UniCell cells directly,
// see architecture_positioning.md -- LIF neuron section.
// In v2, the full neuron fits in 6-8 cells vs 40-50 in v1.

`timescale 1ns / 1ps

module lif_neuron #(
    parameter WIDTH      = 8,
    parameter LEAK_SHIFT = 4,
    parameter THRESHOLD  = 8'h80
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             enable,
    input  wire             spike_in,
    input  wire [WIDTH-1:0] weighted_input,
    output reg              spike_out,
    output wire [WIDTH-1:0] membrane_potential
);

    reg [WIDTH-1:0] membrane;
    reg             refractory;

    wire [WIDTH-1:0] leak_amount       = membrane >> LEAK_SHIFT;
    wire [WIDTH-1:0] next_membrane_raw = membrane - leak_amount
                                         + (spike_in ? weighted_input : 0);
    wire [WIDTH-1:0] next_membrane     = (next_membrane_raw > {WIDTH{1'b1}})
                                         ? {WIDTH{1'b1}}
                                         : (next_membrane_raw[WIDTH-1]
                                            ? 0 : next_membrane_raw);
    wire spike_fire = (membrane >= THRESHOLD) && !refractory;

    always @(posedge clk) begin
        if (rst || !enable) begin
            membrane   <= 0;
            spike_out  <= 1'b0;
            refractory <= 1'b0;
        end else begin
            membrane  <= next_membrane;
            spike_out <= spike_fire;
            refractory <= spike_fire ? 1'b1 : 1'b0;
        end
    end

    assign membrane_potential = membrane;

endmodule
