`timescale 1ns/1ps
// wb_ddr_model_v1.v -- SIMULATION ONLY: behavioural stand-in for the UberDDR3 Wishbone port of the Kintex card as seen by hexn_ddr3_port_v1. Pipelined: a request is accepted when i_stb and not o_stall; answers come in order, LAT (+ a pseudo-random 0..JIT) clocks after the request, reads with the data in the same clock as o_ack. Stalls: o_stall is high on a pseudo-random STALLP out of 16 clocks. WRACK = 0 makes writes silent (no ack) to test the adapter's fault counter. Lines start at zero. i_sel is applied per byte.
module wb_ddr_model_v1 #(parameter ADDR_BITS = 25, parameter DATA_BITS = 576, parameter LINES = 1024, parameter LAT = 9, parameter JIT = 3, parameter STALLP = 4, parameter WRACK = 1, parameter READY_AFTER = 40) (
    input wire clk, input wire resetn, output reg o_ready = 1'b0,
    input wire i_stb, input wire i_we, input wire [ADDR_BITS-1:0] i_addr, input wire [DATA_BITS-1:0] i_data, input wire [DATA_BITS/8-1:0] i_sel,
    output wire o_stall, output reg o_ack, output reg [DATA_BITS-1:0] o_data);
    reg [DATA_BITS-1:0] mem [0:LINES-1]; integer i;
    initial for (i = 0; i < LINES; i = i + 1) mem[i] = 0;
    reg [31:0] lfsr = 32'h1234ABCD; reg [31:0] cyc = 0, rdyc = 0; initial begin o_ack = 0; o_data = 0; end
    always @(posedge clk) begin lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]}; cyc <= cyc + 1; end
    assign o_stall = (lfsr[3:0] < STALLP) || !o_ready;
    // request queue
    reg q_we [0:63]; reg [ADDR_BITS-1:0] q_a [0:63]; reg [DATA_BITS-1:0] q_d [0:63]; reg [DATA_BITS/8-1:0] q_s [0:63]; reg [31:0] q_t [0:63]; integer qh = 0, qt = 0; reg [31:0] last_t = 0;
    integer k; reg [DATA_BITS-1:0] cur, nd;
    always @(posedge clk) begin
        o_ack <= 1'b0;
        if (!resetn) begin o_ready <= 0; rdyc <= 0; end
        else begin
            if (!o_ready) begin rdyc <= rdyc + 1; if (rdyc == READY_AFTER) o_ready <= 1; end
            if (i_stb && !o_stall) begin
                q_we[qt % 64] = i_we; q_a[qt % 64] = i_addr; q_d[qt % 64] = i_data; q_s[qt % 64] = i_sel;
                q_t[qt % 64] = ((cyc + LAT + (lfsr[9:8] % (JIT + 1))) > last_t) ? (cyc + LAT + (lfsr[9:8] % (JIT + 1))) : last_t + 1; last_t = q_t[qt % 64]; qt = qt + 1;
            end
            if (qh < qt && cyc >= q_t[qh % 64]) begin
                cur = mem[q_a[qh % 64] % LINES];
                if (q_we[qh % 64]) begin
                    nd = cur; for (k = 0; k < DATA_BITS / 8; k = k + 1) if (q_s[qh % 64][k]) nd[8 * k +: 8] = q_d[qh % 64][8 * k +: 8];
                    mem[q_a[qh % 64] % LINES] = nd; o_ack <= (WRACK != 0); o_data <= 0;
                end else begin o_ack <= 1'b1; o_data <= cur; end
                qh = qh + 1;
            end
        end
    end
endmodule
