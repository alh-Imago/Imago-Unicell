module bitwise_subtractor_32bit (
    input  wire [31:0] A,       // Minuend
    input  wire [31:0] B,       // Subtrahend
    output wire [31:0] Diff,    // Difference (A - B)
    output wire        Borrow   // Borrow-out flag (if A < B)
);
    // Single-stage combinational subtraction with borrow detection
    assign {Borrow, Diff} = {1'b0, A} - {1'b0, B};
endmodule
