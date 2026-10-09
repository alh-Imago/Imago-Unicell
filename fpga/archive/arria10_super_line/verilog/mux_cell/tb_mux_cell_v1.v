// tb_mux_cell_v1.v — points.md #257/#258 continuation: confirms
// mux_cell_v1.v correctly decodes the routing field and delivers DATA
// to exactly the ONE selected face — never to the other two — and that
// the forwarded routing_out is correctly decremented with the other
// slots left untouched (the property a second-level mux node would
// depend on).
`timescale 1ns / 1ps

module tb_mux_cell_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // Upstream (DATA+ROUTING arrive) on West. Three usable output
    // faces: N, S, E — slot code 00->N, 01->S, 10->E.
    localparam [63:0] CFG = {48'h0,
                             DIR_E /* face_for_slot2 */,
                             DIR_S /* face_for_slot1 */,
                             DIR_N /* face_for_slot0 */,
                             DIR_W /* upstream_mask  */};

    reg  [31:0] data_in = 0;
    reg  [7:0]  routing_in = 0;
    reg         pulse = 0;
    reg         cfg = 0;
    reg  [63:0] cfg_d = 0;

    wire [31:0] data_out_n, data_out_s, data_out_e;
    wire        fire_n, fire_s, fire_e;
    wire [7:0]  routing_out;
    wire        ready_o;

    reg cons_n_ready = 1, cons_s_ready = 1, cons_e_ready = 1;
    reg cons_n_ack = 0, cons_s_ack = 0, cons_e_ack = 0;

    mux_cell_v1 #(.CELL_ID(16'h0005)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg), .cfg_data(cfg_d),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(data_in),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(8'h0), .routing_in_w(routing_in),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(),
        .routing_out(routing_out),
        .ready_out(ready_o),
        .ready_in_n(cons_n_ready), .ready_in_s(cons_s_ready), .ready_in_e(cons_e_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(cons_n_ack), .ack_in_s(cons_s_ack), .ack_in_e(cons_e_ack), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_data_valid()
    );

    integer errors = 0;
    integer n_received = 0, s_received = 0, e_received = 0;
    reg [31:0] expected_data;
    reg [1:0]  expected_face;   // 0=N, 1=S, 2=E
    reg [7:0]  expected_routing_out;

    // Three independent consumers — each only acks its own face's fire.
    reg [1:0] n_state = 0, s_state = 0, e_state = 0;
    always @(posedge clk) begin
        cons_n_ack <= 1'b0; cons_s_ack <= 1'b0; cons_e_ack <= 1'b0;
        if (!rst) begin
            // North
            case (n_state)
                0: if (fire_n) begin
                       if (expected_face !== 2'd0 || data_out_n !== expected_data)
                           begin $display("[%0t] FAIL: DATA arrived on N unexpectedly or wrong value (expected_face=%0d data=%h)", $time, expected_face, data_out_n); errors=errors+1; end
                       else if (routing_out !== expected_routing_out)
                           begin $display("[%0t] FAIL: routing_out mismatch on N: expected=%h got=%h", $time, expected_routing_out, routing_out); errors=errors+1; end
                       else $display("[%0t] N received data=%h routing_out=%h (correct)", $time, data_out_n, routing_out);
                       n_received = n_received + 1; n_state <= 1;
                   end
                1: begin cons_n_ack <= 1'b1; n_state <= 2; end
                2: n_state <= 0;
            endcase
            // South
            case (s_state)
                0: if (fire_s) begin
                       if (expected_face !== 2'd1 || data_out_s !== expected_data)
                           begin $display("[%0t] FAIL: DATA arrived on S unexpectedly or wrong value", $time); errors=errors+1; end
                       else if (routing_out !== expected_routing_out)
                           begin $display("[%0t] FAIL: routing_out mismatch on S: expected=%h got=%h", $time, expected_routing_out, routing_out); errors=errors+1; end
                       else $display("[%0t] S received data=%h routing_out=%h (correct)", $time, data_out_s, routing_out);
                       s_received = s_received + 1; s_state <= 1;
                   end
                1: begin cons_s_ack <= 1'b1; s_state <= 2; end
                2: s_state <= 0;
            endcase
            // East
            case (e_state)
                0: if (fire_e) begin
                       if (expected_face !== 2'd2 || data_out_e !== expected_data)
                           begin $display("[%0t] FAIL: DATA arrived on E unexpectedly or wrong value", $time); errors=errors+1; end
                       else if (routing_out !== expected_routing_out)
                           begin $display("[%0t] FAIL: routing_out mismatch on E: expected=%h got=%h", $time, expected_routing_out, routing_out); errors=errors+1; end
                       else $display("[%0t] E received data=%h routing_out=%h (correct)", $time, data_out_e, routing_out);
                       e_received = e_received + 1; e_state <= 1;
                   end
                1: begin cons_e_ack <= 1'b1; e_state <= 2; end
                2: e_state <= 0;
            endcase
        end
    end

    // routing byte: [7:6]=count [5:4]=slot1 [3:2]=slot2 [1:0]=slot3
    task send(input [31:0] val, input [1:0] cnt, input [1:0] s1, input [1:0] s2, input [1:0] s3,
              input [1:0] face, input [1:0] exp_cnt_after);
        begin
            wait (ready_o == 1'b1);
            expected_data = val;
            expected_face = face;
            expected_routing_out = {exp_cnt_after, s1, s2, s3};
            data_in = val;
            routing_in = {cnt, s1, s2, s3};
            pulse = 1'b1;
            #10;
            pulse = 1'b0;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 cfg = 1; cfg_d = CFG;
        #10 cfg = 0;
        #10;

        // count=1, slot1 selects the face directly, decrements to 0.
        send(32'hAAAA_0001, 2'd1, 2'b00 /*->N*/, 2'b01, 2'b10, 2'd0, 2'd0);
        #60;
        send(32'hBBBB_0002, 2'd1, 2'b01 /*->S*/, 2'b00, 2'b00, 2'd1, 2'd0);
        #60;
        send(32'hCCCC_0003, 2'd1, 2'b10 /*->E*/, 2'b11, 2'b11, 2'd2, 2'd0);
        #60;

        // count=2 case: this node reads slot2 (not slot1), decrements to 1.
        send(32'hDDDD_0004, 2'd2, 2'b11 /*unused at this node*/, 2'b00 /*->N*/, 2'b11, 2'd0, 2'd1);
        #60;
        send(32'hEEEE_0005, 2'd2, 2'b11, 2'b10 /*->E*/, 2'b01, 2'd2, 2'd1);
        #60;

        #40;
        if (errors == 0 && n_received == 2 && s_received == 1 && e_received == 2)
            $display("PASS: mux_cell_v1 -- 5/5 transactions routed to the CORRECT face every time (N=%0d S=%0d E=%0d), routing_out correctly decremented with other slots untouched",
                n_received, s_received, e_received);
        else
            $display("FAIL: errors=%0d N=%0d S=%0d E=%0d", errors, n_received, s_received, e_received);

        $finish;
    end

endmodule
