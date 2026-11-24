// farram_bram_v2.v - farram_bram_v1 with the far RAM held as TWO separate banks of 2**(AW-1) words, chosen by the top address bit (ledger #1475).
// Reason: in Vivado the one 2**16-word array became 32 cascaded RAMB36E1 pairs and, for the 12- and 16-block builds, six of them failed DRC REQP-1962
// (ADDR15 pin check, #1474).  Two banks of 2**15 words need no cascade.  Same ports, same timing (one clock per write, two per read), same contents
// as v1 for every address.  v1 is left as proven.
module farram_bram_v2 #(parameter AW = 16) (
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
    (* ram_style = "block" *) reg [31:0] mem_lo [0:(1<<(AW-1))-1];
    (* ram_style = "block" *) reg [31:0] mem_hi [0:(1<<(AW-1))-1];
    reg [31:0] rd_lo, rd_hi;
    reg        rd_sel = 0;
    reg        rd_pend = 0;
    reg [3:0]  initc = 0;
    wire [AW-2:0] a_lo = req_a[AW-2:0];
    wire          a_hi = req_a[AW-1];
    assign busy    = rd_pend;
    assign req_rdy = init_done && !rd_pend && !rst;
    wire take = req_v && req_rdy;
    wire we_lo = take && req_we && !a_hi;
    wire we_hi = take && req_we &&  a_hi;
    wire rd_en = take && !req_we;
    // the two arrays have no reset and no other control, so each infers a plain simple-dual-port block RAM
    always @(posedge clk) begin if (we_lo) mem_lo[a_lo] <= req_wd; if (rd_en) rd_lo <= mem_lo[a_lo]; end
    always @(posedge clk) begin if (we_hi) mem_hi[a_lo] <= req_wd; if (rd_en) rd_hi <= mem_hi[a_lo]; end
    always @(posedge clk) begin
        ack_v <= 1'b0;
        if (rst) begin init_done <= 1'b0; initc <= 0; rd_pend <= 1'b0; end
        else begin
            if (!init_done) begin initc <= initc + 1'b1; if (initc == 4'hF) init_done <= 1'b1; end
            if (take) begin
                if (req_we) begin ack_v <= 1'b1; ack_d <= 32'd0; end
                else begin rd_sel <= a_hi; rd_pend <= 1'b1; end
            end
            if (rd_pend) begin ack_v <= 1'b1; ack_d <= rd_sel ? rd_hi : rd_lo; rd_pend <= 1'b0; end
        end
    end
endmodule
