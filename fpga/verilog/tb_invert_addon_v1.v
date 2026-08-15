// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_invert_addon_v1.v — verifies invert_addon_v1.v.
`timescale 1ns / 1ps

module tb_invert_addon_v1;

    reg         invert_en;
    reg  [31:0] data_in;
    wire [31:0] data_out;

    integer errors = 0;

    invert_addon_v1 DUT (
        .invert_en(invert_en), .data_in(data_in), .data_out(data_out)
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
        invert_en = 0; data_in = 32'h12345678;
        check("invert_en=0 passthrough", 32'h12345678);

        invert_en = 1;
        check("invert_en=1 inverts", 32'hEDCBA987);

        data_in = 32'h00000000;
        check("invert of all-zero", 32'hFFFFFFFF);

        data_in = 32'hFFFFFFFF;
        check("invert of all-one", 32'h00000000);

        if (errors == 0)
            $display("PASS: invert_addon_v1 -- correct");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
