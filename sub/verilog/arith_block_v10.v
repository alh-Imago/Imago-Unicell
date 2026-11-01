`default_nettype none
`timescale 1ns / 1ps
// arith_block_v10 = arith_block_v9 + the SECOND-OPERAND SOURCE for a chain of units (1 Nov 2026, Alan 19:19: 'start with the chain side ... much like the chained dsp units on the arria 10, but here you define the steps'). cfg_data[28:27] = bsrc: 0 = the side operand in_b as before (v9 behaviour), 1 = the 8-bit step field zero-extended (a constant chosen by the config, e.g. a shift amount or a small addend), 2 = in_a itself (a op a), 3 = as 0. cfg_data[31] is RESERVED for the stage wrapper (bypass); the block ignores it. v9 left as it was; with bsrc = 0 this block equals v9.
// arith_block_v10 -- the arithmetic block SIZED FOR HEX-N (1 Nov 2026, Alan 18:01: 'there was a specific arith block for the hexn system, would have to size it up correctly, as the board is not too large'). New file; v1 to v8 left as they were.
// = arith_block_v8 with: (1) a data WIDTH parameter (default 18 = the Hex-N core width; 32 gives the old size), (2) the choices fixed to the smallest measured form: ONE shared adder, ONE shared shifter (barrel, shift_out = shifted in_a[SW-1:0], SW = min(WIDTH,18)), the truth-table nano. The 32-bit config word is unchanged:
//   cfg_data[2:0] mode (0 add, 1 sub, 2 signed >= (1/0), 3 signed compare (0 lt, 1 eq, 2 gt), 4 accumulate, 5 shift left, 6 shift right, 7 nano logic), [15:8] step / keep flags, [25:16] nano topology, [26] held operand from the config (keep flags per 4-bit lane) instead of in_b.
// Every word is answered (valid_out for each valid_in once armed). Config clears the total and the output (a reconfigure is a fresh start). Accumulate pulses: in_a[0] = inc, in_a[1] = dec, qualified by valid_in.
module arith_block_v10 #(parameter WIDTH = 18) (
    input  wire clk, input wire rst, input wire cfg_valid, input wire [31:0] cfg_data,
    input  wire [WIDTH-1:0] in_a, input wire [WIDTH-1:0] in_b_side, input wire valid_in,
    output wire [WIDTH-1:0] data_out, output wire valid_out
);
    localparam SW = (WIDTH < 18) ? WIDTH : 18;
    reg [WIDTH-1:0] in_b;                                   // the operand the block uses, chosen by bsrc
    always @* case (bsrc) 2'd1: in_b = step; 2'd2: in_b = in_a; default: in_b = in_b_side; endcase
    reg [1:0] bsrc = 2'd0; reg [2:0] mode = 3'd0; reg [7:0] step = 8'h0; reg [9:0] topo = 10'h0; reg heldsrc = 1'b0; reg armed = 1'b0;
    reg [WIDTH-1:0] total = 0; reg [WIDTH-1:0] out_buffer = 0; reg valid_out_r = 1'b0;
    reg [WIDTH-1:0] result;
    wire inc = in_a[0] && valid_in, dec = in_a[1] && valid_in;
    wire pulse = valid_in && (mode == 3'd4) && (inc || dec);
    wire [WIDTH-1:0] step_ext = step;
    // ---- nano logic as a truth table decoded once
    wire [31:0] keep32 = {{4{step[7]}},{4{step[6]}},{4{step[5]}},{4{step[4]}},{4{step[3]}},{4{step[2]}},{4{step[1]}},{4{step[0]}}};
    wire [WIDTH-1:0] nh = heldsrc ? keep32[WIDTH-1:0] : in_b; wire [WIDTH-1:0] nf = in_a;
    reg [3:0] tt;
    always_comb case (topo)
        10'h000: tt = 4'b1010; 10'h02C: tt = 4'b1100; 10'h001: tt = 4'b0101; 10'h002: tt = 4'b0011; 10'h004: tt = 4'b0001; 10'h007: tt = 4'b1000;
        10'h024: tt = 4'b1110; 10'h027: tt = 4'b0111; 10'h0BC: tt = 4'b0110; 10'h03C: tt = 4'b1001; 10'h030: tt = 4'b0000; 10'h0B0: tt = 4'b1111;
        default: tt = 4'b1010;
    endcase
    wire [WIDTH-1:0] nano_tt; genvar gi;
    generate for (gi = 0; gi < WIDTH; gi = gi + 1) begin : g_tt assign nano_tt[gi] = tt[{nf[gi], nh[gi]}]; end endgenerate
    // ---- shifts (amount in_b[4:0]; SW or more gives 0)
    wire [4:0] sh = in_b[4:0];
    wire acc = (mode == 3'd4);
    wire sub = (mode == 3'd1) || (mode == 3'd2) || (mode == 3'd3) || (acc && dec && !inc);
    wire [WIDTH-1:0] opa = acc ? total : in_a;
    wire [WIDTH-1:0] opb = acc ? ((inc ^ dec) ? step_ext : {WIDTH{1'b0}}) : in_b;
    wire [WIDTH:0] a1 = {opa[WIDTH-1], opa};
    wire [WIDTH:0] b1 = {opb[WIDTH-1], opb} ^ {(WIDTH+1){sub}};
    wire [WIDTH:0] s1 = a1 + b1 + {{WIDTH{1'b0}}, sub};
    reg [SW-1:0] rev_in; integer ri;
    always @* for (ri = 0; ri < SW; ri = ri + 1) rev_in[ri] = in_a[SW-1-ri];
    wire [SW-1:0] sx = (mode == 3'd6) ? rev_in : in_a[SW-1:0];
    wire [SW-1:0] sy = sx << sh;
    reg [SW-1:0] sy_rev; integer qi;
    always @* for (qi = 0; qi < SW; qi = qi + 1) sy_rev[qi] = sy[SW-1-qi];
    wire [SW-1:0] sres = (mode == 3'd6) ? sy_rev : sy;
    always @* case (mode)
        3'd5, 3'd6: result = {{(WIDTH-SW){1'b0}}, sres};
        3'd7: result = nano_tt;
        3'd2: result = {{(WIDTH-1){1'b0}}, ~s1[WIDTH]};
        3'd3: result = s1[WIDTH] ? 0 : (s1 == 0) ? 1 : 2;
        default: result = s1[WIDTH-1:0];
    endcase
    assign data_out = out_buffer; assign valid_out = valid_out_r;
    always @(posedge clk) begin
        if (rst) begin mode <= 3'd0; step <= 8'h0; topo <= 10'h0; heldsrc <= 1'b0; bsrc <= 2'd0; armed <= 1'b0; total <= 0; out_buffer <= 0; valid_out_r <= 1'b0; end
        else if (cfg_valid) begin bsrc <= cfg_data[28:27]; mode <= cfg_data[2:0]; step <= cfg_data[15:8]; topo <= cfg_data[25:16]; heldsrc <= cfg_data[26]; armed <= 1'b1; total <= 0; out_buffer <= 0; valid_out_r <= 1'b0; end
        else begin
            if (pulse) total <= result;
            out_buffer  <= result;
            valid_out_r <= armed && valid_in;
        end
    end
endmodule
