// hexn_tier: the Kintex memory tier (LUT table -> block RAM -> DDR3 bucket lines) AND the Hex-N core in ONE bitstream. Same idea as hexn_joint (drop-in replacement for ypcb designs/uberddr3/memtest.v: SAME module name and ports, so the generated uberddr3 top level, its pins and its USER1 debug register stay as they are), but the DDR3 Wishbone port that memtest.v drives belongs to the tier here, not to a test.
//   JTAG USER1 (IR 0x02): ypcb's own DDR3 debug register (calibration status etc.). Its memory-test results read zero here, except errors = 1 if the tier saw a DDR3 error.
//   JTAG USER2 (IR 0x03): Hex-N core (`HX_CORE: hexn_core_v9 by default, set by prebuild.py) through hexn_jtag_bridge_v1 CHAIN 2, as in hexn_joint.
//   JTAG USER3 (IR 0x22): the tier's command layer (rtl/hexn_tier7_cmd_v1.v) through hexn_jtag_bridge_v1 CHAIN 3; host: tools/hexn_tier7_card_v1.py with HEXN_CHAIN=3.
// Everything runs on this module's clk (the DDR3 controller clock, 83.33 MHz). Sizes come from defines written by prebuild.py (TIER_KW ... TIER_SB). NOT built, NOT run on the card.
module memtest #(
    parameter integer ADDR_BITS = 25,
    parameter integer DATA_BITS = 576
) (
    input wire clk,
    input wire ready,
    input wire start,
    input wire [1:0] mode,
    input wire [4:0] len,
    input wire [7:0] seed,
    output wire busy,
    output wire [31:0] errors,
    output wire [31:0] first_err_addr,
    output wire [DATA_BITS / 8 - 1:0] err_mask,
    output wire [31:0] write_cycles,
    output wire [31:0] read_cycles,
    output wire wb_stb,
    output wire wb_we,
    output wire [ADDR_BITS - 1:0] wb_addr,
    output wire [DATA_BITS - 1:0] wb_data,
    input wire wb_stall,
    input wire wb_ack,
    input wire [DATA_BITS - 1:0] wb_rdata
);
    // power-on reset for the tier and its command layer (the registers start at 0 in the FPGA)
    reg [7:0] por = 8'd0; always @(posedge clk) if (por != 8'hFF) por <= por + 8'd1;
    wire resetn = (por == 8'hFF);
    // ---- the tier on USER3 ----
    wire [7:0] tr_rx_d, tr_tx_d; wire tr_rx_v, tr_tx_s, tr_tx_b; wire t_ready, t_ddr_err;
    hexn_jtag_bridge_v1 #(.CHAIN(3), .FSPACING(128)) tr_br (.clk(clk), .rst(~resetn), .rx_d(tr_rx_d), .rx_v(tr_rx_v), .tx_d(tr_tx_d), .tx_s(tr_tx_s), .tx_b(tr_tx_b));
    hexn_tier7_cmd_v1 #(.KW(`TIER_KW), .VW(`TIER_VW), .FB(`TIER_FB), .BMB(`TIER_BMB), .RAMB(`TIER_RAMB), .SB(`TIER_SB), .DDR_BASE(0)) tier (
        .clk(clk), .resetn(resetn), .rx_d(tr_rx_d), .rx_v(tr_rx_v), .tx_d(tr_tx_d), .tx_s(tr_tx_s), .tx_b(tr_tx_b), .ddr_ready(ready),
        .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata), .t_ready(t_ready), .t_ddr_err(t_ddr_err));
    // ---- Hex-N on USER2 ----
    wire [7:0] hx_rx_d, hx_tx_d; wire hx_rx_v, hx_tx_s, hx_tx_b; wire [5:0] hx_led;
    hexn_jtag_bridge_v1 #(.CHAIN(2), .FSPACING(128)) hx_br (.clk(clk), .rst(1'b0), .rx_d(hx_rx_d), .rx_v(hx_rx_v), .tx_d(hx_tx_d), .tx_s(hx_tx_s), .tx_b(hx_tx_b));
    `HX_CORE hx_core (.clk(clk), .rx_d(hx_rx_d), .rx_v(hx_rx_v), .tx_d(hx_tx_d), .tx_s(hx_tx_s), .tx_b(hx_tx_b), .led(hx_led));
    // ---- the old memory-test fields ----
    assign busy = 1'b0; assign errors = {31'd0, t_ddr_err}; assign first_err_addr = 32'd0; assign err_mask = {(DATA_BITS / 8){1'b0}};
    assign write_cycles = 32'd0; assign read_cycles = 32'd0;
endmodule
