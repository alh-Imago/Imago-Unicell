`default_nettype none
// hexn_ramroute_probe_v2 -- MEASUREMENT PROTOTYPE (2 Nov 2026, Alan 07:40): RAM-routing cell, how the held word is RELEASED. Counts only, NOT function-tested (yosys 0.69, -nowidelut).
//   REL = 0 TIMED   : release a configured number of clocks (dly) after the word was written (a read pointer that trails the write pointer by dly). No trigger input.
//   REL = 1 TRIGGER : release when a pulse arrives on face tsel. The word's start is marked by a start flag on face wsel (the UniCell cell has a start flag per word); the cell stores the write pointer at that flag,
//                     and on the trigger starts reading from it for 32 clocks (a 6-bit counter). No dly register.
//   REL = 2 BOTH    : trigger starts a read that is delayed by dly clocks more (trigger + delay); both selects present.
//   mode 0 pass, mode 1 hold (released as above), mode 2 repeat (record len bits, replay forever). Six faces in, six registered faces out, one stream held, others still route.
module hexn_ramroute_probe_v2 #(parameter DEPTH = 64, parameter AW = 6, parameter REL = 0) (input wire clk, input wire [5:0] fi, output reg [5:0] fo, input wire cfg_en, input wire cfg_in, output wire cfg_out);
    localparam CW = 18 + 2 + 3 + 3 + AW + AW + 3 + 3;
    reg [CW-1:0] cfg = 0; assign cfg_out = cfg[CW-1];
    always @(posedge clk) if (cfg_en) cfg <= {cfg[CW-2:0], cfg_in};
    wire [1:0] mode = cfg[19:18]; wire [2:0] hsel = cfg[22:20]; wire [2:0] hout = cfg[25:23];
    wire [AW-1:0] dly = cfg[25+AW:26]; wire [AW-1:0] len = cfg[25+2*AW:26+AW];
    wire [2:0] tsel = cfg[28+2*AW:26+2*AW]; wire [2:0] wsel = cfg[31+2*AW:29+2*AW];
    wire [7:0] fx = {2'b00, fi}; wire din = fx[hsel];
    wire trig = fx[tsel]; wire wflag = fx[wsel];
    reg mem [0:DEPTH-1]; reg [AW-1:0] wp = 0, rp = 0, wp0 = 0; reg q = 1'b0; reg rec = 1'b1;
    reg run = 1'b0; reg [5:0] bc = 0; reg [AW-1:0] pre = 0; reg pend = 1'b0;
    always @(posedge clk) begin
        if (mode == 2'd1) begin
            mem[wp] <= din; wp <= wp + 1'b1;
            if (REL == 0) begin rp <= wp - dly; q <= mem[rp]; end
            else begin
                if (wflag) wp0 <= wp;
                if (trig && !run && !pend) begin if (REL == 2 && dly != 0) begin pend <= 1'b1; pre <= dly; end else begin run <= 1'b1; rp <= wp0; bc <= 0; end end
                if (pend) begin pre <= pre - 1'b1; if (pre == 1) begin pend <= 1'b0; run <= 1'b1; rp <= wp0; bc <= 0; end end
                if (run) begin q <= mem[rp]; rp <= rp + 1'b1; bc <= bc + 1'b1; if (bc == 31) run <= 1'b0; end else q <= 1'b0;
            end
        end else if (mode == 2'd2) begin
            if (rec) begin mem[wp] <= din; wp <= wp + 1'b1; if (wp == len - 1'b1) begin rec <= 1'b0; rp <= 0; end end
            else begin q <= mem[rp]; rp <= (rp == len - 1'b1) ? {AW{1'b0}} : rp + 1'b1; end
        end else begin wp <= 0; rp <= 0; rec <= 1'b1; run <= 1'b0; pend <= 1'b0; end
    end
    integer j;
    always @(posedge clk) for (j = 0; j < 6; j = j + 1) fo[j] <= (mode != 2'd0 && hout == j) ? q : fx[cfg[3 * j +: 3]];
endmodule
