// uart_bridge.v — Host CPU Interface for UniCell Array
// Claudette v1.1
//
// Simple UART interface connecting the UniCell array to a host PC.
// The host PC runs the Python workbench, COMPANION, Shore etc.
// The FPGA handles the cell array and bus timing.
//
// Protocol (115200 8N1 default, configurable):
//
//   Host → FPGA (commands):
//     0x01 [addr:4] [data:4]  — inject bus transaction
//     0x02 [addr:4] [data:4]  — configure cell (sends LOAD_PATTERN then values)
//     0x03                    — reset array
//     0x04                    — query status (returns armed_count, cycle_count)
//     0x05 [cell_id:2]        — query cell state (returns full register file)
//
//   FPGA → Host (responses):
//     0x10 [addr:4] [data:4]  — cell fired (spontaneous, sent when out_valid)
//     0x11 [armed:2] [cycles:4] — status response
//     0x12 [cell_id:2] [gs:4] [iaddr:4] [oaddr:4] [armed:1] — cell state
//     0xFF                    — error / unknown command
//
// All multi-byte values are big-endian.
//
// At 115200 baud a bus transaction takes ~0.35ms.
// For higher throughput use 1Mbaud or connect via USB FIFO (FT232H etc.)

`timescale 1ns / 1ps

module uart_bridge #(
    parameter CLK_FREQ  = 12_000_000,   // 12MHz for iCEBreaker
    parameter BAUD_RATE = 115_200
) (
    input  wire clk,
    input  wire rst,

    // UART pins
    input  wire uart_rx,
    output wire uart_tx,

    // UniCell array interface
    output reg  [31:0] cpu_addr,
    output reg  [31:0] cpu_data,
    output reg         cpu_valid,
    output reg         array_rst,

    input  wire [31:0] out_addr,
    input  wire [31:0] out_data,
    input  wire        out_valid,
    input  wire [15:0] armed_count,
    input  wire [31:0] cycle_count
);

// ── UART parameters ───────────────────────────────────────────────────────────
localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

// ── UART RX ───────────────────────────────────────────────────────────────────
reg [3:0]  rx_state;
reg [15:0] rx_clk_cnt;
reg [7:0]  rx_shift;
reg [2:0]  rx_bit_cnt;
reg [7:0]  rx_byte;
reg        rx_valid;

localparam RX_IDLE  = 0;
localparam RX_START = 1;
localparam RX_DATA  = 2;
localparam RX_STOP  = 3;

always @(posedge clk) begin
    rx_valid <= 1'b0;
    if (rst) begin
        rx_state <= RX_IDLE;
    end else begin
        case (rx_state)
            RX_IDLE: begin
                if (!uart_rx) begin
                    rx_state   <= RX_START;
                    rx_clk_cnt <= CLKS_PER_BIT / 2;
                end
            end
            RX_START: begin
                if (rx_clk_cnt == 0) begin
                    rx_state   <= RX_DATA;
                    rx_clk_cnt <= CLKS_PER_BIT;
                    rx_bit_cnt <= 0;
                end else rx_clk_cnt <= rx_clk_cnt - 1;
            end
            RX_DATA: begin
                if (rx_clk_cnt == 0) begin
                    rx_shift   <= {uart_rx, rx_shift[7:1]};
                    rx_clk_cnt <= CLKS_PER_BIT;
                    if (rx_bit_cnt == 7) rx_state <= RX_STOP;
                    else rx_bit_cnt <= rx_bit_cnt + 1;
                end else rx_clk_cnt <= rx_clk_cnt - 1;
            end
            RX_STOP: begin
                if (rx_clk_cnt == 0) begin
                    rx_byte  <= rx_shift;
                    rx_valid <= 1'b1;
                    rx_state <= RX_IDLE;
                end else rx_clk_cnt <= rx_clk_cnt - 1;
            end
        endcase
    end
end

// ── UART TX ───────────────────────────────────────────────────────────────────
reg [7:0]  tx_byte;
reg        tx_send;
reg        tx_busy;
reg [3:0]  tx_state;
reg [15:0] tx_clk_cnt;
reg [7:0]  tx_shift;
reg [2:0]  tx_bit_cnt;
reg        tx_pin;

assign uart_tx = tx_pin;

always @(posedge clk) begin
    if (rst) begin
        tx_state <= 0;
        tx_pin   <= 1'b1;
        tx_busy  <= 1'b0;
    end else begin
        case (tx_state)
            0: begin
                tx_pin  <= 1'b1;
                tx_busy <= 1'b0;
                if (tx_send) begin
                    tx_shift   <= tx_byte;
                    tx_clk_cnt <= CLKS_PER_BIT;
                    tx_state   <= 1;
                    tx_busy    <= 1'b1;
                    tx_pin     <= 1'b0;  // Start bit
                end
            end
            1: begin
                if (tx_clk_cnt == 0) begin
                    tx_pin     <= tx_shift[0];
                    tx_shift   <= {1'b1, tx_shift[7:1]};
                    tx_clk_cnt <= CLKS_PER_BIT;
                    tx_bit_cnt <= tx_bit_cnt + 1;
                    if (tx_bit_cnt == 7) tx_state <= 2;
                end else tx_clk_cnt <= tx_clk_cnt - 1;
            end
            2: begin
                if (tx_clk_cnt == 0) begin
                    tx_pin   <= 1'b1;  // Stop bit
                    tx_state <= 0;
                end else tx_clk_cnt <= tx_clk_cnt - 1;
            end
        endcase
    end
end

// ── Command processor ─────────────────────────────────────────────────────────
reg [7:0]  cmd_buf [0:8];   // Command buffer (max 9 bytes: cmd + 2x4byte args)
reg [3:0]  cmd_len;          // Expected command length
reg [3:0]  cmd_pos;          // Current position in buffer
reg [7:0]  cmd_byte;         // Current command byte
reg        cmd_active;

// TX queue (simple single-entry for now)
reg [71:0] tx_queue;         // 9 bytes
reg [3:0]  tx_queue_len;
reg [3:0]  tx_queue_pos;
reg        tx_queue_valid;

always @(posedge clk) begin
    cpu_valid  <= 1'b0;
    array_rst  <= 1'b0;
    tx_send    <= 1'b0;

    // Forward cell outputs to host
    if (out_valid && !tx_busy && !tx_queue_valid) begin
        // Send 0x10 [addr:4] [data:4]
        tx_queue[71:64] <= 8'h10;
        tx_queue[63:32] <= out_addr;
        tx_queue[31:0]  <= out_data;
        tx_queue_len    <= 9;
        tx_queue_pos    <= 0;
        tx_queue_valid  <= 1'b1;
    end

    // Process TX queue
    if (tx_queue_valid && !tx_busy) begin
        tx_byte <= tx_queue[71:64];
        tx_queue <= {tx_queue[63:0], 8'h0};
        tx_send <= 1'b1;
        if (tx_queue_pos == tx_queue_len - 1) begin
            tx_queue_valid <= 1'b0;
            tx_queue_pos   <= 0;
        end else tx_queue_pos <= tx_queue_pos + 1;
    end

    // Process incoming bytes
    if (rx_valid) begin
        if (!cmd_active) begin
            cmd_byte   <= rx_byte;
            cmd_pos    <= 1;
            cmd_active <= 1'b1;
            case (rx_byte)
                8'h01: cmd_len <= 9;   // inject: cmd + addr(4) + data(4)
                8'h02: cmd_len <= 9;   // configure: cmd + addr(4) + data(4)
                8'h03: cmd_len <= 1;   // reset: cmd only
                8'h04: cmd_len <= 1;   // status: cmd only
                default: begin
                    cmd_active <= 1'b0;
                    // Send error
                    tx_byte <= 8'hFF;
                    tx_send <= 1'b1;
                end
            endcase
        end else begin
            cmd_buf[cmd_pos] <= rx_byte;
            cmd_pos <= cmd_pos + 1;

            if (cmd_pos == cmd_len - 1) begin
                cmd_active <= 1'b0;
                case (cmd_byte)
                    8'h01: begin
                        // Inject bus transaction
                        cpu_addr  <= {cmd_buf[1], cmd_buf[2], cmd_buf[3], cmd_buf[4]};
                        cpu_data  <= {cmd_buf[5], cmd_buf[6], cmd_buf[7], rx_byte};
                        cpu_valid <= 1'b1;
                    end
                    8'h03: begin
                        // Reset array
                        array_rst <= 1'b1;
                    end
                    8'h04: begin
                        // Status response
                        tx_queue[71:64] <= 8'h11;
                        tx_queue[63:48] <= armed_count;
                        tx_queue[47:16] <= cycle_count;
                        tx_queue[15:0]  <= 16'h0;
                        tx_queue_len    <= 7;
                        tx_queue_pos    <= 0;
                        tx_queue_valid  <= 1'b1;
                    end
                endcase
            end
        end
    end
end

endmodule
