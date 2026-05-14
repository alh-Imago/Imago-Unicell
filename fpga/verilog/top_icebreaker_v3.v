// top_icebreaker_v3.v — iCEBreaker top level for unicell_v3 bring-up
//
// Minimal test top: single unicell_v3 instance, UART bridge,
// cmd_bus constructed from UART commands.
//
// Clock: internal SB_HFOSC at 24MHz (validated on hardware)
// No external clock pin — avoids schematic/manual pin discrepancy.
//
// UART protocol (same as v1.2 fpga_bridge.py):
//   Host sends: [addr_hi][addr_lo][data_hi][data_lo] (4 x 16-bit words)
//   The bridge reconstructs bus_addr, bus_data, bus_valid.
//   cmd_bus is constructed from the top byte of addr word.
//
// Bring-up sequence:
//   1. Flash this bitstream
//   2. Run fpga_bridge.py — it will need updating for cmd_bus protocol
//   3. Send CMD_SET_INPUT_ADDR, CMD_SET_OUTPUT_ADDR
//   4. Send CMD_RECONFIGURE (auth word + config word)
//   5. Send data, observe output
//
// LED indicators:
//   LEDG_N: pulses when out_valid (cell fired)
//   LEDR_N: on when cell is armed (start_flag set in cmd_latch)

`default_nettype none

module top (
    input  wire BTN_N,
    input  wire RX,
    output wire TX,
    output wire LEDR_N,
    output wire LEDG_N
);

// ── Clock: internal HFOSC 24MHz ───────────────────────────────────────────────
wire CLK;
SB_HFOSC #(.CLKHF_DIV("0b01")) osc (
    .CLKHFPU(1'b1),
    .CLKHFEN(1'b1),
    .CLKHF(CLK)
);

wire rst = 1'b0;

// ── UART bridge ───────────────────────────────────────────────────────────────
wire [31:0] cpu_cmd, cpu_addr, cpu_data;
wire        cpu_valid;
wire [31:0] out_addr, out_data;
wire        out_valid;

uart_bridge #(
    .CLK_FREQ(24_000_000),
    .BAUD_RATE(115200)
) bridge (
    .clk        (CLK),
    .rst        (rst),
    .uart_rx    (RX),
    .uart_tx    (TX),
    .cpu_cmd    (cpu_cmd),
    .cpu_addr   (cpu_addr),
    .cpu_data   (cpu_data),
    .cpu_valid  (cpu_valid),
    .array_rst  (),
    .array_freeze(),
    .out_addr   (out_addr),
    .out_data   (out_data),
    .out_valid  (out_valid),
    .armed_count(array_armed),
    .cycle_count(array_cycles)
);

// ── cmd_bus construction ──────────────────────────────────────────────────────
// Temporary: construct cmd_bus from cpu_addr upper byte.
// cpu_addr[31:24] carries the command code for now.
// Full cmd_bus protocol (auth token, seq count etc) will move to
// fpga_bridge.py once bring-up validates the cell model.
//
// cmd_bus[3:0]  = cpu_addr[3:0]   -- command code
// cmd_bus[14:4] = cpu_addr[14:4]  -- auth token (11 bits)
// cmd_bus[15]   = cpu_addr[15]    -- address mode
// cmd_bus[31:16]= 16'h0           -- scope/handshake/seq (host sets via addr word)
wire [31:0] cmd_bus  = cpu_cmd;    // Bus 1 — command bus word from uart_bridge
wire        cmd_valid = cpu_valid;

// bus_data carries the payload (config word, data value etc)
// bus_addr carries the target cell address for data writes
// For CMD_SET_INPUT_ADDR and CMD_SET_OUTPUT_ADDR:
//   cmd_bus word identifies the command, bus_data carries the address value

// ── Cell array (8 cells, IDs 0-7) ────────────────────────────────────────────
wire [31:0] array_out_addr, array_out_data;
wire        array_out_valid;
wire [15:0] array_armed;
wire [31:0] array_cycles;
wire [31:0] array_tap_addr, array_tap_data;
wire        array_tap_valid;

unicell_array_v3 #(
    .NUM_CELLS(8),
    .BASE_ID  (0)
) array (
    .clk        (CLK),
    .rst        (rst),
    .freeze     (1'b0),
    .cmd_bus    (cmd_bus),
    .cmd_valid  (cmd_valid),
    .bus_addr   (cpu_addr),
    .bus_data   (cpu_data),
    .bus_valid  (cpu_valid),
    .out_addr   (array_out_addr),
    .out_data   (array_out_data),
    .out_valid  (array_out_valid),
    .armed_count(array_armed),
    .cycle_count(array_cycles),
    .tap_addr   (array_tap_addr),
    .tap_data   (array_tap_data),
    .tap_valid  (array_tap_valid)
);

// Feed both cell fires and raw bus tap to uart_bridge.
// Bus tap takes priority (more frequent). Cell fires included too.
// uart_bridge queues them -- host receives in order.
wire feed_valid = array_tap_valid || array_out_valid;
wire [31:0] feed_addr = array_tap_valid ? array_tap_addr : array_out_addr;
wire [31:0] feed_data = array_tap_valid ? array_tap_data : array_out_data;
assign out_addr  = feed_addr;
assign out_data  = feed_data;
assign out_valid = feed_valid;

// ── LED indicators ────────────────────────────────────────────────────────────
// LEDG_N: pulses on cell fire (out_valid) — active low
// LEDR_N: on when cell armed (start_flag = cmd_latch[22]) — active low
reg led_fired = 1'b0;
always @(posedge CLK) begin
    if (array_out_valid)
        led_fired <= 1'b1;
    else if (!BTN_N)      // button clears the fire indicator
        led_fired <= 1'b0;
end

assign LEDG_N = ~led_fired;                // green: cell has fired
assign LEDR_N = ~(array_armed > 0);         // red:   any cell armed

endmodule
