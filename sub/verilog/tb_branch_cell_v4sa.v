`timescale 1ns/1ps
module tb_branch_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] cfg_emit_fixed_value = 0;
    reg [31:0] in1_data = 0, in2_data = 0;
    reg in1_valid = 0, in2_valid = 0;
    reg ack_in_1 = 0, ack_in_2 = 0;
    wire ack_out;
    wire [31:0] data_out_1, data_out_2;
    wire valid_out_1, valid_out_2;

    always #5 clk = ~clk;

    branch_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data), .cfg_emit_fixed_value(cfg_emit_fixed_value),
        .in1_data(in1_data), .in1_valid(in1_valid),
        .in2_data(in2_data), .in2_valid(in2_valid), .ack_out(ack_out),
        .data_out_1(data_out_1), .valid_out_1(valid_out_1), .ack_in_1(ack_in_1),
        .data_out_2(data_out_2), .valid_out_2(valid_out_2), .ack_in_2(ack_in_2)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word, input [31:0] fixed_val);
        begin
            cfg_data = word; cfg_emit_fixed_value = fixed_val; cfg_valid = 1;
            @(posedge clk); #1;
            cfg_valid = 0;
        end
    endtask

    task load_in1(input [31:0] val);
        begin
            in1_data = val; in1_valid = 1;
            @(posedge clk);
            #1;
            in1_valid = 0;
        end
    endtask

    // Presents one in2 round and advances EXACTLY one edge -- leaves the
    // resulting offer visible immediately for the caller to check, rather
    // than waiting for ack_out (which, with ack_in held continuously high,
    // would mean the offer has ALREADY been consumed by the time this
    // returns -- the real mistake caught in this file's own first draft).
    task present_round(input [31:0] in2_val);
        begin
            in2_data = in2_val; in2_valid = 1;
            @(posedge clk);
            #1;
            in2_valid = 0;
        end
    endtask

    // For when the test genuinely wants to wait until the cell is ready
    // for a fresh round (used only where that is actually the intent).
    task wait_ready;
        begin
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === one fixed (in1), one flowing (in2). emit=diff; low->out1,
        // equal->out2, high->both. ===
        cfg({22'h0, 2'b11 /*route_high=both*/, 2'b10 /*route_equal=out2*/,
             2'b01 /*route_low=out1*/, 2'b11 /*emit=diff*/, 1'b0 /*in2 flowing*/, 1'b1 /*in1 fixed*/}, 32'h0);
        ack_in_1 = 1; ack_in_2 = 1;
        load_in1(32'd100);

        present_round(32'd50);  // 100 > 50 -> HIGH -> route_high=both, diff=50
        check_cond(data_out_1 === 32'd50 && valid_out_1 === 1'b1, "HIGH: out1 gets diff=50");
        check_cond(data_out_2 === 32'd50 && valid_out_2 === 1'b1, "HIGH: out2 ALSO gets diff=50 (route_high=both)");
        wait_ready();

        present_round(32'd100);  // 100 == 100 -> EQUAL -> route_equal=out2 only, diff=0
        check_cond(valid_out_1 === 1'b0, "EQUAL: out1 does NOT fire (route_equal=out2 only)");
        check_cond(data_out_2 === 32'd0 && valid_out_2 === 1'b1, "EQUAL: out2 gets diff=0");
        wait_ready();

        present_round(32'd150);  // 100 < 150 -> LOW -> route_low=out1 only, diff=100-150=-50
        check_cond(data_out_1 === 32'hFFFFFFCE && valid_out_1 === 1'b1, "LOW: out1 gets diff=-50 (two's complement, 0xffffffce)");
        check_cond(valid_out_2 === 1'b0, "LOW: out2 does NOT fire (route_low=out1 only)");
        wait_ready();

        // === emit_source = in1, in2, and fixed constant ===
        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b01 /*emit=in1*/, 1'b0, 1'b1}, 32'h0);
        load_in1(32'd77);
        present_round(32'd1);
        check_cond(data_out_1 === 32'd77, "emit_source=in1: emits the held in1 value (77)");
        wait_ready();

        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b10 /*emit=in2*/, 1'b0, 1'b1}, 32'h0);
        load_in1(32'd77);
        present_round(32'd1);
        check_cond(data_out_1 === 32'd1, "emit_source=in2: emits the flowing in2 value (1)");
        wait_ready();

        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b00 /*emit=fixed*/, 1'b0, 1'b1}, 32'hDEADBEEF);
        load_in1(32'd77);
        present_round(32'd1);
        check_cond(data_out_1 === 32'hDEADBEEF, "emit_source=fixed: emits the configured constant");
        wait_ready();

        // === the swallow case: route=00 means consumed, nothing offered ===
        cfg({22'h0, 2'b00 /*route_high=NEITHER*/, 2'b01, 2'b01, 2'b01, 1'b0, 1'b1}, 32'h0);
        load_in1(32'd100);
        present_round(32'd1);  // 100>1 -> HIGH -> route_high=00, swallowed
        check_cond(valid_out_1 === 1'b0 && valid_out_2 === 1'b0, "swallow: HIGH with route=00 produces no offer on either output");
        check_cond(ack_out === 1'b1, "swallow: the cell is immediately ready for the next round (nothing was left pending)");

        // === BOTH flowing: a real synchronisation requirement ===
        cfg({22'h0, 2'b01, 2'b01, 2'b01, 2'b11 /*emit=diff*/, 1'b0 /*in2_fixed_mode=0: flowing*/, 1'b0 /*in1_fixed_mode=0: flowing*/}, 32'h0);
        in1_data = 32'd9; in1_valid = 1; in2_data = 32'd4; in2_valid = 0;  // only in1 fresh
        @(posedge clk); #1; in1_valid = 0;
        check_cond(valid_out_1 === 1'b0, "both-flowing: no firing when only ONE side presents a fresh value");
        in1_data = 32'd9; in1_valid = 1; in2_data = 32'd4; in2_valid = 1;  // BOTH fresh, same cycle
        @(posedge clk); #1; in1_valid = 0; in2_valid = 0;
        check_cond(data_out_1 === 32'd5 && valid_out_1 === 1'b1, "both-flowing: fires correctly once BOTH present a fresh value the same cycle (9-4=5)");
        wait_ready();

        // === real differential backpressure ===
        cfg({22'h0, 2'b11 /*route_high=both*/, 2'b01, 2'b01, 2'b11, 1'b0, 1'b1}, 32'h0);
        ack_in_1 = 1; ack_in_2 = 1;
        load_in1(32'd100);
        present_round(32'd1);  // HIGH, both outputs fire, diff=99
        check_cond(data_out_1 === 32'd99 && data_out_2 === 32'd99, "both outputs offering diff=99");

        ack_in_1 = 1; ack_in_2 = 0;  // out1 ready, out2 stalls
        @(posedge clk); #1;
        check_cond(valid_out_1 === 1'b0, "out1's offer cleared once acked");
        check_cond(valid_out_2 === 1'b1 && data_out_2 === 32'd99, "out2's offer still held -- out2 has not acked yet");
        check_cond(ack_out === 1'b0, "ack_out correctly LOW -- waiting on out2, even though out1 already acked");
        ack_in_2 = 1;
        @(posedge clk); #1;
        check_cond(valid_out_2 === 1'b0 && ack_out === 1'b1, "once out2 finally acks, both clear and the cell is ready again");

        // === freeze: a real, true pause ===
        ack_in_1 = 1; ack_in_2 = 1;
        present_round(32'd1);
        check_cond(data_out_1 === 32'd99, "pre-freeze: real value captured");
        freeze_in = 1;
        in2_data = 32'd999; in2_valid = 1; ack_in_1 = 1; ack_in_2 = 1;
        @(posedge clk); @(posedge clk); #1;
        // outputs were ALREADY pending (data_out_1=99) before freezing; the
        // correct frozen behaviour is that they STAY pending -- freeze must
        // block ack_in from clearing them, not clear them itself
        check_cond(data_out_1 === 32'd99 && valid_out_1 === 1'b1 && valid_out_2 === 1'b1,
            "frozen: the already-pending offers are correctly PRESERVED, not cleared by ack_in while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
