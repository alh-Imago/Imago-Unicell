// sc_top_sdt.v - Tang Nano 20K: the in-package SDRAM with a UART-driven test (stage 1 of the "far RAM" work).  27 MHz, UART via the BL616.
//   led_n[0] heartbeat   led_n[1] SDRAM initialised   led_n[2] UART rx   led_n[3] UART tx   led_n[4] a test is running   led_n[5] last test finished with no errors
module sc_top_sdt #(parameter BAUD_DIV = 234, parameter INIT_CLKS = 5400) (
    input  wire        clk,
    input  wire        uart_rx,
    output wire        uart_tx,
    output wire [5:0]  led_n,
    output wire        O_sdram_clk, O_sdram_cke, O_sdram_cs_n, O_sdram_ras_n, O_sdram_cas_n, O_sdram_wen_n,
    output wire [3:0]  O_sdram_dqm,
    output wire [10:0] O_sdram_addr,
    output wire [1:0]  O_sdram_ba,
    inout  wire [31:0] IO_sdram_dq
);
    reg [7:0] por = 8'd0;
    wire rst = (por != 8'hFF);
    always @(posedge clk) if (por != 8'hFF) por <= por + 1'b1;

    wire [1:0] cfg_cl, cfg_dly; wire cfg_inv, reinit, init_done, busy;
    wire h_v, h_we; wire [20:0] h_a; wire [31:0] h_wd;
    wire t_start, t_run, t_done; wire [1:0] t_mode; wire [4:0] t_lg; wire [20:0] t_base; wire [21:0] t_count; wire [31:0] t_seed;
    wire [31:0] t_err, t_fa, t_fe, t_fg, t_wc, t_rc;
    wire tq_v, tq_we; wire [20:0] tq_a; wire [31:0] tq_wd;
    wire req_rdy, ack_v; wire [31:0] ack_d;
    wire act_rx, act_tx;

    wire        req_v  = t_run ? tq_v  : h_v;                 // while a test runs it owns the controller
    wire        req_we = t_run ? tq_we : h_we;
    wire [20:0] req_a  = t_run ? tq_a  : h_a;
    wire [31:0] req_wd = t_run ? tq_wd : h_wd;
    wire        h_acc  = h_v && req_rdy && !t_run;

    sdram_ctl #(.INIT_CLKS(INIT_CLKS)) ctl (
        .clk(clk), .rst(rst), .cfg_cl(cfg_cl), .cfg_dly(cfg_dly), .cfg_inv(cfg_inv), .reinit(reinit),
        .req_v(req_v), .req_we(req_we), .req_a(req_a), .req_wd(req_wd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d),
        .init_done(init_done), .busy(busy),
        .O_sdram_clk(O_sdram_clk), .O_sdram_cke(O_sdram_cke), .O_sdram_cs_n(O_sdram_cs_n), .O_sdram_ras_n(O_sdram_ras_n), .O_sdram_cas_n(O_sdram_cas_n), .O_sdram_wen_n(O_sdram_wen_n),
        .O_sdram_dqm(O_sdram_dqm), .O_sdram_addr(O_sdram_addr), .O_sdram_ba(O_sdram_ba), .IO_sdram_dq(IO_sdram_dq));

    sdt_selftest st (
        .clk(clk), .rst(rst), .start(t_start), .mode(t_mode), .lg(t_lg), .base(t_base), .count(t_count), .seed(t_seed),
        .run(t_run), .done(t_done), .err_cnt(t_err), .first_a(t_fa), .first_exp(t_fe), .first_got(t_fg), .wcyc(t_wc), .rcyc(t_rc),
        .req_v(tq_v), .req_we(tq_we), .req_a(tq_a), .req_wd(tq_wd), .req_rdy(req_rdy), .ack_v(ack_v), .ack_d(ack_d));

    sdt_bridge #(.DIV(BAUD_DIV)) br (
        .clk(clk), .rx(uart_rx), .tx(uart_tx), .cfg_cl(cfg_cl), .cfg_dly(cfg_dly), .cfg_inv(cfg_inv), .reinit(reinit), .init_done(init_done),
        .h_v(h_v), .h_we(h_we), .h_a(h_a), .h_wd(h_wd), .h_acc(h_acc), .ack_v(ack_v), .ack_d(ack_d),
        .t_start(t_start), .t_mode(t_mode), .t_lg(t_lg), .t_base(t_base), .t_count(t_count), .t_seed(t_seed),
        .t_run(t_run), .t_done(t_done), .t_err(t_err), .t_fa(t_fa), .t_fe(t_fe), .t_fg(t_fg), .t_wc(t_wc), .t_rc(t_rc),
        .act_rx(act_rx), .act_tx(act_tx));

    reg [24:0] hb = 0; always @(posedge clk) hb <= hb + 1'b1;
    assign led_n = ~{t_done && (t_err == 32'd0), t_run, act_tx, act_rx, init_done, hb[24]};
endmodule
