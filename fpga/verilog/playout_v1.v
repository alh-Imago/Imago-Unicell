// playout_v1.v -- ledger #1036: a RAM that PLAYS OUT preloaded words into a design's entry ports by itself.
// The host (JTAG, UART, SD card ...) fills the RAM once through the write port (wr_*); `start` then streams it out with no host involvement.
// Words are stored item-major, lane-minor: address = item*LANES + lane, so item k's word for entry lane j sits at k*LANES + j.
// Each lane is a flex entry port: data + valid (held until ack) + ack. Lanes run independently; one RAM read per two cycles.
// The memory is a plain synchronous-read array: Quartus maps it to M10K/M20K, Gowin to BSRAM, yosys/iverilog simulate it. No vendor IP.
`default_nettype none
module playout_v1 #(
    parameter LANES = 4,
    parameter WIDTH = 32,
    parameter AW    = 10                         // RAM depth = 2**AW words
) (
    input  wire                     clk,
    input  wire                     rst,
    // load port (host side)
    input  wire                     wr_en,
    input  wire [AW-1:0]            wr_addr,
    input  wire [WIDTH-1:0]         wr_data,
    // control
    input  wire                     start,       // one-cycle pulse: play words 0 .. count-1
    input  wire [AW:0]              count,       // total words (items * LANES); must be a multiple of LANES
    // optional pacing for designs that cannot hold several items at once (a non-pipelined design): at most `max_out` results outstanding (0 = unlimited);
    // each item is expected to produce `rpi` results; `results` is the capture count (clear the capture RAM before a paced run)
    input  wire [AW:0]              max_out,
    input  wire [AW:0]              rpi,
    input  wire [AW:0]              results,
    output wire                     busy,
    output reg                      done,        // one-cycle pulse when the last word has been taken by its consumer
    // the lanes (to the design's in_*_data / in_*_valid / in_*_ack)
    output wire [LANES*WIDTH-1:0]   lane_data,
    output wire [LANES-1:0]         lane_valid,
    input  wire [LANES-1:0]         lane_ack
);
    localparam LW = (LANES > 1) ? $clog2(LANES) : 1;
    reg [WIDTH-1:0] mem [0:(1<<AW)-1];
    always @(posedge clk) if (wr_en) mem[wr_addr] <= wr_data;

    reg [AW:0]  total, issued;
    reg [AW+1:0] expected;
    wire gate_ok = (lane != 0) || (max_out == 0) || (results >= expected) || ((expected - results) < max_out);
    reg [LW-1:0] lane;
    reg         running, pending;
    reg [WIDTH-1:0] rdata;
    reg [WIDTH-1:0] ldata [0:LANES-1];
    reg [LANES-1:0] lvalid;
    reg [LW-1:0] pend_lane;

    always @(posedge clk) rdata <= mem[issued[AW-1:0]];   // synchronous read -> block RAM; the word asked for this cycle is in rdata next cycle

    genvar g;
    generate for (g = 0; g < LANES; g = g + 1) begin : L
        assign lane_data[g*WIDTH +: WIDTH] = ldata[g];
    end endgenerate
    assign lane_valid = lvalid;
    assign busy = running;

    integer i;
    always @(posedge clk) begin
        done <= 1'b0;
        if (rst) begin
            running <= 1'b0; pending <= 1'b0; lvalid <= {LANES{1'b0}}; issued <= 0; total <= 0; lane <= 0; pend_lane <= 0; expected <= 0;
        end else begin
            for (i = 0; i < LANES; i = i + 1) if (lvalid[i] && lane_ack[i]) lvalid[i] <= 1'b0;
            if (pending) begin                           // the word read last cycle lands in its lane
                ldata[pend_lane] <= rdata;
                lvalid[pend_lane] <= 1'b1;
                pending <= 1'b0;
            end else if (running && issued < total && !lvalid[lane] && gate_ok) begin
                pend_lane <= lane;
                pending <= 1'b1;
                issued <= issued + 1;
                if (lane == 0) expected <= expected + rpi;
                lane <= (lane == LANES-1) ? 0 : lane + 1'b1;
            end
            if (start) begin
                running <= 1'b1; total <= count; issued <= 0; lane <= 0; expected <= 0;
            end else if (running && issued >= total && !pending && (lvalid & ~lane_ack) == 0) begin
                running <= 1'b0; done <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
