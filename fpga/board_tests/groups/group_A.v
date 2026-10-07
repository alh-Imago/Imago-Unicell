`default_nettype none
module board_top_group #(parameter integer SELBIT = 26, parameter integer CPB = 234, parameter integer SETTLE = 131072, parameter integer TIMEOUT = 33554432) (input wire BOARD_CLK, output wire UART_TX, output wire LED0_N, output wire LED1_N, output wire LED2_N, output wire LED3_N);
wire [4:0] tx, p_n, f_n, d_n;
board_top_relay_chain #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t0 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[0]), .LED0_N(), .LED1_N(p_n[0]), .LED2_N(f_n[0]), .LED3_N(d_n[0]));
board_top_relay_chain_stalled #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t1 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[1]), .LED0_N(), .LED1_N(p_n[1]), .LED2_N(f_n[1]), .LED3_N(d_n[1]));
board_top_adder_stream #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t2 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[2]), .LED0_N(), .LED1_N(p_n[2]), .LED2_N(f_n[2]), .LED3_N(d_n[2]));
board_top_adder_stalled #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t3 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[3]), .LED0_N(), .LED1_N(p_n[3]), .LED2_N(f_n[3]), .LED3_N(d_n[3]));
board_top_adder_constant #(.CPB(CPB), .SETTLE(SETTLE), .TIMEOUT(TIMEOUT)) t4 (.BOARD_CLK(BOARD_CLK), .UART_TX(tx[4]), .LED0_N(), .LED1_N(p_n[4]), .LED2_N(f_n[4]), .LED3_N(d_n[4]));
reg [27:0] sel_cnt = 28'd0; always @(posedge BOARD_CLK) sel_cnt <= sel_cnt + 28'd1;
reg [2:0] sel = 3'd0; reg wrap = 1'b0; always @(posedge BOARD_CLK) begin wrap <= sel_cnt[SELBIT]; if (wrap && !sel_cnt[SELBIT]) sel <= (sel == 3'd4) ? 3'd0 : sel + 3'd1; end
assign UART_TX = tx[sel];
wire all_done = (d_n == 5'd0); wire any_fail = (f_n != {5{1'b1}}); wire all_pass = (p_n == 5'd0);
reg [23:0] hb = 24'd0; always @(posedge BOARD_CLK) hb <= hb + 24'd1;
assign LED0_N = ~hb[23]; assign LED1_N = ~(all_done && all_pass && !any_fail); assign LED2_N = ~any_fail; assign LED3_N = ~all_done;
endmodule
