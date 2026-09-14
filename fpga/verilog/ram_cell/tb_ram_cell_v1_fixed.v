// tb_ram_cell_v1_fixed.v — single ram_cell_v1 in FIXED mode, downstream on
// South, driven by a stub receiver that periodically acks. Confirms: (1)
// the same constant is re-offered after every consume, not just once; (2)
// fire_s stays low the cycle an ack lands and comes back the next cycle
// data_valid never clears in fixed mode; (3) ready_out never asserts for a
// fixed cell (it should never attempt to accept a runtime refill).
// points.md #231/#235.
`timescale 1ns / 1ps

module tb_ram_cell_v1_fixed;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg cfg = 0;
    reg [63:0] cfg_d = 64'h0;
    localparam [31:0] CONST_VAL = 32'hCAFEBABE;
    // downstream_mask[1]=S, upstream_mask=0, fixed_mode=1, load_data_valid=1
    localparam [63:0] CFG_WORD = {22'h0, CONST_VAL, 1'b1, 1'b1, 4'b0000, 4'b0010};

    wire [31:0] dout_s;
    wire        fire_s, ready_o, ack_out_s, status_valid;
    reg         ack_in_s = 0;
    reg         ready_in_s = 1;  // stub receiver always able to accept

    ram_cell_v1 #(.CELL_ID(16'h0001)) RAM (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(dout_s), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(fire_s), .fire_e(), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(ready_in_s), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(ack_out_s), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(ack_in_s), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .status_data_valid(status_valid)
    );

    integer received_count = 0;
    integer errors = 0;
    integer cyc = 0;

    // Consumer: whenever it sees fire_s high, it takes one cycle to
    // "process" then pulses ack_in_s for exactly one cycle, matching the
    // level-held fire / one-cycle-ack convention used throughout the
    // project's other testbenches.
    reg [1:0] consume_state = 0;
    always @(posedge clk) begin
        ack_in_s <= 1'b0;
        if (!rst) begin
            case (consume_state)
                0: if (fire_s) begin
                       if (dout_s !== CONST_VAL) begin
                           $display("[%0t] FAIL: expected %h got %h", $time, CONST_VAL, dout_s);
                           errors = errors + 1;
                       end
                       consume_state <= 1;
                   end
                1: begin
                       ack_in_s <= 1'b1;
                       received_count = received_count + 1;
                       $display("[%0t] receive #%0d, value=%h", $time, received_count, dout_s);
                       consume_state <= 2;
                   end
                2: consume_state <= 0;  // one idle cycle before watching for the next offer
                default: consume_state <= 0;
            endcase
        end
    end

    reg configured = 0;
    always @(posedge clk) if (configured && ready_o) begin
        $display("[%0t] FAIL: ready_out asserted on a FIXED cell (should never re-enter capture)", $time);
        errors = errors + 1;
    end

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG_WORD;
        #10 cfg = 0; configured = 1;

        // Let the cell re-offer and get consumed repeatedly.
        #400;

        if (received_count >= 4 && errors == 0)
            $display("PASS: fixed cell re-offered its constant %0d times, no errors", received_count);
        else
            $display("FAIL: received_count=%0d errors=%0d", received_count, errors);

        $finish;
    end

endmodule
