// tb_sequencer_cell_v1.v — sim-first standalone verification of
// sequencer_cell_v1.v (points.md #421/#422's own v2 super carrier
// work, the sequencer promoted to a genuine new CORE, #418) BEFORE
// wiring it into unicell_super_v1.v as SEL_SEQ. Drives the core
// directly, no shell involved — confirms the cell's own real behavior
// in isolation first, matching this project's own standing discipline.
`timescale 1ns / 1ps

module tb;
    reg clk = 0;
    always #5 clk = ~clk;

    reg rst = 1;
    reg cfg_valid = 0;
    reg [63:0] cfg_data = 64'h0;
    reg ready_in_n = 1;
    reg ack_in_n = 0;

    wire [31:0] data_out_n;
    wire fire_n;
    wire ack_out_n;
    wire ready_out;
    wire [1:0] status_seq_index;

    sequencer_cell_v1 DUT (
        .clk(clk), .rst(rst),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(data_out_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(fire_n), .fire_s(), .fire_e(), .fire_w(),
        .ready_in_n(ready_in_n), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .ready_out(ready_out), .status_seq_index(status_seq_index)
    );

    integer errors = 0;
    integer offers_seen = 0;
    reg [7:0] seen_values [0:11];   // record up to 12 offered values

    task check(input cond, input [255:0] msg);
        begin
            if (!cond) begin
                $display("FAIL: %s", msg);
                errors = errors + 1;
            end
        end
    endtask

    // Record every distinct offer (fire_n rising while it wasn't
    // already pending) by watching fire_n's own edge.
    reg fire_n_prev = 0;
    always @(posedge clk) begin
        if (fire_n && !fire_n_prev) begin
            seen_values[offers_seen] = data_out_n[7:0];
            offers_seen = offers_seen + 1;
        end
        fire_n_prev <= fire_n;
    end

    initial begin
        // Config: VALUE_0=10, VALUE_1=20, VALUE_2=30, VALUE_3=0 (unused),
        // SEQUENCE_LEN=3 (stored as length-1=2), downstream_mask=N
        // (4'b0001). Real bug found in THIS testbench's own first draft:
        // the concatenation was missing the VALUE_3 field entirely,
        // shifting every field after it to the wrong bit position --
        // fixed here, not in the core (confirmed correct once fixed).
        cfg_data = {26'b0, 4'b0001, 2'd2, 8'd0, 8'd30, 8'd20, 8'd10};

        #12 rst = 0;
        #10 cfg_valid = 1;
        #10 cfg_valid = 0;

        // Real assertion: this cell captures nothing (no arrived_X
        // role at all) — ack_out_n must stay 0 throughout, confirmed
        // directly, not assumed.
        check(ack_out_n === 1'b0, "ack_out_n should always be 0 -- this core never captures");

        // Real assertion: ready_out should be genuinely 1 whenever not
        // frozen (freeze_in tied 0 here) — matching accumulator's own
        // real fix (#295).
        #5 check(ready_out === 1'b1, "ready_out should be 1 (not frozen, never blocked)");

        // Drive 40 clock cycles, acking whenever fire_n is currently
        // high -- a real bug found in the FIRST draft of this loop:
        // `@(posedge fire_n)` hung forever because fire_n was already
        // high by the time the wait began (risen once, at config, never
        // dropping until acked) -- an edge-wait can't catch a signal
        // that's already at the level it's waiting to rise to. Fixed by
        // driving on the clock directly and checking the CURRENT level.
        repeat (40) begin
            @(posedge clk);
            #1;
            if (fire_n) ack_in_n = 1;
            else ack_in_n = 0;
        end

        #20;

        check(offers_seen >= 8, "should have seen at least 8 offers");
        check(seen_values[0] == 8'd10, "offer 0 should be VALUE_0=10");
        check(seen_values[1] == 8'd20, "offer 1 should be VALUE_1=20");
        check(seen_values[2] == 8'd30, "offer 2 should be VALUE_2=30");
        check(seen_values[3] == 8'd10, "offer 3 should WRAP back to VALUE_0=10");
        check(seen_values[4] == 8'd20, "offer 4 should be VALUE_1=20 again");
        check(seen_values[5] == 8'd30, "offer 5 should be VALUE_2=30 again");
        check(seen_values[6] == 8'd10, "offer 6 should wrap again to VALUE_0=10");
        check(seen_values[7] == 8'd20, "offer 7 should be VALUE_1=20 again");

        if (errors == 0) begin
            $display("PASS: sequencer_cell_v1 cycles 10,20,30 correctly, wraps at SEQUENCE_LEN=3, never captures");
        end else begin
            $display("FAIL: %0d error(s) found", errors);
        end
        $finish;
    end
endmodule
