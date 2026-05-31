// top_icebreaker.v — Imago UniCell Top Level for iCEBreaker
// v2.3 — unified 32-bit command bus
//
// CLOCK: SB_HFOSC internal oscillator, NOT the external crystal.
//   "0b10" = 12MHz — reduced from 24MHz; 32-bit gate tree needs timing margin.
//
// Changes from v2.0:
//   - cmd_bus widened to 32-bit (v2.3 unified command word)
//   - cpu_cmd[7:0] + cpu_addr[15:0] → cpu_bus[31:0]
//   - cmd_valid_w checks cpu_bus[7:0] (opcode field) not separate cpu_cmd
//   - DATA_WRITE opcode (0x01) still excluded from cmd_valid

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// Internal HFOSC — 12MHz (48MHz / 4)
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b10")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

wire rst = 1'b0;

// ── Wires between bridge and array ───────────────────────────────────────────
wire [31:0] cpu_bus;     // v2.3 unified command word (replaces cpu_cmd + cpu_addr)
wire [31:0] cpu_data;    // payload
wire        cpu_valid, array_rst_req;

// Command bus — from bridge to all cells
// cpu_bus[31:0] is the full v2.3 cmd_bus word; array takes it directly.
wire [31:0] cmd_bus_w  = cpu_bus;    // unified 32-bit command word
wire [31:0] cmd_data_w = cpu_data;   // 32-bit payload
wire        cmd_valid_w;

// Data bus — from array to bridge (fired cell outputs)
wire [15:0] out_addr;
wire [31:0] out_data;
wire        out_valid;
wire [15:0] armed_count;
wire [31:0] cycle_count;

// cmd_valid: HIGH only for command opcodes, NOT for data writes (opcode 0x01).
// DATA_WRITE goes to data bus only — cells suppress bus_hit when cmd_valid HIGH,
// so data writes must never assert cmd_valid.
// Opcode is in cpu_bus[7:0] (v2.3 layout).
assign cmd_valid_w = cpu_valid && (cpu_bus[7:0] != 8'd0)   // not NOP
                               && (cpu_bus[7:0] != 8'd1);  // not DATA_WRITE

// cpu_addr mux:
//   DATA_WRITE (opcode 0x01): bus address in cmd_data[31:16]
//                             data value  in cmd_data[15:0] (16-bit, zero-extended)
//   All other commands:       target address in cmd_data[15:0]
//
// DATA_WRITE packet layout (9 bytes):
//   cmd_bus[7:0]   = 0x01 (opcode)
//   cmd_bus[28:21] = auth_token
//   cmd_data[31:16]= bus_addr (16-bit logical address)
//   cmd_data[15:0] = data value (16-bit, sign/zero extend to 32-bit in array)
//
// For full 32-bit data values on the bus, the array zero-extends cmd_data[15:0].
// Expand to full 32-bit cmd_data layout once 32-bit data bus needed on iCEBreaker.
wire [15:0] cpu_addr_w = (cpu_bus[7:0] == 8'd1) ? cmd_data_w[31:16]
                                                 : cmd_data_w[15:0];

unicell_array #(
    .NUM_CELLS(4)
) array (
    .clk        (CLK),
    .rst        (rst | array_rst_req),
    .cmd_bus    (cmd_bus_w),
    .cmd_data   (cmd_data_w),
    .cmd_valid  (cmd_valid_w),
    .cpu_addr   (cpu_addr_w),
    .cpu_data   (cmd_data_w),
    .cpu_valid  (cpu_valid),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(armed_count),
    .cycle_count(cycle_count)
);

uart_bridge #(
    .CLK_FREQ (12_000_000),
    .BAUD_RATE(115_200)
) bridge (
    .clk         (CLK),
    .rst         (rst),
    .uart_rx     (RX),
    .uart_tx     (TX),
    .cpu_bus     (cpu_bus),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .array_rst   (array_rst_req),
    .array_freeze(),             // CMD_FREEZE on command bus handles it
    .out_addr    (out_addr),
    .out_data    (out_data),
    .out_valid   (out_valid),
    .armed_count (armed_count),
    .cycle_count (cycle_count)
);

// LEDs — registered to keep combinational comparison off async IO path
reg ledr_n_reg = 1'b1;
always @(posedge CLK) ledr_n_reg <= (armed_count == 0);
assign LEDR_N = ledr_n_reg;
assign LEDG_N = 1'b0;  // Green always on

endmodule
