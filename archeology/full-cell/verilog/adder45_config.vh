// AUTO-GENERATED config table -- ladder-scheduled 85-cell adder.
// Fixed 2026-07-06: no address is ever shared by cells that would
// produce DIFFERENT outputs when triggered by the same event (a
// transform like RELAY_SHIFT sharing with a plain passthrough was
// the remaining hazard -- their simultaneous, same-cluster firing
// OR'd differing values together even though addressing looked
// individually correct). Verified: every shared address's listeners
// are ALL plain RELAY type producing identical output.

    assign cfg_target[0]      = 16'd0;  // G0
    assign cfg_input_addr[0]  = 16'd0;
    assign cfg_output_addr[0] = 16'd4;
    assign cfg_c1_bus[0]      = {24'h0, 8'd23};
    assign cfg_c1_data[0]     = 32'h00000807;
    assign cfg_c2_bus[0]      = {24'h0, 8'd33};
    assign cfg_c2_data[0]     = 32'h0;
    assign cfg_cluster[0]     = 8'd0;

    assign cfg_target[1]      = 16'd320;  // P0
    assign cfg_input_addr[1]  = 16'd0;
    assign cfg_output_addr[1] = 16'd321;
    assign cfg_c1_bus[1]      = {24'h0, 8'd23};
    assign cfg_c1_data[1]     = 32'h000008bc;
    assign cfg_c2_bus[1]      = {24'h0, 8'd33};
    assign cfg_c2_data[1]     = 32'h0;
    assign cfg_cluster[1]     = 8'd10;

    assign cfg_target[2]      = 16'd321;  // P0_anchor1
    assign cfg_input_addr[2]  = 16'd321;
    assign cfg_output_addr[2] = 16'd322;
    assign cfg_c1_bus[2]      = {24'h0, 8'd23};
    assign cfg_c1_data[2]     = 32'h0002082c;
    assign cfg_c2_bus[2]      = {24'h0, 8'd33};
    assign cfg_c2_data[2]     = 32'h0;
    assign cfg_cluster[2]     = 8'd10;

    assign cfg_target[3]      = 16'd322;  // P0_spine1
    assign cfg_input_addr[3]  = 16'd322;
    assign cfg_output_addr[3] = 16'd352;
    assign cfg_c1_bus[3]      = {24'h0, 8'd23};
    assign cfg_c1_data[3]     = 32'h0002082c;
    assign cfg_c2_bus[3]      = {24'h0, 8'd33};
    assign cfg_c2_data[3]     = 32'h0;
    assign cfg_cluster[3]     = 8'd10;

    assign cfg_target[4]      = 16'd352;  // P0_spine2
    assign cfg_input_addr[4]  = 16'd352;
    assign cfg_output_addr[4] = 16'd323;
    assign cfg_c1_bus[4]      = {24'h0, 8'd23};
    assign cfg_c1_data[4]     = 32'h0002082c;
    assign cfg_c2_bus[4]      = {24'h0, 8'd33};
    assign cfg_c2_data[4]     = 32'h0;
    assign cfg_cluster[4]     = 8'd11;

    assign cfg_target[5]      = 16'd323;  // P0_bridge3_to_AND_P1
    assign cfg_input_addr[5]  = 16'd323;
    assign cfg_output_addr[5] = 16'd384;
    assign cfg_c1_bus[5]      = {24'h0, 8'd23};
    assign cfg_c1_data[5]     = 32'h0002082c;
    assign cfg_c2_bus[5]      = {24'h0, 8'd33};
    assign cfg_c2_data[5]     = 32'h0;
    assign cfg_cluster[5]     = 8'd10;

    assign cfg_target[6]      = 16'd353;  // P0_bridge2_to_SHL_P1
    assign cfg_input_addr[6]  = 16'd352;
    assign cfg_output_addr[6] = 16'd356;
    assign cfg_c1_bus[6]      = {24'h0, 8'd23};
    assign cfg_c1_data[6]     = 32'h0002082c;
    assign cfg_c2_bus[6]      = {24'h0, 8'd33};
    assign cfg_c2_data[6]     = 32'h0;
    assign cfg_cluster[6]     = 8'd11;

    assign cfg_target[7]      = 16'd324;  // P0_bridge1_to_REQ1
    assign cfg_input_addr[7]  = 16'd322;
    assign cfg_output_addr[7] = 16'd354;
    assign cfg_c1_bus[7]      = {24'h0, 8'd23};
    assign cfg_c1_data[7]     = 32'h0002082c;
    assign cfg_c2_bus[7]      = {24'h0, 8'd33};
    assign cfg_c2_data[7]     = 32'h0;
    assign cfg_cluster[7]     = 8'd10;

    assign cfg_target[8]      = 16'd354;  // REQ1
    assign cfg_input_addr[8]  = 16'd354;
    assign cfg_output_addr[8] = 16'd355;
    assign cfg_c1_bus[8]      = {24'h0, 8'd23};
    assign cfg_c1_data[8]     = 32'h0002082c;
    assign cfg_c2_bus[8]      = {24'h0, 8'd33};
    assign cfg_c2_data[8]     = 32'h0;
    assign cfg_cluster[8]     = 8'd11;

    assign cfg_target[9]      = 16'd355;  // REQ1_anchor1
    assign cfg_input_addr[9]  = 16'd355;
    assign cfg_output_addr[9] = 16'd1;
    assign cfg_c1_bus[9]      = {24'h0, 8'd23};
    assign cfg_c1_data[9]     = 32'h0002082c;
    assign cfg_c2_bus[9]      = {24'h0, 8'd33};
    assign cfg_c2_data[9]     = 32'h0;
    assign cfg_cluster[9]     = 8'd11;

    assign cfg_target[10]      = 16'd1;  // REQ1_spine1
    assign cfg_input_addr[10]  = 16'd1;
    assign cfg_output_addr[10] = 16'd2;
    assign cfg_c1_bus[10]      = {24'h0, 8'd23};
    assign cfg_c1_data[10]     = 32'h0002082c;
    assign cfg_c2_bus[10]      = {24'h0, 8'd33};
    assign cfg_c2_data[10]     = 32'h0;
    assign cfg_cluster[10]     = 8'd0;

    assign cfg_target[11]      = 16'd2;  // REQ1_bridge2_to_SUM_XOR
    assign cfg_input_addr[11]  = 16'd2;
    assign cfg_output_addr[11] = 16'd288;
    assign cfg_c1_bus[11]      = {24'h0, 8'd23};
    assign cfg_c1_data[11]     = 32'h0002082c;
    assign cfg_c2_bus[11]      = {24'h0, 8'd33};
    assign cfg_c2_data[11]     = 32'h0;
    assign cfg_cluster[11]     = 8'd0;

    assign cfg_target[12]      = 16'd3;  // REQ1_bridge1_to_AND_PG1
    assign cfg_input_addr[12]  = 16'd1;
    assign cfg_output_addr[12] = 16'd64;
    assign cfg_c1_bus[12]      = {24'h0, 8'd23};
    assign cfg_c1_data[12]     = 32'h0002082c;
    assign cfg_c2_bus[12]      = {24'h0, 8'd33};
    assign cfg_c2_data[12]     = 32'h0;
    assign cfg_cluster[12]     = 8'd0;

    assign cfg_target[13]      = 16'd4;  // DELAY_G1
    assign cfg_input_addr[13]  = 16'd4;
    assign cfg_output_addr[13] = 16'd32;
    assign cfg_c1_bus[13]      = {24'h0, 8'd23};
    assign cfg_c1_data[13]     = 32'h0002082c;
    assign cfg_c2_bus[13]      = {24'h0, 8'd33};
    assign cfg_c2_data[13]     = 32'h0;
    assign cfg_cluster[13]     = 8'd0;

    assign cfg_target[14]      = 16'd32;  // DELAY_G1_anchor1
    assign cfg_input_addr[14]  = 16'd32;
    assign cfg_output_addr[14] = 16'd33;
    assign cfg_c1_bus[14]      = {24'h0, 8'd23};
    assign cfg_c1_data[14]     = 32'h0002082c;
    assign cfg_c2_bus[14]      = {24'h0, 8'd33};
    assign cfg_c2_data[14]     = 32'h0;
    assign cfg_cluster[14]     = 8'd1;

    assign cfg_target[15]      = 16'd33;  // DELAY_G1_spine1
    assign cfg_input_addr[15]  = 16'd33;
    assign cfg_output_addr[15] = 16'd34;
    assign cfg_c1_bus[15]      = {24'h0, 8'd23};
    assign cfg_c1_data[15]     = 32'h0002082c;
    assign cfg_c2_bus[15]      = {24'h0, 8'd33};
    assign cfg_c2_data[15]     = 32'h0;
    assign cfg_cluster[15]     = 8'd1;

    assign cfg_target[16]      = 16'd34;  // DELAY_G1_bridge2_to_OR_G1
    assign cfg_input_addr[16]  = 16'd34;
    assign cfg_output_addr[16] = 16'd65;
    assign cfg_c1_bus[16]      = {24'h0, 8'd23};
    assign cfg_c1_data[16]     = 32'h0002082c;
    assign cfg_c2_bus[16]      = {24'h0, 8'd33};
    assign cfg_c2_data[16]     = 32'h0;
    assign cfg_cluster[16]     = 8'd1;

    assign cfg_target[17]      = 16'd35;  // DELAY_G1_bridge1_to_SHL_G1
    assign cfg_input_addr[17]  = 16'd33;
    assign cfg_output_addr[17] = 16'd36;
    assign cfg_c1_bus[17]      = {24'h0, 8'd23};
    assign cfg_c1_data[17]     = 32'h0002082c;
    assign cfg_c2_bus[17]      = {24'h0, 8'd33};
    assign cfg_c2_data[17]     = 32'h0;
    assign cfg_cluster[17]     = 8'd1;

    assign cfg_target[18]      = 16'd36;  // SHL_G1
    assign cfg_input_addr[18]  = 16'd36;
    assign cfg_output_addr[18] = 16'd64;
    assign cfg_c1_bus[18]      = {24'h0, 8'd23};
    assign cfg_c1_data[18]     = 32'h0002082c;
    assign cfg_c2_bus[18]      = {24'h0, 8'd31};
    assign cfg_c2_data[18]     = 32'd1;
    assign cfg_cluster[18]     = 8'd1;

    assign cfg_target[19]      = 16'd64;  // AND_PG1
    assign cfg_input_addr[19]  = 16'd64;
    assign cfg_output_addr[19] = 16'd65;
    assign cfg_c1_bus[19]      = {24'h0, 8'd23};
    assign cfg_c1_data[19]     = 32'h00000807;
    assign cfg_c2_bus[19]      = {24'h0, 8'd33};
    assign cfg_c2_data[19]     = 32'h0;
    assign cfg_cluster[19]     = 8'd2;

    assign cfg_target[20]      = 16'd65;  // OR_G1
    assign cfg_input_addr[20]  = 16'd65;
    assign cfg_output_addr[20] = 16'd66;
    assign cfg_c1_bus[20]      = {24'h0, 8'd23};
    assign cfg_c1_data[20]     = 32'h00000824;
    assign cfg_c2_bus[20]      = {24'h0, 8'd33};
    assign cfg_c2_data[20]     = 32'h0;
    assign cfg_cluster[20]     = 8'd2;

    assign cfg_target[21]      = 16'd356;  // SHL_P1
    assign cfg_input_addr[21]  = 16'd356;
    assign cfg_output_addr[21] = 16'd384;
    assign cfg_c1_bus[21]      = {24'h0, 8'd23};
    assign cfg_c1_data[21]     = 32'h0002082c;
    assign cfg_c2_bus[21]      = {24'h0, 8'd31};
    assign cfg_c2_data[21]     = 32'd1;
    assign cfg_cluster[21]     = 8'd11;

    assign cfg_target[22]      = 16'd384;  // AND_P1
    assign cfg_input_addr[22]  = 16'd384;
    assign cfg_output_addr[22] = 16'd385;
    assign cfg_c1_bus[22]      = {24'h0, 8'd23};
    assign cfg_c1_data[22]     = 32'h00000807;
    assign cfg_c2_bus[22]      = {24'h0, 8'd33};
    assign cfg_c2_data[22]     = 32'h0;
    assign cfg_cluster[22]     = 8'd12;

    assign cfg_target[23]      = 16'd385;  // AND_P1_anchor1
    assign cfg_input_addr[23]  = 16'd385;
    assign cfg_output_addr[23] = 16'd386;
    assign cfg_c1_bus[23]      = {24'h0, 8'd23};
    assign cfg_c1_data[23]     = 32'h0002082c;
    assign cfg_c2_bus[23]      = {24'h0, 8'd33};
    assign cfg_c2_data[23]     = 32'h0;
    assign cfg_cluster[23]     = 8'd12;

    assign cfg_target[24]      = 16'd386;  // AND_P1_spine1
    assign cfg_input_addr[24]  = 16'd386;
    assign cfg_output_addr[24] = 16'd416;
    assign cfg_c1_bus[24]      = {24'h0, 8'd23};
    assign cfg_c1_data[24]     = 32'h0002082c;
    assign cfg_c2_bus[24]      = {24'h0, 8'd33};
    assign cfg_c2_data[24]     = 32'h0;
    assign cfg_cluster[24]     = 8'd12;

    assign cfg_target[25]      = 16'd416;  // AND_P1_spine2
    assign cfg_input_addr[25]  = 16'd416;
    assign cfg_output_addr[25] = 16'd387;
    assign cfg_c1_bus[25]      = {24'h0, 8'd23};
    assign cfg_c1_data[25]     = 32'h0002082c;
    assign cfg_c2_bus[25]      = {24'h0, 8'd33};
    assign cfg_c2_data[25]     = 32'h0;
    assign cfg_cluster[25]     = 8'd13;

    assign cfg_target[26]      = 16'd387;  // AND_P1_bridge3_to_AND_P2
    assign cfg_input_addr[26]  = 16'd387;
    assign cfg_output_addr[26] = 16'd420;
    assign cfg_c1_bus[26]      = {24'h0, 8'd23};
    assign cfg_c1_data[26]     = 32'h0002082c;
    assign cfg_c2_bus[26]      = {24'h0, 8'd33};
    assign cfg_c2_data[26]     = 32'h0;
    assign cfg_cluster[26]     = 8'd12;

    assign cfg_target[27]      = 16'd417;  // AND_P1_bridge2_to_SHL_P2
    assign cfg_input_addr[27]  = 16'd416;
    assign cfg_output_addr[27] = 16'd419;
    assign cfg_c1_bus[27]      = {24'h0, 8'd23};
    assign cfg_c1_data[27]     = 32'h0002082c;
    assign cfg_c2_bus[27]      = {24'h0, 8'd33};
    assign cfg_c2_data[27]     = 32'h0;
    assign cfg_cluster[27]     = 8'd13;

    assign cfg_target[28]      = 16'd388;  // AND_P1_bridge1_to_REQ2
    assign cfg_input_addr[28]  = 16'd386;
    assign cfg_output_addr[28] = 16'd418;
    assign cfg_c1_bus[28]      = {24'h0, 8'd23};
    assign cfg_c1_data[28]     = 32'h0002082c;
    assign cfg_c2_bus[28]      = {24'h0, 8'd33};
    assign cfg_c2_data[28]     = 32'h0;
    assign cfg_cluster[28]     = 8'd12;

    assign cfg_target[29]      = 16'd418;  // REQ2
    assign cfg_input_addr[29]  = 16'd418;
    assign cfg_output_addr[29] = 16'd99;
    assign cfg_c1_bus[29]      = {24'h0, 8'd23};
    assign cfg_c1_data[29]     = 32'h0002082c;
    assign cfg_c2_bus[29]      = {24'h0, 8'd33};
    assign cfg_c2_data[29]     = 32'h0;
    assign cfg_cluster[29]     = 8'd13;

    assign cfg_target[30]      = 16'd66;  // DELAY_G2
    assign cfg_input_addr[30]  = 16'd66;
    assign cfg_output_addr[30] = 16'd67;
    assign cfg_c1_bus[30]      = {24'h0, 8'd23};
    assign cfg_c1_data[30]     = 32'h0002082c;
    assign cfg_c2_bus[30]      = {24'h0, 8'd33};
    assign cfg_c2_data[30]     = 32'h0;
    assign cfg_cluster[30]     = 8'd2;

    assign cfg_target[31]      = 16'd67;  // DELAY_G2_anchor1
    assign cfg_input_addr[31]  = 16'd67;
    assign cfg_output_addr[31] = 16'd96;
    assign cfg_c1_bus[31]      = {24'h0, 8'd23};
    assign cfg_c1_data[31]     = 32'h0002082c;
    assign cfg_c2_bus[31]      = {24'h0, 8'd33};
    assign cfg_c2_data[31]     = 32'h0;
    assign cfg_cluster[31]     = 8'd2;

    assign cfg_target[32]      = 16'd96;  // DELAY_G2_spine1
    assign cfg_input_addr[32]  = 16'd96;
    assign cfg_output_addr[32] = 16'd68;
    assign cfg_c1_bus[32]      = {24'h0, 8'd23};
    assign cfg_c1_data[32]     = 32'h0002082c;
    assign cfg_c2_bus[32]      = {24'h0, 8'd33};
    assign cfg_c2_data[32]     = 32'h0;
    assign cfg_cluster[32]     = 8'd3;

    assign cfg_target[33]      = 16'd68;  // DELAY_G2_bridge2_to_OR_G2
    assign cfg_input_addr[33]  = 16'd68;
    assign cfg_output_addr[33] = 16'd100;
    assign cfg_c1_bus[33]      = {24'h0, 8'd23};
    assign cfg_c1_data[33]     = 32'h0002082c;
    assign cfg_c2_bus[33]      = {24'h0, 8'd33};
    assign cfg_c2_data[33]     = 32'h0;
    assign cfg_cluster[33]     = 8'd2;

    assign cfg_target[34]      = 16'd97;  // DELAY_G2_bridge1_to_SHL_G2
    assign cfg_input_addr[34]  = 16'd96;
    assign cfg_output_addr[34] = 16'd98;
    assign cfg_c1_bus[34]      = {24'h0, 8'd23};
    assign cfg_c1_data[34]     = 32'h0002082c;
    assign cfg_c2_bus[34]      = {24'h0, 8'd33};
    assign cfg_c2_data[34]     = 32'h0;
    assign cfg_cluster[34]     = 8'd3;

    assign cfg_target[35]      = 16'd98;  // SHL_G2
    assign cfg_input_addr[35]  = 16'd98;
    assign cfg_output_addr[35] = 16'd99;
    assign cfg_c1_bus[35]      = {24'h0, 8'd23};
    assign cfg_c1_data[35]     = 32'h0002082c;
    assign cfg_c2_bus[35]      = {24'h0, 8'd31};
    assign cfg_c2_data[35]     = 32'd2;
    assign cfg_cluster[35]     = 8'd3;

    assign cfg_target[36]      = 16'd99;  // AND_PG2
    assign cfg_input_addr[36]  = 16'd99;
    assign cfg_output_addr[36] = 16'd100;
    assign cfg_c1_bus[36]      = {24'h0, 8'd23};
    assign cfg_c1_data[36]     = 32'h00000807;
    assign cfg_c2_bus[36]      = {24'h0, 8'd33};
    assign cfg_c2_data[36]     = 32'h0;
    assign cfg_cluster[36]     = 8'd3;

    assign cfg_target[37]      = 16'd100;  // OR_G2
    assign cfg_input_addr[37]  = 16'd100;
    assign cfg_output_addr[37] = 16'd128;
    assign cfg_c1_bus[37]      = {24'h0, 8'd23};
    assign cfg_c1_data[37]     = 32'h00000824;
    assign cfg_c2_bus[37]      = {24'h0, 8'd33};
    assign cfg_c2_data[37]     = 32'h0;
    assign cfg_cluster[37]     = 8'd3;

    assign cfg_target[38]      = 16'd419;  // SHL_P2
    assign cfg_input_addr[38]  = 16'd419;
    assign cfg_output_addr[38] = 16'd420;
    assign cfg_c1_bus[38]      = {24'h0, 8'd23};
    assign cfg_c1_data[38]     = 32'h0002082c;
    assign cfg_c2_bus[38]      = {24'h0, 8'd31};
    assign cfg_c2_data[38]     = 32'd2;
    assign cfg_cluster[38]     = 8'd13;

    assign cfg_target[39]      = 16'd420;  // AND_P2
    assign cfg_input_addr[39]  = 16'd420;
    assign cfg_output_addr[39] = 16'd448;
    assign cfg_c1_bus[39]      = {24'h0, 8'd23};
    assign cfg_c1_data[39]     = 32'h00000807;
    assign cfg_c2_bus[39]      = {24'h0, 8'd33};
    assign cfg_c2_data[39]     = 32'h0;
    assign cfg_cluster[39]     = 8'd13;

    assign cfg_target[40]      = 16'd448;  // AND_P2_anchor1
    assign cfg_input_addr[40]  = 16'd448;
    assign cfg_output_addr[40] = 16'd449;
    assign cfg_c1_bus[40]      = {24'h0, 8'd23};
    assign cfg_c1_data[40]     = 32'h0002082c;
    assign cfg_c2_bus[40]      = {24'h0, 8'd33};
    assign cfg_c2_data[40]     = 32'h0;
    assign cfg_cluster[40]     = 8'd14;

    assign cfg_target[41]      = 16'd449;  // AND_P2_spine1
    assign cfg_input_addr[41]  = 16'd449;
    assign cfg_output_addr[41] = 16'd450;
    assign cfg_c1_bus[41]      = {24'h0, 8'd23};
    assign cfg_c1_data[41]     = 32'h0002082c;
    assign cfg_c2_bus[41]      = {24'h0, 8'd33};
    assign cfg_c2_data[41]     = 32'h0;
    assign cfg_cluster[41]     = 8'd14;

    assign cfg_target[42]      = 16'd450;  // AND_P2_spine2
    assign cfg_input_addr[42]  = 16'd450;
    assign cfg_output_addr[42] = 16'd480;
    assign cfg_c1_bus[42]      = {24'h0, 8'd23};
    assign cfg_c1_data[42]     = 32'h0002082c;
    assign cfg_c2_bus[42]      = {24'h0, 8'd33};
    assign cfg_c2_data[42]     = 32'h0;
    assign cfg_cluster[42]     = 8'd14;

    assign cfg_target[43]      = 16'd480;  // AND_P2_bridge3_to_AND_P3
    assign cfg_input_addr[43]  = 16'd480;
    assign cfg_output_addr[43] = 16'd483;
    assign cfg_c1_bus[43]      = {24'h0, 8'd23};
    assign cfg_c1_data[43]     = 32'h0002082c;
    assign cfg_c2_bus[43]      = {24'h0, 8'd33};
    assign cfg_c2_data[43]     = 32'h0;
    assign cfg_cluster[43]     = 8'd15;

    assign cfg_target[44]      = 16'd451;  // AND_P2_bridge2_to_SHL_P3
    assign cfg_input_addr[44]  = 16'd450;
    assign cfg_output_addr[44] = 16'd482;
    assign cfg_c1_bus[44]      = {24'h0, 8'd23};
    assign cfg_c1_data[44]     = 32'h0002082c;
    assign cfg_c2_bus[44]      = {24'h0, 8'd33};
    assign cfg_c2_data[44]     = 32'h0;
    assign cfg_cluster[44]     = 8'd14;

    assign cfg_target[45]      = 16'd452;  // AND_P2_bridge1_to_REQ3
    assign cfg_input_addr[45]  = 16'd449;
    assign cfg_output_addr[45] = 16'd481;
    assign cfg_c1_bus[45]      = {24'h0, 8'd23};
    assign cfg_c1_data[45]     = 32'h0002082c;
    assign cfg_c2_bus[45]      = {24'h0, 8'd33};
    assign cfg_c2_data[45]     = 32'h0;
    assign cfg_cluster[45]     = 8'd14;

    assign cfg_target[46]      = 16'd481;  // REQ3
    assign cfg_input_addr[46]  = 16'd481;
    assign cfg_output_addr[46] = 16'd161;
    assign cfg_c1_bus[46]      = {24'h0, 8'd23};
    assign cfg_c1_data[46]     = 32'h0002082c;
    assign cfg_c2_bus[46]      = {24'h0, 8'd33};
    assign cfg_c2_data[46]     = 32'h0;
    assign cfg_cluster[46]     = 8'd15;

    assign cfg_target[47]      = 16'd128;  // DELAY_G3
    assign cfg_input_addr[47]  = 16'd128;
    assign cfg_output_addr[47] = 16'd129;
    assign cfg_c1_bus[47]      = {24'h0, 8'd23};
    assign cfg_c1_data[47]     = 32'h0002082c;
    assign cfg_c2_bus[47]      = {24'h0, 8'd33};
    assign cfg_c2_data[47]     = 32'h0;
    assign cfg_cluster[47]     = 8'd4;

    assign cfg_target[48]      = 16'd129;  // DELAY_G3_anchor1
    assign cfg_input_addr[48]  = 16'd129;
    assign cfg_output_addr[48] = 16'd130;
    assign cfg_c1_bus[48]      = {24'h0, 8'd23};
    assign cfg_c1_data[48]     = 32'h0002082c;
    assign cfg_c2_bus[48]      = {24'h0, 8'd33};
    assign cfg_c2_data[48]     = 32'h0;
    assign cfg_cluster[48]     = 8'd4;

    assign cfg_target[49]      = 16'd130;  // DELAY_G3_spine1
    assign cfg_input_addr[49]  = 16'd130;
    assign cfg_output_addr[49] = 16'd131;
    assign cfg_c1_bus[49]      = {24'h0, 8'd23};
    assign cfg_c1_data[49]     = 32'h0002082c;
    assign cfg_c2_bus[49]      = {24'h0, 8'd33};
    assign cfg_c2_data[49]     = 32'h0;
    assign cfg_cluster[49]     = 8'd4;

    assign cfg_target[50]      = 16'd131;  // DELAY_G3_bridge2_to_OR_G3
    assign cfg_input_addr[50]  = 16'd131;
    assign cfg_output_addr[50] = 16'd162;
    assign cfg_c1_bus[50]      = {24'h0, 8'd23};
    assign cfg_c1_data[50]     = 32'h0002082c;
    assign cfg_c2_bus[50]      = {24'h0, 8'd33};
    assign cfg_c2_data[50]     = 32'h0;
    assign cfg_cluster[50]     = 8'd4;

    assign cfg_target[51]      = 16'd132;  // DELAY_G3_bridge1_to_SHL_G3
    assign cfg_input_addr[51]  = 16'd130;
    assign cfg_output_addr[51] = 16'd160;
    assign cfg_c1_bus[51]      = {24'h0, 8'd23};
    assign cfg_c1_data[51]     = 32'h0002082c;
    assign cfg_c2_bus[51]      = {24'h0, 8'd33};
    assign cfg_c2_data[51]     = 32'h0;
    assign cfg_cluster[51]     = 8'd4;

    assign cfg_target[52]      = 16'd160;  // SHL_G3
    assign cfg_input_addr[52]  = 16'd160;
    assign cfg_output_addr[52] = 16'd161;
    assign cfg_c1_bus[52]      = {24'h0, 8'd23};
    assign cfg_c1_data[52]     = 32'h0002082c;
    assign cfg_c2_bus[52]      = {24'h0, 8'd31};
    assign cfg_c2_data[52]     = 32'd4;
    assign cfg_cluster[52]     = 8'd5;

    assign cfg_target[53]      = 16'd161;  // AND_PG3
    assign cfg_input_addr[53]  = 16'd161;
    assign cfg_output_addr[53] = 16'd162;
    assign cfg_c1_bus[53]      = {24'h0, 8'd23};
    assign cfg_c1_data[53]     = 32'h00000807;
    assign cfg_c2_bus[53]      = {24'h0, 8'd33};
    assign cfg_c2_data[53]     = 32'h0;
    assign cfg_cluster[53]     = 8'd5;

    assign cfg_target[54]      = 16'd162;  // OR_G3
    assign cfg_input_addr[54]  = 16'd162;
    assign cfg_output_addr[54] = 16'd163;
    assign cfg_c1_bus[54]      = {24'h0, 8'd23};
    assign cfg_c1_data[54]     = 32'h00000824;
    assign cfg_c2_bus[54]      = {24'h0, 8'd33};
    assign cfg_c2_data[54]     = 32'h0;
    assign cfg_cluster[54]     = 8'd5;

    assign cfg_target[55]      = 16'd482;  // SHL_P3
    assign cfg_input_addr[55]  = 16'd482;
    assign cfg_output_addr[55] = 16'd483;
    assign cfg_c1_bus[55]      = {24'h0, 8'd23};
    assign cfg_c1_data[55]     = 32'h0002082c;
    assign cfg_c2_bus[55]      = {24'h0, 8'd31};
    assign cfg_c2_data[55]     = 32'd4;
    assign cfg_cluster[55]     = 8'd15;

    assign cfg_target[56]      = 16'd483;  // AND_P3
    assign cfg_input_addr[56]  = 16'd483;
    assign cfg_output_addr[56] = 16'd484;
    assign cfg_c1_bus[56]      = {24'h0, 8'd23};
    assign cfg_c1_data[56]     = 32'h00000807;
    assign cfg_c2_bus[56]      = {24'h0, 8'd33};
    assign cfg_c2_data[56]     = 32'h0;
    assign cfg_cluster[56]     = 8'd15;

    assign cfg_target[57]      = 16'd484;  // AND_P3_anchor1
    assign cfg_input_addr[57]  = 16'd484;
    assign cfg_output_addr[57] = 16'd512;
    assign cfg_c1_bus[57]      = {24'h0, 8'd23};
    assign cfg_c1_data[57]     = 32'h0002082c;
    assign cfg_c2_bus[57]      = {24'h0, 8'd33};
    assign cfg_c2_data[57]     = 32'h0;
    assign cfg_cluster[57]     = 8'd15;

    assign cfg_target[58]      = 16'd512;  // AND_P3_spine1
    assign cfg_input_addr[58]  = 16'd512;
    assign cfg_output_addr[58] = 16'd513;
    assign cfg_c1_bus[58]      = {24'h0, 8'd23};
    assign cfg_c1_data[58]     = 32'h0002082c;
    assign cfg_c2_bus[58]      = {24'h0, 8'd33};
    assign cfg_c2_data[58]     = 32'h0;
    assign cfg_cluster[58]     = 8'd16;

    assign cfg_target[59]      = 16'd513;  // AND_P3_spine2
    assign cfg_input_addr[59]  = 16'd513;
    assign cfg_output_addr[59] = 16'd514;
    assign cfg_c1_bus[59]      = {24'h0, 8'd23};
    assign cfg_c1_data[59]     = 32'h0002082c;
    assign cfg_c2_bus[59]      = {24'h0, 8'd33};
    assign cfg_c2_data[59]     = 32'h0;
    assign cfg_cluster[59]     = 8'd16;

    assign cfg_target[60]      = 16'd514;  // AND_P3_bridge3_to_AND_P4
    assign cfg_input_addr[60]  = 16'd514;
    assign cfg_output_addr[60] = 16'd546;
    assign cfg_c1_bus[60]      = {24'h0, 8'd23};
    assign cfg_c1_data[60]     = 32'h0002082c;
    assign cfg_c2_bus[60]      = {24'h0, 8'd33};
    assign cfg_c2_data[60]     = 32'h0;
    assign cfg_cluster[60]     = 8'd16;

    assign cfg_target[61]      = 16'd515;  // AND_P3_bridge2_to_SHL_P4
    assign cfg_input_addr[61]  = 16'd513;
    assign cfg_output_addr[61] = 16'd545;
    assign cfg_c1_bus[61]      = {24'h0, 8'd23};
    assign cfg_c1_data[61]     = 32'h0002082c;
    assign cfg_c2_bus[61]      = {24'h0, 8'd33};
    assign cfg_c2_data[61]     = 32'h0;
    assign cfg_cluster[61]     = 8'd16;

    assign cfg_target[62]      = 16'd516;  // AND_P3_bridge1_to_REQ4
    assign cfg_input_addr[62]  = 16'd512;
    assign cfg_output_addr[62] = 16'd544;
    assign cfg_c1_bus[62]      = {24'h0, 8'd23};
    assign cfg_c1_data[62]     = 32'h0002082c;
    assign cfg_c2_bus[62]      = {24'h0, 8'd33};
    assign cfg_c2_data[62]     = 32'h0;
    assign cfg_cluster[62]     = 8'd16;

    assign cfg_target[63]      = 16'd544;  // REQ4
    assign cfg_input_addr[63]  = 16'd544;
    assign cfg_output_addr[63] = 16'd196;
    assign cfg_c1_bus[63]      = {24'h0, 8'd23};
    assign cfg_c1_data[63]     = 32'h0002082c;
    assign cfg_c2_bus[63]      = {24'h0, 8'd33};
    assign cfg_c2_data[63]     = 32'h0;
    assign cfg_cluster[63]     = 8'd17;

    assign cfg_target[64]      = 16'd163;  // DELAY_G4
    assign cfg_input_addr[64]  = 16'd163;
    assign cfg_output_addr[64] = 16'd164;
    assign cfg_c1_bus[64]      = {24'h0, 8'd23};
    assign cfg_c1_data[64]     = 32'h0002082c;
    assign cfg_c2_bus[64]      = {24'h0, 8'd33};
    assign cfg_c2_data[64]     = 32'h0;
    assign cfg_cluster[64]     = 8'd5;

    assign cfg_target[65]      = 16'd164;  // DELAY_G4_anchor1
    assign cfg_input_addr[65]  = 16'd164;
    assign cfg_output_addr[65] = 16'd192;
    assign cfg_c1_bus[65]      = {24'h0, 8'd23};
    assign cfg_c1_data[65]     = 32'h0002082c;
    assign cfg_c2_bus[65]      = {24'h0, 8'd33};
    assign cfg_c2_data[65]     = 32'h0;
    assign cfg_cluster[65]     = 8'd5;

    assign cfg_target[66]      = 16'd192;  // DELAY_G4_spine1
    assign cfg_input_addr[66]  = 16'd192;
    assign cfg_output_addr[66] = 16'd193;
    assign cfg_c1_bus[66]      = {24'h0, 8'd23};
    assign cfg_c1_data[66]     = 32'h0002082c;
    assign cfg_c2_bus[66]      = {24'h0, 8'd33};
    assign cfg_c2_data[66]     = 32'h0;
    assign cfg_cluster[66]     = 8'd6;

    assign cfg_target[67]      = 16'd193;  // DELAY_G4_bridge2_to_OR_G4
    assign cfg_input_addr[67]  = 16'd193;
    assign cfg_output_addr[67] = 16'd224;
    assign cfg_c1_bus[67]      = {24'h0, 8'd23};
    assign cfg_c1_data[67]     = 32'h0002082c;
    assign cfg_c2_bus[67]      = {24'h0, 8'd33};
    assign cfg_c2_data[67]     = 32'h0;
    assign cfg_cluster[67]     = 8'd6;

    assign cfg_target[68]      = 16'd194;  // DELAY_G4_bridge1_to_SHL_G4
    assign cfg_input_addr[68]  = 16'd192;
    assign cfg_output_addr[68] = 16'd195;
    assign cfg_c1_bus[68]      = {24'h0, 8'd23};
    assign cfg_c1_data[68]     = 32'h0002082c;
    assign cfg_c2_bus[68]      = {24'h0, 8'd33};
    assign cfg_c2_data[68]     = 32'h0;
    assign cfg_cluster[68]     = 8'd6;

    assign cfg_target[69]      = 16'd195;  // SHL_G4
    assign cfg_input_addr[69]  = 16'd195;
    assign cfg_output_addr[69] = 16'd196;
    assign cfg_c1_bus[69]      = {24'h0, 8'd23};
    assign cfg_c1_data[69]     = 32'h0002082c;
    assign cfg_c2_bus[69]      = {24'h0, 8'd31};
    assign cfg_c2_data[69]     = 32'd8;
    assign cfg_cluster[69]     = 8'd6;

    assign cfg_target[70]      = 16'd196;  // AND_PG4
    assign cfg_input_addr[70]  = 16'd196;
    assign cfg_output_addr[70] = 16'd224;
    assign cfg_c1_bus[70]      = {24'h0, 8'd23};
    assign cfg_c1_data[70]     = 32'h00000807;
    assign cfg_c2_bus[70]      = {24'h0, 8'd33};
    assign cfg_c2_data[70]     = 32'h0;
    assign cfg_cluster[70]     = 8'd6;

    assign cfg_target[71]      = 16'd224;  // OR_G4
    assign cfg_input_addr[71]  = 16'd224;
    assign cfg_output_addr[71] = 16'd225;
    assign cfg_c1_bus[71]      = {24'h0, 8'd23};
    assign cfg_c1_data[71]     = 32'h00000824;
    assign cfg_c2_bus[71]      = {24'h0, 8'd33};
    assign cfg_c2_data[71]     = 32'h0;
    assign cfg_cluster[71]     = 8'd7;

    assign cfg_target[72]      = 16'd545;  // SHL_P4
    assign cfg_input_addr[72]  = 16'd545;
    assign cfg_output_addr[72] = 16'd546;
    assign cfg_c1_bus[72]      = {24'h0, 8'd23};
    assign cfg_c1_data[72]     = 32'h0002082c;
    assign cfg_c2_bus[72]      = {24'h0, 8'd31};
    assign cfg_c2_data[72]     = 32'd8;
    assign cfg_cluster[72]     = 8'd17;

    assign cfg_target[73]      = 16'd546;  // AND_P4
    assign cfg_input_addr[73]  = 16'd546;
    assign cfg_output_addr[73] = 16'd547;
    assign cfg_c1_bus[73]      = {24'h0, 8'd23};
    assign cfg_c1_data[73]     = 32'h00000807;
    assign cfg_c2_bus[73]      = {24'h0, 8'd33};
    assign cfg_c2_data[73]     = 32'h0;
    assign cfg_cluster[73]     = 8'd17;

    assign cfg_target[74]      = 16'd547;  // REQ5
    assign cfg_input_addr[74]  = 16'd547;
    assign cfg_output_addr[74] = 16'd258;
    assign cfg_c1_bus[74]      = {24'h0, 8'd23};
    assign cfg_c1_data[74]     = 32'h0002082c;
    assign cfg_c2_bus[74]      = {24'h0, 8'd33};
    assign cfg_c2_data[74]     = 32'h0;
    assign cfg_cluster[74]     = 8'd17;

    assign cfg_target[75]      = 16'd225;  // DELAY_G5
    assign cfg_input_addr[75]  = 16'd225;
    assign cfg_output_addr[75] = 16'd226;
    assign cfg_c1_bus[75]      = {24'h0, 8'd23};
    assign cfg_c1_data[75]     = 32'h0002082c;
    assign cfg_c2_bus[75]      = {24'h0, 8'd33};
    assign cfg_c2_data[75]     = 32'h0;
    assign cfg_cluster[75]     = 8'd7;

    assign cfg_target[76]      = 16'd226;  // DELAY_G5_anchor1
    assign cfg_input_addr[76]  = 16'd226;
    assign cfg_output_addr[76] = 16'd227;
    assign cfg_c1_bus[76]      = {24'h0, 8'd23};
    assign cfg_c1_data[76]     = 32'h0002082c;
    assign cfg_c2_bus[76]      = {24'h0, 8'd33};
    assign cfg_c2_data[76]     = 32'h0;
    assign cfg_cluster[76]     = 8'd7;

    assign cfg_target[77]      = 16'd227;  // DELAY_G5_spine1
    assign cfg_input_addr[77]  = 16'd227;
    assign cfg_output_addr[77] = 16'd256;
    assign cfg_c1_bus[77]      = {24'h0, 8'd23};
    assign cfg_c1_data[77]     = 32'h0002082c;
    assign cfg_c2_bus[77]      = {24'h0, 8'd33};
    assign cfg_c2_data[77]     = 32'h0;
    assign cfg_cluster[77]     = 8'd7;

    assign cfg_target[78]      = 16'd256;  // DELAY_G5_bridge2_to_OR_G5
    assign cfg_input_addr[78]  = 16'd256;
    assign cfg_output_addr[78] = 16'd259;
    assign cfg_c1_bus[78]      = {24'h0, 8'd23};
    assign cfg_c1_data[78]     = 32'h0002082c;
    assign cfg_c2_bus[78]      = {24'h0, 8'd33};
    assign cfg_c2_data[78]     = 32'h0;
    assign cfg_cluster[78]     = 8'd8;

    assign cfg_target[79]      = 16'd228;  // DELAY_G5_bridge1_to_SHL_G5
    assign cfg_input_addr[79]  = 16'd227;
    assign cfg_output_addr[79] = 16'd257;
    assign cfg_c1_bus[79]      = {24'h0, 8'd23};
    assign cfg_c1_data[79]     = 32'h0002082c;
    assign cfg_c2_bus[79]      = {24'h0, 8'd33};
    assign cfg_c2_data[79]     = 32'h0;
    assign cfg_cluster[79]     = 8'd7;

    assign cfg_target[80]      = 16'd257;  // SHL_G5
    assign cfg_input_addr[80]  = 16'd257;
    assign cfg_output_addr[80] = 16'd258;
    assign cfg_c1_bus[80]      = {24'h0, 8'd23};
    assign cfg_c1_data[80]     = 32'h0002082c;
    assign cfg_c2_bus[80]      = {24'h0, 8'd31};
    assign cfg_c2_data[80]     = 32'd16;
    assign cfg_cluster[80]     = 8'd8;

    assign cfg_target[81]      = 16'd258;  // AND_PG5
    assign cfg_input_addr[81]  = 16'd258;
    assign cfg_output_addr[81] = 16'd259;
    assign cfg_c1_bus[81]      = {24'h0, 8'd23};
    assign cfg_c1_data[81]     = 32'h00000807;
    assign cfg_c2_bus[81]      = {24'h0, 8'd33};
    assign cfg_c2_data[81]     = 32'h0;
    assign cfg_cluster[81]     = 8'd8;

    assign cfg_target[82]      = 16'd259;  // OR_G5
    assign cfg_input_addr[82]  = 16'd259;
    assign cfg_output_addr[82] = 16'd260;
    assign cfg_c1_bus[82]      = {24'h0, 8'd23};
    assign cfg_c1_data[82]     = 32'h00000824;
    assign cfg_c2_bus[82]      = {24'h0, 8'd33};
    assign cfg_c2_data[82]     = 32'h0;
    assign cfg_cluster[82]     = 8'd8;

    assign cfg_target[83]      = 16'd260;  // CARRY_SHL
    assign cfg_input_addr[83]  = 16'd260;
    assign cfg_output_addr[83] = 16'd288;
    assign cfg_c1_bus[83]      = {24'h0, 8'd23};
    assign cfg_c1_data[83]     = 32'h0002082c;
    assign cfg_c2_bus[83]      = {24'h0, 8'd31};
    assign cfg_c2_data[83]     = 32'd1;
    assign cfg_cluster[83]     = 8'd8;

    assign cfg_target[84]      = 16'd288;  // SUM_XOR
    assign cfg_input_addr[84]  = 16'd288;
    assign cfg_output_addr[84] = 16'd2000;
    assign cfg_c1_bus[84]      = {24'h0, 8'd23};
    assign cfg_c1_data[84]     = 32'h000008bc;
    assign cfg_c2_bus[84]      = {24'h0, 8'd33};
    assign cfg_c2_data[84]     = 32'h0;
    assign cfg_cluster[84]     = 8'd9;

    // Priming table
    assign prime_target[0] = 16'd321;
    assign prime_target[1] = 16'd322;
    assign prime_target[2] = 16'd352;
    assign prime_target[3] = 16'd323;
    assign prime_target[4] = 16'd353;
    assign prime_target[5] = 16'd324;
    assign prime_target[6] = 16'd354;
    assign prime_target[7] = 16'd355;
    assign prime_target[8] = 16'd1;
    assign prime_target[9] = 16'd2;
    assign prime_target[10] = 16'd3;
    assign prime_target[11] = 16'd4;
    assign prime_target[12] = 16'd32;
    assign prime_target[13] = 16'd33;
    assign prime_target[14] = 16'd34;
    assign prime_target[15] = 16'd35;
    assign prime_target[16] = 16'd36;
    assign prime_target[17] = 16'd356;
    assign prime_target[18] = 16'd385;
    assign prime_target[19] = 16'd386;
    assign prime_target[20] = 16'd416;
    assign prime_target[21] = 16'd387;
    assign prime_target[22] = 16'd417;
    assign prime_target[23] = 16'd388;
    assign prime_target[24] = 16'd418;
    assign prime_target[25] = 16'd66;
    assign prime_target[26] = 16'd67;
    assign prime_target[27] = 16'd96;
    assign prime_target[28] = 16'd68;
    assign prime_target[29] = 16'd97;
    assign prime_target[30] = 16'd98;
    assign prime_target[31] = 16'd419;
    assign prime_target[32] = 16'd448;
    assign prime_target[33] = 16'd449;
    assign prime_target[34] = 16'd450;
    assign prime_target[35] = 16'd480;
    assign prime_target[36] = 16'd451;
    assign prime_target[37] = 16'd452;
    assign prime_target[38] = 16'd481;
    assign prime_target[39] = 16'd128;
    assign prime_target[40] = 16'd129;
    assign prime_target[41] = 16'd130;
    assign prime_target[42] = 16'd131;
    assign prime_target[43] = 16'd132;
    assign prime_target[44] = 16'd160;
    assign prime_target[45] = 16'd482;
    assign prime_target[46] = 16'd484;
    assign prime_target[47] = 16'd512;
    assign prime_target[48] = 16'd513;
    assign prime_target[49] = 16'd514;
    assign prime_target[50] = 16'd515;
    assign prime_target[51] = 16'd516;
    assign prime_target[52] = 16'd544;
    assign prime_target[53] = 16'd163;
    assign prime_target[54] = 16'd164;
    assign prime_target[55] = 16'd192;
    assign prime_target[56] = 16'd193;
    assign prime_target[57] = 16'd194;
    assign prime_target[58] = 16'd195;
    assign prime_target[59] = 16'd545;
    assign prime_target[60] = 16'd547;
    assign prime_target[61] = 16'd225;
    assign prime_target[62] = 16'd226;
    assign prime_target[63] = 16'd227;
    assign prime_target[64] = 16'd256;
    assign prime_target[65] = 16'd228;
    assign prime_target[66] = 16'd257;
    assign prime_target[67] = 16'd260;
