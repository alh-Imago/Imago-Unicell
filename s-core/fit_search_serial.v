// fit_search_serial.v - the v13 placement search, copied unchanged from sc_sys_v13.v into a module of its own, ONLY so that fit_search_tree can be
// proven identical to it (tb_fit_equiv.v).  Not used by any design.
module fit_search_serial #(parameter S = 4, parameter BESTFIT = 1) (
    input  wire [63:0] slice_busy,
    input  wire [5:0]  cur_w,
    output wire        fit_found_o,
    output wire [5:0]  fit_base_o);
    wire [63:0] cur_gm = (64'd1 << cur_w) - 64'd1;
    function [63:0] gmask(input [6:0] w);
        gmask = (64'd1 << w) - 64'd1;
    endfunction
    reg        fit_found;
    reg [5:0]  fit_base;
    reg [6:0]  best_sz, bsz, blk;
    reg [5:0]  bbase;
    integer    bi, kk;
    always @* begin
        fit_found = 1'b0; fit_base = 6'd0; best_sz = 7'd127; bsz = 7'd0; blk = 7'd0; bbase = 6'd0;
        for (bi = 0; bi < S; bi = bi + 1) begin
            if (((bi & (cur_w - 1)) == 0) && (bi + cur_w <= S) && (((slice_busy >> bi) & cur_gm) == 64'd0)) begin
                bsz = {1'b0, cur_w};
                if (BESTFIT) begin
                    for (kk = 0; kk <= 5; kk = kk + 1) begin
                        blk = 7'd1 << kk;
                        if (blk >= cur_w) begin
                            bbase = bi & ~(blk - 1);
                            if ((bbase + blk <= S) && (((slice_busy >> bbase) & gmask(blk)) == 64'd0)) bsz = blk;
                        end
                    end
                end
                if (!fit_found || (BESTFIT && bsz < best_sz)) begin
                    fit_found = 1'b1; fit_base = bi[5:0]; best_sz = bsz;
                end
            end
        end
    end
    assign fit_found_o = fit_found;
    assign fit_base_o  = fit_base;
endmodule
