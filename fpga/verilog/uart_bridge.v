// uart_bridge.v v1.5 — 4-entry TX FIFO, no dropped packets on back-to-back fires

`timescale 1ns / 1ps
`default_nettype none

module uart_bridge #(
    parameter CLK_FREQ  = 12_000_000,
    parameter BAUD_RATE = 115_200
) (
    input  wire clk, rst, uart_rx,
    output wire uart_tx,
    output reg   [7:0] cpu_cmd,
    output reg  [15:0] cpu_addr, cpu_data,
    output reg         cpu_valid, array_rst, array_freeze,
    input  wire [15:0] out_addr,
    input  wire [31:0] out_data,
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
reg        tx_go    = 0;

assign uart_tx = tx_pin;

always @(posedge clk) begin
    if (rst) begin tx_state<=0; tx_pin<=1; tx_busy<=0; end
    else case (tx_state)
        0: begin
            tx_pin<=1;
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
        2: if (tx_cnt==0) begin
               tx_pin<=1; tx_cnt<=CPB-1; tx_state<=3;
           end else tx_cnt<=tx_cnt-1;
        3: if (tx_cnt==0) begin tx_busy<=0; tx_state<=0; end
           else tx_cnt<=tx_cnt-1;
    endcase
end

// ── TX FIFO — 4 entries × 10 bytes ───────────────────────────────────────────
// Each entry is 80 bits (10 bytes). Stored as 4 × 88-bit shift registers
// (same format as old q_sr) with a 2-bit read/write pointer.
// Write: push a new 88-bit packet + length into the next slot.
// Read:  drain the current slot byte by byte, then advance read pointer.
//
// FIFO depth 4: handles cell0+cell1+cell2+cell3 firing back-to-back.

localparam FIFO_DEPTH = 4;

reg [87:0] fifo_data [0:FIFO_DEPTH-1];
reg [3:0]  fifo_len  [0:FIFO_DEPTH-1];
reg [1:0]  fifo_wr   = 0;   // write pointer
reg [1:0]  fifo_rd   = 0;   // read pointer
reg [2:0]  fifo_cnt  = 0;   // occupancy (0-4)

wire fifo_full  = (fifo_cnt == FIFO_DEPTH);
wire fifo_empty = (fifo_cnt == 0);

// Current read slot
wire [87:0] q_sr_head = fifo_data[fifo_rd];
wire [3:0]  q_len_head = fifo_len[fifo_rd];

reg [3:0]  q_pos    = 0;    // byte position within current slot
reg        q_draining = 0;  // currently draining a slot

// Push a packet into the FIFO
task fifo_push;
    input [87:0] data;
    input [3:0]  len;
    begin
        if (!fifo_full) begin
            fifo_data[fifo_wr] <= data;
            fifo_len[fifo_wr]  <= len;
            fifo_wr  <= fifo_wr + 1;
            fifo_cnt <= fifo_cnt + 1;
        end
        // If full: silently drop (shouldn't happen with depth 4)
    end
endtask

// ── Queue drain — byte by byte from head slot ─────────────────────────────────
reg        stup_done = 0;
reg [11:0] stup_cnt  = 0;

reg [7:0]  cmd_buf[0:4];   // 5 bytes buffered (6th = rx_byte direct)
reg [3:0]  cmd_len   = 0;
reg [3:0]  cmd_pos   = 0;
reg [7:0]  cmd_byte  = 0;
reg        cmd_active = 0;

integer fi;

always @(posedge clk) begin
    tx_go     <= 0;
    cpu_valid <= 0;
    array_rst <= 0;

    if (rst) begin
        stup_done <= 0; stup_cnt <= 0;
        fifo_wr   <= 0; fifo_rd  <= 0; fifo_cnt <= 0;
        q_pos     <= 0; q_draining <= 0;
        cmd_active <= 0; array_freeze <= 0;
        for (fi = 0; fi < FIFO_DEPTH; fi = fi + 1) begin
            fifo_data[fi] <= 88'h0;
            fifo_len[fi]  <= 4'h0;
        end
    end

    if (!stup_done) stup_cnt <= stup_cnt + 1;

    // ── Drain FIFO head ───────────────────────────────────────────────────────
    if (!fifo_empty && !tx_busy && !tx_go) begin
        if (!q_draining) begin
            q_pos      <= 0;
            q_draining <= 1;
        end else begin
            tx_load <= fifo_data[fifo_rd][87:80];
            tx_go   <= 1;
            fifo_data[fifo_rd] <= {fifo_data[fifo_rd][79:0], 8'h0};
            if (q_pos == fifo_len[fifo_rd] - 1) begin
                // Finished this slot — advance read pointer
                fifo_rd    <= fifo_rd + 1;
                fifo_cnt   <= fifo_cnt - 1;
                q_pos      <= 0;
                q_draining <= 0;
            end else begin
                q_pos <= q_pos + 1;
            end
        end
    end

    // ── Startup: UCOK\r\n after 4096 cycles ───────────────────────────────────
    if (!stup_done && fifo_empty && !tx_busy && !tx_go && (&stup_cnt)) begin
        fifo_push(
            {8'h55,8'h43,8'h4F,8'h4B,8'h0D,8'h0A,40'h0},
            4'd6
        );
        stup_done <= 1;
    end

    // ── Cell fired -> host ────────────────────────────────────────────────────
    // Push into FIFO — no longer dropped if bridge is busy
    if (out_valid) begin
        fifo_push(
            {8'h10, out_addr, out_data, 16'h0, 8'h0},
            4'd8
        );
    end

    // ── RX command processor ──────────────────────────────────────────────────
    if (rx_ready) begin
        if (!cmd_active) begin
            cmd_byte<=rx_byte; cmd_pos<=1; cmd_active<=1;
            case (rx_byte)
                8'h01: cmd_len<=6;
                8'h02: cmd_len<=5;
                8'h03: begin cmd_active<=0; array_rst<=1; end
                8'h04: begin cmd_active<=0;
                    fifo_push(
                        {8'h11, armed_count, cycle_count, 32'h0},
                        4'd7
                    ); end
                8'h06: begin cmd_active<=0; array_freeze<=1;
                    fifo_push({8'h13,80'h0}, 4'd1); end
                8'h07: begin cmd_active<=0; array_freeze<=0;
                    fifo_push({8'h14,80'h0}, 4'd1); end
                default: begin
                    cmd_active<=0;
                    fifo_push({8'hFF,80'h0}, 4'd1);
                end
            endcase
        end else begin
            cmd_buf[cmd_pos] <= rx_byte;
            cmd_pos <= cmd_pos+1;
            if (cmd_pos == cmd_len-1) begin
                cmd_active<=0;
                case (cmd_byte)
                    8'h01: begin
                        // Frame: [0]=0x01 [1]=opcode [2]=addr_hi [3]=addr_lo [4]=data_hi [5]=data_lo
                        cpu_cmd  <= cmd_buf[1];              // 8-bit opcode
                        cpu_addr <= {cmd_buf[2], cmd_buf[3]};// 16-bit address
                        cpu_data <= {cmd_buf[4], rx_byte};   // 16-bit data (rx_byte = byte 5)
                        cpu_valid <= 1;
                    end
                    8'h02: begin
                        cpu_addr<={cmd_buf[1],cmd_buf[2]};  // 16-bit
                        cpu_data<={cmd_buf[3],rx_byte};          // 16-bit
                        cpu_valid<=1;
                    end
                    8'h03: array_rst<=1;
                    8'h04: begin
                        fifo_push(
                            {8'h11, armed_count, cycle_count, 32'h0},
                            4'd7
                        );
                    end
                endcase
            end
        end
    end
end

endmodule
