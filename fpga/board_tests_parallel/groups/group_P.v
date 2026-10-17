`default_nettype none
module board_top_group #(parameter integer SELBIT = 24, parameter integer CPB = 234, parameter integer SETTLE = 131072, parameter integer TIMEOUT = 33554432) (input wire BOARD_CLK, output wire UART_TX, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);
wire [2:0] tx, p_n, f_n, d_n;
board_top_iso_s0 #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t0 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[0]), .LED0_N(), .LED1_N(p_n[0]), .LED2_N(f_n[0]), .LED3_N(d_n[0]));
board_top_iso_s4 #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t1 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[1]), .LED0_N(), .LED1_N(p_n[1]), .LED2_N(f_n[1]), .LED3_N(d_n[1]));
board_top_iso_s8 #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t2 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[2]), .LED0_N(), .LED1_N(p_n[2]), .LED2_N(f_n[2]), .LED3_N(d_n[2]));
reg [27:0] sel_cnt = 28'd0; always @(posedge BOARD_CLK) sel_cnt <= sel_cnt + 28'd1;
reg [1:0] sel = 2'd0; reg wrap = 1'b0; always @(posedge BOARD_CLK) begin wrap <= sel_cnt[SELBIT]; if (wrap && !sel_cnt[SELBIT]) sel <= (sel == 2'd2) ? 2'd0 : sel + 2'd1; end
assign UART_TX = tx[sel];
wire all_done = (d_n == 3'd0); wire any_fail = (f_n != {3{1'b1}}); wire all_pass = (p_n == 3'd0);
reg [23:0] hb = 24'd0; always @(posedge BOARD_CLK) hb <= hb + 24'd1;
assign LED0_N = ~hb[23]; assign LED1_N = ~(all_done && all_pass && !any_fail); assign LED2_N = ~any_fail; assign LED3_N = ~all_done;
endmodule
