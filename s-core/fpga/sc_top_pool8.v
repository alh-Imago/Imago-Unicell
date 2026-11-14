// sc_top_pool8.v - sc_top_pool6 with hold/go (sc_sys_v8 + host_bridge_v2). LED 5 (heartbeat) is unchanged.
// sc_top_tang.v - S-Core single-set build for the Sipeed Tang Nano 20K.
// 27 MHz board clock, UART to the PC through the on-board BL616, six LEDs (active low).
//   led_n[0] heartbeat   led_n[1] some core is running   led_n[2] UART rx activity
//   led_n[3] UART tx activity   led_n[4] launch error (should never light)   led_n[5] at least one task finished
// Power-on reset only (the S1/S2 buttons are the chip's MODE pins: not used).
module sc_top_pool8 #(
    parameter S = 1, parameter QD = 16, parameter IMEM_WORDS = 128, parameter DMW = 16,
    parameter PROF = 64, parameter BAUD_DIV = 234, parameter LONGEST = 1, parameter FINE = 0
) (
    input  wire       clk,
    input  wire       uart_rx,
    output wire       uart_tx,
    output wire [5:0] led_n
);
    reg [7:0] por = 8'd0;
    wire por_done = (por == 8'hFF);
    always @(posedge clk) if (!por_done) por <= por + 1'b1;
    wire soft_rst, hold;
    wire rst = !por_done | soft_rst;

    wire        h_push, h_crit, imem_we, act_rx, act_tx, q_trap;
    wire [15:0] h_tid, h_code, imem_wa, q_tid;
    wire [2:0]  h_lw;
    wire [5:0]  h_prog, q_slot;
    wire [31:0] imem_wd, q_start, q_end, q_a0, q_arr, o_cyc, o_done, o_lerr, o_disp;
    wire [1:0]  q_state;
    wire [24:0] q_pred;
    wire [63:0] o_busy, o_blocked, o_tail, o_search;
    wire [S-1:0] o_busy_l;

    host_bridge_v2 #(.DIV(BAUD_DIV), .S(S), .IMEM_WORDS(IMEM_WORDS), .DMW(DMW)) br (
        .clk(clk), .rx(uart_rx), .tx(uart_tx),
        .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_lw(h_lw), .h_crit(h_crit), .h_prog(h_prog),
        .imem_we(imem_we), .imem_wa(imem_wa), .imem_wd(imem_wd), .q_tid(q_tid), .soft_rst(soft_rst), .hold(hold),
        .q_start(q_start), .q_end(q_end), .q_a0(q_a0), .q_arr(q_arr), .q_trap(q_trap), .q_state(q_state),
        .q_slot(q_slot), .q_pred(q_pred),
        .o_cyc(o_cyc), .o_done(o_done), .o_lerr(o_lerr), .o_disp(o_disp),
        .o_busy(o_busy), .o_blocked(o_blocked), .o_tail(o_tail), .o_search(o_search), .o_busy_l(o_busy_l),
        .act_rx(act_rx), .act_tx(act_tx));

    sc_sys_v8 #(.S(S), .QD(QD), .IMEM_WORDS(IMEM_WORDS), .DMW(DMW), .PROF(PROF), .EVB(3),
                .PRIO(1), .BESTFIT(1), .LONGEST(LONGEST), .FINE(FINE)) sys (
        .clk(clk), .rst(rst), .hold(hold),
        .h_push(h_push), .h_tid(h_tid), .h_code(h_code), .h_lw(h_lw), .h_crit(h_crit), .h_prog(h_prog),
        .imem_we(imem_we), .imem_wa(imem_wa), .imem_wd(imem_wd),
        .q_tid(q_tid), .q_start(q_start), .q_end(q_end), .q_a0(q_a0), .q_arr(q_arr), .q_trap(q_trap),
        .q_state(q_state), .q_slot(q_slot), .q_pred(q_pred),
        .o_cyc(o_cyc), .o_done(o_done), .o_lerr(o_lerr), .o_disp(o_disp),
        .o_busy(o_busy), .o_blocked(o_blocked), .o_tail(o_tail), .o_search(o_search), .o_busy_l(o_busy_l),
        .ev_pl_we(1'b0), .ev_pl_id(8'd0), .ev_pl_data(32'd0), .ev_set(1'b0), .ev_set_id(8'd0));

    reg [24:0] hb = 0;
    always @(posedge clk) hb <= hb + 1'b1;
    assign led_n = ~{|o_done, |o_lerr, act_tx, act_rx, |o_busy_l, hb[24]};
endmodule
