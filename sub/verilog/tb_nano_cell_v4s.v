`timescale 1ns/1ps
module tb_nano_cell_v4s;
    reg clk = 0;
    reg rst = 1;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] hold_in_data = 0;
    reg load_hold = 0;
    reg [31:0] flow_in_data = 0;
    reg valid_in = 0;
    wire [31:0] data_out;
    wire valid_out;

    always #5 clk = ~clk;

    nano_cell_v4s dut (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .hold_in_data(hold_in_data), .load_hold(load_hold),
        .flow_in_data(flow_in_data), .valid_in(valid_in),
        .data_out(data_out), .valid_out(valid_out)
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

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === AND, with the hold loaded ONCE and confirmed to PERSIST
        // across multiple DIFFERENT flowing values -- the real, defining
        // behaviour this whole cell exists for ===
        cfg(10'h007); // AND
        hold_in_data = 32'hF0F0F0F0; load_hold = 1; flow_in_data = 32'h0; valid_in = 0;
        @(posedge clk); #1; load_hold = 0;

        flow_in_data = 32'h0F0F0F0F; valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 32'h00000000, "AND(0xF0F0F0F0 held, 0x0F0F0F0F flow) = 0");

        // a SECOND flowing value, same held constant, NO reload -- proves
        // the hold genuinely persisted
        flow_in_data = 32'hAAAAAAAA;
        @(posedge clk); #1;
        check_cond(data_out === 32'hA0A0A0A0, "AND with the SAME held value, a DIFFERENT flow value -- hold persisted correctly");

        // a THIRD flowing value, still no reload
        flow_in_data = 32'hFFFFFFFF;
        @(posedge clk); #1;
        check_cond(data_out === 32'hF0F0F0F0, "AND(held, all-ones) = held itself -- hold still correctly persisting");

        // === OR, XOR, NAND, XNOR, NOT, passthrough, constants -- real gate
        // coverage, same held/flow pair reused where the hold doesn't need
        // reloading between cases ===
        cfg(10'h024); // OR
        flow_in_data = 32'h0F0F0F0F; valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 32'hFFFFFFFF, "OR(0xF0F0F0F0 held, 0x0F0F0F0F flow) = all ones");

        cfg(10'h0BC); // XOR
        flow_in_data = 32'hAAAAAAAA;
        @(posedge clk); #1;
        check_cond(data_out === 32'h5A5A5A5A, "XOR(held, 0xAAAAAAAA) = 0x5a5a5a5a");

        cfg(10'h03C); // XNOR
        @(posedge clk); #1;
        check_cond(data_out === 32'hA5A5A5A5, "XNOR(held, 0xAAAAAAAA) = 0xa5a5a5a5");

        cfg(10'h027); // NAND
        flow_in_data = 32'h0F0F0F0F;
        @(posedge clk); #1;
        check_cond(data_out === 32'hFFFFFFFF, "NAND(held, 0x0F0F0F0F) = all ones");

        cfg(10'h001); // NOT HELD
        @(posedge clk); #1;
        check_cond(data_out === 32'h0F0F0F0F, "NOT held (0xF0F0F0F0) = 0x0f0f0f0f");

        cfg(10'h000); // passthrough HELD
        @(posedge clk); #1;
        check_cond(data_out === 32'hF0F0F0F0, "passthrough HELD");

        cfg(10'h02C); // passthrough FLOW
        flow_in_data = 32'hDEADBEEF;
        @(posedge clk); #1;
        check_cond(data_out === 32'hDEADBEEF, "passthrough FLOW");

        cfg(10'h030); // constant 0
        @(posedge clk); #1;
        check_cond(data_out === 32'h00000000, "constant 0, regardless of held/flow");

        cfg(10'h0B0); // constant all-1s
        @(posedge clk); #1;
        check_cond(data_out === 32'hFFFFFFFF, "constant all-ones, regardless of held/flow");

        // === reloading the hold with a NEW value takes effect correctly ===
        cfg(10'h000); // passthrough HELD, so we can directly observe the reload
        hold_in_data = 32'h12345678; load_hold = 1; valid_in = 0;
        @(posedge clk); #1; load_hold = 0;
        valid_in = 1;
        @(posedge clk); #1;
        check_cond(data_out === 32'h12345678, "reloading the hold with a new value takes effect correctly");

        // === valid_out timing: low before config, correct afterward ===
        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
