// axi_unicell_bridge.v — AXI-Lite Slave → UniCell Command/Data Bus
//
// Sits between the XDMA AXI-Lite user interface (BAR0) and the
// unicell_array. Translates AXI-Lite reads/writes into UniCell
// command packets and data bus injections.
//
// BAR0 Memory Map (each cell = 32 bytes = CELL_STRIDE):
//   Base + cell*32 + 0x00  [W]  CMD_WRITE   — opcode(8) + addr(16) + data(32)
//   Base + cell*32 + 0x04  [W]  DATA_WRITE  — inject data packet to cell input addr
//   Base + cell*32 + 0x08  [R]  OUT_READ    — read cell output (out_addr + out_data)
//   Base + cell*32 + 0x0C  [R]  STATUS      — armed_count + cycle_count
//   Base + cell*32 + 0x10  [W]  ARRAY_RST   — write any value to reset array
//   (0x14-0x1C reserved)
//
// AXI-Lite interface: 32-bit address, 32-bit data
// XDMA user clock: 125 MHz (from XDMA IP MMCM)
//
// Command packet format (written to CMD_WRITE offset):
//   axi_wdata[31:24] = opcode  (CMD_RECONFIGURE=4, SET_LOGICAL=14, etc.)
//   axi_waddr[15:0]  = cell physical/logical address
//   axi_wdata[23:0]  = payload (auth[23:16] + config[15:0])
//
// NOTE: This is the AXI-Lite slave interface from XDMA.
// The XDMA IP generates: m_axil_* (master, drives this slave)
//
// Silicon target: xc7k480tffg1156-2
// XDMA config:    x8 Gen1, 125 MHz user clock, 32-bit AXI-Lite

`default_nettype none

module axi_unicell_bridge #(
    parameter NUM_CELLS  = 100,
    parameter CELL_STRIDE = 32   // bytes per cell in BAR0
) (
    // AXI-Lite slave interface (from XDMA m_axil_*)
    input  wire        aclk,
    input  wire        aresetn,

    // Write address channel
    input  wire [31:0] s_axil_awaddr,
    input  wire        s_axil_awvalid,
    output reg         s_axil_awready,

    // Write data channel
    input  wire [31:0] s_axil_wdata,
    input  wire  [3:0] s_axil_wstrb,
    input  wire        s_axil_wvalid,
    output reg         s_axil_wready,

    // Write response channel
    output reg   [1:0] s_axil_bresp,
    output reg         s_axil_bvalid,
    input  wire        s_axil_bready,

    // Read address channel
    input  wire [31:0] s_axil_araddr,
    input  wire        s_axil_arvalid,
    output reg         s_axil_arready,

    // Read data channel
    output reg  [31:0] s_axil_rdata,
    output reg   [1:0] s_axil_rresp,
    output reg         s_axil_rvalid,
    input  wire        s_axil_rready,

    // UniCell array command bus outputs
    output reg   [7:0] cpu_cmd,       // 8-bit opcode
    output reg  [15:0] cpu_addr,      // 16-bit physical/logical address
    output reg  [31:0] cpu_data,      // 32-bit payload (auth[31:24]+config[23:0])
    output reg         cpu_valid,     // command strobe (1 cycle)
    output reg         array_rst,     // array reset

    // UniCell array data bus outputs
    output reg  [15:0] bus_addr,      // data bus address
    output reg  [31:0] bus_data,      // data bus data
    output reg         bus_valid,     // data bus strobe (1 cycle)

    // UniCell array outputs (read back)
    input  wire [15:0] out_addr,      // cell fired output address
    input  wire [31:0] out_data,      // cell fired output data
    input  wire        out_valid,     // cell fired pulse

    // Status inputs
    input  wire [15:0] armed_count,   // number of armed cells
    input  wire [31:0] cycle_count    // free-running cycle counter
);

// ── Register offsets within each cell's CELL_STRIDE block ─────────────────
localparam OFF_CMD    = 5'h00;  // [W] command: opcode+addr+data
localparam OFF_DATA   = 5'h04;  // [W] data inject
localparam OFF_OUT    = 5'h08;  // [R] last fired output
localparam OFF_STATUS = 5'h0C;  // [R] armed_count + out_valid
localparam OFF_RST    = 5'h10;  // [W] array reset

// ── Latch last fired output for reads ─────────────────────────────────────
reg [15:0] last_out_addr = 16'h0;
reg [31:0] last_out_data = 32'h0;
reg        last_out_valid = 1'b0;

always @(posedge aclk) begin
    if (!aresetn) begin
        last_out_addr  <= 16'h0;
        last_out_data  <= 32'h0;
        last_out_valid <= 1'b0;
    end else if (out_valid) begin
        last_out_addr  <= out_addr;
        last_out_data  <= out_data;
        last_out_valid <= 1'b1;
    end
end

// ── Write path ─────────────────────────────────────────────────────────────
reg [31:0] aw_addr_latch;
reg        aw_active = 1'b0;

always @(posedge aclk) begin
    if (!aresetn) begin
        s_axil_awready <= 1'b0;
        s_axil_wready  <= 1'b0;
        s_axil_bvalid  <= 1'b0;
        s_axil_bresp   <= 2'b00;
        cpu_cmd        <= 8'h0;
        cpu_addr       <= 16'h0;
        cpu_data       <= 32'h0;
        cpu_valid      <= 1'b0;
        bus_addr       <= 16'h0;
        bus_data       <= 32'h0;
        bus_valid      <= 1'b0;
        array_rst      <= 1'b0;
        aw_active      <= 1'b0;
    end else begin
        // Clear strobes each cycle
        cpu_valid  <= 1'b0;
        bus_valid  <= 1'b0;
        array_rst  <= 1'b0;

        // Accept write address
        s_axil_awready <= 1'b0;
        if (s_axil_awvalid && !aw_active) begin
            s_axil_awready <= 1'b1;
            aw_addr_latch  <= s_axil_awaddr;
            aw_active      <= 1'b1;
        end

        // Accept write data + process
        s_axil_wready <= 1'b0;
        if (s_axil_wvalid && aw_active) begin
            s_axil_wready <= 1'b1;
            aw_active     <= 1'b0;

            // Decode address: which cell and which register
            // cell_idx = addr[log2(NUM_CELLS)+4 : 5]
            // reg_off  = addr[4:0]
            case (aw_addr_latch[4:0])
                OFF_CMD: begin
                    // Command packet:
                    // wdata[31:24] = opcode
                    // waddr[15:0]  = target cell physical/logical ID
                    // wdata[23:0]  = payload (auth[23:16] + config[15:0])
                    cpu_cmd   <= s_axil_wdata[31:24];
                    cpu_addr  <= aw_addr_latch[20:5]; // cell index from address
                    cpu_data  <= {8'h0, s_axil_wdata[23:0]};
                    cpu_valid <= 1'b1;
                end
                OFF_DATA: begin
                    // Data inject: addr = cell's logical input address
                    // wdata[31:16] = bus address to inject to
                    // wdata[15:0]  = data value
                    bus_addr  <= s_axil_wdata[31:16];
                    bus_data  <= {16'h0, s_axil_wdata[15:0]};
                    bus_valid <= 1'b1;
                end
                OFF_RST: begin
                    array_rst <= 1'b1;
                end
                default: ; // ignore writes to read-only regs
            endcase

            // Send write response
            s_axil_bvalid <= 1'b1;
            s_axil_bresp  <= 2'b00; // OKAY
        end

        // Clear bvalid when accepted
        if (s_axil_bvalid && s_axil_bready) begin
            s_axil_bvalid <= 1'b0;
        end
    end
end

// ── Read path ──────────────────────────────────────────────────────────────
always @(posedge aclk) begin
    if (!aresetn) begin
        s_axil_arready <= 1'b0;
        s_axil_rvalid  <= 1'b0;
        s_axil_rdata   <= 32'h0;
        s_axil_rresp   <= 2'b00;
    end else begin
        s_axil_arready <= 1'b0;
        s_axil_rvalid  <= 1'b0;

        if (s_axil_arvalid && !s_axil_rvalid) begin
            s_axil_arready <= 1'b1;
            s_axil_rvalid  <= 1'b1;
            s_axil_rresp   <= 2'b00;

            case (s_axil_araddr[4:0])
                OFF_OUT: begin
                    // Upper 16 = out_addr, lower 16 = out_data[15:0]
                    // Host reads full out_data with second read if needed
                    s_axil_rdata <= {last_out_addr, last_out_data[15:0]};
                end
                OFF_OUT + 4: begin
                    // Full 32-bit out_data
                    s_axil_rdata <= last_out_data;
                end
                OFF_STATUS: begin
                    // Upper 16 = armed_count, lower 16 = out_valid flag + cycle low
                    s_axil_rdata <= {armed_count, 15'h0, last_out_valid};
                end
                OFF_STATUS + 4: begin
                    s_axil_rdata <= cycle_count;
                end
                default: begin
                    s_axil_rdata <= 32'hDEADBEEF;
                end
            endcase
        end

        if (s_axil_rvalid && s_axil_rready) begin
            s_axil_rvalid <= 1'b0;
        end
    end
end

endmodule

`default_nettype wire
