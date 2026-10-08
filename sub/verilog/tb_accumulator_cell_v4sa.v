`timescale 1ns/1ps
module tb_accumulator_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg inc_pulse = 0, dec_pulse = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    accumulator_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .inc_pulse(inc_pulse), .dec_pulse(dec_pulse), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    // Robust: assert one event for exactly one cycle, then wait (polling the
    // real ack_out signal, not a hand-counted number of cycles) until the
    // cell is genuinely ready for the next one.
    task fire_event(input is_inc);
        begin
            if (is_inc) inc_pulse = 1; else dec_pulse = 1;
            @(posedge clk);
            #1;   // let the DUT's OWN same-edge sampling of inc_pulse/dec_pulse
                  // complete BEFORE clearing them -- clearing immediately, in
                  // the same active region as the edge, races the DUT's own
                  // always block for which one reads the signal first (the
                  // exact bug class #906 first found; same fix here).
            inc_pulse = 0; dec_pulse = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === continuous mode, always-ready consumer ===
        cfg({7'h0, 16'h0, 1'b0, 8'd3}); // step=3, pulse_mode=0, threshold=0
        ack_in = 1;

        fire_event(1);
        check_cond(data_out === 32'd3, "continuous: +3 -> 3, waited for real ack_out before checking");
        fire_event(1);
        check_cond(data_out === 32'd6, "continuous: +3 again -> 6, each event properly acked before the next");
        fire_event(0);
        check_cond(data_out === 32'd3, "continuous: -3 -> 3");

        // === real backpressure: consumer not ready ===
        ack_in = 0;
        inc_pulse = 1;
        @(posedge clk); #1; inc_pulse = 0;
        check_cond(data_out === 32'd6 && valid_out === 1'b1, "backpressure: offer holds at 6 (3+3), receiver not ready yet");
        check_cond(ack_out === 1'b0, "ack_out correctly low while an unacked offer is pending");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd6, "backpressure: offer still holds 6 across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, the offer clears");

        // === pulse mode: real threshold crossing ===
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg({7'h0, 16'd12, 1'b1, 8'd5}); // threshold=12, pulse_mode=1, step=5
        ack_in = 1;
        inc_pulse = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "pulse mode: no offer yet (total=5, below threshold 12)");
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "pulse mode: still no offer (total=10, below threshold 12)");
        @(posedge clk); #1;
        check_cond(valid_out === 1'b1 && data_out === 32'd15, "pulse mode: offers exactly once total crosses threshold (15>=12)");
        inc_pulse = 0;

        // === freeze: a real, true pause ===
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        cfg({7'h0, 16'h0, 1'b0, 8'd3});
        ack_in = 1;
        fire_event(1);
        check_cond(data_out === 32'd3, "pre-freeze: real value captured");
        freeze_in = 1;
        inc_pulse = 1; ack_in = 1;   // try to disturb it while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd3 && valid_out === 1'b0, "frozen: completely unaffected by inc_pulse/ack_in toggling while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
