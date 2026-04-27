// top_tinyfpga_bx.v -- Imago UniCell top level for TinyFPGA BX
// Target: Lattice iCE40LP8K-CM81 (TinyFPGA BX, cs-tinyfpga-06)
// Clock: 16MHz internal oscillator
//
// Pin assignments for TinyFPGA BX:
//   PIN_1..PIN_24: GPIO (3.3V, 8mA drive)
//   USBP/USBN:     USB D+/D- (do not use for GPIO)
//   LED:           User LED (active high)
//
// Differences from iCEBreaker:
//   - iCE40LP8K vs iCE40UP5K (more LUTs: 7680 vs 5280)
//   - 16MHz internal oscillator vs 12MHz on iCEBreaker
//   - USB programming via TinyFPGA bootloader (no FTDI)
//   - No built-in buttons (use GPIO pins with pullups)
//   - Single user LED
//
// Bring-up sequence:
//   1. LED blink (confirm FPGA programs correctly)
//   2. UART loopback via PIN_1(TX) / PIN_2(RX)
//   3. 8 unicells -- NOT gate test
//   4. Two-input AND (posedge A, negedge B)
//   5. Bridge pair
//   6. Scale

`default_nettype none
`timescale 1ns / 1ps

module top_tinyfpga_bx (
    input  wire CLK,        // 16MHz internal oscillator

    // UART (connect USB-serial adapter to these pins)
    output wire PIN_1,      // UART TX
    input  wire PIN_2,      // UART RX

    // Status LED
    output wire LED,        // User LED (active high)

    // USB (leave unconnected unless using USB comms)
    output wire USBPU       // USB pull-up -- drive high to enable USB
);

    // Disable USB (we use UART for host comms)
    assign USBPU = 1'b0;

    // ── Clock ─────────────────────────────────────────────────────────────────
    // TinyFPGA BX has 16MHz internal oscillator on CLK pin.
    // Divide to 1MHz for conservative first bring-up.
    // Increase once basic operation confirmed.

    reg [3:0] clk_div = 0;
    reg       clk_1mhz = 0;

    always @(posedge CLK) begin
        clk_div <= clk_div + 1;
        if (clk_div == 4'd7) begin
            clk_1mhz <= ~clk_1mhz;
            clk_div  <= 0;
        end
    end

    // ── LED blink (bring-up stage 1) ─────────────────────────────────────────
    // Blink at ~1Hz to confirm programming and clock are working.
    reg [19:0] blink_ctr = 0;
    reg        led_reg   = 0;

    always @(posedge clk_1mhz) begin
        blink_ctr <= blink_ctr + 1;
        if (blink_ctr == 20'd500000) begin
            led_reg   <= ~led_reg;
            blink_ctr <= 0;
        end
    end

    assign LED = led_reg;

    // ── UART bridge to host ───────────────────────────────────────────────────
    // Same uart_bridge module as iCEBreaker target.
    // 16MHz clock, 115200 baud -> divider = 139

    wire [31:0] bus_addr_out;
    wire [31:0] bus_data_out;
    wire        bus_valid_out;
    wire        bus_phase_out;

    wire [31:0] cell_addr_in;
    wire [31:0] cell_data_in;
    wire        cell_valid_in;

    uart_bridge #(
        .CLK_FREQ  (16_000_000),
        .BAUD_RATE (115_200)
    ) uart_inst (
        .clk        (CLK),
        .rst        (1'b0),
        .rx         (PIN_2),
        .tx         (PIN_1),
        .bus_addr   (bus_addr_out),
        .bus_data   (bus_data_out),
        .bus_valid  (bus_valid_out),
        .bus_phase  (bus_phase_out),
        .cell_addr  (cell_addr_in),
        .cell_data  (cell_data_in),
        .cell_valid (cell_valid_in)
    );

    // ── UniCell array ─────────────────────────────────────────────────────────
    // iCE40LP8K has 7680 LUTs.
    // At ~82 LUTs per cell: ~93 cells maximum.
    // Conservative first bring-up: 8 cells.
    // Scale up once timing closure confirmed at 16MHz.

    localparam N_CELLS = 8;

    // Cell output buses (each cell drives one output slot)
    wire [31:0] cell_out_addr [0:N_CELLS-1];
    wire [31:0] cell_out_data [0:N_CELLS-1];
    wire        cell_out_valid[0:N_CELLS-1];

    // Wired-OR output bus back to UART
    // (simplified: first valid cell wins -- extend with priority encoder)
    assign cell_addr_in  = cell_out_addr [0]; // extend for N_CELLS
    assign cell_data_in  = cell_out_data [0];
    assign cell_valid_in = |{cell_out_valid};

    // Generate N_CELLS unicell_v2 instances
    genvar i;
    generate
        for (i = 0; i < N_CELLS; i = i + 1) begin : cells
            // Each cell has a unique CONFIG_ADDRESS
            // Address space: 0x00000100 + i*4
            unicell_v2 #(
                .CONFIG_ADDRESS (32'h00000100 + i * 4)
            ) cell_inst (
                .clk       (CLK),
                .rst       (1'b0),
                .freeze    (1'b0),
                .bus_addr  (bus_addr_out),
                .bus_data  (bus_data_out),
                .bus_valid (bus_valid_out),
                .bus_phase (bus_phase_out),
                .out_addr  (cell_out_addr [i]),
                .out_data  (cell_out_data [i]),
                .out_valid (cell_out_valid[i])
            );
        end
    endgenerate

endmodule
