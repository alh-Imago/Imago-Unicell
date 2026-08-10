// tb_combiner_tree2_v1.v — points.md #257/#258's design, the write-side
// mirror of tb_mux_tree2_v1.v (#271): a genuine 2-level combiner tree,
// proving combiner_cell_v2.v's new child-input ENCODE mechanism against
// a real combiner_relay_v1.v child, not just asserted from the design
// note.
//
// TOPOLOGY (mirrors the mux tree exactly, reversed):
//   chainA --N--> ROOT (slot0, raw)  --\
//   chainB --S--> ROOT (slot1, raw)  ---+--> wr_cmd_* --> BRAM
//   RELAY (chainC--N, chainD--S) --E--> ROOT (slot2, CHILD) --/
//
// ADDRESSING PRODUCED:
//   chainA (root slot0, raw):  count=1, slot1=00                 -> {01,00,00,00}
//   chainB (root slot1, raw):  count=1, slot1=01                 -> {01,01,00,00}
//   chainC (relay slot0, then root slot2 child): relay stamps
//     count=1,slot1=00; ROOT reads that via routing_in, computes
//     effective_count=2, writes root's OWN slot(=2, i.e. 2'd2) into
//     the slot2 FIELD, preserves relay's slot1=00 unchanged
//     -> {10, 00, 10, 00}
//   chainD (relay slot1, then root slot2 child): relay stamps
//     count=1,slot1=01; ROOT -> effective_count=2, root's own slot=2
//     into slot2 field, preserves relay's slot1=01
//     -> {10, 01, 10, 00}
`timescale 1ns / 1ps

module tb_combiner_tree2_v1;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

    // ── RELAY (child): chainC on N (slot0), chainD on S (slot1),
    // upward offer on E (toward ROOT's own E input). ──
    reg        relay_cfg = 0;
    reg [63:0] relay_cfg_d = 0;
    localparam [63:0] CFG_RELAY = {48'h0, 4'h0 /*slot2 unused*/, DIR_S /*slot1*/, DIR_N /*slot0*/, DIR_E /*upstream*/};

    reg        c_fire = 0, d_fire = 0;
    reg [31:0] c_data = 0, d_data = 0;
    wire       relay_ack_n, relay_ack_s;
    wire [31:0] relay_data_out_e;
    wire        relay_fire_e, relay_ready_o;
    wire [7:0]  relay_routing_out;
    wire        root_ack_out_e;   // ROOT's ack back to the relay (its slot2 input)

    always @(posedge clk) begin
        if (relay_ack_n) c_fire <= 1'b0;
        if (relay_ack_s) d_fire <= 1'b0;
    end

    combiner_relay_v1 #(.CELL_ID(16'h000B)) RELAY (
        .clk(clk), .rst(rst), .cfg_valid(relay_cfg), .cfg_data(relay_cfg_d),
        .data_in_n(c_data), .data_in_s(d_data), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(c_fire), .arrived_s(d_fire), .arrived_e(1'b0), .arrived_w(1'b0),
        .ack_out_n(relay_ack_n), .ack_out_s(relay_ack_s), .ack_out_e(), .ack_out_w(),
        .data_out_n(), .data_out_s(), .data_out_e(relay_data_out_e), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(relay_fire_e), .fire_w(),
        .routing_out(relay_routing_out),
        .ready_out(relay_ready_o),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1) /* ROOT always has room for a slot check */, .ready_in_w(1'b1),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(root_ack_out_e), .ack_in_w(1'b0),
        .freeze_in(1'b0), .status_slot(), .status_data_valid()
    );

    // ── ROOT: slot0=N (chainA, raw), slot1=S (chainB, raw),
    // slot2=E (RELAY, child). ──
    reg        root_cfg = 0;
    reg [63:0] root_cfg_d = 0;
    localparam [63:0] CFG_ROOT = {45'h0, 1'b1 /*is_child_slot2*/, 2'b00 /*is_child_slot1/0*/,
                                  DIR_E /*slot2->relay*/, DIR_S /*slot1->chainB*/, DIR_N /*slot0->chainA*/,
                                  DIR_W /*downstream, unused (direct wr_cmd)*/};

    reg        a_fire = 0, b_fire = 0;
    reg [31:0] a_data = 0, b_data = 0;
    wire       root_ack_n, root_ack_s;
    wire [1:0] root_status_slot;

    always @(posedge clk) begin
        if (root_ack_n) a_fire <= 1'b0;
        if (root_ack_s) b_fire <= 1'b0;
    end

    wire        wr_cmd_valid;
    wire [15:0] wr_cmd_addr;
    wire [39:0] wr_cmd_wdata;
    wire        wr_write_done;

    combiner_cell_v2 #(.CELL_ID(16'h000C), .ADDR_WIDTH(16)) ROOT (
        .clk(clk), .rst(rst), .cfg_valid(root_cfg), .cfg_data(root_cfg_d),
        .data_in_n(a_data), .data_in_s(b_data), .data_in_e(relay_data_out_e), .data_in_w(32'h0),
        .arrived_n(a_fire), .arrived_s(b_fire), .arrived_e(relay_fire_e), .arrived_w(1'b0),
        .routing_in_n(8'h0), .routing_in_s(8'h0), .routing_in_e(relay_routing_out), .routing_in_w(8'h0),
        .ack_out_n(root_ack_n), .ack_out_s(root_ack_s), .ack_out_e(root_ack_out_e), .ack_out_w(),
        .wr_cmd_valid(wr_cmd_valid), .wr_cmd_addr(wr_cmd_addr), .wr_cmd_wdata(wr_cmd_wdata),
        .wr_write_done(wr_write_done),
        .freeze_in(1'b0),
        .status_slot(root_status_slot), .status_wrote_this_cycle()
    );

    // ── Shared BRAM — root's writes go here directly. ──
    wire        rdata_valid;
    wire [39:0] rdata;
    reg         rd_cmd_valid = 0;
    reg  [15:0] rd_cmd_addr = 0;
    reg         mem_cmd_valid;
    reg         mem_cmd_op;
    reg  [15:0] mem_cmd_addr;
    reg  [39:0] mem_cmd_wdata;
    always @(*) begin
        if (wr_cmd_valid) begin
            mem_cmd_valid = 1'b1; mem_cmd_op = 1'b1;
            mem_cmd_addr = wr_cmd_addr; mem_cmd_wdata = wr_cmd_wdata;
        end else begin
            mem_cmd_valid = rd_cmd_valid; mem_cmd_op = 1'b0;
            mem_cmd_addr = rd_cmd_addr; mem_cmd_wdata = 40'h0;
        end
    end

    bram_controller_v1 #(.ADDR_WIDTH(16), .DATA_WIDTH(40)) MEM (
        .clk(clk), .rst(rst),
        .cmd_valid(mem_cmd_valid), .cmd_op(mem_cmd_op), .cmd_addr(mem_cmd_addr), .cmd_wdata(mem_cmd_wdata),
        .rdata_valid(rdata_valid), .rdata(rdata), .write_done(wr_write_done)
    );

    integer errors = 0;

    task check_read(input [15:0] addr, input [39:0] expected, input [255:0] label);
        begin
            @(posedge clk);
            rd_cmd_valid = 1'b1; rd_cmd_addr = addr;
            @(posedge clk);
            rd_cmd_valid = 1'b0;
            #1;
            if (!rdata_valid) begin
                $display("FAIL: %0s -- rdata_valid never asserted", label);
                errors = errors + 1;
            end else if (rdata !== expected) begin
                $display("FAIL: %0s -- expected=%h got=%h", label, expected, rdata);
                errors = errors + 1;
            end else begin
                $display("%0s: %h (correct)", label, rdata);
            end
            #10;
        end
    endtask

    initial begin
        #12 rst = 0;
        #10 relay_cfg = 1; relay_cfg_d = CFG_RELAY;
            root_cfg  = 1; root_cfg_d  = CFG_ROOT;
        #10 relay_cfg = 0; root_cfg = 0;
        #10;

        // chainA -> root slot0 (raw): count=1, slot1=00
        a_fire = 1'b1; a_data = 32'hA000_0001;
        #60; a_fire = 1'b0; #40;

        // chainB -> root slot1 (raw): count=1, slot1=01
        b_fire = 1'b1; b_data = 32'hB000_0002;
        #60; b_fire = 1'b0; #40;

        // chainC -> relay slot0 -> root slot2 (child): relay stamps
        // {1,00,00,00}; root sees child_count=1, effective_count=2,
        // writes root's own slot(=2) into the slot2 FIELD, preserves
        // relay's slot1=00 -> {10,00,10,00}
        c_fire = 1'b1; c_data = 32'hC000_0003;
        #80; c_fire = 1'b0; #60;

        // chainD -> relay slot1 -> root slot2 (child): relay stamps
        // {1,01,00,00}; root -> {10,01,10,00}
        d_fire = 1'b1; d_data = 32'hD000_0004;
        #80; d_fire = 1'b0; #60;

        check_read(16'h0000, {2'd1, 2'b00, 2'b00, 2'b00, 32'hA000_0001}, "addr0 (chainA, root slot0 raw)");
        check_read(16'h0001, {2'd1, 2'b01, 2'b00, 2'b00, 32'hB000_0002}, "addr1 (chainB, root slot1 raw)");
        check_read(16'h0002, {2'd2, 2'b00, 2'd2, 2'b00, 32'hC000_0003}, "addr2 (chainC via relay+root, 2-hop)");
        check_read(16'h0003, {2'd2, 2'b01, 2'd2, 2'b00, 32'hD000_0004}, "addr3 (chainD via relay+root, 2-hop)");

        if (errors == 0)
            $display("PASS: 2-level combiner tree -- 4/4 correct, 2 raw chains + 2 via a real relay child, count-increment-and-restamp confirmed exactly matching #258's ENCODE description");
        else
            $display("FAIL: %0d error(s)", errors);

        $finish;
    end

endmodule
