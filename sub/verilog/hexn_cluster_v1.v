`default_nettype none
// hexn_cluster_v1 -- MEASUREMENT PROTOTYPE (2 Nov 2026, Alan 06:19: 'a central block with the program in it, the cells immediately around it use that program ... the edge cells are just dumb units, slaves to the central common program unit').
// One CENTRE holds the table (128 bits, shift-loaded in flip-flops, changed on the fly); six SLAVES around it each have only a registered output and a 128:1 selection into the SHARED table. Each slave's address: its own previous output, its two ring neighbours (left, right) and four outside faces.
// All six slaves apply the SAME function to their OWN inputs. Counts only; no routing between clusters, no shell.
module hexn_cluster_v1 (input wire clk, input wire cfg_en, input wire cfg_in, output wire cfg_out, input wire [23:0] ext, output wire [5:0] q);
    reg [127:0] tbl = 128'd0; assign cfg_out = tbl[127];
    always @(posedge clk) if (cfg_en) tbl <= {tbl[126:0], cfg_in};
    genvar i;
    generate for (i = 0; i < 6; i = i + 1) begin : S
        reg o = 1'b0; assign q[i] = o;
        wire [6:0] a = {o, q[(i + 5) % 6], q[(i + 1) % 6], ext[4*i +: 4]};
        always @(posedge clk) o <= tbl[a];
    end endgenerate
endmodule

module hexn_cluster_line #(parameter N = 4) (input wire clk, input wire cfg_en, input wire cfg_in, input wire [N*24-1:0] ext, output wire [N*6-1:0] q, output wire cfg_out);
    wire [N:0] cc; assign cc[0] = cfg_in; assign cfg_out = cc[N];
    genvar k; generate for (k = 0; k < N; k = k + 1) begin : K
        hexn_cluster_v1 U (.clk(clk), .cfg_en(cfg_en), .cfg_in(cc[k]), .cfg_out(cc[k+1]), .ext(ext[24*k +: 24]), .q(q[6*k +: 6]));
    end endgenerate
endmodule
