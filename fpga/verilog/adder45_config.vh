// AUTO-GENERATED config table for the 50-cell packed shift-adder
// (with delay cells added to the G-path at every stage to resolve
// bus contention between the fast local G-computation and the
// cross-cluster P-chain delivery -- see docs/design-notes/
// packed_adder_cluster_mesh.md).

    assign cfg_target[0]      = 16'd0;  // G0
    assign cfg_input_addr[0]  = 16'd0;
    assign cfg_output_addr[0] = 16'd4;
    assign cfg_c1_bus[0]      = {24'h0, 8'd23};
    assign cfg_c1_data[0]     = 32'h00000807;
    assign cfg_c2_bus[0]      = {24'h0, 8'd33};
    assign cfg_c2_data[0]     = 32'h0;
    assign cfg_cluster[0]     = 4'd0;

    assign cfg_target[1]      = 16'd32;  // P0
    assign cfg_input_addr[1]  = 16'd0;
    assign cfg_output_addr[1] = 16'd35;
    assign cfg_c1_bus[1]      = {24'h0, 8'd23};
    assign cfg_c1_data[1]     = 32'h000008bc;
    assign cfg_c2_bus[1]      = {24'h0, 8'd33};
    assign cfg_c2_data[1]     = 32'h0;
    assign cfg_cluster[1]     = 4'd1;

    assign cfg_target[2]      = 16'd1;  // P0_fanout_r1
    assign cfg_input_addr[2]  = 16'd35;
    assign cfg_output_addr[2] = 16'd36;
    assign cfg_c1_bus[2]      = {24'h0, 8'd23};
    assign cfg_c1_data[2]     = 32'h0002082c;
    assign cfg_c2_bus[2]      = {24'h0, 8'd33};
    assign cfg_c2_data[2]     = 32'h0;
    assign cfg_cluster[2]     = 4'd0;

    assign cfg_target[3]      = 16'd2;  // P0_fanout_r2
    assign cfg_input_addr[3]  = 16'd36;
    assign cfg_output_addr[3] = 16'd64;
    assign cfg_c1_bus[3]      = {24'h0, 8'd23};
    assign cfg_c1_data[3]     = 32'h0002082c;
    assign cfg_c2_bus[3]      = {24'h0, 8'd33};
    assign cfg_c2_data[3]     = 32'h0;
    assign cfg_cluster[3]     = 4'd0;

    assign cfg_target[4]      = 16'd3;  // P0_fanout_r3
    assign cfg_input_addr[4]  = 16'd64;
    assign cfg_output_addr[4] = 16'd292;
    assign cfg_c1_bus[4]      = {24'h0, 8'd23};
    assign cfg_c1_data[4]     = 32'h0002082c;
    assign cfg_c2_bus[4]      = {24'h0, 8'd33};
    assign cfg_c2_data[4]     = 32'h0;
    assign cfg_cluster[4]     = 4'd0;

    assign cfg_target[5]      = 16'd4;  // DELAY_G1
    assign cfg_input_addr[5]  = 16'd4;
    assign cfg_output_addr[5] = 16'd34;
    assign cfg_c1_bus[5]      = {24'h0, 8'd23};
    assign cfg_c1_data[5]     = 32'h0002082c;
    assign cfg_c2_bus[5]      = {24'h0, 8'd33};
    assign cfg_c2_data[5]     = 32'h0;
    assign cfg_cluster[5]     = 4'd0;

    assign cfg_target[6]      = 16'd33;  // DELAY_G1_fanout_r1
    assign cfg_input_addr[6]  = 16'd34;
    assign cfg_output_addr[6] = 16'd67;
    assign cfg_c1_bus[6]      = {24'h0, 8'd23};
    assign cfg_c1_data[6]     = 32'h0002082c;
    assign cfg_c2_bus[6]      = {24'h0, 8'd33};
    assign cfg_c2_data[6]     = 32'h0;
    assign cfg_cluster[6]     = 4'd1;

    assign cfg_target[7]      = 16'd34;  // SHL_G1
    assign cfg_input_addr[7]  = 16'd34;
    assign cfg_output_addr[7] = 16'd36;
    assign cfg_c1_bus[7]      = {24'h0, 8'd23};
    assign cfg_c1_data[7]     = 32'h0002082c;
    assign cfg_c2_bus[7]      = {24'h0, 8'd31};
    assign cfg_c2_data[7]     = 32'd1;
    assign cfg_cluster[7]     = 4'd1;

    assign cfg_target[8]      = 16'd35;  // SHL_P1
    assign cfg_input_addr[8]  = 16'd35;
    assign cfg_output_addr[8] = 16'd64;
    assign cfg_c1_bus[8]      = {24'h0, 8'd23};
    assign cfg_c1_data[8]     = 32'h0002082c;
    assign cfg_c2_bus[8]      = {24'h0, 8'd31};
    assign cfg_c2_data[8]     = 32'd1;
    assign cfg_cluster[8]     = 4'd1;

    assign cfg_target[9]      = 16'd36;  // AND_PG1
    assign cfg_input_addr[9]  = 16'd36;
    assign cfg_output_addr[9] = 16'd67;
    assign cfg_c1_bus[9]      = {24'h0, 8'd23};
    assign cfg_c1_data[9]     = 32'h00000807;
    assign cfg_c2_bus[9]      = {24'h0, 8'd33};
    assign cfg_c2_data[9]     = 32'h0;
    assign cfg_cluster[9]     = 4'd1;

    assign cfg_target[10]      = 16'd64;  // AND_P1
    assign cfg_input_addr[10]  = 16'd64;
    assign cfg_output_addr[10] = 16'd98;
    assign cfg_c1_bus[10]      = {24'h0, 8'd23};
    assign cfg_c1_data[10]     = 32'h00000807;
    assign cfg_c2_bus[10]      = {24'h0, 8'd33};
    assign cfg_c2_data[10]     = 32'h0;
    assign cfg_cluster[10]     = 4'd2;

    assign cfg_target[11]      = 16'd65;  // AND_P1_fanout_r1
    assign cfg_input_addr[11]  = 16'd98;
    assign cfg_output_addr[11] = 16'd99;
    assign cfg_c1_bus[11]      = {24'h0, 8'd23};
    assign cfg_c1_data[11]     = 32'h0002082c;
    assign cfg_c2_bus[11]      = {24'h0, 8'd33};
    assign cfg_c2_data[11]     = 32'h0;
    assign cfg_cluster[11]     = 4'd2;

    assign cfg_target[12]      = 16'd66;  // AND_P1_fanout_r2
    assign cfg_input_addr[12]  = 16'd99;
    assign cfg_output_addr[12] = 16'd100;
    assign cfg_c1_bus[12]      = {24'h0, 8'd23};
    assign cfg_c1_data[12]     = 32'h0002082c;
    assign cfg_c2_bus[12]      = {24'h0, 8'd33};
    assign cfg_c2_data[12]     = 32'h0;
    assign cfg_cluster[12]     = 4'd2;

    assign cfg_target[13]      = 16'd67;  // OR_G1
    assign cfg_input_addr[13]  = 16'd67;
    assign cfg_output_addr[13] = 16'd68;
    assign cfg_c1_bus[13]      = {24'h0, 8'd23};
    assign cfg_c1_data[13]     = 32'h00000824;
    assign cfg_c2_bus[13]      = {24'h0, 8'd33};
    assign cfg_c2_data[13]     = 32'h0;
    assign cfg_cluster[13]     = 4'd2;

    assign cfg_target[14]      = 16'd68;  // DELAY_G2
    assign cfg_input_addr[14]  = 16'd68;
    assign cfg_output_addr[14] = 16'd97;
    assign cfg_c1_bus[14]      = {24'h0, 8'd23};
    assign cfg_c1_data[14]     = 32'h0002082c;
    assign cfg_c2_bus[14]      = {24'h0, 8'd33};
    assign cfg_c2_data[14]     = 32'h0;
    assign cfg_cluster[14]     = 4'd2;

    assign cfg_target[15]      = 16'd96;  // DELAY_G2_fanout_r1
    assign cfg_input_addr[15]  = 16'd97;
    assign cfg_output_addr[15] = 16'd130;
    assign cfg_c1_bus[15]      = {24'h0, 8'd23};
    assign cfg_c1_data[15]     = 32'h0002082c;
    assign cfg_c2_bus[15]      = {24'h0, 8'd33};
    assign cfg_c2_data[15]     = 32'h0;
    assign cfg_cluster[15]     = 4'd3;

    assign cfg_target[16]      = 16'd97;  // SHL_G2
    assign cfg_input_addr[16]  = 16'd97;
    assign cfg_output_addr[16] = 16'd99;
    assign cfg_c1_bus[16]      = {24'h0, 8'd23};
    assign cfg_c1_data[16]     = 32'h0002082c;
    assign cfg_c2_bus[16]      = {24'h0, 8'd31};
    assign cfg_c2_data[16]     = 32'd2;
    assign cfg_cluster[16]     = 4'd3;

    assign cfg_target[17]      = 16'd98;  // SHL_P2
    assign cfg_input_addr[17]  = 16'd98;
    assign cfg_output_addr[17] = 16'd100;
    assign cfg_c1_bus[17]      = {24'h0, 8'd23};
    assign cfg_c1_data[17]     = 32'h0002082c;
    assign cfg_c2_bus[17]      = {24'h0, 8'd31};
    assign cfg_c2_data[17]     = 32'd2;
    assign cfg_cluster[17]     = 4'd3;

    assign cfg_target[18]      = 16'd99;  // AND_PG2
    assign cfg_input_addr[18]  = 16'd99;
    assign cfg_output_addr[18] = 16'd130;
    assign cfg_c1_bus[18]      = {24'h0, 8'd23};
    assign cfg_c1_data[18]     = 32'h00000807;
    assign cfg_c2_bus[18]      = {24'h0, 8'd33};
    assign cfg_c2_data[18]     = 32'h0;
    assign cfg_cluster[18]     = 4'd3;

    assign cfg_target[19]      = 16'd100;  // AND_P2
    assign cfg_input_addr[19]  = 16'd100;
    assign cfg_output_addr[19] = 16'd161;
    assign cfg_c1_bus[19]      = {24'h0, 8'd23};
    assign cfg_c1_data[19]     = 32'h00000807;
    assign cfg_c2_bus[19]      = {24'h0, 8'd33};
    assign cfg_c2_data[19]     = 32'h0;
    assign cfg_cluster[19]     = 4'd3;

    assign cfg_target[20]      = 16'd128;  // AND_P2_fanout_r1
    assign cfg_input_addr[20]  = 16'd161;
    assign cfg_output_addr[20] = 16'd162;
    assign cfg_c1_bus[20]      = {24'h0, 8'd23};
    assign cfg_c1_data[20]     = 32'h0002082c;
    assign cfg_c2_bus[20]      = {24'h0, 8'd33};
    assign cfg_c2_data[20]     = 32'h0;
    assign cfg_cluster[20]     = 4'd4;

    assign cfg_target[21]      = 16'd129;  // AND_P2_fanout_r2
    assign cfg_input_addr[21]  = 16'd162;
    assign cfg_output_addr[21] = 16'd163;
    assign cfg_c1_bus[21]      = {24'h0, 8'd23};
    assign cfg_c1_data[21]     = 32'h0002082c;
    assign cfg_c2_bus[21]      = {24'h0, 8'd33};
    assign cfg_c2_data[21]     = 32'h0;
    assign cfg_cluster[21]     = 4'd4;

    assign cfg_target[22]      = 16'd130;  // OR_G2
    assign cfg_input_addr[22]  = 16'd130;
    assign cfg_output_addr[22] = 16'd131;
    assign cfg_c1_bus[22]      = {24'h0, 8'd23};
    assign cfg_c1_data[22]     = 32'h00000824;
    assign cfg_c2_bus[22]      = {24'h0, 8'd33};
    assign cfg_c2_data[22]     = 32'h0;
    assign cfg_cluster[22]     = 4'd4;

    assign cfg_target[23]      = 16'd131;  // DELAY_G3
    assign cfg_input_addr[23]  = 16'd131;
    assign cfg_output_addr[23] = 16'd160;
    assign cfg_c1_bus[23]      = {24'h0, 8'd23};
    assign cfg_c1_data[23]     = 32'h0002082c;
    assign cfg_c2_bus[23]      = {24'h0, 8'd33};
    assign cfg_c2_data[23]     = 32'h0;
    assign cfg_cluster[23]     = 4'd4;

    assign cfg_target[24]      = 16'd132;  // DELAY_G3_fanout_r1
    assign cfg_input_addr[24]  = 16'd160;
    assign cfg_output_addr[24] = 16'd193;
    assign cfg_c1_bus[24]      = {24'h0, 8'd23};
    assign cfg_c1_data[24]     = 32'h0002082c;
    assign cfg_c2_bus[24]      = {24'h0, 8'd33};
    assign cfg_c2_data[24]     = 32'h0;
    assign cfg_cluster[24]     = 4'd4;

    assign cfg_target[25]      = 16'd160;  // SHL_G3
    assign cfg_input_addr[25]  = 16'd160;
    assign cfg_output_addr[25] = 16'd162;
    assign cfg_c1_bus[25]      = {24'h0, 8'd23};
    assign cfg_c1_data[25]     = 32'h0002082c;
    assign cfg_c2_bus[25]      = {24'h0, 8'd31};
    assign cfg_c2_data[25]     = 32'd4;
    assign cfg_cluster[25]     = 4'd5;

    assign cfg_target[26]      = 16'd161;  // SHL_P3
    assign cfg_input_addr[26]  = 16'd161;
    assign cfg_output_addr[26] = 16'd163;
    assign cfg_c1_bus[26]      = {24'h0, 8'd23};
    assign cfg_c1_data[26]     = 32'h0002082c;
    assign cfg_c2_bus[26]      = {24'h0, 8'd31};
    assign cfg_c2_data[26]     = 32'd4;
    assign cfg_cluster[26]     = 4'd5;

    assign cfg_target[27]      = 16'd162;  // AND_PG3
    assign cfg_input_addr[27]  = 16'd162;
    assign cfg_output_addr[27] = 16'd193;
    assign cfg_c1_bus[27]      = {24'h0, 8'd23};
    assign cfg_c1_data[27]     = 32'h00000807;
    assign cfg_c2_bus[27]      = {24'h0, 8'd33};
    assign cfg_c2_data[27]     = 32'h0;
    assign cfg_cluster[27]     = 4'd5;

    assign cfg_target[28]      = 16'd163;  // AND_P3
    assign cfg_input_addr[28]  = 16'd163;
    assign cfg_output_addr[28] = 16'd224;
    assign cfg_c1_bus[28]      = {24'h0, 8'd23};
    assign cfg_c1_data[28]     = 32'h00000807;
    assign cfg_c2_bus[28]      = {24'h0, 8'd33};
    assign cfg_c2_data[28]     = 32'h0;
    assign cfg_cluster[28]     = 4'd5;

    assign cfg_target[29]      = 16'd164;  // AND_P3_fanout_r1
    assign cfg_input_addr[29]  = 16'd224;
    assign cfg_output_addr[29] = 16'd225;
    assign cfg_c1_bus[29]      = {24'h0, 8'd23};
    assign cfg_c1_data[29]     = 32'h0002082c;
    assign cfg_c2_bus[29]      = {24'h0, 8'd33};
    assign cfg_c2_data[29]     = 32'h0;
    assign cfg_cluster[29]     = 4'd5;

    assign cfg_target[30]      = 16'd192;  // AND_P3_fanout_r2
    assign cfg_input_addr[30]  = 16'd225;
    assign cfg_output_addr[30] = 16'd226;
    assign cfg_c1_bus[30]      = {24'h0, 8'd23};
    assign cfg_c1_data[30]     = 32'h0002082c;
    assign cfg_c2_bus[30]      = {24'h0, 8'd33};
    assign cfg_c2_data[30]     = 32'h0;
    assign cfg_cluster[30]     = 4'd6;

    assign cfg_target[31]      = 16'd193;  // OR_G3
    assign cfg_input_addr[31]  = 16'd193;
    assign cfg_output_addr[31] = 16'd194;
    assign cfg_c1_bus[31]      = {24'h0, 8'd23};
    assign cfg_c1_data[31]     = 32'h00000824;
    assign cfg_c2_bus[31]      = {24'h0, 8'd33};
    assign cfg_c2_data[31]     = 32'h0;
    assign cfg_cluster[31]     = 4'd6;

    assign cfg_target[32]      = 16'd194;  // DELAY_G4
    assign cfg_input_addr[32]  = 16'd194;
    assign cfg_output_addr[32] = 16'd196;
    assign cfg_c1_bus[32]      = {24'h0, 8'd23};
    assign cfg_c1_data[32]     = 32'h0002082c;
    assign cfg_c2_bus[32]      = {24'h0, 8'd33};
    assign cfg_c2_data[32]     = 32'h0;
    assign cfg_cluster[32]     = 4'd6;

    assign cfg_target[33]      = 16'd195;  // DELAY_G4_fanout_r1
    assign cfg_input_addr[33]  = 16'd196;
    assign cfg_output_addr[33] = 16'd256;
    assign cfg_c1_bus[33]      = {24'h0, 8'd23};
    assign cfg_c1_data[33]     = 32'h0002082c;
    assign cfg_c2_bus[33]      = {24'h0, 8'd33};
    assign cfg_c2_data[33]     = 32'h0;
    assign cfg_cluster[33]     = 4'd6;

    assign cfg_target[34]      = 16'd196;  // SHL_G4
    assign cfg_input_addr[34]  = 16'd196;
    assign cfg_output_addr[34] = 16'd225;
    assign cfg_c1_bus[34]      = {24'h0, 8'd23};
    assign cfg_c1_data[34]     = 32'h0002082c;
    assign cfg_c2_bus[34]      = {24'h0, 8'd31};
    assign cfg_c2_data[34]     = 32'd8;
    assign cfg_cluster[34]     = 4'd6;

    assign cfg_target[35]      = 16'd224;  // SHL_P4
    assign cfg_input_addr[35]  = 16'd224;
    assign cfg_output_addr[35] = 16'd226;
    assign cfg_c1_bus[35]      = {24'h0, 8'd23};
    assign cfg_c1_data[35]     = 32'h0002082c;
    assign cfg_c2_bus[35]      = {24'h0, 8'd31};
    assign cfg_c2_data[35]     = 32'd8;
    assign cfg_cluster[35]     = 4'd7;

    assign cfg_target[36]      = 16'd225;  // AND_PG4
    assign cfg_input_addr[36]  = 16'd225;
    assign cfg_output_addr[36] = 16'd256;
    assign cfg_c1_bus[36]      = {24'h0, 8'd23};
    assign cfg_c1_data[36]     = 32'h00000807;
    assign cfg_c2_bus[36]      = {24'h0, 8'd33};
    assign cfg_c2_data[36]     = 32'h0;
    assign cfg_cluster[36]     = 4'd7;

    assign cfg_target[37]      = 16'd226;  // AND_P4
    assign cfg_input_addr[37]  = 16'd226;
    assign cfg_output_addr[37] = 16'd260;
    assign cfg_c1_bus[37]      = {24'h0, 8'd23};
    assign cfg_c1_data[37]     = 32'h00000807;
    assign cfg_c2_bus[37]      = {24'h0, 8'd33};
    assign cfg_c2_data[37]     = 32'h0;
    assign cfg_cluster[37]     = 4'd7;

    assign cfg_target[38]      = 16'd227;  // AND_P4_fanout_r1
    assign cfg_input_addr[38]  = 16'd260;
    assign cfg_output_addr[38] = 16'd288;
    assign cfg_c1_bus[38]      = {24'h0, 8'd23};
    assign cfg_c1_data[38]     = 32'h0002082c;
    assign cfg_c2_bus[38]      = {24'h0, 8'd33};
    assign cfg_c2_data[38]     = 32'h0;
    assign cfg_cluster[38]     = 4'd7;

    assign cfg_target[39]      = 16'd228;  // AND_P4_fanout_r2
    assign cfg_input_addr[39]  = 16'd288;
    assign cfg_output_addr[39] = 16'd289;
    assign cfg_c1_bus[39]      = {24'h0, 8'd23};
    assign cfg_c1_data[39]     = 32'h0002082c;
    assign cfg_c2_bus[39]      = {24'h0, 8'd33};
    assign cfg_c2_data[39]     = 32'h0;
    assign cfg_cluster[39]     = 4'd7;

    assign cfg_target[40]      = 16'd256;  // OR_G4
    assign cfg_input_addr[40]  = 16'd256;
    assign cfg_output_addr[40] = 16'd257;
    assign cfg_c1_bus[40]      = {24'h0, 8'd23};
    assign cfg_c1_data[40]     = 32'h00000824;
    assign cfg_c2_bus[40]      = {24'h0, 8'd33};
    assign cfg_c2_data[40]     = 32'h0;
    assign cfg_cluster[40]     = 4'd8;

    assign cfg_target[41]      = 16'd257;  // DELAY_G5
    assign cfg_input_addr[41]  = 16'd257;
    assign cfg_output_addr[41] = 16'd259;
    assign cfg_c1_bus[41]      = {24'h0, 8'd23};
    assign cfg_c1_data[41]     = 32'h0002082c;
    assign cfg_c2_bus[41]      = {24'h0, 8'd33};
    assign cfg_c2_data[41]     = 32'h0;
    assign cfg_cluster[41]     = 4'd8;

    assign cfg_target[42]      = 16'd258;  // DELAY_G5_fanout_r1
    assign cfg_input_addr[42]  = 16'd259;
    assign cfg_output_addr[42] = 16'd290;
    assign cfg_c1_bus[42]      = {24'h0, 8'd23};
    assign cfg_c1_data[42]     = 32'h0002082c;
    assign cfg_c2_bus[42]      = {24'h0, 8'd33};
    assign cfg_c2_data[42]     = 32'h0;
    assign cfg_cluster[42]     = 4'd8;

    assign cfg_target[43]      = 16'd259;  // SHL_G5
    assign cfg_input_addr[43]  = 16'd259;
    assign cfg_output_addr[43] = 16'd288;
    assign cfg_c1_bus[43]      = {24'h0, 8'd23};
    assign cfg_c1_data[43]     = 32'h0002082c;
    assign cfg_c2_bus[43]      = {24'h0, 8'd31};
    assign cfg_c2_data[43]     = 32'd16;
    assign cfg_cluster[43]     = 4'd8;

    assign cfg_target[44]      = 16'd260;  // SHL_P5
    assign cfg_input_addr[44]  = 16'd260;
    assign cfg_output_addr[44] = 16'd289;
    assign cfg_c1_bus[44]      = {24'h0, 8'd23};
    assign cfg_c1_data[44]     = 32'h0002082c;
    assign cfg_c2_bus[44]      = {24'h0, 8'd31};
    assign cfg_c2_data[44]     = 32'd16;
    assign cfg_cluster[44]     = 4'd8;

    assign cfg_target[45]      = 16'd288;  // AND_PG5
    assign cfg_input_addr[45]  = 16'd288;
    assign cfg_output_addr[45] = 16'd290;
    assign cfg_c1_bus[45]      = {24'h0, 8'd23};
    assign cfg_c1_data[45]     = 32'h00000807;
    assign cfg_c2_bus[45]      = {24'h0, 8'd33};
    assign cfg_c2_data[45]     = 32'h0;
    assign cfg_cluster[45]     = 4'd9;

    assign cfg_target[46]      = 16'd289;  // AND_P5
    assign cfg_input_addr[46]  = 16'd289;
    assign cfg_output_addr[46] = 16'd9999;
    assign cfg_c1_bus[46]      = {24'h0, 8'd23};
    assign cfg_c1_data[46]     = 32'h00000807;
    assign cfg_c2_bus[46]      = {24'h0, 8'd33};
    assign cfg_c2_data[46]     = 32'h0;
    assign cfg_cluster[46]     = 4'd9;

    assign cfg_target[47]      = 16'd290;  // OR_G5
    assign cfg_input_addr[47]  = 16'd290;
    assign cfg_output_addr[47] = 16'd291;
    assign cfg_c1_bus[47]      = {24'h0, 8'd23};
    assign cfg_c1_data[47]     = 32'h00000824;
    assign cfg_c2_bus[47]      = {24'h0, 8'd33};
    assign cfg_c2_data[47]     = 32'h0;
    assign cfg_cluster[47]     = 4'd9;

    assign cfg_target[48]      = 16'd291;  // CARRY_SHL
    assign cfg_input_addr[48]  = 16'd291;
    assign cfg_output_addr[48] = 16'd292;
    assign cfg_c1_bus[48]      = {24'h0, 8'd23};
    assign cfg_c1_data[48]     = 32'h0002082c;
    assign cfg_c2_bus[48]      = {24'h0, 8'd31};
    assign cfg_c2_data[48]     = 32'd1;
    assign cfg_cluster[48]     = 4'd9;

    assign cfg_target[49]      = 16'd292;  // SUM_XOR
    assign cfg_input_addr[49]  = 16'd292;
    assign cfg_output_addr[49] = 16'd2000;
    assign cfg_c1_bus[49]      = {24'h0, 8'd23};
    assign cfg_c1_data[49]     = 32'h000008bc;
    assign cfg_c2_bus[49]      = {24'h0, 8'd33};
    assign cfg_c2_data[49]     = 32'h0;
    assign cfg_cluster[49]     = 4'd9;

    // Priming table
    assign prime_target[0] = 16'd1;
    assign prime_target[1] = 16'd2;
    assign prime_target[2] = 16'd3;
    assign prime_target[3] = 16'd4;
    assign prime_target[4] = 16'd33;
    assign prime_target[5] = 16'd34;
    assign prime_target[6] = 16'd35;
    assign prime_target[7] = 16'd65;
    assign prime_target[8] = 16'd66;
    assign prime_target[9] = 16'd68;
    assign prime_target[10] = 16'd96;
    assign prime_target[11] = 16'd97;
    assign prime_target[12] = 16'd98;
    assign prime_target[13] = 16'd128;
    assign prime_target[14] = 16'd129;
    assign prime_target[15] = 16'd131;
    assign prime_target[16] = 16'd132;
    assign prime_target[17] = 16'd160;
    assign prime_target[18] = 16'd161;
    assign prime_target[19] = 16'd164;
    assign prime_target[20] = 16'd192;
    assign prime_target[21] = 16'd194;
    assign prime_target[22] = 16'd195;
    assign prime_target[23] = 16'd196;
    assign prime_target[24] = 16'd224;
    assign prime_target[25] = 16'd227;
    assign prime_target[26] = 16'd228;
    assign prime_target[27] = 16'd257;
    assign prime_target[28] = 16'd258;
    assign prime_target[29] = 16'd259;
    assign prime_target[30] = 16'd260;
    assign prime_target[31] = 16'd291;
