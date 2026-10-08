`timescale 1ns/1ps
module tb_ram_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg cfg_fixed_mode = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in = 0;
    wire ack_out;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    ram_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_fixed_mode(cfg_fixed_mode),
        .data_in(data_in), .valid_in(valid_in), .ack_out(ack_out),
        .data_out(data_out), .valid_out(valid_out), .ack_in(ack_in)
    );

    // ledger #1021: a second ram built with OFFER_PRELOAD = 1 (the preload is offered ONCE at start), same inputs
    wire ack_out_p, valid_out_p;
    wire [31:0] data_out_p;
    reg ack_in_p = 0;
    ram_cell_v4sa #(.OFFER_PRELOAD(1)) dut_p (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_fixed_mode(cfg_fixed_mode),
        .data_in(data_in), .valid_in(valid_in), .ack_out(ack_out_p),
        .data_out(data_out_p), .valid_out(valid_out_p), .ack_in(ack_in_p)
    );

    // ledger #1021: HOLD = 1 (fixed mode whose stored value is REPLACED by what arrives on the in-port): one starting empty, one built with OFFER_PRELOAD = 1 (starts holding the configured word)
    wire ack_out_h, valid_out_h, ack_out_hp, valid_out_hp;
    wire [31:0] data_out_h, data_out_hp;
    reg ack_in_h = 0;
    ram_cell_v4sa #(.HOLD(1)) dut_h (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_fixed_mode(cfg_fixed_mode),
        .data_in(data_in), .valid_in(valid_in), .ack_out(ack_out_h),
        .data_out(data_out_h), .valid_out(valid_out_h), .ack_in(ack_in_h)
    );
    ram_cell_v4sa #(.HOLD(1), .OFFER_PRELOAD(1)) dut_hp (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_fixed_mode(cfg_fixed_mode),
        .data_in(data_in), .valid_in(valid_in), .ack_out(ack_out_hp),
        .data_out(data_out_hp), .valid_out(valid_out_hp), .ack_in(ack_in_h)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word, input fixed);
        begin
            cfg_data = word; cfg_fixed_mode = fixed; cfg_valid = 1;
            @(posedge clk); #1;   // settle before clearing -- #906/#911/#912
            cfg_valid = 0;
        end
    endtask

    task fire_write(input [31:0] val);
        begin
            data_in = val; valid_in = 1;
            @(posedge clk); #1;
            valid_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === flowing mode ===
        cfg(32'h0, 1'b0);
        ack_in = 1;
        fire_write(32'hAAAA0001);
        check_cond(data_out === 32'hAAAA0001, "flowing: capture 1");
        fire_write(32'hBBBB0002);
        check_cond(data_out === 32'hBBBB0002, "flowing: overwrite with new capture");

        // real backpressure
        ack_in = 0;
        data_in = 32'hCCCC0003; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(data_out === 32'hCCCC0003 && valid_out === 1'b1, "backpressure: offer holds, receiver not ready");
        check_cond(ack_out === 1'b0, "ack_out correctly low while unacked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'hCCCC0003, "backpressure: holds across multiple stalled cycles");
        ack_in = 1;
        @(posedge clk); #1;
        check_cond(valid_out === 1'b0, "once acked, the offer clears");

        // === fixed mode: always valid, never drains, ack_out never gated by pending ===
        cfg(32'hCAFEBABE, 1'b1);
        check_cond(data_out === 32'hCAFEBABE, "fixed mode: preset value");
        check_cond(valid_out === 1'b1, "fixed mode: valid_out continuously high");
        check_cond(ack_out === 1'b1, "fixed mode: ack_out always ready, nothing to drain");

        // fixed mode genuinely ignores data_in/valid_in/ack_in entirely
        data_in = 32'hDEADDEAD; valid_in = 1; ack_in = 0;
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'hCAFEBABE && valid_out === 1'b1,
            "fixed mode: completely unaffected by data_in/valid_in/ack_in -- a real constant");

        // === freeze, flowing mode: a real, true pause ===
        cfg(32'h0, 1'b0);
        ack_in = 1;
        fire_write(32'd42);
        check_cond(data_out === 32'd42, "pre-freeze: real value captured");
        freeze_in = 1;
        data_in = 32'd999; valid_in = 1; ack_in = 1;  // try to disturb it while frozen
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out === 32'd42 && valid_out === 1'b0,
            "frozen: completely unaffected by data_in/valid_in/ack_in toggling while frozen");
        freeze_in = 0;

        // === OFFER_PRELOAD = 1 (#1021): the configured value is offered ONCE, then the cell is an ordinary flowing ram ===
        valid_in = 0; ack_in = 0; ack_in_p = 0; freeze_in = 0;
        cfg(32'h0BADF00D, 1'b0);
        check_cond(valid_out_p === 1'b1 && data_out_p === 32'h0BADF00D, "preload offer: the configured value is offered at start");
        check_cond(valid_out === 1'b0, "preload offer: the default ram (OFFER_PRELOAD=0) offers nothing");
        check_cond(ack_out_p === 1'b0, "preload offer: not ready for new data while the preload offer is unaccepted");
        @(posedge clk); @(posedge clk); #1;
        check_cond(valid_out_p === 1'b1 && data_out_p === 32'h0BADF00D, "preload offer: held until the receiver takes it");
        ack_in_p = 1; @(posedge clk); #1; ack_in_p = 0;
        check_cond(valid_out_p === 1'b0, "preload offer: taken once, it is not offered again");
        @(posedge clk); @(posedge clk); #1;
        check_cond(valid_out_p === 1'b0, "preload offer: and stays quiet (single-shot)");
        check_cond(ack_out_p === 1'b1, "preload offer: after the one offer it accepts data like a flowing ram");
        data_in = 32'h12345678; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        check_cond(valid_out_p === 1'b1 && data_out_p === 32'h12345678, "preload offer: later data flows through as normal");
        ack_in_p = 1; @(posedge clk); #1; ack_in_p = 0;
        // fixed mode with OFFER_PRELOAD=1 is still the always-valid constant
        cfg(32'hCAFEBABE, 1'b1);
        check_cond(valid_out_p === 1'b1 && data_out_p === 32'hCAFEBABE, "preload offer: fixed mode is still an always-valid constant");
        ack_in_p = 1; @(posedge clk); @(posedge clk); #1;
        check_cond(valid_out_p === 1'b1, "preload offer: fixed mode never drains");
        ack_in_p = 0;

        // === HOLD = 1 (#1021): fixed mode whose stored value is replaced by arrivals ===
        valid_in = 0; ack_in = 0; ack_in_h = 0; freeze_in = 0;
        cfg(32'h5A5A5A5A, 1'b1);
        check_cond(valid_out_h === 1'b0 && ack_out_h === 1'b1, "hold: empty at start (offers nothing) but ready for a write");
        check_cond(valid_out_hp === 1'b1 && data_out_hp === 32'h5A5A5A5A, "hold + OFFER_PRELOAD: starts holding the configured word");
        check_cond(valid_out === 1'b1 && data_out === 32'h5A5A5A5A, "constant (HOLD=0): unchanged, always valid");
        data_in = 32'hA1A1A1A1; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        check_cond(valid_out_h === 1'b1 && data_out_h === 32'hA1A1A1A1, "hold: the first arrival becomes the stored value and is offered");
        check_cond(data_out_hp === 32'hA1A1A1A1, "hold + OFFER_PRELOAD: an arrival replaces the configured word");
        check_cond(data_out === 32'h5A5A5A5A, "constant (HOLD=0): ignores the arrival -- still its constant");
        ack_in_h = 1; @(posedge clk); @(posedge clk); #1;
        check_cond(valid_out_h === 1'b1 && data_out_h === 32'hA1A1A1A1, "hold: taken by a consumer, it is NOT drained (offered again)");
        ack_in_h = 0;
        data_in = 32'hB2B2B2B2; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        check_cond(data_out_h === 32'hB2B2B2B2 && valid_out_h === 1'b1, "hold: a later arrival replaces the value");
        check_cond(ack_out_h === 1'b1, "hold: always ready for the next write");
        freeze_in = 1; data_in = 32'hC3C3C3C3; valid_in = 1; @(posedge clk); @(posedge clk); #1; valid_in = 0;
        check_cond(data_out_h === 32'hB2B2B2B2 && ack_out_h === 1'b0, "hold: frozen -- a write is neither accepted nor applied");
        freeze_in = 0;
        cfg(32'h0, 1'b1);
        check_cond(valid_out_h === 1'b0, "hold: reconfiguration empties it again");
        check_cond(valid_out_hp === 1'b1 && data_out_hp === 32'h0, "hold + OFFER_PRELOAD: reconfiguration loads the new configured word");

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
