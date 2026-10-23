// Testbench for memlat.v with a stand-in Wishbone slave: fixed latency LAT (plus EXTRA for one address in eight),
// acks in order and one per cycle at most, optional stall (PERIOD cycles out of every 16).
`timescale 1ns/1ps
module tb_memlat;
    parameter integer LAT = 20, EXTRA = 0, MODE = 0, COUNT = 50, STALLCYC = 0;
    reg clk = 0; always #5 clk = ~clk;
    integer now = 0; always @(posedge clk) now <= now + 1;
    reg start = 0; reg ready = 1;
    wire busy, wb_stb, wb_we, wb_stall, wb_ack;
    wire [15:0] n_done; wire [31:0] lat_min, lat_max, lat_sum, stall_sum, total_cycles, rd_fold;
    wire [24:0] wb_addr; wire [575:0] wb_data;
    reg [575:0] rdata = 0;
    memlat dut (.clk(clk), .ready(ready), .start(start), .mode(MODE[1:0]), .count(COUNT[15:0]), .seed(8'd7), .busy(busy), .n_done(n_done),
        .lat_min(lat_min), .lat_max(lat_max), .lat_sum(lat_sum), .stall_sum(stall_sum), .total_cycles(total_cycles), .rd_fold(rd_fold),
        .wb_stb(wb_stb), .wb_we(wb_we), .wb_addr(wb_addr), .wb_data(wb_data), .wb_stall(wb_stall), .wb_ack(wb_ack), .wb_rdata(rdata));
    assign wb_stall = (STALLCYC != 0) && ((now % 16) < STALLCYC);
    reg ack_r = 0; assign wb_ack = ack_r;
    integer due [0:65535]; integer head = 0, tail = 0, last_due = 0, d, bad = 0;
    always @(posedge clk) begin
        ack_r <= 0;
        if (wb_stb && !wb_stall) begin
            if (wb_we) bad = bad + 1;
            d = now + LAT + ((EXTRA != 0 && wb_addr[2:0] == 0) ? EXTRA : 0);
            if (d <= last_due) d = last_due + 1;
            last_due = d; due[tail % 65536] = d; tail = tail + 1;
        end
        if (head != tail && due[head % 65536] == now + 1) begin
            ack_r <= 1; rdata <= {18{32'hDEADBEEF}} ^ now; head = head + 1;
        end
    end
    initial begin
        repeat (5) @(posedge clk);
        start <= 1; @(posedge clk); start <= 0;
        wait (busy == 1); wait (busy == 0);
        repeat (3) @(posedge clk);
        $display("RESULT mode=%0d lat=%0d extra=%0d count=%0d stall=%0d : n_done=%0d lat_min=%0d lat_max=%0d lat_sum=%0d stall_sum=%0d total=%0d writes_seen=%0d",
                 MODE, LAT, EXTRA, COUNT, STALLCYC, n_done, lat_min, lat_max, lat_sum, stall_sum, total_cycles, bad);
        $finish;
    end
    initial begin #50000000; $display("TIMEOUT"); $finish; end
endmodule
