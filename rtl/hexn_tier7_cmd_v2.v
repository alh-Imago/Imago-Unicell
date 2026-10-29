`timescale 1ns/1ps
// hexn_tier7_cmd_v2.v -- byte command layer for hexn_tier_v8 (the Kintex memory tier), meant to sit on the byte stream of hexn_jtag_bridge_v1 (rx_d/rx_v from the host, tx_d/tx_s/tx_b to the host) so a PC reads and writes the store over JTAG. Contains the tier. New file. v2 (29 Oct 2026, Alan: clearing the store must be part of the loading sequence instead of reloading the bitstream): clone of v1 (v1 untouched) plus 0x47 CLEAR -> STATUS (1 byte): resets the tier (all tables, presence counters, written bits, line buffer, the 17 counters and the sticky DDR3 error) without touching the DDR3 contents or the command layer; the answer comes when the tier is ready again (about 2^max(FB,RAMB,BMB,SB) clocks, 131,072 at the Kintex sizes = 1.6 ms at 83.33 MHz). Lines already in the DDR3 are no longer reachable (their written bits are cleared), so a LINE read after CLEAR returns written 0.
// All numbers are little-endian. Every command is answered; an unknown opcode is answered with the single byte 0xEE. STATUS byte = {5'b0, ready, ddr_err, found}: bit 0 = found (GET), bit 1 = a DDR3 error happened (sticky, tier or dump read), bit 2 = ready.
//   0x40 PUT   key[4] value[4]            -> STATUS                       store the value (key, value are KW / VW bits, upper bits ignored)
//   0x41 GET   key[4]                     -> STATUS value[4]              value is 0 when not found
//   0x42 FLUSH                            -> STATUS                       write the line buffer back to the DDR3
//   0x43 COUNTERS                         -> 68 bytes                     the 17 counters of the tier, 4 bytes each, in the order of hexn_tier_v7.v (fast_hit ... put_new)
//   0x44 INFO                             -> STATUS KW VW FB BMB RAMB SB 8 (the bucket size)
//   0x45 LEVEL lvl[1] idx[4]              -> 8 bytes                      entry idx of level lvl (0 = LUT table, 1 = block RAM table): word0[4] word1[4]; word0 = {1'b1 valid, zeros, hash h} (0 = empty), word1 = value (the same entry format as the DDR3 lines)
//   0x46 LINE  line[4]                    -> STATUS written[1] data[72]   flushes first, then reads DDR3 line DDR_BASE + line (8 entries x 8 bytes: word0, word1). written 0 = the line was never written; data is then zeros.
// Reading out everything: INFO, FLUSH, LEVEL 0 for every slot, LEVEL 1 for every slot, LINE for every line (tools/hexn_tier7_host_v1.py does it and saves it to a file).
// The host must read the whole answer of a command before it sends the next one (bytes that arrive while the layer is answering are lost); Tier7Dev does. The bytes of a command come at any speed (the bridge delivers one every FSPACING clocks); there is no timeout inside a command, so a host that stops mid-command leaves the layer waiting: reset it (resetn) to resynchronise.
module hexn_tier7_cmd_v2 #(parameter KW = 24, parameter VW = 24, parameter FB = 10, parameter BMB = 17, parameter RAMB = 14, parameter SB = 17, parameter DDR_BASE = 0) (
    input  wire clk, input wire resetn,
    input  wire [7:0] rx_d, input wire rx_v, output reg [7:0] tx_d, output reg tx_s, input wire tx_b,
    input  wire ddr_ready,
    output wire wb_stb, output wire wb_we, output wire [24:0] wb_addr, output wire [575:0] wb_data, input wire wb_stall, input wire wb_ack, input wire [575:0] wb_rdata,
    output wire t_ready, output wire t_ddr_err);
    localparam TG = KW - FB, EWD = 1 + TG + VW, MWD = 1 + KW + VW;
    reg cmd_valid, cmd_we, cmd_flush; reg [KW-1:0] t_key; reg [VW-1:0] t_wdata;
    wire busy, done, found, ready, ddr_err; wire [VW-1:0] rdata; wire [32*17-1:0] cnts;
    wire t_stb, t_we; wire [24:0] t_addr; wire [575:0] t_data;
    reg [FB-1:0] dbg_fa; wire [EWD-1:0] dbg_fq; reg [RAMB-1:0] dbg_ma; wire [MWD-1:0] dbg_mq; reg [SB-1:0] dbg_wa; wire dbg_wq;
    hexn_tier_v8 #(.KW(KW), .VW(VW), .FB(FB), .BMB(BMB), .RAMB(RAMB), .SB(SB), .DDR_BASE(DDR_BASE)) tier (.clk(clk), .resetn(resetn & ~tsoft), .cmd_valid(cmd_valid), .cmd_we(cmd_we), .cmd_flush(cmd_flush), .key(t_key), .wdata(t_wdata),
        .busy(busy), .done(done), .found(found), .rdata(rdata), .ready(ready), .cnts(cnts), .ddr_err(ddr_err), .ddr_ready(ddr_ready),
        .dbg_fa(dbg_fa), .dbg_fq(dbg_fq), .dbg_ma(dbg_ma), .dbg_mq(dbg_mq), .dbg_wa(dbg_wa), .dbg_wq(dbg_wq),
        .wb_stb(t_stb), .wb_we(t_we), .wb_addr(t_addr), .wb_data(t_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(wb_rdata));
    // the dump read of a DDR3 line uses the same Wishbone port while the tier is idle
    reg tsoft; reg [2:0] clr_n;
    reg dump_act, d_stb; reg [24:0] d_addr;
    assign wb_stb = dump_act ? d_stb : t_stb; assign wb_we = dump_act ? 1'b0 : t_we; assign wb_addr = dump_act ? d_addr : t_addr; assign wb_data = t_data;
    assign t_ready = ready; reg dump_err; assign t_ddr_err = ddr_err | dump_err;
    wire [7:0] status = {5'b0, ready, ddr_err | dump_err, found_l};
    reg found_l;
    reg [7:0] txq [0:79]; reg [6:0] txn, txi; reg [63:0] arg; reg [3:0] na, ai; reg [7:0] op; reg [575:0] line; reg [12:0] tmo; reg wr_l; reg [7:0] lvl;
    localparam C_OP = 0, C_ARG = 1, C_RUN = 2, C_RUN2 = 3, C_WAIT = 4, C_RESP = 5, C_DRN = 6, C_DRN1 = 7, C_DRN2 = 8, C_LV1 = 9, C_LV2 = 10, C_LN1 = 11, C_LN2 = 12, C_LN3 = 13, C_LN4 = 14, C_LN5 = 15, C_LN6 = 16, C_CLR1 = 17, C_CLR2 = 18;
    reg [4:0] st; integer i;
    wire [31:0] rd32 = found ? {{(32-VW){1'b0}}, rdata} : 32'd0;
    wire [31:0] w0f = dbg_fq[EWD-1] ? {1'b1, {(31-KW){1'b0}}, dbg_fq[EWD-2:VW], dbg_fa} : 32'd0;
    wire [31:0] w1f = dbg_fq[EWD-1] ? {{(32-VW){1'b0}}, dbg_fq[VW-1:0]} : 32'd0;
    wire [31:0] w0m = dbg_mq[MWD-1] ? {1'b1, {(31-KW){1'b0}}, dbg_mq[VW +: KW]} : 32'd0;
    wire [31:0] w1m = dbg_mq[MWD-1] ? {{(32-VW){1'b0}}, dbg_mq[VW-1:0]} : 32'd0;
    task put32(input [6:0] at, input [31:0] v); begin txq[at] <= v[7:0]; txq[at+1] <= v[15:8]; txq[at+2] <= v[23:16]; txq[at+3] <= v[31:24]; end endtask
    always @(posedge clk) begin
        tx_s <= 1'b0; cmd_valid <= 1'b0;
        if (!resetn) begin tsoft <= 0; clr_n <= 0; st <= C_OP; tx_d <= 0; dump_act <= 0; d_stb <= 0; dump_err <= 0; found_l <= 0; txn <= 0; txi <= 0; cmd_we <= 0; cmd_flush <= 0; tmo <= 0; end
        else begin
            case (st)
            C_OP: if (rx_v) begin
                op <= rx_d; arg <= 64'd0; ai <= 0;
                case (rx_d)
                    8'h40: begin na <= 8; st <= C_ARG; end
                    8'h41: begin na <= 4; st <= C_ARG; end
                    8'h42: begin na <= 0; st <= C_RUN; end
                    8'h43: begin na <= 0; st <= C_RUN; end
                    8'h44: begin na <= 0; st <= C_RUN; end
                    8'h45: begin na <= 5; st <= C_ARG; end
                    8'h46: begin na <= 4; st <= C_ARG; end
                    8'h47: begin na <= 0; st <= C_RUN; end
                    default: begin txq[0] <= 8'hEE; txn <= 1; txi <= 0; st <= C_DRN; end
                endcase
            end
            C_ARG: if (rx_v) begin
                arg[8*ai +: 8] <= rx_d; ai <= ai + 4'd1; if (ai + 4'd1 == na) st <= C_RUN;
            end
            C_RUN: begin
                case (op)
                8'h40: begin t_key <= arg[KW-1:0]; t_wdata <= arg[32 +: VW]; cmd_we <= 1; cmd_flush <= 0; cmd_valid <= 1; st <= C_RUN2; end
                8'h41: begin t_key <= arg[KW-1:0]; t_wdata <= 0; cmd_we <= 0; cmd_flush <= 0; cmd_valid <= 1; st <= C_RUN2; end
                8'h42: begin cmd_we <= 0; cmd_flush <= 1; cmd_valid <= 1; st <= C_RUN2; end
                8'h43: begin for (i = 0; i < 68; i = i + 1) txq[i] <= cnts[8*i +: 8]; txn <= 68; txi <= 0; st <= C_DRN; end
                8'h44: begin txq[0] <= {5'b0, ready, ddr_err | dump_err, 1'b0}; txq[1] <= KW; txq[2] <= VW; txq[3] <= FB; txq[4] <= BMB; txq[5] <= RAMB; txq[6] <= SB; txq[7] <= 8; txn <= 8; txi <= 0; st <= C_DRN; end
                8'h45: begin
                    lvl <= arg[7:0];
                    if (arg[7:0] == 8'd0) begin dbg_fa <= arg[8 +: FB]; end else begin dbg_ma <= arg[8 +: RAMB]; end
                    st <= C_LV1;
                end
                8'h46: begin cmd_we <= 0; cmd_flush <= 1; cmd_valid <= 1; st <= C_LN1; end
                8'h47: begin tsoft <= 1; clr_n <= 0; st <= C_CLR1; end
                endcase
            end
            C_CLR1: begin clr_n <= clr_n + 3'd1; if (clr_n == 3'd3) begin tsoft <= 0; st <= C_CLR2; end end      // hold the tier's reset for a few clocks
            C_CLR2: if (ready) begin dump_err <= 0; found_l <= 0; txq[0] <= {5'b0, 1'b1, 1'b0, 1'b0}; txn <= 1; txi <= 0; st <= C_DRN; end   // the tier cleared its tables and is ready again
            C_RUN2: st <= C_WAIT;   // the command has been taken; wait for done
            C_WAIT: if (done) begin
                found_l <= found;
                txq[0] <= {5'b0, ready, ddr_err | dump_err, found};
                if (op == 8'h41) begin txq[1] <= rd32[7:0]; txq[2] <= rd32[15:8]; txq[3] <= rd32[23:16]; txq[4] <= rd32[31:24]; txn <= 5; end else txn <= 1;
                txi <= 0; st <= C_DRN;
            end
            // level read: address set, one clock for the memory read, one for the register
            C_LV1: st <= C_LV2;
            C_LV2: begin
                if (lvl == 8'd0) begin put32(0, w0f); put32(4, w1f); end else begin put32(0, w0m); put32(4, w1m); end
                txn <= 8; txi <= 0; st <= C_DRN;
            end
            // line read: after the flush, the written bit, then the line
            C_LN1: st <= C_LN2;                                              // command taken
            C_LN2: if (done) begin dbg_wa <= arg[SB-1:0]; st <= C_LN3; end
            C_LN3: st <= C_LN4;                                              // wait for the memory read of the written bit
            C_LN4: begin
                wr_l <= dbg_wq;
                if (dbg_wq) begin dump_act <= 1; d_stb <= 1; d_addr <= DDR_BASE + {{(25-SB){1'b0}}, arg[SB-1:0]}; tmo <= 0; st <= C_LN5; end
                else begin line <= 576'd0; st <= C_LN6; end
            end
            C_LN5: begin
                tmo <= tmo + 13'd1;
                if (d_stb) begin if (!wb_stall) d_stb <= 0; end
                else if (wb_ack) begin line <= wb_rdata; dump_act <= 0; st <= C_LN6; end
                if (tmo == 13'd4095) begin dump_err <= 1; d_stb <= 0; dump_act <= 0; line <= 576'd0; st <= C_LN6; end
            end
            C_LN6: begin
                txq[0] <= status; txq[1] <= {7'b0, wr_l};
                for (i = 0; i < 72; i = i + 1) txq[2 + i] <= line[8*i +: 8];
                txn <= 74; txi <= 0; st <= C_DRN;
            end
            // send txq[0 .. txn-1], one byte at a time
            C_DRN: begin
                if (txi == txn) st <= C_OP;
                else if (!tx_b && !tx_s) begin tx_d <= txq[txi]; tx_s <= 1'b1; txi <= txi + 7'd1; st <= C_DRN1; end
            end
            C_DRN1: st <= C_DRN2;
            C_DRN2: st <= C_DRN;
            default: st <= C_OP;
            endcase
        end
    end
endmodule
