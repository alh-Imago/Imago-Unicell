// sdt_bridge.v - UART commands for the SDRAM test build (sc_top_sdt).  All multi-byte fields are little-endian.
//   'V'                         -> 8 bytes: 'S','D', 1, init_done, words(4)             (words = 2097152)
//   'I'                         -> 4 bytes: init_done, cl, dly, inv                     (the controller's current settings)
//   'K' cl dly inv              set the controller's settings and run the power-up sequence again (poll 'I' until init_done = 1)
//   'w' addr(3) data(4)         write one word            (not while a test runs)
//   'r' addr(3)                 -> 4 bytes: the word      (not while a test runs)
//   'T' mode lg base(3) count(3) seed(4)   start the on-chip memory test (see sdt_selftest.v)
//   'Q'                         -> 25 bytes: flags(1: bit0 running, bit1 done), errors(4), first_addr(4), first_expected(4), first_got(4), write_clocks(4), read_clocks(4)
module sdt_bridge #(parameter DIV = 234) (
    input  wire        clk, rx,
    output wire        tx,
    output reg  [1:0]  cfg_cl, cfg_dly,
    output reg         cfg_inv, reinit,
    input  wire        init_done,
    output reg         h_v, h_we,
    output reg  [20:0] h_a,
    output reg  [31:0] h_wd,
    input  wire        h_acc, ack_v,
    input  wire [31:0] ack_d,
    output reg         t_start,
    output reg  [1:0]  t_mode,
    output reg  [4:0]  t_lg,
    output reg  [20:0] t_base,
    output reg  [21:0] t_count,
    output reg  [31:0] t_seed,
    input  wire        t_run, t_done,
    input  wire [31:0] t_err, t_fa, t_fe, t_fg, t_wc, t_rc,
    output reg         act_rx, act_tx
);
    wire [7:0] rb; wire rv;
    uart_rx #(.DIV(DIV)) urx (.clk(clk), .rx(rx), .data(rb), .valid(rv));
    reg  [7:0] tb = 0; reg tsend = 0; wire tbusy;
    uart_tx #(.DIV(DIV)) utx (.clk(clk), .data(tb), .send(tsend), .tx(tx), .busy(tbusy));
    localparam IDLE = 0, ARGS = 1, EXEC = 2, WACC = 3, WACK = 4, REPLY = 5;
    reg [2:0]  st = IDLE;
    reg [7:0]  cmd = 0;
    reg [4:0]  need = 0, got = 0;
    reg [7:0]  a [0:15];
    reg [6:0]  rlen = 0, ridx = 0;
    reg [31:0] dsave = 0;
    reg [23:0] stx = 0, srx = 0;
    function [7:0] rbyte(input [7:0] c, input [6:0] i);
        reg [31:0] w;
        begin
            w = 32'd0;
            if (c == "Q") begin
                case (i[6:2])
                    0: w = {30'd0, t_done, t_run}; 1: w = t_err; 2: w = t_fa; 3: w = t_fe; 4: w = t_fg; 5: w = t_wc; default: w = t_rc;
                endcase
                // byte 0 is the flags byte, then six 4-byte words: map index i (1..24) to word (i-1)/4
                case ((i - 1) >> 2)
                    0: w = t_err; 1: w = t_fa; 2: w = t_fe; 3: w = t_fg; 4: w = t_wc; default: w = t_rc;
                endcase
                rbyte = (i == 0) ? {6'd0, t_done, t_run} : (w >> (8 * ((i - 1) & 3)));
            end else if (c == "I") begin
                case (i[1:0]) 0: rbyte = {7'd0, init_done}; 1: rbyte = {6'd0, cfg_cl}; 2: rbyte = {6'd0, cfg_dly}; default: rbyte = {7'd0, cfg_inv}; endcase
            end else if (c == "r") begin
                rbyte = dsave >> (8 * i[1:0]);
            end else begin                                  // 'V'
                case (i[2:0]) 0: rbyte = "S"; 1: rbyte = "D"; 2: rbyte = 8'd1; 3: rbyte = {7'd0, init_done}; 4: rbyte = 8'h00; 5: rbyte = 8'h00; 6: rbyte = 8'h20; default: rbyte = 8'h00; endcase
            end
        end
    endfunction
    always @(posedge clk) begin
        t_start <= 1'b0; reinit <= 1'b0; tsend <= 1'b0;
        stx <= (tsend) ? 24'hFFFFFF : (stx != 0 ? stx - 1'b1 : 24'd0);
        srx <= (rv)    ? 24'hFFFFFF : (srx != 0 ? srx - 1'b1 : 24'd0);
        act_tx <= (stx != 0); act_rx <= (srx != 0);
        case (st)
            IDLE: if (rv) begin
                cmd <= rb; got <= 0;
                case (rb)
                    "V": begin rlen <= 8;  ridx <= 0; st <= REPLY; end
                    "I": begin rlen <= 4;  ridx <= 0; st <= REPLY; end
                    "Q": begin rlen <= 25; ridx <= 0; st <= REPLY; end
                    "K": begin need <= 3;  st <= ARGS; end
                    "w": begin need <= 7;  st <= ARGS; end
                    "r": begin need <= 3;  st <= ARGS; end
                    "T": begin need <= 12; st <= ARGS; end
                    default: ;
                endcase
            end
            ARGS: if (rv) begin
                a[got] <= rb; got <= got + 1'b1;
                if (got + 1'b1 == need) st <= EXEC;
            end
            EXEC: begin
                case (cmd)
                    "K": begin cfg_cl <= a[0][1:0]; cfg_dly <= a[1][1:0]; cfg_inv <= a[2][0]; reinit <= 1'b1; st <= IDLE; end
                    "T": begin if (!t_run && init_done) begin t_mode <= a[0][1:0]; t_lg <= a[1][4:0]; t_base <= {a[4][4:0], a[3], a[2]}; t_count <= {a[7][5:0], a[6], a[5]}; t_seed <= {a[11], a[10], a[9], a[8]}; t_start <= 1'b1; end st <= IDLE; end
                    "w": if (t_run || !init_done) st <= IDLE; else begin h_v <= 1'b1; h_we <= 1'b1; h_a <= {a[2][4:0], a[1], a[0]}; h_wd <= {a[6], a[5], a[4], a[3]}; st <= WACC; end
                    "r": if (t_run || !init_done) begin dsave <= 32'hDEADBEEF; rlen <= 4; ridx <= 0; st <= REPLY; end
                         else begin h_v <= 1'b1; h_we <= 1'b0; h_a <= {a[2][4:0], a[1], a[0]}; st <= WACC; end
                    default: st <= IDLE;
                endcase
            end
            WACC: if (h_acc) begin h_v <= 1'b0; st <= WACK; end
            WACK: if (ack_v) begin
                if (cmd == "r") begin dsave <= ack_d; rlen <= 4; ridx <= 0; st <= REPLY; end else st <= IDLE;
            end
            REPLY: if (!tbusy && !tsend) begin
                if (ridx == rlen) st <= IDLE;
                else begin tb <= rbyte(cmd, ridx); tsend <= 1'b1; ridx <= ridx + 1'b1; end
            end
        endcase
    end
    initial begin cfg_cl = 2'd2; cfg_dly = 2'd1; cfg_inv = 1'b0; reinit = 0; h_v = 0; h_we = 0; h_a = 0; h_wd = 0; t_start = 0; t_mode = 0; t_lg = 0; t_base = 0; t_count = 0; t_seed = 0; end
endmodule
