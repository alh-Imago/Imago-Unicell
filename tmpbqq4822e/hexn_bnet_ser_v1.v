`default_nettype none
`timescale 1ns / 1ps
// hexn_bnet_ser_v1 (8 Nov 2026): SOURCE SERIALISER of the merged bus network design. N sources (cells of one bus, or external input lines) each have one pending bit. All events of a clock are taken at once; ONE pending source per clock is sent out (first set bit at or after a rotating pointer, so none starves). An event on a source whose bit is still pending is merged (lost) and counted.
// BYP=1 (input lines): events of this clock can be sent in the same clock. BYP=0 (cells): the fire of clock t is registered and sent from clock t+1.
module hexn_bnet_ser_v1 #(parameter N = 16, parameter IW = 4, parameter BYP = 0) (
    input wire clk, input wire [N-1:0] ev, output wire o_v, output wire [IW-1:0] o_i, output reg [15:0] merged);
    reg [N-1:0] pend = 0; reg [IW-1:0] ptr = 0; initial merged = 0;
    wire [N-1:0] a = BYP ? (pend | ev) : pend;
    reg found; reg [IW-1:0] idx; integer k, j;
    always_comb begin
        found = 1'b0; idx = {IW{1'b0}};
        for (k = 0; k < N; k = k + 1) begin
            j = (ptr + k) % N;
            if (!found && a[j]) begin found = 1'b1; idx = j[IW-1:0]; end
        end
    end
    assign o_v = found; assign o_i = idx;
    reg [N-1:0] oh, lostv; integer m, pc;
    always_comb begin oh = {N{1'b0}}; for (m = 0; m < N; m = m + 1) if (found && idx == m) oh[m] = 1'b1; lostv = BYP ? (ev & pend) : (ev & pend & ~oh); pc = 0; for (m = 0; m < N; m = m + 1) if (lostv[m]) pc = pc + 1; end
    always @(posedge clk) begin
        if (found) ptr <= (idx == N - 1) ? {IW{1'b0}} : idx + 1'b1;
        if (BYP) pend <= a & ~oh; else pend <= (pend & ~oh) | ev;
        merged <= merged + pc[15:0];
    end
endmodule
