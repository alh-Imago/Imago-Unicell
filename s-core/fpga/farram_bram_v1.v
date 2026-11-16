// farram_bram_v1.v - far RAM in the FPGA's own block RAM, with the same request / acknowledge interface as sdram_ctl.v (so the copy engine, the batch
// sequencer and the bridge are unchanged).  For the Kintex card, which has no SDRAM that the open toolchain drives yet (its DDR3 comes later, behind
// this same interface).  AW address bits = 2**AW words of 32 bits; the upper address bits are ignored (the copy window already limits the range).
// The SDRAM tuning inputs (cfg_*, reinit) are accepted and ignored.  Request: req_v & req_rdy hands over {req_we, req_a, req_wd}; ack_v pulses
// when done (ack_d = the word read, 0 for a write).  Two clocks per read, one per write.
module farram_bram_v1 #(parameter AW = 16) (
    input  wire        clk,
    input  wire        rst,
    input  wire [1:0]  cfg_cl,
    input  wire [1:0]  cfg_dly,
    input  wire        cfg_inv,
    input  wire        reinit,
    input  wire        req_v, req_we,
    input  wire [20:0] req_a,
    input  wire [31:0] req_wd,
    output wire        req_rdy,
    output reg         ack_v,
    output reg  [31:0] ack_d,
    output reg         init_done,
    output wire        busy
);
    (* ram_style = "block" *) reg [31:0] mem [0:(1<<AW)-1];
    reg [31:0] rd;
    reg        rd_pend = 0;
    reg [3:0]  initc = 0;
    assign busy    = rd_pend;
    assign req_rdy = init_done && !rd_pend && !rst;
    wire take = req_v && req_rdy;
    always @(posedge clk) begin
        ack_v <= 1'b0;
        if (rst) begin init_done <= 1'b0; initc <= 0; rd_pend <= 1'b0; end
        else begin
            if (!init_done) begin initc <= initc + 1'b1; if (initc == 4'hF) init_done <= 1'b1; end
            if (take) begin
                if (req_we) begin mem[req_a[AW-1:0]] <= req_wd; ack_v <= 1'b1; ack_d <= 32'd0; end
                else begin rd <= mem[req_a[AW-1:0]]; rd_pend <= 1'b1; end
            end
            if (rd_pend) begin ack_v <= 1'b1; ack_d <= rd; rd_pend <= 1'b0; end
        end
    end
endmodule
