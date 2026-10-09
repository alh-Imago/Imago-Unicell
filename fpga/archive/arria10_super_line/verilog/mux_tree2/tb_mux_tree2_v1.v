// tb_mux_tree2_v1.v — points.md #257/#258's design, first real
// MULTI-LEVEL tree test: a real 2-level mux_cell_v1.v tree, reaching 5
// destinations (above the 4-chain minimum) from a single splitter feed.
//
// TOPOLOGY:
//   SPLITTER --W--> ROOT --N--> leaf1 (direct, 1 hop)
//                     --S--> leaf2 (direct, 1 hop)
//                     --E--> CHILD --N--> leaf3 (via root+child, 2 hops)
//                              --S--> leaf4
//                              --E--> leaf5
//
// ADDRESSING (points.md #258's scheme, bit layout pinned in #266):
//   leaf1/leaf2: count=1 — ROOT reads slot1 directly (its own
//     face_for_slot0=N/face_for_slot1=S), decrements to 0 (terminal).
//   leaf3/leaf4/leaf5: count=2 — ROOT reads slot2 (its own
//     face_for_slot2=E, "route to CHILD"), decrements to 1, forwards
//     the WHOLE field unchanged otherwise. CHILD then reads slot1
//     (count is now 1) using ITS OWN face_for_slot0/1/2 mapping
//     (N/S/E) to reach its 3 leaves, decrements to 0 (terminal).
// This is the real proof of #258's "no bit shifting, just decrement
// and read whichever slot count currently indexes" claim across a
// GENUINE two-node hop, not just asserted from the single-node test.
`timescale 1ns / 1ps

module tb_mux_tree2_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ── SPLITTER: address on North, DATA+ROUTING out East -> ROOT's West ──
    reg        splitter_cfg = 0;
    reg [63:0] splitter_cfg_d = 0;
    localparam [63:0] CFG_SPLITTER = {56'h0, DIR_N, DIR_E};

    reg  [31:0] addr_in = 0;
    reg         addr_pulse = 0;
    wire [31:0] splitter_data_out_e;
    wire [7:0]  splitter_routing_out;
    wire        splitter_fire_e, splitter_ready_o;
    wire        root_ack_out_w;

    mem_read_splitter_v1 #(.CELL_ID(16'h0008), .ADDR_WIDTH(16)) SPLITTER (
        .clk(clk), .rst(rst), .cfg_valid(splitter_cfg), .cfg_data(splitter_cfg_d),
        .data_in_n(addr_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(addr_pulse), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(splitter_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(splitter_fire_e), .fire_w(),
        .ready_out(splitter_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(root_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(root_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0),
        .routing_out(splitter_routing_out),
        .status_data_valid(), .status_addr_captured()
    );

    // ── ROOT: upstream West (from splitter). N=leaf1, S=leaf2, E=CHILD ──
    reg        root_cfg = 0;
    reg [63:0] root_cfg_d = 0;
    localparam [63:0] CFG_ROOT = {48'h0, DIR_E /*slot2->child*/, DIR_S /*slot1->leaf2*/, DIR_N /*slot0->leaf1*/, DIR_W /*upstream*/};

    wire root_ready_out;
    wire [31:0] root_data_out_n, root_data_out_s, root_data_out_e;
    wire        root_fire_n, root_fire_s, root_fire_e;
    wire [7:0]  root_routing_out;
    wire        child_ack_out_w;

    reg cons1_ready = 1, cons2_ready = 1;
    reg cons1_ack = 0, cons2_ack = 0;

    mux_cell_v1 #(.CELL_ID(16'h0009)) ROOT (
        .clk(clk), .rst(rst), .cfg_valid(root_cfg), .cfg_data(root_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(splitter_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(splitter_fire_e),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(splitter_routing_out),
        .data_out_n(root_data_out_n), .data_out_s(root_data_out_s), .data_out_e(root_data_out_e), .data_out_w(),
        .fire_n(root_fire_n), .fire_s(root_fire_s), .fire_e(root_fire_e), .fire_w(),
        .routing_out(root_routing_out),
        .ready_out(root_ready_out),
        .ready_in_n(cons1_ready), .ready_in_s(cons2_ready), .ready_in_e(child_ready_out), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(root_ack_out_w),
        .ack_in_n(cons1_ack), .ack_in_s(cons2_ack), .ack_in_e(child_ack_out_w), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // ── CHILD: upstream West (from ROOT's East). N=leaf3, S=leaf4, E=leaf5 ──
    reg        child_cfg = 0;
    reg [63:0] child_cfg_d = 0;
    localparam [63:0] CFG_CHILD = {48'h0, DIR_E /*slot2, unused this test*/, DIR_S /*slot1->leaf4*/, DIR_N /*slot0->leaf3*/, DIR_W /*upstream*/};

    wire child_ready_out;
    wire [31:0] child_data_out_n, child_data_out_s, child_data_out_e;
    wire        child_fire_n, child_fire_s, child_fire_e;

    reg cons3_ready = 1, cons4_ready = 1, cons5_ready = 1;
    reg cons3_ack = 0, cons4_ack = 0, cons5_ack = 0;

    mux_cell_v1 #(.CELL_ID(16'h000A)) CHILD (
        .clk(clk), .rst(rst), .cfg_valid(child_cfg), .cfg_data(child_cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(root_data_out_e),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(root_fire_e),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(root_routing_out),
        .data_out_n(child_data_out_n), .data_out_s(child_data_out_s), .data_out_e(child_data_out_e), .data_out_w(),
        .fire_n(child_fire_n), .fire_s(child_fire_s), .fire_e(child_fire_e), .fire_w(),
        .routing_out(),
        .ready_out(child_ready_out),
        .ready_in_n(cons3_ready), .ready_in_s(cons4_ready), .ready_in_e(cons5_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(child_ack_out_w),
        .ack_in_n(cons3_ack), .ack_in_s(cons4_ack), .ack_in_e(cons5_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    // Seed 6 known words: 2 targeting ROOT's direct leaves (count=1),
    // 3 targeting CHILD's leaves via ROOT (count=2), and 1 REPEAT of a
    // child leaf to confirm the tree stays correct across repeats, not
    // just a single pass.
    initial begin
        // leaf1 (root N):  count=1, slot1=00
        SPLITTER.CORE.mem[16'h1000] = {2'd1, 2'b00, 2'b00, 2'b00, 32'hCEED0001};
        // leaf2 (root S):  count=1, slot1=01
        SPLITTER.CORE.mem[16'h1001] = {2'd1, 2'b01, 2'b00, 2'b00, 32'hCEED0002};
        // leaf3 (child N via root E): count=2, slot2=10(->E/child), slot1=00(->N)
        SPLITTER.CORE.mem[16'h1002] = {2'd2, 2'b00, 2'b10, 2'b00, 32'hCEED0003};
        // leaf4 (child S via root E): count=2, slot2=10, slot1=01
        SPLITTER.CORE.mem[16'h1003] = {2'd2, 2'b01, 2'b10, 2'b00, 32'hCEED0004};
        // leaf5 (child E via root E): count=2, slot2=10, slot1=10
        SPLITTER.CORE.mem[16'h1004] = {2'd2, 2'b10, 2'b10, 2'b00, 32'hCEED0005};
        // leaf3 again (repeat check)
        SPLITTER.CORE.mem[16'h1005] = {2'd2, 2'b00, 2'b10, 2'b00, 32'hCEED0006};
    end

    integer errors = 0;
    integer recv1=0, recv2=0, recv3=0, recv4=0, recv5=0;
    reg [31:0] expected_data;
    reg [2:0]  expected_leaf;   // 1..5

    // Five independent consumers.
    reg [1:0] s1=0, s2=0, s3=0, s4=0, s5=0;
    always @(posedge clk) begin
        cons1_ack<=0; cons2_ack<=0; cons3_ack<=0; cons4_ack<=0; cons5_ack<=0;
        if (!rst) begin
            case (s1)
                0: if (root_fire_n) begin
                       if (expected_leaf!==1 || root_data_out_n!==expected_data) begin
                           $display("[%0t] FAIL leaf1: expected_leaf=%0d data=%h", $time, expected_leaf, root_data_out_n); errors=errors+1;
                       end else $display("[%0t] leaf1 received %h (correct)", $time, root_data_out_n);
                       recv1=recv1+1; s1<=1;
                   end
                1: begin cons1_ack<=1; s1<=2; end
                2: s1<=0;
            endcase
            case (s2)
                0: if (root_fire_s) begin
                       if (expected_leaf!==2 || root_data_out_s!==expected_data) begin
                           $display("[%0t] FAIL leaf2", $time); errors=errors+1;
                       end else $display("[%0t] leaf2 received %h (correct)", $time, root_data_out_s);
                       recv2=recv2+1; s2<=1;
                   end
                1: begin cons2_ack<=1; s2<=2; end
                2: s2<=0;
            endcase
            case (s3)
                0: if (child_fire_n) begin
                       if (expected_leaf!==3 || child_data_out_n!==expected_data) begin
                           $display("[%0t] FAIL leaf3", $time); errors=errors+1;
                       end else $display("[%0t] leaf3 received %h (correct, via 2-hop tree)", $time, child_data_out_n);
                       recv3=recv3+1; s3<=1;
                   end
                1: begin cons3_ack<=1; s3<=2; end
                2: s3<=0;
            endcase
            case (s4)
                0: if (child_fire_s) begin
                       if (expected_leaf!==4 || child_data_out_s!==expected_data) begin
                           $display("[%0t] FAIL leaf4", $time); errors=errors+1;
                       end else $display("[%0t] leaf4 received %h (correct, via 2-hop tree)", $time, child_data_out_s);
                       recv4=recv4+1; s4<=1;
                   end
                1: begin cons4_ack<=1; s4<=2; end
                2: s4<=0;
            endcase
            case (s5)
                0: if (child_fire_e) begin
                       if (expected_leaf!==5 || child_data_out_e!==expected_data) begin
                           $display("[%0t] FAIL leaf5", $time); errors=errors+1;
                       end else $display("[%0t] leaf5 received %h (correct, via 2-hop tree)", $time, child_data_out_e);
                       recv5=recv5+1; s5<=1;
                   end
                1: begin cons5_ack<=1; s5<=2; end
                2: s5<=0;
            endcase
        end
    end

    task read_check(input [15:0] addr, input [31:0] exp_data, input [2:0] exp_leaf);
        begin
            wait (splitter_ready_o == 1'b1);
            expected_data = exp_data;
            expected_leaf = exp_leaf;
            addr_in = {16'h0, addr}; addr_pulse = 1'b1;
            #10;
            addr_pulse = 1'b0;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 splitter_cfg=1; splitter_cfg_d=CFG_SPLITTER;
            root_cfg=1;      root_cfg_d=CFG_ROOT;
            child_cfg=1;     child_cfg_d=CFG_CHILD;
        #10 splitter_cfg=0; root_cfg=0; child_cfg=0;
        #10;

        read_check(16'h1000, 32'hCEED0001, 3'd1); #100;
        read_check(16'h1001, 32'hCEED0002, 3'd2); #100;
        read_check(16'h1002, 32'hCEED0003, 3'd3); #100;
        read_check(16'h1003, 32'hCEED0004, 3'd4); #100;
        read_check(16'h1004, 32'hCEED0005, 3'd5); #100;
        read_check(16'h1005, 32'hCEED0006, 3'd3); #100;

        if (errors==0 && recv1==1 && recv2==1 && recv3==2 && recv4==1 && recv5==1)
            $display("PASS: 2-level mux tree -- 6/6 correct, all 5 leaves reached (2 direct 1-hop, 3 via 2-hop child), repeat delivery confirmed correct");
        else
            $display("FAIL: errors=%0d recv1=%0d recv2=%0d recv3=%0d recv4=%0d recv5=%0d", errors, recv1, recv2, recv3, recv4, recv5);

        $finish;
    end

endmodule
