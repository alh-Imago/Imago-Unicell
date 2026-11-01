// arith_block_v7 = arith_block_v6 + SHIFT_CF (1 Nov 2026, Alan 05:49-05:54): the 18-bit shifter as a FINE stage (0-3, amount bits [1:0]) followed by a COARSE stage of evenly spaced fixed taps 0,4,8,12,16 (amount bits [4:2]; 20 or more gives 0). Both stages go the SAME way, so the result equals one shift (no bits come back). SHIFT_CF=0 is the v6 shifter unchanged. v6 left as it was.
// arith_block_v7 = arith_block_v5 + MASK (1 Nov 2026, Alan 05:38 "the mask feature"): in mode 7, cfg_data[26]=1 takes the HELD operand from the CONFIG instead of in_b:
//   the 8 bits in cfg_data[15:8] are KEEP flags, one per 4-bit nibble lane, expanded to 32 bits. With topology AND (10'h007) this is exactly mask_cell_v4s:
//   mask_en=1 -> step = ~nibble_mask ; mask_en=0 -> step = 8'hFF (keep all). v5 left as it was; with cfg_data[26]=0 v6 behaves as v5.
`default_nettype none
`timescale 1ns / 1ps
// arith_block_v7 = arith_block_v4 + THREE MODES (1 Nov 2026, Alan 05:22): 5 shift left, 6 shift right (18-bit, the width of the core; amount = in_b[4:0], 18 or more gives 0), 7 nano logic (the 12-function NOR network of nano_cell_v4s; topology = cfg_data[25:16]; FLOW = in_a, HELD = in_b: the nano cell held register is replaced by in_b). v4 left as it was.
// Original v4 header: arith_block_v3 with ONE change: every word gets a result (1 Nov 2026, Alan 03:04: the region must answer every word; a stuck cell is a fault). v3 left as it was.
// arith_block_v7 = arith_block_v2 with ONE FIX (accumulate pulses were not qualified by valid_in; found by tb_gate_block_v1, 1 Nov 2026). v2 left as it was. Original header: arith_block_v1 (kept unchanged) plus a 3-way compare and an accumulate mode.
// MEASUREMENT PROTOTYPE (1 Nov 2026). cfg_data[2:0] = mode, cfg_data[15:8] = step (accumulate).
//   0 add (a+b)   1 sub (a-b)   2 ge (signed a>=b -> 1/0)
//   3 cmp3 (signed: 0 a<b, 1 a==b, 2 a>b)   [the arithmetic of branch_cell_v4s's is_low/is_equal; NOT its routing, held registers or emit mux]
//   4 accumulate: in_a[0]=inc, in_a[1]=dec pulses, total += +-step, out = new total (the continuous mode of
//     accumulator_cell_v4s, 32-bit; NOT its pulse_mode / threshold logic). Config clears the total, as the cell does.
// SHARED=1: ONE 33-bit adder serves every mode. SHARED=0: a separate adder/comparators/accumulator adder per function, output mux.
module arith_block_v7 #(parameter SHARED = 1, parameter NANO_TT = 0, parameter SHIFT_CF = 0) (   // NANO_TT=1: the same 12 functions via a 4-bit truth table decoded once from the topology word (same behaviour, smaller)
    input  wire clk, input wire rst, input wire cfg_valid, input wire [31:0] cfg_data,
    input  wire [31:0] in_a, input wire [31:0] in_b, input wire valid_in,
    output wire [31:0] data_out, output wire valid_out
);
    reg [2:0] mode = 3'd0; reg [7:0] step = 8'h0; reg [9:0] topo = 10'h0; reg heldsrc = 1'b0; reg armed = 1'b0;
    reg [31:0] total = 32'h0; reg [31:0] out_buffer = 32'h0; reg valid_out_r = 1'b0;
    reg [31:0] result;
    wire inc = in_a[0] && valid_in, dec = in_a[1] && valid_in;   // v3 FIX: qualified by valid_in, so held data bits never look like a pulse
    wire pulse = valid_in && (mode == 3'd4) && (inc || dec);   // v3 FIX: pulses only count with valid_in (v2 treated the held in_a bits as fresh pulses)
    wire [31:0] step_ext = {24'b0, step};

    // ---- nano logic: the same network and the same 12 topologies as nano_cell_v4s (FLOW = in_a, HELD = in_b)
    wire [31:0] keep_exp = {{4{step[7]}},{4{step[6]}},{4{step[5]}},{4{step[4]}},{4{step[3]}},{4{step[2]}},{4{step[1]}},{4{step[0]}}};
    wire [31:0] nh = heldsrc ? keep_exp : in_b; wire [31:0] nf = in_a;
    wire [31:0] g0 = ~(nh | nh), g1 = ~(nf | nf), g2 = ~(g0 | g1), g3 = ~(g2 | g2), g4 = ~(nh | nf), g5 = ~(g4 | g4), g6 = ~(nh | g4), g7 = ~(nf | g4), g8 = ~(g6 | g7), g9 = ~(g8 | g8);
    reg [31:0] nano_net;
    always @* case (topo)
        10'h000: nano_net = nh;   10'h02C: nano_net = nf;   10'h001: nano_net = g0;  10'h002: nano_net = g1;
        10'h004: nano_net = g4;   10'h007: nano_net = g2;   10'h024: nano_net = g5;  10'h027: nano_net = g3;
        10'h0BC: nano_net = g9;   10'h03C: nano_net = g8;   10'h030: nano_net = 32'h0; 10'h0B0: nano_net = 32'hFFFFFFFF;
        default: nano_net = nh;
    endcase
    // truth-table form: tt[{flow_bit, held_bit}] is the output bit; the topology is decoded ONCE, not per bit
    reg [3:0] tt;
    always_comb case (topo)   // always_comb, not always @*: runs at time 0, so a topology that never changes from its reset value (0) still gives a defined table in simulation
        10'h000: tt = 4'b1010; 10'h02C: tt = 4'b1100; 10'h001: tt = 4'b0101; 10'h002: tt = 4'b0011; 10'h004: tt = 4'b0001; 10'h007: tt = 4'b1000;
        10'h024: tt = 4'b1110; 10'h027: tt = 4'b0111; 10'h0BC: tt = 4'b0110; 10'h03C: tt = 4'b1001; 10'h030: tt = 4'b0000; 10'h0B0: tt = 4'b1111;
        default: tt = 4'b1010;
    endcase
    wire [31:0] nano_tt; genvar gi;
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_tt assign nano_tt[gi] = tt[{nf[gi], nh[gi]}]; end endgenerate
    wire [31:0] nano_sel = NANO_TT ? nano_tt : nano_net;
    // ---- 18-bit shifts
    wire [4:0] sh = in_b[4:0];
    reg [31:0] shift_out;
    generate if (SHARED) begin : g_shared
        wire acc = (mode == 3'd4);
        wire sub = (mode == 3'd1) || (mode == 3'd2) || (mode == 3'd3) || (acc && dec && !inc);
        wire [31:0] opa = acc ? total : in_a;
        wire [31:0] opb = acc ? ((inc ^ dec) ? step_ext : 32'h0) : in_b;
        wire [32:0] a33 = {opa[31], opa};
        wire [32:0] b33 = {opb[31], opb} ^ {33{sub}};
        wire [32:0] s33 = a33 + b33 + {32'b0, sub};
        // ONE 18-bit shifter for both directions: right = reverse, shift left, reverse
        wire [17:0] rev_in = {in_a[0],in_a[1],in_a[2],in_a[3],in_a[4],in_a[5],in_a[6],in_a[7],in_a[8],in_a[9],in_a[10],in_a[11],in_a[12],in_a[13],in_a[14],in_a[15],in_a[16],in_a[17]};
        wire [17:0] sx = (mode == 3'd6) ? rev_in : in_a[17:0];
        wire [17:0] fine = sx << sh[1:0];                 // fine stage 0-3
        reg [17:0] coarse;                                // coarse stage: fixed wirings 0,4,8,12,16
        always @* case (sh[4:2])
            3'd0: coarse = fine;        3'd1: coarse = fine << 4;  3'd2: coarse = fine << 8;
            3'd3: coarse = fine << 12;  3'd4: coarse = fine << 16; default: coarse = 18'h0;
        endcase
        wire [17:0] sy = SHIFT_CF ? coarse : (sx << sh);
        wire [17:0] sy_rev = {sy[0],sy[1],sy[2],sy[3],sy[4],sy[5],sy[6],sy[7],sy[8],sy[9],sy[10],sy[11],sy[12],sy[13],sy[14],sy[15],sy[16],sy[17]};
        always @* shift_out = {14'b0, (mode == 3'd6) ? sy_rev : sy};
        always @* case (mode)
            3'd5, 3'd6: result = shift_out;
            3'd7: result = nano_sel;
            3'd2: result = {31'h0, ~s33[32]};
            3'd3: result = s33[32] ? 32'd0 : (s33 == 33'd0) ? 32'd1 : 32'd2;
            default: result = s33[31:0];
        endcase
    end else begin : g_naive
        wire [31:0] b_in = (mode == 3'd1) ? ~in_b : in_b;
        wire [31:0] sum; wire cout;
        adder_v1 #(.WIDTH(32)) ADD (.a(in_a), .b(b_in), .cin(mode == 3'd1), .sum(sum), .cout(cout));
        wire ge = ($signed(in_a) >= $signed(in_b));
        wire lt = ($signed(in_a) < $signed(in_b)), eq = (in_a == in_b);
        wire [31:0] delta = (inc && !dec) ? step_ext : (dec && !inc) ? -step_ext : 32'h0;
        wire [31:0] next = total + delta;
        wire [17:0] shl = in_a[17:0] << sh;
        wire [17:0] shr = in_a[17:0] >> sh;
        always @* shift_out = {14'b0, (mode == 3'd6) ? shr : shl};
        always @* case (mode)
            3'd5, 3'd6: result = shift_out;
            3'd7: result = nano_sel;
            3'd2: result = {31'h0, ge};
            3'd3: result = lt ? 32'd0 : eq ? 32'd1 : 32'd2;
            3'd4: result = next;
            default: result = sum;
        endcase
    end endgenerate
    assign data_out = out_buffer; assign valid_out = valid_out_r;
    always @(posedge clk) begin
        if (rst) begin mode <= 3'd0; step <= 8'h0; topo <= 10'h0; heldsrc <= 1'b0; armed <= 1'b0; total <= 32'h0; out_buffer <= 32'h0; valid_out_r <= 1'b0; end
        else if (cfg_valid) begin mode <= cfg_data[2:0]; step <= cfg_data[15:8]; topo <= cfg_data[25:16]; heldsrc <= cfg_data[26]; armed <= 1'b1; total <= 32'h0; out_buffer <= 32'h0; valid_out_r <= 1'b0; end
        else begin
            if (pulse) total <= result;
            out_buffer  <= result;
            valid_out_r <= armed && valid_in;   // v4: EVERY word is answered (accumulate with no pulse returns the unchanged total)
        end
    end
endmodule
