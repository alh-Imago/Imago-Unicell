`timescale 1ns/1ps
module tb;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg [31:0] in_data = 0; reg in_valid = 0; wire in_ack; wire [31:0] out_data; wire out_valid; reg out_ack = 0;
    hexn_scorer_v1 D (.clk(clk), .rst(rst), .in_data(in_data), .in_valid(in_valid), .in_ack(in_ack), .out_data(out_data), .out_valid(out_valid), .out_ack(out_ack));
    reg [31:0] inw [0:4095]; reg [31:0] expw [0:4095];
    integer nin = 0, nexp = 0, i = 0, got = 0, bad = 0, seed = 7, gap;
    initial begin
        $readmemh("tests/hexn_scorer/in.hex", inw); $readmemh("tests/hexn_scorer/exp.hex", expw);
        while (inw[nin] !== 32'bx) nin = nin + 1;
        while (expw[nexp] !== 32'bx) nexp = nexp + 1;
        repeat (4) @(posedge clk); rst = 0;
        for (i = 0; i < nin; i = i + 1) begin
            gap = $random(seed) & 3; repeat (gap) @(posedge clk);
            in_data <= inw[i]; in_valid <= 1; @(posedge clk);
            while (!in_ack) @(posedge clk);
            in_valid <= 0;
        end
        repeat (60) @(posedge clk);
        if (got == nexp && bad == 0) $display("PASS %0d results", got); else $display("FAIL got %0d of %0d, bad %0d", got, nexp, bad);
        $finish;
    end
    // consumer: acks after a random delay (valid is held until ack)
    integer d = 0;
    always @(posedge clk) begin
        out_ack <= 0;
        if (out_valid && !out_ack) begin
            if (d == 0) begin out_ack <= 1; d = $random(seed) & 3; end else d = d - 1;
        end
        if (out_valid && out_ack) begin
            if (out_data !== expw[got]) begin bad = bad + 1; if (bad < 5) $display("MISMATCH %0d: got %08x expw %08x", got, out_data, expw[got]); end
            got = got + 1;
        end
    end
endmodule
