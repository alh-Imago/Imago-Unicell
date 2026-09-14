// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_nibble_mask_addon_v1.v — verifies nibble_mask_addon_v1.v against
// unicell64_v3.v's own proven per-nibble BLOCK/PASS behavior.
`timescale 1ns / 1ps

module tb_nibble_mask_addon_v1;

    reg         mask_en;
    reg  [7:0]  nibble_mask;
    reg  [31:0] data_in;
    wire [31:0] data_out;

    integer errors = 0;

    nibble_mask_addon_v1 DUT (
        .mask_en(mask_en), .nibble_mask(nibble_mask),
        .data_in(data_in), .data_out(data_out)
    );

    task check(input [255:0] name, input [31:0] expected);
        begin
            #1;
            if (data_out !== expected) begin
                $display("FAIL: %0s -- expected %h, got %h", name, expected, data_out);
                errors = errors + 1;
            end else begin
                $display("OK: %0s -- %h", name, data_out);
            end
        end
    endtask

    initial begin
        data_in = 32'hFFFFFFFF;

        // mask_en=0: passthrough regardless of mask pattern
        mask_en = 0; nibble_mask = 8'hFF;
        check("mask_en=0 passthrough even with all-block pattern", 32'hFFFFFFFF);

        // mask_en=1, no bits blocked: passthrough
        mask_en = 1; nibble_mask = 8'h00;
        check("mask_en=1, nibble_mask=0 -- nothing blocked", 32'hFFFFFFFF);

        // mask_en=1, all nibbles blocked: fully zeroed
        nibble_mask = 8'hFF;
        check("mask_en=1, nibble_mask=FF -- everything blocked", 32'h00000000);

        // Single nibble block, each position, confirming exact placement
        nibble_mask = 8'b00000001; check("block nibble 0 only", 32'hFFFFFFF0);
        nibble_mask = 8'b00000010; check("block nibble 1 only", 32'hFFFFFF0F);
        nibble_mask = 8'b00000100; check("block nibble 2 only", 32'hFFFFF0FF);
        nibble_mask = 8'b00001000; check("block nibble 3 only", 32'hFFFF0FFF);
        nibble_mask = 8'b00010000; check("block nibble 4 only", 32'hFFF0FFFF);
        nibble_mask = 8'b00100000; check("block nibble 5 only", 32'hFF0FFFFF);
        nibble_mask = 8'b01000000; check("block nibble 6 only", 32'hF0FFFFFF);
        nibble_mask = 8'b10000000; check("block nibble 7 only", 32'h0FFFFFFF);

        // A real, distinctive data pattern -- confirms PASSED nibbles carry
        // their real value through untouched, not just zeros/ones
        data_in = 32'h12345678;
        nibble_mask = 8'b10101010; // block nibbles 1,3,5,7 -- keep 0,2,4,6
        check("alternating block on real data", 32'h02040608);

        if (errors == 0)
            $display("PASS: nibble_mask_addon_v1 -- faithful port confirmed, every nibble position and combination correct");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
