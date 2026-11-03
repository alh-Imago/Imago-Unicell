`default_nettype none
// hexn_aligned_core_v2 = hexn_aligned_core_v1 (untouched) (3 Nov 2026, Alan 09:50 'the general wipe command'): adds a CLEAR input - while clear is 1 every state register goes to its idle value (words in flight, FIFO 'have' flags, counters, carries, routed registers). Hold it for at least 130 clocks if the pattern has RAM hold cells (their delay line is wiped one address per clock). The config chain is NOT touched. 
// hexn_aligned_core_v2 -- the ALIGNED two-input serial work core (3 Nov 2026, planner type AL): both operands arrive bit-serial, least significant bit first, with their start flags at the SAME clock (the planner places it only where they do), so no FIFO.
//   op 0 add, 1 sub (a - b), 2 and, 3 or, 4 xor (other values read as xor).  rs marks bit 0 of the result word (it is af, one clock later); the result is registered, so it shows one clock after the operands.
//   Mirrors the aligned branch of the word-level model (hexn_wrgrid_v8.Core). Function-tested through the tile (tests/vm/test_hexn_tile_al_v1.py).
module hexn_aligned_core_v2 (input wire clk, input wire clear, input wire [2:0] op, input wire a, input wire af, input wire b, output reg r, output reg rs);
    reg c = 1'b0;
    wire sub = (op == 3'd1);
    wire bb = b ^ sub;
    wire ci = af ? sub : c;
    wire sm = a ^ bb ^ ci;
    wire cn = (a & bb) | (a & ci) | (bb & ci);
    wire arith = (op == 3'd0) || sub;
    always @(posedge clk) begin
        rs <= af;
        r <= arith ? sm : (op == 3'd2) ? (a & b) : (op == 3'd3) ? (a | b) : (a ^ b);
        if (arith) c <= cn;
        if (clear) begin c <= 1'b0; r <= 1'b0; rs <= 1'b0; end
    end
    initial begin r = 1'b0; rs = 1'b0; end
endmodule
