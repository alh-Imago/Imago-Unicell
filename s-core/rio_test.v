// rio_test.v - cost of the word-RAM digit select and write accumulator (ledger #1365): today's 1-bit version (rio1) against a run-time width 1..16 version (rio16).
// Same structure as sc_sys_v15.v lines 475-480: read = pick bits of a 32-bit word; write = insert bits into a 32-bit accumulator.
module rio1 (input clk, input [31:0] word, input [4:0] k, input wd, input we, output rd, output reg [31:0] acc);
    assign rd = word[k];
    wire [31:0] nx = (acc & ~(32'd1 << k)) | ({31'b0, wd} << k);
    always @(posedge clk) if (we) acc <= nx;
endmodule
module rio16 (input clk, input [31:0] word, input [4:0] k, input [15:0] wd, input [2:0] lw, input we, output [15:0] rd, output reg [31:0] acc);
    // k = digit index (0 .. 32/W-1). Explicit choices per width (no variable shifts).
    wire [15:0] r0 = {15'b0, word[k]};
    wire [15:0] r1 = {14'b0, (k[3:0] == 0 ? word[1:0] : 2'b0)};
    reg [15:0] r;
    integer i;
    always @* begin
        case (lw)
            3'd0: r = {15'b0, word[k]};
            3'd1: r = {14'b0, word[{k[3:0],1'b0} +: 2]};
            3'd2: r = {12'b0, word[{k[2:0],2'b0} +: 4]};
            3'd3: r = {8'b0, word[{k[1:0],3'b0} +: 8]};
            default: r = k[0] ? word[31:16] : word[15:0];
        endcase
    end
    assign rd = r;
    reg [31:0] nx;
    always @* begin
        nx = acc;
        case (lw)
            3'd0: nx[k] = wd[0];
            3'd1: nx[{k[3:0],1'b0} +: 2] = wd[1:0];
            3'd2: nx[{k[2:0],2'b0} +: 4] = wd[3:0];
            3'd3: nx[{k[1:0],3'b0} +: 8] = wd[7:0];
            default: if (k[0]) nx[31:16] = wd; else nx[15:0] = wd;
        endcase
    end
    always @(posedge clk) if (we) acc <= nx;
endmodule
