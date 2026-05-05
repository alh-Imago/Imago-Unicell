// uart_bridge.v — Host CPU Interface for UniCell Array
// Claudette v1.3 — single always block, clean timing
//
// Protocol (115200 8N1):
//   Host -> FPGA:
//     0x01 [bus1:4] [addr:4] [data:4]  -- inject
//     0x02 [addr:4] [data:4]            -- configure cell
//     0x03                              -- reset array
//     0x04                              -- query status
//     0x06                              -- freeze
//     0x07                              -- release freeze
//
//   FPGA -> Host:
//     0x10 [addr:4] [data:4] [hs:1]    -- cell fired
//     0x11 [armed:2] [cycles:4]        -- status response
//     0x13                             -- freeze ack
//     0x14                             -- release ack
//     0xFF                             -- error

`timescale 1ns / 1ps
`default_nettype none

module uart_bridge #(
    parameter CLK_FREQ  = 12_000_000,
    parameter BAUD_RATE = 115_200
) (
    input  wire clk,
    input  wire rst,
    input  wire uart_rx,
    output wire uart_tx,
    output reg  [31:0] cpu_addr,
    output reg  [31:0] cpu_data,
    output reg         cpu_valid,
    output reg         array_rst,
    output reg         array_freeze,
    input  wire [31:0] out_addr,
    input  wire [31:0] out_data,
    input  wire        out_valid,
    input  wire [15:0] armed_count,
    input  wire [31:0] cycle_count
);

localparam CPB = CLK_FREQ / BAUD_RATE;  // clocks per bit

// ── RX ────────────────────────────────────────────────────────────────────────
reg [2:0]  rx_state   = 0;
reg [15:0] rx_cnt     = 0;
reg [7:0]  rx_shift   = 0;
reg [2:0]  rx_bit     = 0;
reg [7:0]  rx_byte    = 0;
reg        rx_ready   = 0;

localparam RX_IDLE=0, RX_START=1, RX_DATA=2, RX_STOP=3;

always @(posedge clk) begin
    rx_ready <= 0;
    case (rx_state)
        RX_IDLE:  if (!uart_rx) begin rx_state <= RX_START; rx_cnt <= CPB/2; end
        RX_START: if (rx_cnt == 0) begin rx_state <= RX_DATA; rx_cnt <= CPB-1; rx_bit <= 0; end
                  else rx_cnt <= rx_cnt - 1;
        RX_DATA:  if (rx_cnt == 0) begin
                      rx_shift <= {uart_rx, rx_shift[7:1]};
                      rx_cnt   <= CPB-1;
                      if (rx_bit == 7) rx_state <= RX_STOP;
                      else rx_bit <= rx_bit + 1;
                  end else rx_cnt <= rx_cnt - 1;
        RX_STOP:  if (rx_cnt == 0) begin rx_byte <= rx_shift; rx_ready <= 1; rx_state <= RX_IDLE; end
                  else rx_cnt <= rx_cnt - 1;
    endcase
end

// ── TX ────────────────────────────────────────────────────────────────────────
reg        tx_pin   = 1;
reg [2:0]  tx_state = 0;
reg [15:0] tx_cnt   = 0;
reg [7:0]  tx_shift = 0;
reg [2:0]  tx_bit   = 0;
reg        tx_busy  = 0;
reg [7:0]  tx_load  = 0;
reg        tx_start = 0;

assign uart_tx = tx_pin;

always @(posedge clk) begin
    case (tx_state)
        0: begin  // idle
            tx_pin  <= 1;
            tx_busy <= 0;
            if (tx_start) begin
                tx_shift <= tx_load;
                tx_cnt   <= CPB-1;
                tx_bit   <= 0;
                tx_busy  <= 1;
                tx_pin   <= 0;        // start bit
                tx_state <= 1;
            end
        end
        1: begin  // data bits
            if (tx_cnt == 0) begin
                tx_pin   <= tx_shift[0];
                tx_shift <= {1'b1, tx_shift[7:1]};
                tx_cnt   <= CPB-1;
                if (tx_bit == 7) tx_state <= 2;
                else tx_bit <= tx_bit + 1;
            end else tx_cnt <= tx_cnt - 1;
        end
        2: begin  // stop bit
            if (tx_cnt == 0) begin tx_pin <= 1; tx_state <= 0; end
            else tx_cnt <= tx_cnt - 1;
        end
    endcase
end

// ── Command processor + TX queue ─────────────────────────────────────────────
reg [7:0]  cmd_buf[0:12];
reg [3:0]  cmd_len    = 0;
reg [3:0]  cmd_pos    = 0;
reg [7:0]  cmd_byte   = 0;
reg        cmd_active = 0;

// Simple byte queue: 11 bytes max
reg [7:0]  queue[0:10];
reg [3:0]  q_len      = 0;
reg [3:0]  q_pos      = 0;
reg        q_valid    = 0;

reg        startup_done = 0;
reg [11:0] startup_cnt  = 0;
reg [3:0]  last_hs      = 0;

always @(posedge clk) begin
    tx_start    <= 0;
    cpu_valid   <= 0;
    array_rst   <= 0;

    if (rst) begin
        startup_done <= 0;
        startup_cnt  <= 0;
        q_valid      <= 0;
        q_pos        <= 0;
        cmd_active   <= 0;
        array_freeze <= 0;
    end

    // Startup counter
    if (!startup_done) startup_cnt <= startup_cnt + 1;

    // Drain queue into TX
    if (q_valid && !tx_busy && !tx_start) begin
        tx_load  <= queue[q_pos];
        tx_start <= 1;
        if (q_pos == q_len - 1) begin
            q_valid <= 0;
            q_pos   <= 0;
        end else q_pos <= q_pos + 1;
    end

    // Startup message: UCOK\r\n after 4096 cycles
    if (!startup_done && !q_valid && !tx_busy && !tx_start && (&startup_cnt)) begin
        queue[0] <= 8'h55; // U
        queue[1] <= 8'h43; // C
        queue[2] <= 8'h4F; // O
        queue[3] <= 8'h4B; // K
        queue[4] <= 8'h0D; // \r
        queue[5] <= 8'h0A; // \n
        q_len        <= 6;
        q_pos        <= 0;
        q_valid      <= 1;
        startup_done <= 1;
    end

    // Forward cell fired events
    if (out_valid && !q_valid && !tx_busy && !tx_start) begin
        queue[0] <= 8'h10;
        queue[1] <= out_addr[31:24];
        queue[2] <= out_addr[23:16];
        queue[3] <= out_addr[15:8];
        queue[4] <= out_addr[7:0];
        queue[5] <= out_data[31:24];
        queue[6] <= out_data[23:16];
        queue[7] <= out_data[15:8];
        queue[8] <= out_data[7:0];
        queue[9] <= {4'h0, last_hs};
        q_len    <= 10;
        q_pos    <= 0;
        q_valid  <= 1;
    end

    // Process received bytes
    if (rx_ready) begin
        if (!cmd_active) begin
            cmd_byte   <= rx_byte;
            cmd_pos    <= 1;
            cmd_active <= 1;
            case (rx_byte)
                8'h01: cmd_len <= 13;
                8'h02: cmd_len <= 9;
                8'h03: cmd_len <= 1;
                8'h04: cmd_len <= 1;
                8'h06: cmd_len <= 1;
                8'h07: cmd_len <= 1;
                default: begin
                    cmd_active <= 0;
                    queue[0]   <= 8'hFF;
                    q_len      <= 1;
                    q_pos      <= 0;
                    q_valid    <= 1;
                end
            endcase
        end else begin
            cmd_buf[cmd_pos] <= rx_byte;
            cmd_pos <= cmd_pos + 1;
            if (cmd_pos == cmd_len - 1) begin
                cmd_active <= 0;
                case (cmd_byte)
                    8'h01: begin
                        last_hs   <= {cmd_buf[3][5:4], cmd_buf[3][7:6]};
                        cpu_addr  <= {cmd_buf[5], cmd_buf[6], cmd_buf[7], cmd_buf[8]};
                        cpu_data  <= {cmd_buf[9], cmd_buf[10], cmd_buf[11], rx_byte};
                        cpu_valid <= 1;
                    end
                    8'h02: begin
                        cpu_addr  <= {cmd_buf[1], cmd_buf[2], cmd_buf[3], cmd_buf[4]};
                        cpu_data  <= {cmd_buf[5], cmd_buf[6], cmd_buf[7], rx_byte};
                        cpu_valid <= 1;
                    end
                    8'h03: array_rst <= 1;
                    8'h04: begin
                        queue[0] <= 8'h11;
                        queue[1] <= armed_count[15:8];
                        queue[2] <= armed_count[7:0];
                        queue[3] <= cycle_count[31:24];
                        queue[4] <= cycle_count[23:16];
                        queue[5] <= cycle_count[15:8];
                        queue[6] <= cycle_count[7:0];
                        q_len    <= 7;
                        q_pos    <= 0;
                        q_valid  <= 1;
                    end
                    8'h06: begin array_freeze <= 1; queue[0] <= 8'h13; q_len <= 1; q_pos <= 0; q_valid <= 1; end
                    8'h07: begin array_freeze <= 0; queue[0] <= 8'h14; q_len <= 1; q_pos <= 0; q_valid <= 1; end
                endcase
            end
        end
    end
end

endmodule
