// tb_single_memory_interface_v1.v — points.md #257/#258/#260's design,
// the COMPLETE single memory interface Alan asked for next: wires
// mem_read_splitter_v1.v (address -> real BRAM read -> DATA/ROUTING
// split) directly into mux_cell_v1.v (routing decode -> correct
// destination), end to end. Not a 4-chain distribution system yet
// (that needs a real tree, per #258) — this is the smallest complete
// working unit: ONE address, through real BRAM, correctly split,
// correctly routed to ONE of 3 possible destinations, confirmed for
// real across several addresses each targeting a different face.
`timescale 1ns / 1ps

module tb_single_memory_interface_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ── mem_read_splitter_v1.v: address arrives on North, DATA+ROUTING
    // offered on East (straight into the mux's West/upstream input). ──
    reg        splitter_cfg = 0;
    reg [63:0] splitter_cfg_d = 0;
    localparam [63:0] CFG_SPLITTER = {56'h0, DIR_N, DIR_E};

    reg  [31:0] addr_in = 0;
    reg         addr_pulse = 0;
    wire [31:0] splitter_data_out_e;
    wire [7:0]  splitter_routing_out;
    wire        splitter_fire_e, splitter_ready_o;
    wire        mux_ack_out_w;   // mux's ack for consuming from the splitter

    mem_read_splitter_v1 #(.CELL_ID(16'h0006), .ADDR_WIDTH(16)) SPLITTER (
        .clk(clk), .rst(rst), .cfg_valid(splitter_cfg), .cfg_data(splitter_cfg_d),
        .data_in_n(addr_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(addr_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(splitter_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(splitter_fire_e), .fire_w(),
        .ready_out(splitter_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(mux_ready_out_for_splitter), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(mux_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .routing_out(splitter_routing_out),
        .status_data_valid(), .status_addr_captured()
    );

    // ── mux_cell_v1.v: upstream (DATA+ROUTING) on West, from the
    // splitter's East output. Three usable output faces N/S/E, slot
    // code 00/01/10. ──
    reg        mux_cfg = 0;
    reg [63:0] mux_cfg_d = 0;
    localparam [63:0] CFG_MUX = {48'h0, DIR_E /*slot2*/, DIR_S /*slot1*/, DIR_N /*slot0*/, DIR_W /*upstream*/};

    wire mux_ready_out_for_splitter;   // forward-declared above via Verilog's
                                        // implicit net rules — see NOTE below

    wire [31:0] mux_data_out_n, mux_data_out_s, mux_data_out_e;
    wire        mux_fire_n, mux_fire_s, mux_fire_e;

    reg cons_n_ready = 1, cons_s_ready = 1, cons_e_ready = 1;
    reg cons_n_ack = 0, cons_s_ack = 0, cons_e_ack = 0;

    mux_cell_v1 #(.CELL_ID(16'h0007)) MUX (
        .clk(clk), .rst(rst), .cfg_valid(mux_cfg), .cfg_data(mux_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(splitter_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(splitter_fire_e),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(splitter_routing_out),
        .data_out_n(mux_data_out_n), .data_out_s(mux_data_out_s), .data_out_e(mux_data_out_e), .data_out_w(),
        .fire_n(mux_fire_n), .fire_s(mux_fire_s), .fire_e(mux_fire_e), .fire_w(),
        .routing_out(),
        .ready_out(mux_ready_out_for_splitter),
        .ready_in_n(cons_n_ready), .ready_in_s(cons_s_ready), .ready_in_e(cons_e_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(mux_ack_out_w),
        .ack_in_n(cons_n_ack), .ack_in_s(cons_s_ack), .ack_in_e(cons_e_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // Seed 5 known 40-bit words directly into the splitter's own BRAM --
    // DATA distinct per address, ROUTING selecting a DIFFERENT face
    // each time. Routing byte layout: [7:6]=count [5:4]=slot1
    // [3:2]=slot2 [1:0]=slot3. An earlier draft's binary literals put
    // the "01" pattern at the LSB end (slot3) instead of the MSB end
    // (count) -- e.g. 8'b00_00_00_01 encodes count=0, slot3=01, NOT the
    // intended count=1/slot1=00. Every seeded word was silently
    // count=0, which the mux (correctly, per its own "count==0 is not a
    // valid arrival" behavior) decoded as slot=00 every time -- hence
    // everything landing on N regardless of the intended face. Not a
    // DUT bug -- a testbench encoding mistake, caught by the DUT
    // behaving exactly as designed. Fixed with explicit 2-bit fields
    // instead of a single ambiguous binary literal.
    initial begin
        SPLITTER.CORE.mem[16'h0100] = {2'd1, 2'b00, 2'b00, 2'b00, 32'hF00D_0001};   // count=1 slot1=00 -> N
        SPLITTER.CORE.mem[16'h0200] = {2'd1, 2'b01, 2'b00, 2'b00, 32'hF00D_0002};   // count=1 slot1=01 -> S
        SPLITTER.CORE.mem[16'h0300] = {2'd1, 2'b10, 2'b00, 2'b00, 32'hF00D_0003};   // count=1 slot1=10 -> E
        SPLITTER.CORE.mem[16'h0400] = {2'd1, 2'b00, 2'b00, 2'b00, 32'hF00D_0004};   // -> N again
        SPLITTER.CORE.mem[16'h0500] = {2'd1, 2'b10, 2'b00, 2'b00, 32'hF00D_0005};   // -> E again
    end

    integer errors = 0;
    integer n_recv = 0, s_recv = 0, e_recv = 0;
    reg [31:0] expected_data;
    reg [1:0]  expected_face;   // 0=N 1=S 2=E

    reg [1:0] n_state = 0, s_state = 0, e_state = 0;
    always @(posedge clk) begin
        cons_n_ack <= 1'b0; cons_s_ack <= 1'b0; cons_e_ack <= 1'b0;
        if (!rst) begin
            case (n_state)
                0: if (mux_fire_n) begin
                       if (expected_face !== 2'd0 || mux_data_out_n !== expected_data)
                           begin $display("[%0t] FAIL: unexpected/wrong delivery on N", $time); errors=errors+1; end
                       else $display("[%0t] N received %h (correct)", $time, mux_data_out_n);
                       n_recv = n_recv + 1; n_state <= 1;
                   end
                1: begin cons_n_ack <= 1'b1; n_state <= 2; end
                2: n_state <= 0;
            endcase
            case (s_state)
                0: if (mux_fire_s) begin
                       if (expected_face !== 2'd1 || mux_data_out_s !== expected_data)
                           begin $display("[%0t] FAIL: unexpected/wrong delivery on S", $time); errors=errors+1; end
                       else $display("[%0t] S received %h (correct)", $time, mux_data_out_s);
                       s_recv = s_recv + 1; s_state <= 1;
                   end
                1: begin cons_s_ack <= 1'b1; s_state <= 2; end
                2: s_state <= 0;
            endcase
            case (e_state)
                0: if (mux_fire_e) begin
                       if (expected_face !== 2'd2 || mux_data_out_e !== expected_data)
                           begin $display("[%0t] FAIL: unexpected/wrong delivery on E", $time); errors=errors+1; end
                       else $display("[%0t] E received %h (correct)", $time, mux_data_out_e);
                       e_recv = e_recv + 1; e_state <= 1;
                   end
                1: begin cons_e_ack <= 1'b1; e_state <= 2; end
                2: e_state <= 0;
            endcase
        end
    end

    task read_check(input [15:0] addr, input [31:0] exp_data, input [1:0] exp_face);
        begin
            wait (splitter_ready_o == 1'b1);
            expected_data = exp_data;
            expected_face = exp_face;
            addr_in = {16'h0, addr}; addr_pulse = 1'b1;
            #10;
            addr_pulse = 1'b0;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 splitter_cfg = 1; splitter_cfg_d = CFG_SPLITTER;
            mux_cfg = 1;      mux_cfg_d = CFG_MUX;
        #10 splitter_cfg = 0; mux_cfg = 0;
        #10;

        read_check(16'h0100, 32'hF00D_0001, 2'd0);
        #80;
        read_check(16'h0200, 32'hF00D_0002, 2'd1);
        #80;
        read_check(16'h0300, 32'hF00D_0003, 2'd2);
        #80;
        read_check(16'h0400, 32'hF00D_0004, 2'd0);
        #80;
        read_check(16'h0500, 32'hF00D_0005, 2'd2);
        #80;

        if (errors == 0 && n_recv == 2 && s_recv == 1 && e_recv == 2)
            $display("PASS: COMPLETE single memory interface -- address -> real BRAM read -> DATA/ROUTING split -> mux decode -> correct destination, 5/5 correct end to end (N=%0d S=%0d E=%0d)",
                n_recv, s_recv, e_recv);
        else
            $display("FAIL: errors=%0d N=%0d S=%0d E=%0d", errors, n_recv, s_recv, e_recv);

        $finish;
    end

endmodule
