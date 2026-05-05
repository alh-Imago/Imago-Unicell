// uart_bridge.v v1.4 — shift register queue, no indexed array reads

`timescale 1ns / 1ps
`default_nettype none

module uart_bridge #(
    parameter CLK_FREQ  = 12_000_000,
    parameter BAUD_RATE = 115_200
) (
    input  wire clk, rst, uart_rx,
    output wire uart_tx,
    output reg  [31:0] cpu_addr, cpu_data,
    output reg         cpu_valid, array_rst, array_freeze,
    input  wire [31:0] out_addr, out_data,
    input  wire        out_valid,
    input  wire [15:0] armed_count,
    input  wire [31:0] cycle_count
);

localparam CPB = CLK_FREQ / BAUD_RATE;

// ── RX ────────────────────────────────────────────────────────────────────────
reg [1:0]  rx_state = 0;
reg [15:0] rx_cnt   = 0;
reg [7:0]  rx_shift = 0;
reg [2:0]  rx_bit   = 0;
reg [7:0]  rx_byte  = 0;
reg        rx_ready = 0;

always @(posedge clk) begin
    rx_ready <= 0;
    case (rx_state)
        0: if (!uart_rx) begin rx_state<=1; rx_cnt<=CPB/2; end
        1: if (rx_cnt==0) begin rx_state<=2; rx_cnt<=CPB-1; rx_bit<=0; end
           else rx_cnt<=rx_cnt-1;
        2: if (rx_cnt==0) begin
               rx_shift<={uart_rx,rx_shift[7:1]}; rx_cnt<=CPB-1;
               if (rx_bit==7) rx_state<=3; else rx_bit<=rx_bit+1;
           end else rx_cnt<=rx_cnt-1;
        3: if (rx_cnt==0) begin rx_byte<=rx_shift; rx_ready<=1; rx_state<=0; end
           else rx_cnt<=rx_cnt-1;
    endcase
end

// ── TX ────────────────────────────────────────────────────────────────────────
reg        tx_pin   = 1;
reg [1:0]  tx_state = 0;
reg [15:0] tx_cnt   = 0;
reg [7:0]  tx_shift = 0;
reg [2:0]  tx_bit   = 0;
reg        tx_busy  = 0;
reg [7:0]  tx_load  = 0;
reg        tx_go    = 0;   // one-cycle pulse: load tx_load and start

assign uart_tx = tx_pin;

always @(posedge clk) begin
    if (rst) begin tx_state<=0; tx_pin<=1; tx_busy<=0; end
    else case (tx_state)
        0: begin
            tx_pin<=1; tx_busy<=0;
            if (tx_go) begin
                tx_shift<=tx_load; tx_cnt<=CPB-1; tx_bit<=0;
                tx_busy<=1; tx_pin<=0; tx_state<=1;
            end
        end
        1: if (tx_cnt==0) begin
               tx_pin<=tx_shift[0]; tx_shift<={1'b1,tx_shift[7:1]};
               tx_cnt<=CPB-1;
               if (tx_bit==7) tx_state<=2; else tx_bit<=tx_bit+1;
           end else tx_cnt<=tx_cnt-1;
        2: if (tx_cnt==0) begin tx_pin<=1; tx_state<=0; end
           else tx_cnt<=tx_cnt-1;
    endcase
end

// ── Queue + command processor ─────────────────────────────────────────────────
// Shift register queue — always sends q_sr[87:80], shifts on drain
// No indexed reads, no synthesis surprises
reg [87:0] q_sr       = 0;
reg [3:0]  q_len      = 0;
reg [3:0]  q_pos      = 0;
reg        q_valid    = 0;

reg [7:0]  cmd_buf[0:12];
reg [3:0]  cmd_len    = 0;
reg [3:0]  cmd_pos    = 0;
reg [7:0]  cmd_byte   = 0;
reg        cmd_active = 0;

reg [3:0]  last_hs    = 0;
reg        stup_done  = 0;
reg [11:0] stup_cnt   = 0;

// helper task — not synthesised, used inline
// Load 6-byte message into q_sr
task load6;
    input [7:0] b0,b1,b2,b3,b4,b5;
    input [3:0] len;
    begin
        q_sr  <= {b0,b1,b2,b3,b4,b5,40'h0};
        q_len <= len; q_pos <= 0; q_valid <= 1;
    end
endtask

always @(posedge clk) begin
    tx_go       <= 0;
    cpu_valid   <= 0;
    array_rst   <= 0;

    if (rst) begin
        stup_done<=0; stup_cnt<=0; q_valid<=0;
        q_pos<=0; cmd_active<=0; array_freeze<=0;
    end

    if (!stup_done) stup_cnt <= stup_cnt + 1;

    // Drain queue
    if (q_valid && !tx_busy && !tx_go) begin
        tx_load <= q_sr[87:80];
        tx_go   <= 1;
        q_sr    <= {q_sr[79:0], 8'h0};
        if (q_pos == q_len-1) begin q_valid<=0; q_pos<=0; end
        else q_pos <= q_pos+1;
    end

    // Startup: UCOK\r\n after 4096 cycles
    if (!stup_done && !q_valid && !tx_busy && !tx_go && (&stup_cnt)) begin
        q_sr  <= {8'h55,8'h43,8'h4F,8'h4B,8'h0D,8'h0A,40'h0};
        q_len<=6; q_pos<=0; q_valid<=1; stup_done<=1;
    end

    // Cell fired -> host
    if (out_valid && !q_valid && !tx_busy && !tx_go) begin
        q_sr  <= {8'h10, out_addr, out_data, {4'h0,last_hs}, 8'h0};
        q_len<=10; q_pos<=0; q_valid<=1;
    end

    // RX command processor
    if (rx_ready) begin
        if (!cmd_active) begin
            cmd_byte<=rx_byte; cmd_pos<=1; cmd_active<=1;
            case (rx_byte)
                8'h01: cmd_len<=13;
                8'h02: cmd_len<=9;
                8'h03: cmd_len<=1;
                8'h04: cmd_len<=1;
                8'h06: cmd_len<=1;
                8'h07: cmd_len<=1;
                default: begin
                    cmd_active<=0;
                    q_sr<={8'hFF,80'h0}; q_len<=1; q_pos<=0; q_valid<=1;
                end
            endcase
        end else begin
            cmd_buf[cmd_pos] <= rx_byte;
            cmd_pos <= cmd_pos+1;
            if (cmd_pos == cmd_len-1) begin
                cmd_active<=0;
                case (cmd_byte)
                    8'h01: begin
                        last_hs  <= {cmd_buf[3][5:4],cmd_buf[3][7:6]};
                        cpu_addr <= {cmd_buf[5],cmd_buf[6],cmd_buf[7],cmd_buf[8]};
                        cpu_data <= {cmd_buf[9],cmd_buf[10],cmd_buf[11],rx_byte};
                        cpu_valid<=1;
                    end
                    8'h02: begin
                        cpu_addr<={cmd_buf[1],cmd_buf[2],cmd_buf[3],cmd_buf[4]};
                        cpu_data<={cmd_buf[5],cmd_buf[6],cmd_buf[7],rx_byte};
                        cpu_valid<=1;
                    end
                    8'h03: array_rst<=1;
                    8'h04: begin
                        q_sr<={8'h11,armed_count,cycle_count,16'h0};
                        q_len<=7; q_pos<=0; q_valid<=1;
                    end
                    8'h06: begin
                        array_freeze<=1;
                        q_sr<={8'h13,80'h0}; q_len<=1; q_pos<=0; q_valid<=1;
                    end
                    8'h07: begin
                        array_freeze<=0;
                        q_sr<={8'h14,80'h0}; q_len<=1; q_pos<=0; q_valid<=1;
                    end
                endcase
            end
        end
    end
end

endmodule
