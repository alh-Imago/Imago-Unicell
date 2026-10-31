// hexn_presets_v1.v -- Hex-N open unit stage 4b: PRESETS (new file 1 Nov 2026). `psel` = 0 means no preset (the config registers act directly, as before). psel = 1..8 APPLIES preset psel-1: the eight words of that preset are read from the preset RAM
// (hexn_tabs_v2 space 5) and held as the EFFECTIVE settings: word 0 mode, 1 reaction bins, 2 press bins, 3 gap bins, 4 input pins, 5 output pins, 6 raw judge control, 7 reserved. While a preset is being applied `applying` is high (the top holds the personalities in reset);
// afterwards `active` stays high until psel returns to 0 or a different value is written. Any change of psel starts an apply (psel > 8 = no preset).
`default_nettype none
module hexn_presets_v1 (
    input  wire clk, input wire rst, input wire [31:0] psel,
    output reg  [5:0] pr_addr, input wire [31:0] pr_data,
    output reg  active, output wire applying,
    output reg  [1:0] e_mode, output reg [31:0] e_br, e_bp, e_bg, output reg [11:0] e_in, output reg [15:0] e_out, output reg [2:0] e_raw
);
    localparam S_IDLE = 0, S_A = 1, S_B = 2, S_C = 3;
    reg [1:0] st = S_IDLE; reg [31:0] psel_q = 0; reg [2:0] k; reg [2:0] p;
    assign applying = (st != S_IDLE);
    always @(posedge clk) begin
        if (rst) begin st <= S_IDLE; active <= 0; psel_q <= psel; end
        else case (st)
            S_IDLE: if (psel != psel_q) begin
                    psel_q <= psel;
                    if (psel == 0 || psel > 8) active <= 0; else begin active <= 0; p <= psel[2:0] - 3'd1; k <= 0; st <= S_A; end
                end
            S_A: begin pr_addr <= {p, k}; st <= S_B; end
            S_B: st <= S_C;
            S_C: begin
                case (k)
                    3'd0: e_mode <= pr_data[1:0]; 3'd1: e_br <= pr_data; 3'd2: e_bp <= pr_data; 3'd3: e_bg <= pr_data;
                    3'd4: e_in <= pr_data[11:0]; 3'd5: e_out <= pr_data[15:0]; 3'd6: e_raw <= pr_data[2:0]; default: ;
                endcase
                if (k == 3'd6) begin active <= 1; st <= S_IDLE; end else begin k <= k + 1'b1; st <= S_A; end
            end
        endcase
    end
endmodule
`default_nettype wire
