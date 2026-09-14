// tb_ram_cell_v1_chain.v — R0 (FIXED source) -> R1 (flowing) -> R2 (flowing)
// -> stub consumer, all chained West<-East. Confirms the core #231 claim:
// a single consume at the near end (consumer acking R2) cascades a pull
// backward through the whole chain with NO dedicated request signal —
// R2 emptying makes its ready_out go high, which is what lets R1's own
// targets_all_ready see R2 as ready and fire toward it, and the same
// one level up for R0->R1. Runs many consumes in a row to confirm the
// chain keeps re-filling itself repeatedly, not just once.
// points.md #231/#235.
`timescale 1ns / 1ps

module tb_ram_cell_v1_chain;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg cfg0=0, cfg1=0, cfg2=0;
    reg [63:0] cfg0_d=0, cfg1_d=0, cfg2_d=0;

    localparam [31:0] SRC_VAL = 32'h000000AA;
    // R0: FIXED source. downstream=E(0100), upstream=0000, fixed=1, valid=1
    localparam [63:0] CFG_R0 = {22'h0, SRC_VAL, 1'b1, 1'b1, 4'b0000, 4'b0100};
    // R1: flowing. downstream=E(0100), upstream=W(1000), fixed=0, valid=0
    localparam [63:0] CFG_R1 = {22'h0, 32'h0,   1'b0, 1'b0, 4'b1000, 4'b0100};
    // R2: flowing. downstream=E(0100), upstream=W(1000), fixed=0, valid=0
    localparam [63:0] CFG_R2 = {22'h0, 32'h0,   1'b0, 1'b0, 4'b1000, 4'b0100};

    // R0 -> R1 (R0's east feeds R1's west)
    wire [31:0] r0_dout_e;
    wire        r0_fire_e, r0_ready_o, r0_ack_out_e;
    wire        r1_ready_o, r1_ack_out_w;

    // R1 -> R2 (R1's east feeds R2's west)
    wire [31:0] r1_dout_e;
    wire        r1_fire_e, r1_ack_out_e;
    wire        r2_ready_o, r2_ack_out_w;

    // R2 -> consumer
    wire [31:0] r2_dout_e;
    wire        r2_fire_e;
    reg         cons_ack = 0;
    reg         cons_ready = 1;

    wire status0, status1, status2;
    wire r2_ack_out_e_unused;

    ram_cell_v1 #(.CELL_ID(16'h0000)) R0 (
        .clk(clk), .rst(rst), .cfg_valid(cfg0), .cfg_data(cfg0_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(r0_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(r0_fire_e), .fire_w(),
        .ready_out(r0_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(r1_ready_o), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(r0_ack_out_e), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(r1_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid(status0)
    );

    ram_cell_v1 #(.CELL_ID(16'h0001)) R1 (
        .clk(clk), .rst(rst), .cfg_valid(cfg1), .cfg_data(cfg1_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(r0_dout_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(r0_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(r1_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(r1_fire_e), .fire_w(),
        .ready_out(r1_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(r2_ready_o), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(r1_ack_out_e), .ack_out_w(r1_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(r2_ack_out_w), .ack_in_w(r0_ack_out_e),
        .freeze_in(1'b0), .status_data_valid(status1)
    );

    ram_cell_v1 #(.CELL_ID(16'h0002)) R2 (
        .clk(clk), .rst(rst), .cfg_valid(cfg2), .cfg_data(cfg2_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(r1_dout_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(r1_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(r2_dout_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(r2_fire_e), .fire_w(),
        .ready_out(r2_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(r2_ack_out_e_unused), .ack_out_w(r2_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(r1_ack_out_e),
        .freeze_in(1'b0), .status_data_valid(status2)
    );

    integer received_count = 0;
    integer errors = 0;

    reg [1:0] consume_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (consume_state)
                0: if (r2_fire_e) begin
                       if (r2_dout_e !== SRC_VAL) begin
                           $display("[%0t] FAIL: consumer expected %h got %h", $time, SRC_VAL, r2_dout_e);
                           errors = errors + 1;
                       end
                       consume_state <= 1;
                   end
                1: begin
                       cons_ack <= 1'b1;
                       received_count = received_count + 1;
                       $display("[%0t] consumer receive #%0d value=%h  (R0 valid=%b R1 valid=%b R2 valid=%b)",
                                $time, received_count, r2_dout_e, status0, status1, status2);
                       consume_state <= 2;
                   end
                2: consume_state <= 0;
                default: consume_state <= 0;
            endcase
        end
    end

    initial begin
        #12 rst = 0;
        #10 cfg0=1; cfg0_d=CFG_R0;
            cfg1=1; cfg1_d=CFG_R1;
            cfg2=1; cfg2_d=CFG_R2;
        #10 cfg0=0; cfg1=0; cfg2=0;

        // Let the chain cascade-fill and drain repeatedly.
        #800;

        if (received_count >= 5 && errors == 0)
            $display("PASS: chain delivered %0d consumes with correct value each time, cascading refill confirmed", received_count);
        else
            $display("FAIL: received_count=%0d errors=%0d", received_count, errors);

        $finish;
    end

endmodule
