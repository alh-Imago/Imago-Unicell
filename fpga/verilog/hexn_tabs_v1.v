// hexn_tabs_v1.v -- Hex-N open unit STAGE 2 (new file 1 Nov 2026): the LOADABLE TABLES of the open unit, with factory defaults copied in at power-up.
//   space 1: reaction scorer table  (256 x 32, LOAD/BIAS words)       space 2: Morse scorer table (256 x 32)
//   space 3: Morse decode table (256 x 6): index {length(3), dots/dashes(5)} -> character code (0..25 A..Z, 26..35 0..9, 62 space, 63 not a character)
//   space 4: glyph table (64 x 8): character code -> seven-segment byte (a 0 bit lights a segment; bit 7 = the decimal point)
// Defaults come from the generated ROMs (hexn_demo_rom_v1, hexn_morse_gen_v1) and are copied in by a small state machine after reset (about 800 clock cycles), and again when `restore` changes. The host loads a table by writing the words into the
// scratch RAM over SPI and then COPYING them: `ctl` = {space[3:0], base[11:0] in the scratch RAM, count[15:0]}, then change `go` (any new value) to start. The copy sets that space's length to `count` (for the two scorer tables, the number of words the core loads at start).
// busy = 1 while a copy or the default fill is running; init_done = 1 after the first fill. Read ports are synchronous (data one cycle after the address).
`default_nettype none
module hexn_tabs_v1 (
    input  wire clk, input wire rst,
    input  wire [31:0] ctl, input  wire [31:0] go, input wire [31:0] restore,
    output reg  [9:0]  sr_addr, input wire [31:0] sr_data,                 // the scratch RAM read port (registered by the owner)
    input  wire [7:0]  rt_addr, output reg [31:0] rt_data, output reg [8:0] rt_len,
    input  wire [7:0]  mt_addr, output reg [31:0] mt_data, output reg [8:0] mt_len,
    input  wire [7:0]  dec_addr, output reg [5:0] dec_ch,
    input  wire [23:0] chars, input wire pend, output reg [31:0] gsegs,
    output wire busy, output reg init_done
);
    reg [31:0] rt [0:255]; reg [31:0] mt [0:255]; reg [5:0] dec [0:255]; reg [7:0] gly [0:63];
    // one write port per table (so the tools can use block RAM): enable, address and data are chosen by the state machine below
    reg rt_we, mt_we, dc_we, gl_we; reg [7:0] wa; reg [31:0] wd;
    always @(posedge clk) begin
        rt_data <= rt[rt_addr]; mt_data <= mt[mt_addr]; dec_ch <= dec[dec_addr];
        if (rt_we) rt[wa] <= wd;
        if (mt_we) mt[wa] <= wd;
        if (dc_we) dec[wa] <= wd[5:0];
        if (gl_we) gly[wa[5:0]] <= wd[7:0];
    end
    // ---- defaults
    wire [31:0] rom_r_d, rom_m_d; wire [7:0] rom_m_last; wire [5:0] dec_d; wire [7:0] gly_d; reg [8:0] i;
    hexn_demo_rom_v1  ROMR (.addr(i[7:0]), .data(rom_r_d));
    hexn_morse_rom_v1 ROMM (.addr(i[7:0]), .data(rom_m_d), .last(rom_m_last));
    hexn_morse_dec_v1 DECR (.len(i[7:5]), .bits(i[4:0]), .ch(dec_d));
    hexn_glyph_v1     GLYR (.ch(i[5:0]), .pend(1'b0), .seg(gly_d));
    localparam LEN_R = 193, LEN_M = 209;
    // ---- state machine
    localparam S_IR = 0, S_IM = 1, S_ID = 2, S_IG = 3, S_IDLE = 4, S_CA = 5, S_CB = 6, S_CC = 7;
    reg [2:0] st = S_IR; reg [31:0] go_q = 0, rs_q = 0; reg [3:0] sp; reg [11:0] base; reg [15:0] cnt;
    assign busy = (st != S_IDLE);
    wire cwr = (st == S_CC);
    // write strobes (combinational from the state): init states write the defaults, S_CC writes the copied word
    always @* begin
        rt_we = 0; mt_we = 0; dc_we = 0; gl_we = 0; wa = i[7:0]; wd = sr_data;
        case (st)
            S_IR: begin rt_we = 1; wd = rom_r_d; end
            S_IM: begin mt_we = 1; wd = rom_m_d; end
            S_ID: begin dc_we = 1; wd = {26'd0, dec_d}; end
            S_IG: begin gl_we = 1; wd = {24'd0, gly_d}; end
            S_CC: begin rt_we = (sp == 4'd1); mt_we = (sp == 4'd2); dc_we = (sp == 4'd3); gl_we = (sp == 4'd4) && (i[7:0] < 64); end
            default: ;
        endcase
    end
    always @(posedge clk) begin
        go_q <= go; rs_q <= restore;
        if (rst) begin st <= S_IR; i <= 0; init_done <= 0; sr_addr <= 0; rt_len <= 0; mt_len <= 0; end
        else case (st)
            S_IR: begin if (i == LEN_R - 1) begin rt_len <= LEN_R; i <= 0; st <= S_IM; end else i <= i + 1'b1; end
            S_IM: begin if (i == LEN_M - 1) begin mt_len <= LEN_M; i <= 0; st <= S_ID; end else i <= i + 1'b1; end
            S_ID: begin if (i == 255) begin i <= 0; st <= S_IG; end else i <= i + 1'b1; end
            S_IG: begin if (i == 63) begin i <= 0; st <= S_IDLE; init_done <= 1; end else i <= i + 1'b1; end
            S_IDLE: begin
                if (restore != rs_q) begin i <= 0; st <= S_IR; end
                else if (go != go_q) begin sp <= ctl[31:28]; base <= ctl[27:16]; cnt <= ctl[15:0]; i <= 0; if (ctl[15:0] != 0) st <= S_CA; end
            end
            S_CA: begin sr_addr <= {2'b00, i[7:0]} + base[9:0]; st <= S_CB; end
            S_CB: st <= S_CC;                                                  // the RAM read happens at this edge
            S_CC: begin
                if (i + 1 >= cnt || i == 255) begin
                    if (sp == 4'd1) rt_len <= (cnt > 256) ? 9'd256 : cnt[8:0];
                    if (sp == 4'd2) mt_len <= (cnt > 256) ? 9'd256 : cnt[8:0];
                    st <= S_IDLE;
                end else begin i <= i + 1'b1; st <= S_CA; end
            end
            default: st <= S_IDLE;
        endcase
    end
    // ---- glyph reader: four characters, one per cycle in turn
    reg [1:0] gk = 0; reg [5:0] gch; reg [7:0] gq; reg [1:0] gk_d = 0, gk_dd = 0; reg [31:0] gs = 32'hFFFFFFFF;
    always @(posedge clk) begin
        gk <= gk + 1'b1; gk_d <= gk; gk_dd <= gk_d;
        gch <= (gk == 0) ? chars[23:18] : (gk == 1) ? chars[17:12] : (gk == 2) ? chars[11:6] : chars[5:0];     // registered address
        gq <= gly[gch];                                                   // data for the address of the previous cycle
        case (gk_dd)
            2'd0: gs[31:24] <= gq; 2'd1: gs[23:16] <= gq; 2'd2: gs[15:8] <= gq; default: gs[7:0] <= gq & (pend ? 8'h7F : 8'hFF);
        endcase
        gsegs <= gs;
    end
endmodule
`default_nettype wire
