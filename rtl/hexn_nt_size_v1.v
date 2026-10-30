// hexn_nt_size_v1.v -- SIZING ONLY (30 Oct 2026): a combinational nearest-template classifier (Hamming distance to K stored templates, unique minimum wins), used to compare logic size with the counted detector bank. Not a design for use; templates are inputs (storage excluded). Synthesis: yosys read_verilog; chparam -set K k -set NB n nt; synth_gowin -top nt; stat
module nt #(parameter K=8, parameter NB=18) (input wire [NB-1:0] x, input wire [K*NB-1:0] tpl, output reg [$clog2(K)-1:0] win, output reg valid);
  localparam DW = $clog2(NB+1);
  reg [DW-1:0] d [0:K-1]; reg [DW-1:0] mn; integer k, j, c;
  always @* begin
    for (k=0;k<K;k=k+1) begin d[k]=0; for (j=0;j<NB;j=j+1) d[k]=d[k]+(x[j]^tpl[k*NB+j]); end
    mn=d[0]; for (k=1;k<K;k=k+1) if (d[k]<mn) mn=d[k];
    c=0; win=0; for (k=0;k<K;k=k+1) if (d[k]==mn) begin c=c+1; win=k; end
    valid=(c==1);
  end
endmodule
