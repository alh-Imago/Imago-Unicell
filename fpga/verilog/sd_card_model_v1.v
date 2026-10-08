// sd_card_model_v1.v -- SIMULATION ONLY: a behavioural SD card in SPI mode (mode 0) for testing sd_spi_v1. Not synthesisable.
// Understands CMD0, CMD8, CMD55, ACMD41 (ready after READY_AFTER tries), CMD58 (CCS = SDHC), CMD17 (read block), CMD24 (write block). Storage: mem[block*512 + byte].
`timescale 1ns/1ps
module sd_card_model_v1 #(parameter SDHC = 1, parameter BLOCKS = 8, parameter READY_AFTER = 3, parameter V1 = 0) (
    input  wire sclk, input wire mosi, input wire cs_n, output wire miso
);
    reg [7:0] mem [0:BLOCKS*512-1];
    reg [7:0] txq [0:600];
    integer txn = 0, txp = 0;
    reg [7:0] txb = 8'hFF;
    reg [7:0] rxs;
    integer bits = 0;
    reg [7:0] cmd [0:5];
    integer cn = 0;
    integer state = 0;           // 0 idle/command, 1 wait write token, 2 write data, 3 busy
    integer wcount = 0, wblock = 0;
    integer acmd_tries = 0;
    reg app = 0;
    reg load_pending = 0;
    assign miso = cs_n ? 1'b1 : txb[7];
    integer i;
    task push(input [7:0] b); begin txq[txn] = b; txn = txn + 1; end endtask
    task command(input [5:0] idx, input [31:0] arg);
        integer blk;
        begin
            txn = 0; txp = 0;
            push(8'hFF);                                             // one byte of delay before the response
            case (idx)
                0: begin push(8'h01); app = 0; end
                8: begin if (V1) push(8'h05); else begin push(8'h01); push(8'h00); push(8'h00); push(8'h01); push(8'hAA); end end   // an SD 1.x card: illegal command
                16: push(8'h00);
                55: begin push(8'h01); app = 1; end
                41: begin
                        if (acmd_tries >= READY_AFTER) push(8'h00); else push(8'h01);
                        acmd_tries = acmd_tries + 1; app = 0;
                    end
                58: begin push(8'h00); push(SDHC ? 8'hC0 : 8'h80); push(8'hFF); push(8'h80); push(8'h00); end
                17: begin
                        blk = SDHC ? arg : (arg >> 9);
                        push(8'h00); push(8'hFF); push(8'hFF); push(8'hFE);
                        for (i = 0; i < 512; i = i + 1) push(mem[blk*512 + i]);
                        push(8'hAA); push(8'hAA);
                    end
                24: begin push(8'h00); wblock = SDHC ? arg : (arg >> 9); state = 1; end
                default: push(8'h04);
            endcase
        end
    endtask
    always @(posedge sclk) if (!cs_n) begin
        rxs = {rxs[6:0], mosi};
        bits = bits + 1;
        if (bits == 8) begin
            bits = 0;
            if (state == 0) begin
                if (cn == 0) begin if (rxs[7:6] == 2'b01) begin cmd[0] = rxs; cn = 1; end end
                else begin cmd[cn] = rxs; cn = cn + 1; if (cn == 6) begin cn = 0; command(cmd[0][5:0], {cmd[1], cmd[2], cmd[3], cmd[4]}); end end
            end else if (state == 1) begin
                if (rxs == 8'hFE) begin state = 2; wcount = 0; end
            end else if (state == 2) begin
                if (wcount < 512) mem[wblock*512 + wcount] = rxs;
                wcount = wcount + 1;
                if (wcount == 514) begin state = 3; txn = 0; txp = 0; push(8'h05); push(8'h00); push(8'h00); push(8'h00); end
            end
            load_pending = 1;                                          // the next byte to send is loaded on the falling edge that ends this byte
        end
    end
    always @(negedge sclk) if (!cs_n) begin
        if (load_pending) begin
            load_pending = 0;
            if (txp < txn) begin txb = txq[txp]; txp = txp + 1; if (txp == txn && state == 3) state = 0; end
            else txb = 8'hFF;
        end else txb = {txb[6:0], 1'b1};
    end
    always @(posedge cs_n) begin bits = 0; cn = 0; txn = 0; txp = 0; txb = 8'hFF; load_pending = 0; if (state == 3 || state == 1) state = 0; end
endmodule
