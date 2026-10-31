// hw262_shield_v1.v -- drives the HW-262 multi-function shield's 4-digit display (two 74HC595 shift registers) and its buzzer, straight from the FPGA.
// The display shows `value` as FOUR HEX DIGITS (left to right = bits 15..12, 11..8, 7..4, 3..0) while `enable` is 1, and is blank otherwise. The four digits are scanned one at a time,
// one every ~1 ms. Protocol (as the shield's own library uses it): latch LOW, then 16 bits MSB first on data with a rising clock for each -- first the SEGMENT byte (a 0 bit lights a segment),
// then the DIGIT byte (one hot, 0001 = leftmost digit) -- then latch HIGH. The buzzer line is driven low (BUZZ_ACTIVE_LOW=1, how the usual shield wires it) while `buzz` is 1.
// Segment code (active low): bit0 a, bit1 b, bit2 c, bit3 d, bit4 e, bit5 f, bit6 g, bit7 dp.  NOT yet tried on a real shield: if the idle buzzer sounds, set BUZZ_ACTIVE_LOW to 0.
`default_nettype none
module hw262_shield_v1 #(
    parameter BUZZ_ACTIVE_LOW = 1,
    parameter HALF = 14,                 // clock cycles per half shift-clock period (27 MHz / 28 = about 1 MHz)
    parameter DWELL = 26000              // idle cycles after each digit write (about 1 ms)
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        enable,
    input  wire [15:0] value,
    input  wire        buzz,
    output reg         latch,
    output reg         sclk,
    output reg         sdata,
    output wire        buzzer
);
    assign buzzer = (buzz & enable) ? ~BUZZ_ACTIVE_LOW[0] : BUZZ_ACTIVE_LOW[0];

    function [7:0] seg(input [3:0] n);
        case (n)
            4'h0: seg = 8'hC0; 4'h1: seg = 8'hF9; 4'h2: seg = 8'hA4; 4'h3: seg = 8'hB0;
            4'h4: seg = 8'h99; 4'h5: seg = 8'h92; 4'h6: seg = 8'h82; 4'h7: seg = 8'hF8;
            4'h8: seg = 8'h80; 4'h9: seg = 8'h90; 4'hA: seg = 8'h88; 4'hB: seg = 8'h83;
            4'hC: seg = 8'hC6; 4'hD: seg = 8'hA1; 4'hE: seg = 8'h86; default: seg = 8'h8E;
        endcase
    endfunction

    reg [1:0]  dig;
    reg [15:0] frame;
    reg [4:0]  nbit;
    reg [15:0] cnt;
    reg [1:0]  st;                       // 0 idle/dwell, 1 shifting (clock low), 2 shifting (clock high), 3 latch high
    wire [3:0] nib = (dig == 2'd0) ? value[15:12] : (dig == 2'd1) ? value[11:8] : (dig == 2'd2) ? value[7:4] : value[3:0];
    wire [7:0] segbyte = enable ? seg(nib) : 8'hFF;

    always @(posedge clk) begin
        if (rst) begin latch <= 1'b1; sclk <= 1'b0; sdata <= 1'b1; st <= 0; cnt <= 0; dig <= 0; nbit <= 0; frame <= 0; end
        else case (st)
            2'd0: begin
                if (cnt >= DWELL) begin
                    cnt <= 0; frame <= {segbyte, 8'h01 << dig}; nbit <= 0; latch <= 1'b0; sclk <= 1'b0; st <= 2'd1;
                end else cnt <= cnt + 1'b1;
            end
            2'd1: begin                                     // put the next bit on the data line, then raise the clock after half a period
                sdata <= frame[15];
                if (cnt >= HALF) begin cnt <= 0; sclk <= 1'b1; st <= 2'd2; end else cnt <= cnt + 1'b1;
            end
            2'd2: begin
                if (cnt >= HALF) begin
                    cnt <= 0; sclk <= 1'b0; frame <= {frame[14:0], 1'b0}; nbit <= nbit + 1'b1;
                    if (nbit == 5'd15) begin st <= 2'd3; end else st <= 2'd1;
                end else cnt <= cnt + 1'b1;
            end
            2'd3: begin
                if (cnt >= HALF) begin cnt <= 0; latch <= 1'b1; dig <= dig + 1'b1; st <= 2'd0; end else cnt <= cnt + 1'b1;
            end
        endcase
    end
endmodule
`default_nettype wire
