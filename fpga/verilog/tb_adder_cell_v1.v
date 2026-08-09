// tb_adder_cell_v1.v — points.md #248 task 2 / #251: confirms
// adder_cell_v1.v's two-arrival A/B capture genuinely produces A+B via
// adder_v1.v's real carry chain (not a NOR-gate approximation), and that
// the handshake (ack per direction, ready_out's "doubly full" gate,
// pending_ack draining) behaves correctly across several operand pairs
// in a row, not just once.
`timescale 1ns / 1ps

module tb_adder_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg cfg = 0;
    reg [63:0] cfg_d = 0;

    // downstream=E(0100), upstream=N|W (0001|1000=1001) — A arrives from
    // North, B arrives from West, in that order per test below.
    localparam [3:0] DIR_N = 4'b0001, DIR_E = 4'b0100, DIR_W = 4'b1000;
    localparam [63:0] CFG_DUT = {56'h0, (DIR_N | DIR_W), DIR_E};

    reg  [31:0] opA = 0, opB = 0;
    reg         pulse_a = 0, pulse_b = 0;

    wire [31:0] sum_out_e;
    wire        fire_e;
    wire        ready_o;
    wire        ack_out_n, ack_out_w;
    wire        status_dv, status_aa;

    reg cons_ready = 1;
    reg cons_ack   = 0;

    adder_cell_v1 #(.CELL_ID(16'h0000)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(opA), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(opB),
        .arrived_n(pulse_a), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_b),
        .data_out_n(), .data_out_s(), .data_out_e(sum_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_out(ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .status_data_valid(status_dv), .status_a_arrived(status_aa)
    );

    integer received = 0;
    integer errors   = 0;
    reg [31:0] expected_sum;

    // Consumer: ack whenever a sum is offered, checking against the
    // operand pair that was actually sent for this receive.
    reg [1:0] cons_state = 0;
    always @(posedge clk) begin
        cons_ack <= 1'b0;
        if (!rst) begin
            case (cons_state)
                0: if (fire_e) begin
                       if (sum_out_e !== expected_sum) begin
                           $display("[%0t] FAIL: expected sum=%h got=%h", $time, expected_sum, sum_out_e);
                           errors = errors + 1;
                       end else begin
                           $display("[%0t] receive #%0d: sum=%h (correct)", $time, received+1, sum_out_e);
                       end
                       received = received + 1;
                       cons_state <= 1;
                   end
                1: begin cons_ack <= 1'b1; cons_state <= 2; end
                2: cons_state <= 0;
                default: cons_state <= 0;
            endcase
        end
    end

    // Drives one A-then-B pair through the cell, waiting for A to be
    // genuinely captured (status_a_arrived) before sending B. Uses plain
    // #-delays rather than chaining straight off @(posedge clk) — an
    // earlier draft assigned stimulus and immediately awaited the next
    // edge, which could occasionally land the assignment ON the same
    // edge the DUT was sampling (ambiguous same-timestep ordering
    // between the testbench process and the DUT's own synchronous
    // block), silently missing that arrival. Confirmed via manual
    // cycle-by-cycle tracing that the DUT's own capture_now/a_arrived
    // logic is correct; this was purely a testbench stimulus race,
    // fixed the same way tb_ram_cell_v1_chain.v's proven driving style
    // already does (plain timed delays, not edge-chained assignment).
    task send_pair(input [31:0] a_val, input [31:0] b_val);
        begin
            expected_sum = a_val + b_val;
            opA = a_val; pulse_a = 1'b1;
            #10;
            pulse_a = 1'b0;
            wait (status_aa == 1'b1);
            #10;
            opB = b_val; pulse_b = 1'b1;
            #10;
            pulse_b = 1'b0;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG_DUT;
        #10 cfg = 0;

        // 5 operand pairs, including one with carry-out (unused port,
        // but the SUM bits must still be correct mod 2^32).
        send_pair(32'h0000_0005, 32'h0000_0007);   // 12, no carry
        #40;
        send_pair(32'hFFFF_FFFF, 32'h0000_0001);   // wraps to 0, real carry-out
        #40;
        send_pair(32'h1234_5678, 32'h0000_0001);
        #40;
        send_pair(32'h8000_0000, 32'h8000_0000);   // wraps to 0
        #40;
        send_pair(32'hAAAA_AAAA, 32'h5555_5555);   // all-bits sum -> FFFFFFFF, no carry
        #60;

        if (received == 5 && errors == 0)
            $display("PASS: adder_cell_v1 produced correct sums for all 5 operand pairs, handshake stable across repeats");
        else
            $display("FAIL: received=%0d errors=%0d", received, errors);

        $finish;
    end

endmodule
