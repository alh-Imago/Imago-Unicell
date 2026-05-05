// uart_bridge.v — Host CPU Interface for UniCell Array
// Claudette v1.2
//
// UART interface connecting the UniCell array to a host PC.
// The host PC runs the Python workbench, COMPANION, Shore etc.
//
// Bus 1 structure (bits carried in inject command):
//   bits  0-3:   command code
//   bits  4-14:  auth token
//   bit   15:    address mode
//   bits 16-17:  scope (00=LOCAL, 01=SHORE, 10=EXTENDED)
//   bits 18-21:  handshake (0=NONE,1=ACK,2=NAK,3=BUSY,4=REQ,5=GRANT,6=DENY,7=RETRY)
//   bits 22-31:  reserved
//
// The bridge passes Bus 1 transparently — it does not modify the handshake
// or scope fields. It extracts the handshake field from inject commands and
// echoes it back in the cell-fired response so the host can track ACK/NAK.
//
// Protocol (115200 8N1 default, configurable):
//
//   Host -> FPGA (commands):
//     0x01 [bus1:4] [addr:4] [data:4]  -- inject bus transaction
//                                          bus1 = Bus 1 word (scope+handshake+auth)
//                                          addr = Bus 3 target address
//                                          data = Bus 2 data payload
//     0x02 [addr:4] [data:4]            -- configure cell (LOAD_PATTERN sequence)
//     0x03                              -- reset array
//     0x04                              -- query status
//     0x05 [cell_id:2]                  -- query cell state
//     0x06                              -- freeze array (all cells decouple)
//     0x07                              -- release freeze
//
//   FPGA -> Host (responses):
//     0x10 [addr:4] [data:4] [hs:1]    -- cell fired (addr, data, handshake byte)
//     0x11 [armed:2] [cycles:4]        -- status response
//     0x12 [cell_id:2] [gs:4] [iaddr:4] [oaddr:4] [armed:1] -- cell state
//     0x13                             -- freeze acknowledged
//     0x14                             -- release acknowledged
//     0xFF                             -- error / unknown command
//
// All multi-byte values are big-endian.

`timescale 1ns / 1ps

module uart_bridge #(
    parameter CLK_FREQ  = 12_000_000,
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
    output reg         array_freeze,   // Freeze line to array

    input  wire [31:0] out_addr,
    input  wire [31:0] out_data,
    input  wire        out_valid,
    input  wire [15:0] armed_count,
    input  wire [31:0] cycle_count
);

// ── UART parameters ────────────────────────────────────────────────────────────
localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

// ── Handshake field extraction ─────────────────────────────────────────────────
// Bus 1 bits 18-21 carry the handshake field.
// Extracted from inject commands, echoed in cell-fired responses.
reg [3:0] last_handshake;   // Last handshake value seen on bus

// ── UART RX ────────────────────────────────────────────────────────────────────
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

// ── UART TX ────────────────────────────────────────────────────────────────────
reg [7:0]  tx_byte    = 8'h0;
reg        tx_send    = 1'b0;
reg        tx_busy    = 1'b0;
reg [3:0]  tx_state   = 4'h0;
reg [15:0] tx_clk_cnt = 16'h0;
reg [7:0]  tx_shift   = 8'h0;
reg [2:0]  tx_bit_cnt = 3'h0;
reg        tx_pin     = 1'b1;  // UART idle high

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
                    tx_clk_cnt <= CLKS_PER_BIT - 1;  // -1: count 0..N-1 = N cycles
                    tx_bit_cnt <= 3'h0;
                    tx_state   <= 1;
                    tx_busy    <= 1'b1;
                    tx_pin     <= 1'b0;
                end
            end
            1: begin
                if (tx_clk_cnt == 0) begin
                    tx_pin     <= tx_shift[0];
                    tx_shift   <= {1'b1, tx_shift[7:1]};
                    tx_clk_cnt <= CLKS_PER_BIT - 1;  // -1: consistent timing
                    tx_bit_cnt <= tx_bit_cnt + 1;
                    if (tx_bit_cnt == 7) tx_state <= 2;
                end else tx_clk_cnt <= tx_clk_cnt - 1;
            end
            2: begin
                if (tx_clk_cnt == 0) begin
                    tx_pin   <= 1'b1;
                    tx_state <= 0;
                end else tx_clk_cnt <= tx_clk_cnt - 1;
            end
        endcase
    end
end

// ── Command processor ──────────────────────────────────────────────────────────
reg [7:0]  cmd_buf [0:12];  // Command buffer — max 13 bytes (0x01: cmd+bus1(4)+addr(4)+data(4))
reg [3:0]  cmd_len;
reg [3:0]  cmd_pos;
reg [7:0]  cmd_byte;
reg        cmd_active = 1'b0;

// TX queue — 11 bytes max (0x10: hdr+addr(4)+data(4)+hs(1) = 10 bytes)
reg [87:0] tx_queue;        // 11 bytes
reg [3:0]  tx_queue_len   = 4'h0;
reg [3:0]  tx_queue_pos   = 4'h0;
reg        tx_queue_valid = 1'b0;

// Startup message: sends "UCOK\r\n" on reset release
// Proves UART TX is working in full design without needing RX
reg        startup_sent = 1'b0;  // explicit init — iCE40 regs can power up as 1
reg [9:0]  startup_cnt  = 10'h0;
// "UCOK\r\n" = 0x55 0x43 0x4F 0x4B 0x0D 0x0A (6 bytes)
localparam [47:0] STARTUP_MSG = 48'h55434F4B0D0A;

always @(posedge clk) begin
    cpu_valid    <= 1'b0;
    array_rst    <= 1'b0;
    tx_send      <= 1'b0;
    if (!startup_sent) startup_cnt <= startup_cnt + 1;

    if (rst) begin
        startup_sent    <= 1'b0;
        tx_queue_valid  <= 1'b0;
        tx_queue_pos    <= 0;
    end

    // Startup message: fire after 1024 cycles regardless
    // Using a free-running counter avoids synthesis optimisation
    if (!startup_sent && !tx_busy && !tx_queue_valid && (&startup_cnt)) begin
        tx_queue[87:40] <= STARTUP_MSG;
        tx_queue[39:0]  <= 40'h0;
        tx_queue_len    <= 6;
        tx_queue_pos    <= 0;
        tx_queue_valid  <= 1'b1;
        startup_sent    <= 1'b1;
    end

    // Forward cell outputs to host
    // Response: 0x10 [addr:4] [data:4] [hs:1]
    // handshake byte echoes the last Bus 1 handshake field seen
    if (out_valid && !tx_busy && !tx_queue_valid) begin
        tx_queue[87:80] <= 8'h10;
        tx_queue[79:48] <= out_addr;
        tx_queue[47:16] <= out_data;
        tx_queue[15:8]  <= {4'h0, last_handshake};  // handshake echo
        tx_queue[7:0]   <= 8'h0;
        tx_queue_len    <= 10;
        tx_queue_pos    <= 0;
        tx_queue_valid  <= 1'b1;
    end

    // Process TX queue
    if (tx_queue_valid && !tx_busy && !tx_send) begin
        tx_byte    <= tx_queue[87:80];
        tx_queue   <= {tx_queue[79:0], 8'h0};
        tx_send    <= 1'b1;
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
                // 0x01: inject — cmd(1) + bus1(4) + addr(4) + data(4) = 13 bytes
                8'h01: cmd_len <= 13;
                // 0x02: configure — cmd(1) + addr(4) + data(4) = 9 bytes
                8'h02: cmd_len <= 9;
                // 0x03: reset — cmd only
                8'h03: cmd_len <= 1;
                // 0x04: status — cmd only
                8'h04: cmd_len <= 1;
                // 0x06: freeze — cmd only
                8'h06: cmd_len <= 1;
                // 0x07: release freeze — cmd only
                8'h07: cmd_len <= 1;
                default: begin
                    cmd_active <= 1'b0;
                    tx_byte    <= 8'hFF;
                    tx_send    <= 1'b1;
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
                        // bus1 = cmd_buf[1..4] — Bus 1 word (scope+handshake+auth)
                        // addr = cmd_buf[5..8] — Bus 3 target address
                        // data = cmd_buf[9..12] — Bus 2 data
                        // Extract handshake field from Bus 1 bits 18-21
                        last_handshake <= {cmd_buf[3][5:4], cmd_buf[3][7:6]};
                        // Bus 1 passes through transparently to cpu_addr
                        // (Python side builds Bus 1 using build_bus1)
                        cpu_addr  <= {cmd_buf[5], cmd_buf[6], cmd_buf[7], cmd_buf[8]};
                        cpu_data  <= {cmd_buf[9], cmd_buf[10], cmd_buf[11], rx_byte};
                        cpu_valid <= 1'b1;
                    end
                    8'h02: begin
                        // Configure cell — send LOAD_PATTERN then values
                        // (handled as plain inject at Python side, kept for compat)
                        cpu_addr  <= {cmd_buf[1], cmd_buf[2], cmd_buf[3], cmd_buf[4]};
                        cpu_data  <= {cmd_buf[5], cmd_buf[6], cmd_buf[7], rx_byte};
                        cpu_valid <= 1'b1;
                    end
                    8'h03: begin
                        array_rst <= 1'b1;
                    end
                    8'h04: begin
                        // Status response: 0x11 [armed:2] [cycles:4]
                        tx_queue[87:80] <= 8'h11;
                        tx_queue[79:64] <= armed_count;
                        tx_queue[63:32] <= cycle_count;
                        tx_queue[31:0]  <= 32'h0;
                        tx_queue_len    <= 7;
                        tx_queue_pos    <= 0;
                        tx_queue_valid  <= 1'b1;
                    end
                    8'h06: begin
                        // Freeze — decouple all cells
                        array_freeze <= 1'b1;
                        tx_byte      <= 8'h13;  // Freeze acknowledged
                        tx_send      <= 1'b1;
                    end
                    8'h07: begin
                        // Release freeze
                        array_freeze <= 1'b0;
                        tx_byte      <= 8'h14;  // Release acknowledged
                        tx_send      <= 1'b1;
                    end
                endcase
            end
        end
    end
end

endmodule
