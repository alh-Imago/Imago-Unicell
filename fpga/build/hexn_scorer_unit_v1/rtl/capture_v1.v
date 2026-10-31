// capture_v1.v -- ledger #1036: the other end of playout_v1. Takes the design's result words (flex exit ports: data + valid + ack) into a RAM, in arrival order,
// each tagged with the exit it came from, so the host (JTAG / UART / SD card) can read them back afterwards. Round-robin between exits; one word per cycle.
// Stored word = {tag, data} (tag is TAGW bits, 0 when there is only one exit). Plain synchronous-read array -> block RAM on Quartus and Gowin.
`default_nettype none
module capture_v1 #(
    parameter OUTS  = 1,
    parameter WIDTH = 32,
    parameter AW    = 10,
    parameter TAGW  = (OUTS > 1) ? $clog2(OUTS) : 1
) (
    input  wire                     clk,
    input  wire                     rst,
    input  wire                     clear,         // one-cycle pulse: forget everything captured
    input  wire [OUTS*WIDTH-1:0]    out_data,
    input  wire [OUTS-1:0]          out_valid,
    output wire [OUTS-1:0]          out_ack,
    output reg  [AW:0]              count,         // words captured so far
    // read port (host side): rd_data is valid one cycle after rd_addr
    input  wire [AW-1:0]            rd_addr,
    output reg  [WIDTH+TAGW-1:0]    rd_data
);
    reg [WIDTH+TAGW-1:0] mem [0:(1<<AW)-1];
    reg [TAGW-1:0] rr;
    reg [TAGW-1:0] pick;
    reg            have;
    integer k;
    always @* begin
        have = 1'b0; pick = {TAGW{1'b0}};
        for (k = 0; k < OUTS; k = k + 1) begin
            if (!have && out_valid[(rr + k) % OUTS]) begin have = 1'b1; pick = (rr + k) % OUTS; end
        end
        if (count[AW]) have = 1'b0;                  // full: stop taking (the design stalls, nothing is lost)
    end
    genvar g;
    generate for (g = 0; g < OUTS; g = g + 1) begin : A
        assign out_ack[g] = have && (pick == g);
    end endgenerate
    always @(posedge clk) begin
        if (rst || clear) begin count <= 0; rr <= 0; end
        else if (have) begin
            mem[count[AW-1:0]] <= {pick, out_data[pick*WIDTH +: WIDTH]};
            count <= count + 1;
            rr <= (pick == OUTS-1) ? 0 : pick + 1'b1;
        end
    end
    always @(posedge clk) rd_data <= mem[rd_addr];
endmodule
`default_nettype wire
