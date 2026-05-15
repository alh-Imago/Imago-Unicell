// unicell_v3.v — Imago UniCell v3
// Matches CELL_INTERNALS.md spec (2026-05-14)
//
// Key changes from v1.2:
//   - 32-bit command latch (one word, complete cell identity)
//   - Separate cmd_bus port (Bus 1) — distinct from data bus
//   - Auth token check on system commands (CMD_RECONFIGURE/FREEZE/RELEASE)
//   - Port-local address latches (input port + output port own their addresses)
//   - CMD_RECONFIGURE: 2 words only (auth_mask at boot + 32-bit config word)
//   - Cell type field (bits 25-26): standard/latch/posedge/negedge in one module
//   - Data type field (bits 23-24): NUMERIC/SIGNED/ALPHA/DATETIME
//   - Priority, trace, breakpoint flags persistent in command latch
//   - SYNC_WAIT: arrival count at own address (no input_b_address needed)
//   - 10-bit soft ECC on cmd_bus bits 22-31 (sequence count + identifier)
//   - LOAD_PATTERN magic retired — cmd_bus carries config protocol
//   - Shore index zone: bus_addr[31:28]==4'hF → intercept (not implemented here,
//     handled at array level)
//
// Command latch bit map:
//   bits  0-10:  NOR topology     (11 bits)
//   bits 11-21:  auth_mask        (11 bits, WRITE-ONLY)
//   bit   22:    start_flag       ( 1 bit)
//   bits 23-24:  data type        ( 2 bits) NUMERIC/SIGNED/ALPHA/DATETIME
//   bits 25-26:  cell type        ( 2 bits) standard/latch/posedge/negedge
//   bit   27:    priority         ( 1 bit)
//   bit   28:    trace            ( 1 bit)
//   bit   29:    breakpoint       ( 1 bit)
//   bits 30-31:  RESERVED         ( 2 bits, hard reserved)
//
// Command bus (Bus 1) bit map:
//   bits  0-3:   command code
//   bits  4-14:  auth token (11 bits, card-wide)
//   bit   15:    address mode
//   bits 16-17:  scope
//   bits 18-21:  handshake
//   bits 22-28:  sequence count (7 bits)  } 10-bit soft ECC
//   bits 29-31:  identifier     (3 bits)  }
//
// CMD_RECONFIGURE sequence:
//   Word 0: auth_mask[10:0]  — FIRST BOOT ONLY (cmd_latch[21:11] == 0)
//   Word 1: full 32-bit config word → command latch
//   After Word 1: start_flag set, cell armed.
//
// SYNC_WAIT: counts arrivals at own input_address (no second address needed).
//   arrival_count[0] → holds, arrival_count[1] → fires, resets to 0.
//
// Silicon note:
//   iCE40 does not support negedge flip-flops. Negedge cell type uses
//   odd_phase toggle (same technique as v1.2). On Kintex-7 true negedge
//   FFs are available — revisit.
//
// Resource estimate: ~65-70 LCs per cell on iCE40 (slightly more than v1.2
// due to cmd_bus logic and arrival counter). Kintex-7: ~50 LUTs.

`timescale 1ns / 1ps

module unicell_v3 #(
    parameter CELL_ID = 0           // Unique ID — for debug output only
) (
    input  wire        clk,         // System clock (rising edge)
    input  wire        rst,         // Synchronous reset (active high)
    input  wire        freeze,      // Fabric freeze line (array controller)

    // Command bus (Bus 1) — separate from data bus
    input  wire [31:0] cmd_bus,     // Full command bus word
    input  wire        cmd_valid,   // Command bus has valid data this cycle

    // Data bus (Bus 2/3)
    input  wire [31:0] bus_addr,    // Target address (Bus 3)
    input  wire [31:0] bus_data,    // Data payload (Bus 2)
    input  wire        bus_valid,   // Bus has valid data this cycle

    // Output (wired-OR across array)
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,
    output reg         out_valid,

    // Ward / debug outputs
    output wire [31:0] dbg_cmd_latch,   // Full command latch word (read-only)
    output wire [31:0] dbg_input_addr,  // Input port address latch
    output wire [31:0] dbg_output_addr, // Output port address latch
    output wire        dbg_frozen,
    output wire        dbg_trace,       // Trace flag (Ward monitors)
    output wire        dbg_breakpoint,  // Breakpoint flag (Ward monitors)
    output wire        dbg_priority     // Priority flag (scheduler monitors)
);

// ── Command codes ──────────────────────────────────────────────────────────────
localparam CMD_NOP             = 4'd0;
localparam CMD_DATA_WRITE      = 4'd1;
localparam CMD_SET_INPUT_ADDR  = 4'd2;
localparam CMD_SET_OUTPUT_ADDR = 4'd3;
localparam CMD_RECONFIGURE     = 4'd4;  // auth required
localparam CMD_FREEZE          = 4'd5;  // auth required
localparam CMD_RELEASE         = 4'd6;  // auth required
localparam CMD_COPY_TO_OUT     = 4'd7;
localparam CMD_COPY_TO_IN      = 4'd8;
localparam CMD_PING            = 4'd9;
// 10-15: runtime GS_ mode commands (TBD)

// ── Cell type constants ────────────────────────────────────────────────────────
localparam CTYPE_STANDARD = 2'b00;
localparam CTYPE_LATCH    = 2'b01;
localparam CTYPE_POSEDGE  = 2'b10;
localparam CTYPE_NEGEDGE  = 2'b11;

// ── Data type constants ────────────────────────────────────────────────────────
localparam DTYPE_NUMERIC  = 2'b00;
localparam DTYPE_SIGNED   = 2'b01;
localparam DTYPE_ALPHA    = 2'b10;
localparam DTYPE_DATETIME = 2'b11;

// ── CMD_RECONFIGURE state machine ──────────────────────────────────────────────
localparam RCFG_IDLE      = 2'd0;  // waiting
localparam RCFG_AUTH      = 2'd1;  // waiting for auth_mask word (boot only)
localparam RCFG_CONFIG    = 2'd2;  // waiting for 32-bit config word

// ── Command latch ──────────────────────────────────────────────────────────────
// The complete cell identity. Written only by CMD_RECONFIGURE (auth checked).
// auth_mask (bits 11-21) is write-only — never appears on any output.
reg [31:0] cmd_latch = 32'h0;

// Convenience wires into command latch fields
wire [10:0] cl_topology  = cmd_latch[10:0];
wire [10:0] cl_auth_mask = cmd_latch[21:11];  // INTERNAL ONLY — not on any output
wire        cl_start_flag= cmd_latch[22];
wire [1:0]  cl_dtype     = cmd_latch[24:23];
wire [1:0]  cl_ctype     = cmd_latch[26:25];
wire        cl_priority  = cmd_latch[27];
wire        cl_trace     = cmd_latch[28];
wire        cl_breakpoint= cmd_latch[29];
// bits 30-31: hard reserved — never read or written

// ── Port address latches ───────────────────────────────────────────────────────
// Each port owns its own address. Set by CMD_SET_INPUT/OUTPUT_ADDR.
// Completely separate from the command latch.
reg [31:0] input_addr_latch  = 32'h0;
reg [31:0] output_addr_latch = 32'h0;

// ── Data latches ───────────────────────────────────────────────────────────────
reg [31:0] input_latch_a  = 32'h0;  // SYNC_WAIT: first arrival
reg [31:0] input_latch_b  = 32'h0;  // SYNC_WAIT: second arrival
reg        arrival_count  = 1'b0;   // 0=waiting for first, 1=waiting for second
reg [31:0] data_reg       = 32'h0;  // latch-mode held value

// ── Config state ───────────────────────────────────────────────────────────────
reg [1:0]  rcfg_state     = RCFG_IDLE;
reg        freeze_latch   = 1'b0;   // set by CMD_FREEZE, cleared by CMD_RELEASE

// ── Phase toggle (negedge emulation on iCE40) ─────────────────────────────────
reg        odd_phase      = 1'b0;

// ── Output buffer ──────────────────────────────────────────────────────────────
reg [31:0] out_buf_data   = 32'h0;
reg [31:0] out_buf_addr   = 32'h0;
reg        out_buf_valid  = 1'b0;
reg        out_buf_posedge= 1'b0;  // 1=release on posedge, 0=release on negedge

// ── Auth check ─────────────────────────────────────────────────────────────────
wire [3:0]  cmd_code   = cmd_bus[3:0];
wire [10:0] cmd_token  = cmd_bus[14:4];
wire        cmd_amode  = cmd_bus[15];
wire [6:0]  cmd_seqcnt = cmd_bus[28:22];
wire [2:0]  cmd_ident  = cmd_bus[31:29];

// Auth OK: token matches, OR auth_mask is zero (bootstrap)
wire auth_ok = (cl_auth_mask == 11'h0) || (cmd_token == cl_auth_mask);

// Cell address match — system commands only execute on the targeted cell
// bus_addr == CELL_ID: direct address
// bus_addr == 0xFFFFFFFF: broadcast (all cells)
wire addr_match = (bus_addr == CELL_ID[31:0]) || (&bus_addr);

// Cell active: armed and not frozen
wire cell_active = cl_start_flag && !freeze && !freeze_latch;

// Data arriving at this cell's input address
wire data_match = bus_valid && (bus_addr == input_addr_latch) && cell_active;

// SYNC_WAIT mode flag (from topology bit 10 — reserved for SYNC_WAIT)
// Using topology bit 10 as the SYNC_WAIT flag within the NOR tree config.
wire sync_wait_mode = cl_topology[10];

// ── Debug outputs ──────────────────────────────────────────────────────────────
// cmd_latch is readable for Ward/debug — but auth_mask bits are ZEROED on output.
// Hardware enforces: auth_mask (bits 21:11) always read as zero from any port.
assign dbg_cmd_latch  = {cmd_latch[31:22], 11'h0, cmd_latch[10:0]};
assign dbg_input_addr = input_addr_latch;
assign dbg_output_addr= output_addr_latch;
assign dbg_frozen     = freeze || freeze_latch;
assign dbg_trace      = cl_trace;
assign dbg_breakpoint = cl_breakpoint;
assign dbg_priority   = cl_priority;

// ── NOR gate topology (combinatorial, untimed) ─────────────────────────────────
// Direct 11-bit mapping. No decode stage. Single-cycle guarantee preserved.
// Topology bits 0-9 select gate output. Bit 10 = SYNC_WAIT (handled separately).
//
// Gate tree (NOR-universal):
//   g0 = NOR(in, in) = NOT(in)
//   g1 = NOR(in, in) = NOT(in)
//   g2 = NOR(g0, g1) = NOT(NOT(in) | NOT(in)) = in  (PASS)
//   g3 = NOR(g2, in)
//   g4 = NOR(g2, in)
//   g5 = NOR(g3, g4)
//   g6 = NOR(g5, in)
//   g7 = NOR(g6, g5)
//   g8 = NOR(g7, 1'b0) = NOT(g7)
//   g9 = NOR(g8, g6)

reg computed_output;
reg g0,g1,g2,g3,g4,g5,g6,g7,g8,g9;
reg in_val;

always @(*) begin
    // Input value: new bus data if arriving this cycle, else held data_reg
    in_val = data_match ? bus_data[0] : data_reg[0];

    g0 = ~(in_val | in_val);
    g1 = ~(in_val | in_val);
    g2 = ~(g0 | g1);
    g3 = ~(g2 | in_val);
    g4 = ~(g2 | in_val);
    g5 = ~(g3 | g4);
    g6 = ~(g5 | in_val);
    g7 = ~(g6 | g5);
    g8 = ~(g7 | 1'b0);
    g9 = ~(g8 | g6);

    case (cl_topology[9:0])
        10'b0000000001: computed_output = g0;
        10'b0000000010: computed_output = g1;
        10'b0000000100: computed_output = g2;
        10'b0000001000: computed_output = g3;
        10'b0000010000: computed_output = g4;
        10'b0000100000: computed_output = g5;
        10'b0001000000: computed_output = g6;
        10'b0010000000: computed_output = g7;
        10'b0100000000: computed_output = g8;
        10'b1000000000: computed_output = g9;
        default:        computed_output = in_val;  // PASS (topology = 0)
    endcase
end

// ── Main clocked logic ─────────────────────────────────────────────────────────
always @(posedge clk) begin
    if (rst) begin
        cmd_latch        <= 32'h0;
        input_addr_latch <= 32'h0;
        output_addr_latch<= 32'h0;
        input_latch_a    <= 32'h0;
        input_latch_b    <= 32'h0;
        arrival_count    <= 1'b0;
        data_reg         <= 32'h0;
        rcfg_state       <= RCFG_IDLE;
        freeze_latch     <= 1'b0;
        odd_phase        <= 1'b0;
        out_valid        <= 1'b0;
        out_addr         <= 32'h0;
        out_data         <= 32'h0;
        out_buf_valid    <= 1'b0;
        out_buf_data     <= 32'h0;
        out_buf_addr     <= 32'h0;
        out_buf_posedge  <= 1'b0;

    end else begin
        out_valid <= 1'b0;
        odd_phase <= ~odd_phase;

        // ── Output buffer drain ──────────────────────────────────────────────
        // Negedge release (odd_phase=1, posedge emulation of negedge)
        if (odd_phase && out_buf_valid && !out_buf_posedge) begin
            out_addr     <= out_buf_addr;
            out_data     <= out_buf_data;
            out_valid    <= 1'b1;
            out_buf_valid<= 1'b0;
        end
        // Posedge release
        if (!odd_phase && out_buf_valid && out_buf_posedge) begin
            out_addr     <= out_buf_addr;
            out_data     <= out_buf_data;
            out_valid    <= 1'b1;
            out_buf_valid<= 1'b0;
        end

        // ── Command bus processing ───────────────────────────────────────────
        if (cmd_valid) begin
            case (cmd_code)

                CMD_SET_INPUT_ADDR: begin
                    // User+system — no auth, but must address this cell
                    if (bus_valid && addr_match)
                        input_addr_latch <= bus_data;
                end

                CMD_SET_OUTPUT_ADDR: begin
                    // User+system — no auth, but must address this cell
                    if (bus_valid && addr_match)
                        output_addr_latch <= bus_data;
                end

                CMD_RECONFIGURE: begin
                    if (auth_ok && addr_match) begin
                        if (cl_auth_mask == 11'h0) begin
                            // Bootstrap: auth_mask==0, this word IS the auth_mask
                            if (bus_valid) begin
                                cmd_latch[21:11] <= bus_data[10:0];
                                cmd_latch[22]    <= 1'b0;
                                rcfg_state       <= RCFG_CONFIG;
                            end
                        end else begin
                            // Normal reconfigure — this word IS the config word
                            if (bus_valid) begin
                                cmd_latch[10:0]  <= bus_data[10:0];
                                cmd_latch[22]    <= 1'b1;
                                cmd_latch[24:23] <= bus_data[24:23];
                                cmd_latch[26:25] <= bus_data[26:25];
                                cmd_latch[27]    <= bus_data[27];
                                cmd_latch[28]    <= bus_data[28];
                                cmd_latch[29]    <= bus_data[29];
                                data_reg         <= 32'h0;
                                arrival_count    <= 1'b0;
                                input_latch_a    <= 32'h0;
                                input_latch_b    <= 32'h0;
                                rcfg_state       <= RCFG_IDLE;
                            end
                        end
                    end
                    // Silent drop on auth/addr mismatch
                end

                CMD_FREEZE: begin
                    if (auth_ok && addr_match)
                        freeze_latch <= 1'b1;
                    // Silent drop on mismatch
                end

                CMD_RELEASE: begin
                    if (auth_ok && addr_match)
                        freeze_latch <= 1'b0;
                    // Silent drop on mismatch
                end

                CMD_PING: begin
                    // Anyone can ping — responds with CELL_ID
                    // Works regardless of armed state — just not when frozen
                    if (!freeze && !freeze_latch) begin
                        out_addr  <= output_addr_latch;
                        out_data  <= CELL_ID[31:0];
                        out_valid <= 1'b1;
                    end
                end

                default: ; // CMD_NOP and unimplemented codes — do nothing
            endcase
        end

        // ── CMD_RECONFIGURE config word state machine ─────────────────────────
        // Runs independently of cmd_valid — waits for bus_data word
        if (rcfg_state == RCFG_CONFIG && bus_valid && addr_match) begin
            // Load full 32-bit config word into command latch
            // Preserve auth_mask (bits 21:11) — only topology and flags update
            cmd_latch[10:0]  <= bus_data[10:0];   // NOR topology
            // bits 21:11 (auth_mask) NOT overwritten here — set at bootstrap only
            cmd_latch[22]    <= 1'b1;              // start_flag: arm cell
            cmd_latch[24:23] <= bus_data[24:23];   // data type
            cmd_latch[26:25] <= bus_data[26:25];   // cell type
            cmd_latch[27]    <= bus_data[27];       // priority
            cmd_latch[28]    <= bus_data[28];       // trace
            cmd_latch[29]    <= bus_data[29];       // breakpoint
            // bits 30-31: hard reserved — never written
            // Reset runtime state
            data_reg         <= 32'h0;
            arrival_count    <= 1'b0;
            input_latch_a    <= 32'h0;
            input_latch_b    <= 32'h0;
            rcfg_state       <= RCFG_IDLE;
        end

        // ── Data path (only when cell is active and not in reconfig) ──────────
        if (!freeze && !freeze_latch && cl_start_flag && rcfg_state == RCFG_IDLE) begin

            if (data_match) begin
                case (cl_ctype)

                    CTYPE_STANDARD: begin
                        // Purely combinatorial — fire immediately, same cycle.
                        // No output buffer, no phase wait.
                        data_reg  <= bus_data;
                        out_addr  <= output_addr_latch;
                        out_data  <= {31'h0, computed_output};
                        out_valid <= 1'b1;
                        if (sync_wait_mode) begin
                            if (!arrival_count) begin
                                input_latch_a <= bus_data;
                                arrival_count <= 1'b1;
                                out_valid     <= 1'b0;  // suppress first arrival
                            end else begin
                                input_latch_b <= bus_data;
                                arrival_count <= 1'b0;
                                out_valid     <= 1'b1;  // fire on second arrival
                                input_latch_a <= 32'h0;
                            end
                        end
                    end

                    CTYPE_LATCH: begin
                        // Fire immediately like STANDARD, but hold value for re-emit.
                        data_reg  <= {31'h0, computed_output};
                        out_addr  <= output_addr_latch;
                        out_data  <= {31'h0, computed_output};
                        out_valid <= 1'b1;
                    end

                    CTYPE_POSEDGE: begin
                        // Rising edge — load buffer, release on posedge (odd_phase=0)
                        data_reg        <= bus_data;
                        out_buf_addr    <= output_addr_latch;
                        out_buf_data    <= {31'h0, computed_output};
                        out_buf_valid   <= 1'b1;
                        out_buf_posedge <= 1'b1;
                    end

                    CTYPE_NEGEDGE: begin
                        // Falling edge — load buffer, release on negedge (odd_phase=1)
                        data_reg        <= bus_data;
                        out_buf_addr    <= output_addr_latch;
                        out_buf_data    <= {31'h0, computed_output};
                        out_buf_valid   <= 1'b1;
                        out_buf_posedge <= 1'b0;
                    end

                endcase

            end else if (cl_ctype == CTYPE_LATCH && cl_start_flag &&
                         data_reg != 32'h0) begin
                // LATCH: re-emit held value every tick even with no new data
                out_addr  <= output_addr_latch;
                out_data  <= data_reg;
                out_valid <= 1'b1;
            end
        end
    end
end

endmodule
