// tb_addr_counter_v1.v — confirms adder_v1's plain arithmetic (not just
// synthesizing, actually correct across a few cases), and
// addr_counter_v1's ack-gated pacing (holds while advance_en=0, exactly
// the pacing points.md #245 said the BRAM-interface counter needs) plus
// wraparound at a small, easy-to-check WRAP_AT. points.md #246.
`timescale 1ns / 1ps

module tb_addr_counter_v1;

    // ── adder_v1 direct checks ─────────────────────────────────────────
    reg  [7:0] a = 0, b = 0;
    reg        cin = 0;
    wire [7:0] sum;
    wire       cout;
    integer adder_errors = 0;

    adder_v1 #(.WIDTH(8)) DUT_ADD (.a(a), .b(b), .cin(cin), .sum(sum), .cout(cout));

    task check_add(input [7:0] va, input [7:0] vb, input vcin);
        begin
            a = va; b = vb; cin = vcin;
            #1;
            if ({cout, sum} !== (va + vb + vcin)) begin
                $display("FAIL adder: %0d + %0d + %0d = {cout=%b,sum=%0d}, expected %0d",
                          va, vb, vcin, cout, sum, va + vb + vcin);
                adder_errors = adder_errors + 1;
            end else begin
                $display("OK adder: %0d + %0d + %0d = {cout=%b,sum=%0d}", va, vb, vcin, cout, sum);
            end
        end
    endtask

    // ── addr_counter_v1 checks ─────────────────────────────────────────
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;
    reg advance = 0;
    wire [3:0] addr;
    integer counter_errors = 0;

    // Small WRAP_AT so wraparound is easy to hit and check within a short sim.
    addr_counter_v1 #(.WIDTH(4), .WRAP_AT(4'd5)) DUT_CNT (
        .clk(clk), .rst(rst), .advance_en(advance), .addr(addr)
    );

    initial begin
        // -- adder_v1 --
        check_add(8'd0,   8'd0,   1'b0);
        check_add(8'd5,   8'd10,  1'b0);
        check_add(8'd255, 8'd1,   1'b0);   // should carry out, sum wraps to 0
        check_add(8'd255, 8'd0,   1'b1);   // cin also carries out
        check_add(8'd100, 8'd27,  1'b1);

        if (adder_errors == 0) $display("PASS: adder_v1, all cases correct");
        else $display("FAIL: adder_v1, %0d error(s)", adder_errors);

        // -- addr_counter_v1 --
        #12 rst = 0;

        // Hold advance low for a few cycles -- addr must NOT move (this is
        // the ack-gated pacing points.md #245 asked for).
        #30;
        if (addr !== 4'd0) begin
            $display("FAIL: addr moved to %0d while advance_en was held low", addr);
            counter_errors = counter_errors + 1;
        end else begin
            $display("OK: addr held at 0 while advance_en=0 (%0d cycles)", 3);
        end

        // Now advance every cycle and confirm 0,1,2,3,4,5, then wrap to 0.
        advance = 1;
        repeat (8) begin
            @(posedge clk);
            #1;
            $display("[%0t] addr=%0d", $time, addr);
        end

        // After 8 advances from 0: 0->1->2->3->4->5->0->1->2, so addr should be 2.
        if (addr !== 4'd2) begin
            $display("FAIL: after 8 advances from 0 (wrap at 5), expected addr=2, got %0d", addr);
            counter_errors = counter_errors + 1;
        end else begin
            $display("OK: wraparound landed exactly where expected (addr=2 after 8 advances, wrap at 5)");
        end

        // Hold again mid-stream, confirm it stays put.
        advance = 0;
        #30;
        if (addr !== 4'd2) begin
            $display("FAIL: addr drifted to %0d while advance_en held low again", addr);
            counter_errors = counter_errors + 1;
        end

        if (adder_errors == 0 && counter_errors == 0)
            $display("PASS: adder_v1 + addr_counter_v1, ack-gated pacing and wraparound both correct");
        else
            $display("FAIL: adder_errors=%0d counter_errors=%0d", adder_errors, counter_errors);

        $finish;
    end

endmodule
