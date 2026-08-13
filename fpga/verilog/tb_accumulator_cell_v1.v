// tb_accumulator_cell_v1.v — points.md #291/#293 continuation: confirms
// accumulator_cell_v1.v's own real design claim -- the internal running
// total NEVER drops or corrupts an event, even while a slow downstream
// reader hasn't drained the previous offer yet. Also confirms the free
// sign-bit tap and reconfiguration reset.
`timescale 1ns / 1ps

module tb_accumulator_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;
    // inc on N, dec on S, offer downstream on E
    localparam [63:0] CFG = {52'h0, DIR_E, DIR_S, DIR_N};

    reg        cfg = 0;
    reg [63:0] cfg_d = 0;

    reg inc_pulse = 0, dec_pulse = 0;
    wire [31:0] data_out_e;
    wire        fire_e, status_neg;

    reg cons_ready = 1;
    reg cons_ack = 0;

    accumulator_cell_v1 #(.CELL_ID(16'h0001), .WIDTH(32)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(inc_pulse), .arrived_s(dec_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cons_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_negative(status_neg)
    );

    integer errors = 0;

    task pulse_inc; begin inc_pulse = 1; #10; inc_pulse = 0; #10; end endtask
    task pulse_dec; begin dec_pulse = 1; #10; dec_pulse = 0; #10; end endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #10;

        // ── PART 1: normal operation, consumer keeping up. ──
        pulse_inc(); pulse_inc(); pulse_inc(); pulse_inc();
        #10;
        if (DUT.accumulator !== 4) begin
            $display("FAIL: internal accumulator should be 4, got %0d", DUT.accumulator);
            errors = errors + 1;
        end else $display("OK: internal accumulator correctly reached 4");

        wait (fire_e);
        @(posedge clk); cons_ack = 1; @(posedge clk); cons_ack = 0;
        #20;   // generous settle margin (2 full periods) -- a #10 margin here
                // landed right on an ambiguous edge boundary in an earlier
                // draft, making a genuinely working mechanism look broken;
                // confirmed via direct tracing, not assumed
        if (data_out_e !== 32'd4) begin
            $display("FAIL: offered value should now read 4, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: offered snapshot correctly refreshed to 4");

        // ── PART 2: the real claim -- a SLOW consumer must NOT cause
        // the internal accumulator to drop or corrupt events. ──
        cons_ready = 0;
        #10;
        pulse_inc(); pulse_inc(); pulse_inc();
        pulse_dec();
        pulse_inc(); pulse_inc();
        pulse_dec(); pulse_dec(); pulse_dec();
        #10;
        if (DUT.accumulator !== 5) begin
            $display("FAIL: internal accumulator should be 5 after 9 real events with a stuck consumer, got %0d -- events were LOST", DUT.accumulator);
            errors = errors + 1;
        end else $display("OK: internal accumulator correctly tracked all 9 real events (reached 5) despite a stuck consumer -- NO events lost");

        if (data_out_e !== 32'd4) begin
            $display("FAIL: offered value should have stayed stable at 4 while consumer was stuck, got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: offered snapshot correctly stayed STABLE at 4 while consumer was stuck (protocol-correct)");

        cons_ready = 1;
        #10;
        wait (fire_e);
        @(posedge clk); cons_ack = 1; @(posedge clk); cons_ack = 0;
        #20;
        if (data_out_e !== 32'd5) begin
            $display("FAIL: offered value should now show the LATEST total (5), got %0d", data_out_e);
            errors = errors + 1;
        end else $display("OK: consumer correctly caught up to the LATEST total (5) once ready again");

        // ── PART 3: the free sign-bit tap. ──
        pulse_dec(); pulse_dec(); pulse_dec(); pulse_dec(); pulse_dec(); pulse_dec();
        #10;
        if (DUT.accumulator !== -1) begin
            $display("FAIL: internal accumulator should be -1, got %0d", DUT.accumulator);
            errors = errors + 1;
        end
        wait (fire_e);
        @(posedge clk); cons_ack = 1; @(posedge clk); cons_ack = 0;
        #20;
        if (!status_neg) begin
            $display("FAIL: status_negative should be 1 once the offer reflects a negative total");
            errors = errors + 1;
        end else $display("OK: free sign-bit tap correctly reads negative once the accumulator genuinely is");

        // ── PART 4: reconfiguration resets everything ──
        cfg = 1; cfg_d = CFG; #10; cfg = 0; #10;
        if (DUT.accumulator !== 0) begin
            $display("FAIL: reconfiguration should reset the accumulator to 0, got %0d", DUT.accumulator);
            errors = errors + 1;
        end else $display("OK: reconfiguration correctly resets the accumulator");

        if (errors == 0)
            $display("PASS: accumulator_cell_v1 -- internal total never drops events even with a stuck consumer, offered snapshot stays protocol-stable, free sign-bit tap correct, reconfiguration reset correct");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
