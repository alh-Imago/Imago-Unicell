// hexn_bnet (9 Nov 2026): the MERGED bus network (hexn_bnet_net_v2: serialisers with a register, merger, buses, tables, cells, feedback) on the YPCB-00338-1P1 (Kintex-7 XC7K480T), built with the openXC7 flow, as a SIZE AND CLOCK test only.
// The card has no pins to drive it, so a free-running LFSR feeds the wrapper's single input; the wrapper shifts that into every input of the network (event lines, table writes, threshold writes) and folds every output into one bit. That exercises the logic and keeps all of it from being optimised away, but it is not a functional test: no table is loaded on purpose and nothing is read back. Pins: SYS_CLK (50 MHz), led[2:0] as designs/hello of the ypcb-00338-1p1 repo. led[0] = heartbeat (~1.5 Hz), led[1] = folded network output, led[2] = LFSR bit.
// The RTL is not in this folder: prebuild.py gathers it from the Imago-Unicell checkout (HEXN_REPO) into the build directory as gen_00_bnet.v, together with the wrapper hexn_bnet_pnr_top_v1 whose shape parameters it sets (HEXN_G, HEXN_PER, HEXN_NIN, HEXN_SQL, HEXN_FB).
module hexn_bnet (input SYS_CLK, output [2:0] led);
    reg [31:0] count = 0; always @(posedge SYS_CLK) count <= count + 1;
    reg [31:0] lfsr = 32'hACE1_2468; always @(posedge SYS_CLK) lfsr <= {lfsr[0], lfsr[31:1]} ^ (lfsr[0] ? 32'h8020_0003 : 32'd0);
    wire sout; hexn_bnet_pnr_top_v1 w (.clk(SYS_CLK), .sin(lfsr[0]), .sout(sout));
    assign led = {lfsr[0], sout, count[25]};
endmodule
