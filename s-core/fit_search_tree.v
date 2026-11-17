// fit_search_tree.v - the placement search of sc_sys_v14: same answer as the serial loop of v13 (proven by tb_fit_equiv.v), found as a tree.
// The serial loop walked the S positions in order, each step comparing with the best so far, so its depth grew with S (S comparators in series, the
// path that limited the clock after the watcher was split, ledger #1342).  Here every position is judged on its own (valid, size of the smallest free
// aligned block that holds it - exactly the v13 rules), then the positions are combined in pairs, pairs of pairs, and so on: log2(S) steps.
// Rule kept: the first valid position wins; with BESTFIT a later position wins only if its size is STRICTLY smaller, so the answer is the
// smallest size, lowest position among equals.  In the tree the right-hand (higher) side replaces the left-hand side only under the same rule.
module fit_search_tree #(parameter S = 4, parameter BESTFIT = 1) (
    input  wire [63:0] slice_busy,
    input  wire [5:0]  cur_w,
    output reg         fit_found,
    output reg  [5:0]  fit_base);
    wire [63:0] cur_gm = (64'd1 << cur_w) - 64'd1;
    function [63:0] gmask(input [6:0] w);
        gmask = (64'd1 << w) - 64'd1;
    endfunction
    reg        tv [0:63];
    reg [6:0]  ts [0:63];
    reg [5:0]  ti [0:63];
    reg [6:0]  bsz, blk;
    reg [5:0]  bbase;
    integer    bi, kk, st, j;
    always @* begin
        // step 1: judge every position on its own
        for (bi = 0; bi < 64; bi = bi + 1) begin
            tv[bi] = 1'b0; ts[bi] = 7'd127; ti[bi] = bi[5:0];
            bsz = 7'd0; blk = 7'd0; bbase = 6'd0;
            if (bi < S) begin
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
                    tv[bi] = 1'b1; ts[bi] = bsz;
                end
            end
        end
        // step 2: combine in pairs (left = lower positions), then pairs of pairs
        for (st = 1; st < S; st = st * 2)
            for (j = 0; j + st < 64; j = j + 2 * st)
                if (tv[j + st] && (!tv[j] || (BESTFIT && ts[j + st] < ts[j]))) begin
                    tv[j] = 1'b1; ts[j] = ts[j + st]; ti[j] = ti[j + st];
                end
        fit_found = tv[0];
        fit_base  = tv[0] ? ti[0] : 6'd0;
    end
endmodule
