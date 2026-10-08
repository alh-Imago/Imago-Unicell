`timescale 1ns/1ps
// Second output port of adder_cell_v4sa (carry_out) and mul_cell_v4sa (data_out_hi), WIDTH=8 so
// every case is checkable by hand. Own valid/ack pair per port; a new round needs BOTH consumed;
// port silent when its enable bit is clear.
module tb_second_port_v4sa;
    localparam W = 8;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfg_valid = 0; reg [31:0] cfg_data = 0;
    reg [W-1:0] a = 0, b = 0; reg vin = 0;
    reg ack_s = 0, ack_c = 0, ack_h = 0, ack_m = 0;
    wire ao, vo, vc; wire [W-1:0] so, co;
    wire mo, mv, mh; wire [W-1:0] ml, mhw;
    wire mack;
    adder_cell_v4sa #(.WIDTH(W), .SECOND_PORT(1)) ADD (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(a), .in_b(b), .valid_in(vin), .ack_out(ao), .data_out(so), .valid_out(vo), .ack_in(ack_s),
        .carry_out(co), .valid_out_c(vc), .ack_in_c(ack_c));
`ifdef DSP
    mul_cell_v4sa_dsp #(.WIDTH(W), .SECOND_PORT(1)) MUL
`else
    mul_cell_v4sa #(.WIDTH(W), .SECOND_PORT(1)) MUL
`endif
     (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(a), .in_b(b), .valid_in(vin), .ack_out(mack), .data_out(ml), .valid_out(mv), .ack_in(ack_m),
        .data_out_hi(mhw), .valid_out_hi(mh), .ack_in_hi(ack_h));
    // a SECOND_PORT=0 adder ignores the enable bit: the port stays silent
    wire [W-1:0] s0o, c0o; wire a0o, v0o, vc0o;
    adder_cell_v4sa #(.WIDTH(W), .SECOND_PORT(0)) ADD_OFF (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .in_a(a), .in_b(b), .valid_in(vin), .ack_out(a0o), .data_out(s0o), .valid_out(v0o), .ack_in(1'b1),
        .carry_out(c0o), .valid_out_c(vc0o), .ack_in_c(1'b1));
    integer errors = 0;
    task chk(input c, input [255:0] l); begin if (!c) begin $display("FAIL: %0s", l); errors = errors + 1; end else $display("PASS: %0s", l); end endtask
    task cfg(input [31:0] w); begin cfg_data = w; cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0; end endtask
    initial begin
        @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);
        // ---- enable bits clear: ports silent, unconnected-safe
        cfg(32'h0); #1;
        a = 8'd200; b = 8'd100; vin = 1; @(posedge clk); #1; vin = 0;
        chk(so === 8'd44 && vo === 1 && vc === 0, "adder: carry disabled -> sum wraps, carry port silent");
        chk(mv === 1 && mh === 0, "mul: hi disabled -> hi port silent");
        ack_s = 1; ack_m = 1; @(posedge clk); #1; ack_s = 0; ack_m = 0;
        chk(vo === 0 && ao === 1 && mv === 0 && mack === 1, "both cells ready again with no carry/hi ack ever given");
        // ---- enabled
        cfg(32'h2); #1;                                       // adder carry_enable (bit1); mul hi_enable is bit0 -> 0 here
        a = 8'd200; b = 8'd100; vin = 1; @(posedge clk); #1; vin = 0;
        chk(so === 8'd44 && vo === 1 && vc === 1 && co === 8'd1, "adder 200+100: sum 44, carry 1 (word 0/1)");
        ack_s = 1; @(posedge clk); #1; ack_s = 0;
        chk(vo === 0 && vc === 1 && ao === 0, "sum consumed, carry still held -> cell NOT ready (needs both)");
        a = 8'd1; b = 8'd1; vin = 1; @(posedge clk); #1; vin = 0;
        chk(so === 8'd44 && co === 8'd1, "a new item offered while carry held is ignored");
        ack_c = 1; @(posedge clk); #1; ack_c = 0;
        chk(vc === 0 && ao === 1, "carry consumed -> ready");
        a = 8'd3; b = 8'd4; vin = 1; @(posedge clk); #1; vin = 0;
        chk(so === 8'd7 && co === 8'd0 && vc === 1, "3+4: carry 0 still produced as a valid word");
        ack_s = 1; ack_c = 1; @(posedge clk); #1; ack_s = 0; ack_c = 0;
        chk(vo === 0 && vc === 0 && ao === 1, "independent acks can arrive together");
        cfg(32'h3); #1;                                       // subtract + carry: raw carry = NOT borrow
        a = 8'd5; b = 8'd3; vin = 1; @(posedge clk); #1; vin = 0;
        chk(so === 8'd2 && co === 8'd1, "5-3=2, no borrow -> carry 1");
        ack_s = 1; ack_c = 1; @(posedge clk); #1; ack_s = 0; ack_c = 0;
        a = 8'd3; b = 8'd5; vin = 1; @(posedge clk); #1; vin = 0;
        chk(so === 8'hFE && co === 8'd0, "3-5=-2, borrow -> carry 0");
        ack_s = 1; ack_c = 1; @(posedge clk); #1; ack_s = 0; ack_c = 0;
        chk(vc0o === 0, "SECOND_PORT=0 adder: carry port silent even with the enable bit set");
        // ---- multiplier hi
        cfg(32'h1); #1;
        a = 8'd200; b = 8'd100; vin = 1; @(posedge clk); #1; vin = 0;   // 20000 = 0x4E20
        chk(ml === 8'h20 && mhw === 8'h4E && mv === 1 && mh === 1, "mul 200*100 = 0x4E20: low 0x20, high 0x4E");
        ack_m = 1; @(posedge clk); #1; ack_m = 0;
        chk(mack === 0 && mh === 1, "low consumed, high held -> not ready");
        ack_h = 1; @(posedge clk); #1; ack_h = 0;
        chk(mack === 1 && mh === 0, "high consumed -> ready");
        if (errors == 0) $display("ALL PASS"); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
