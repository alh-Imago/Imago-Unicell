`timescale 1ns/1ps
module tb_router_cell_v4sa;
    reg clk = 0;
    reg rst = 1;
    reg freeze_in = 0;
    reg cfg_valid = 0;
    reg [31:0] cfg_data = 0;
    reg [31:0] data_in = 0;
    reg valid_in = 0;
    reg ack_in_a = 0, ack_in_b = 0;
    wire ack_out;
    wire [31:0] data_out_a, data_out_b;
    wire valid_out_a, valid_out_b;

    always #5 clk = ~clk;

    router_cell_v4sa dut (
        .clk(clk), .rst(rst), .freeze_in(freeze_in),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in(data_in), .valid_in(valid_in), .ack_out(ack_out),
        .data_out_a(data_out_a), .valid_out_a(valid_out_a), .ack_in_a(ack_in_a),
        .data_out_b(data_out_b), .valid_out_b(valid_out_b), .ack_in_b(ack_in_b)
    );

    integer errors = 0;
    task check_cond(input cond, input [255:0] label);
        begin
            if (!cond) begin $display("FAIL: %0s", label); errors = errors + 1; end
            else $display("PASS: %0s", label);
        end
    endtask

    task cfg(input [31:0] word);
        begin
            cfg_data = word; cfg_valid = 1;
            @(posedge clk); #1;   // settle before clearing -- #906/#911/#912
            cfg_valid = 0;
        end
    endtask

    task fire_send(input [31:0] val);
        begin
            data_in = val; valid_in = 1;
            @(posedge clk); #1;
            valid_in = 0;
            while (ack_out !== 1'b1) begin
                @(posedge clk);
                #1;
            end
        end
    endtask

    initial begin
        rst = 1; @(posedge clk); @(posedge clk); rst = 0; @(posedge clk);

        // === both outputs enabled, both acking promptly ===
        cfg(32'b11);
        ack_in_a = 1; ack_in_b = 1;
        fire_send(32'hCAFEF00D);
        check_cond(data_out_a === 32'hCAFEF00D && data_out_b === 32'hCAFEF00D,
            "both outputs carry the same data");

        // === real differential backpressure: A acks immediately, B stalls --
        // the router must wait for BOTH, not accept new input just because
        // one of them is ready ===
        data_in = 32'h11223344; valid_in = 1;
        @(posedge clk); #1; valid_in = 0;
        check_cond(valid_out_a === 1'b1 && valid_out_b === 1'b1, "both offers presented");
        ack_in_a = 1; ack_in_b = 0;   // A ready, B not
        @(posedge clk); #1;
        check_cond(valid_out_a === 1'b0, "A's offer cleared once acked");
        check_cond(valid_out_b === 1'b1, "B's offer still held -- B has not acked yet");
        check_cond(ack_out === 1'b0, "ack_out correctly LOW -- waiting on B, even though A already acked");
        @(posedge clk); @(posedge clk); #1;
        check_cond(data_out_b === 32'h11223344 && valid_out_b === 1'b1,
            "B's offer still correctly held across multiple cycles while only B is slow");
        ack_in_b = 1;
        @(posedge clk); #1;
        check_cond(valid_out_b === 1'b0 && ack_out === 1'b1, "once B finally acks, both clear and the router is ready again");

        // === only A enabled: B's ack is irrelevant, never blocks anything ===
        cfg(32'b01);
        ack_in_a = 1; ack_in_b = 0;   // B's ack deliberately never arrives
        fire_send(32'hAAAA5555);     // fire_send itself waits for ack_out -- if B wrongly
                                       // mattered, this would hang forever
        check_cond(data_out_a === 32'hAAAA5555, "only-A-enabled: A receives the data");
        check_cond(valid_out_b === 1'b0, "only-A-enabled: B never offers anything (disabled)");

        // === freeze: a real, true pause ===
        cfg(32'b11);
        ack_in_a = 1; ack_in_b = 1;
        fire_send(32'd7);
        freeze_in = 1;
        data_in = 32'd999; valid_in = 1; ack_in_a = 1; ack_in_b = 1;
        @(posedge clk); @(posedge clk); #1;
        check_cond(valid_out_a === 1'b0 && valid_out_b === 1'b0,
            "frozen: completely unaffected by data_in/valid_in/acks toggling while frozen");
        freeze_in = 0;

        if (errors == 0) $display("ALL PASS");
        else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
