// hexn_tabs_v3.v -- Hex-N open unit STAGE 5a (new file 1 Nov 2026; clone of hexn_tabs_v2.v, untouched): as v2 PLUS the REVERSE COPY (Alan, 13:01): a SAVE command copies a table space BACK into the scratch RAM, where the host can read it over SPI. `sctl` = {space[31:28], scratch base[27:16], count[15:0]} (same layout as `ctl`), then change `sgo` (any new value) to start. count 0 = the space's own size: space 1 = rt_len words, 2 = mt_len, 3 = 256, 4 = 64, 5 = 64. Narrow tables are zero-extended to 32 bits (decode 6 bits, glyph 8 bits), exactly as the load path takes them.
//   Runs only from idle (like the load copy); busy is high meanwhile and the cores are held in reset by the top. The scratch RAM's single write port is taken through sv_act / sv_we / sv_addr / sv_data (the top gives it to this block while sv_act is high, as it does for the raw engine): do NOT write over SPI while busy.
//   REFUSED (nothing written, busy never goes high): a space other than 1 to 5, a count that resolves to 0, or a block that would run past scratch word 1023. v2 text follows.
// hexn_tabs_v2.v -- Hex-N open unit STAGE 4b (new file 1 Nov 2026; clone of hexn_tabs_v1.v, untouched): as v1 PLUS space 5 = the PRESET RAM (64 x 32, eight presets of eight words: mode, react bins, press bins, gap bins, input pins, output pins, raw judge control, reserved; read port pr_addr/pr_data). v1 text: the LOADABLE TABLES of the open unit, with factory defaults copied in at power-up.
//   space 1: reaction scorer table  (256 x 32, LOAD/BIAS words)       space 2: Morse scorer table (256 x 32)
//   space 3: Morse decode table (256 x 6): index {length(3), dots/dashes(5)} -> character code (0..25 A..Z, 26..35 0..9, 62 space, 63 not a character)
//   space 4: glyph table (64 x 8): character code -> seven-segment byte (a 0 bit lights a segment; bit 7 = the decimal point)
// Defaults come from the generated ROMs (hexn_demo_rom_v1, hexn_morse_gen_v1) and are copied in by a small state machine after reset (about 800 clock cycles), and again when `restore` changes. The host loads a table by writing the words into the
// scratch RAM over SPI and then COPYING them: `ctl` = {space[3:0], base[11:0] in the scratch RAM, count[15:0]}, then change `go` (any new value) to start. The copy sets that space's length to `count` (for the two scorer tables, the number of words the core loads at start).
// busy = 1 while a copy or the default fill is running; init_done = 1 after the first fill. Read ports are synchronous (data one cycle after the address).
`default_nettype none
module hexn_tabs_v3 (
    input  wire clk, input wire rst,
    input  wire [31:0] ctl, input  wire [31:0] go, input wire [31:0] restore, input wire [31:0] sctl, input wire [31:0] sgo,
    output wire sv_act, output wire sv_we, output wire [9:0] sv_addr, output reg [31:0] sv_data,
    output reg  [9:0]  sr_addr, input wire [31:0] sr_data,                 // the scratch RAM read port (registered by the owner)
    input  wire [7:0]  rt_addr, output reg [31:0] rt_data, output reg [8:0] rt_len,
    input  wire [7:0]  mt_addr, output reg [31:0] mt_data, output reg [8:0] mt_len,
    input  wire [7:0]  dec_addr, output reg [5:0] dec_ch,
    input  wire [23:0] chars, input wire pend, output reg [31:0] gsegs,
    input  wire [5:0] pr_addr, output reg [31:0] pr_data,
    output wire busy, output reg init_done
);
    reg [31:0] rt [0:255]; reg [31:0] mt [0:255]; reg [5:0] dec [0:255]; reg [7:0] gly [0:63]; reg [31:0] pre [0:63];
    // one write port per table (so the tools can use block RAM): enable, address and data are chosen by the state machine below
    reg rt_we, mt_we, dc_we, gl_we, pr_we; reg [7:0] wa; reg [31:0] wd;
    always @(posedge clk) begin
        if (rt_we) rt[wa] <= wd;
        if (mt_we) mt[wa] <= wd;
        if (dc_we) dec[wa] <= wd[5:0];
        if (gl_we) gly[wa[5:0]] <= wd[7:0];
        if (pr_we) pre[wa[5:0]] <= wd;
    end
    // ---- defaults
    wire [31:0] rom_r_d, rom_m_d; wire [7:0] rom_m_last; wire [5:0] dec_d; wire [7:0] gly_d; reg [8:0] i;
    hexn_demo_rom_v1  ROMR (.addr(i[7:0]), .data(rom_r_d));
    hexn_morse_rom_v1 ROMM (.addr(i[7:0]), .data(rom_m_d), .last(rom_m_last));
    hexn_morse_dec_v1 DECR (.len(i[7:5]), .bits(i[4:0]), .ch(dec_d));
    hexn_glyph_v1     GLYR (.ch(i[5:0]), .pend(1'b0), .seg(gly_d));
    localparam LEN_R = 193, LEN_M = 209;
    // ---- factory presets: 0 reaction game, 1 Morse key, 2 raw stream (one judge), 3 raw stream (two judges, loads go to judge A), 4..7 idle
    function [31:0] pdef(input [5:0] n);
        begin pdef = 32'd0;
            if (n[2:0] == 3'd0) pdef = (n[5:3] == 3'd0) ? 32'd1 : (n[5:3] == 3'd1) ? 32'd2 : (n[5:3] <= 3'd3) ? 32'd3 : 32'd0;
            if (n[2:0] == 3'd6 && n[5:3] == 3'd3) pdef = 32'd1;
        end
    endfunction
    // ---- state machine
    localparam S_IR = 0, S_IM = 1, S_ID = 2, S_IG = 3, S_IDLE = 4, S_CA = 5, S_CB = 6, S_CC = 7, S_IP = 8, S_SA = 9, S_SW = 10;
    reg [3:0] st = S_IR; reg [31:0] go_q = 0, rs_q = 0, sgo_q = 0; reg [3:0] ssp; reg [11:0] sbase; reg [15:0] scnt; reg [3:0] sp; reg [11:0] base; reg [15:0] cnt;
    assign busy = (st != S_IDLE);
    wire cwr = (st == S_CC);
    // ---- reverse copy (save): while active the read addresses of the table RAMs come from the walker, not from the cores
    assign sv_act = (st == S_SA) || (st == S_SW);
    assign sv_we  = (st == S_SW);
    assign sv_addr = sbase[9:0] + {2'b00, i[7:0]};
    reg [7:0] gsv;
    always @(posedge clk) begin
        rt_data <= rt[sv_act ? i[7:0] : rt_addr]; mt_data <= mt[sv_act ? i[7:0] : mt_addr]; dec_ch <= dec[sv_act ? i[7:0] : dec_addr]; pr_data <= pre[sv_act ? {2'b00, i[5:0]} : {2'b00, pr_addr}];
        gsv <= gly[i[5:0]];
    end
    always @* case (ssp) 4'd1: sv_data = rt_data; 4'd2: sv_data = mt_data; 4'd3: sv_data = {26'd0, dec_ch}; 4'd4: sv_data = {24'd0, gsv}; 4'd5: sv_data = pr_data; default: sv_data = 32'd0; endcase
    wire [15:0] sdef = (sctl[31:28] == 4'd1) ? {7'd0, rt_len} : (sctl[31:28] == 4'd2) ? {7'd0, mt_len} : (sctl[31:28] == 4'd3) ? 16'd256 : (sctl[31:28] == 4'd4 || sctl[31:28] == 4'd5) ? 16'd64 : 16'd0;
    wire [15:0] scount_in = (sctl[15:0] != 16'd0) ? sctl[15:0] : sdef;
    wire sv_ok = (sctl[31:28] >= 4'd1) && (sctl[31:28] <= 4'd5) && (scount_in != 16'd0) && ({4'd0, sctl[27:16]} + scount_in <= 17'd1024);
    // write strobes (combinational from the state): init states write the defaults, S_CC writes the copied word
    always @* begin
        rt_we = 0; mt_we = 0; dc_we = 0; gl_we = 0; pr_we = 0; wa = i[7:0]; wd = sr_data;
        case (st)
            S_IR: begin rt_we = 1; wd = rom_r_d; end
            S_IM: begin mt_we = 1; wd = rom_m_d; end
            S_ID: begin dc_we = 1; wd = {26'd0, dec_d}; end
            S_IG: begin gl_we = 1; wd = {24'd0, gly_d}; end
            S_IP: begin pr_we = 1; wd = pdef(i[5:0]); end
            S_CC: begin rt_we = (sp == 4'd1); mt_we = (sp == 4'd2); dc_we = (sp == 4'd3); gl_we = (sp == 4'd4) && (i[7:0] < 64); pr_we = (sp == 4'd5) && (i[7:0] < 64); end
            default: ;
        endcase
    end
    always @(posedge clk) begin
        go_q <= go; rs_q <= restore; sgo_q <= sgo;
        if (rst) begin st <= S_IR; i <= 0; init_done <= 0; sr_addr <= 0; rt_len <= 0; mt_len <= 0; end
        else case (st)
            S_IR: begin if (i == LEN_R - 1) begin rt_len <= LEN_R; i <= 0; st <= S_IM; end else i <= i + 1'b1; end
            S_IM: begin if (i == LEN_M - 1) begin mt_len <= LEN_M; i <= 0; st <= S_ID; end else i <= i + 1'b1; end
            S_ID: begin if (i == 255) begin i <= 0; st <= S_IG; end else i <= i + 1'b1; end
            S_IG: begin if (i == 63) begin i <= 0; st <= S_IP; end else i <= i + 1'b1; end
            S_IP: begin if (i == 63) begin i <= 0; st <= S_IDLE; init_done <= 1; end else i <= i + 1'b1; end
            S_IDLE: begin
                if (restore != rs_q) begin i <= 0; st <= S_IR; end
                else if (go != go_q) begin sp <= ctl[31:28]; base <= ctl[27:16]; cnt <= ctl[15:0]; i <= 0; if (ctl[15:0] != 0) st <= S_CA; end
                else if (sgo != sgo_q) begin ssp <= sctl[31:28]; sbase <= sctl[27:16]; scnt <= scount_in; i <= 0; if (sv_ok) st <= S_SA; end
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
            S_SA: st <= S_SW;                                                  // the RAM read happens at this edge
            S_SW: begin                                                        // write the word to the scratch RAM (sv_we is high in this state)
                if (i + 1 >= scnt || i == 255) st <= S_IDLE; else begin i <= i + 1'b1; st <= S_SA; end
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
