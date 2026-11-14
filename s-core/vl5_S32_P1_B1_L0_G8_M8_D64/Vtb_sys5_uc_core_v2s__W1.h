// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtb_sys5.h for the primary calling header

#ifndef VERILATED_VTB_SYS5_UC_CORE_V2S__W1_H_
#define VERILATED_VTB_SYS5_UC_CORE_V2S__W1_H_  // guard

#include "verilated.h"
#include "verilated_timing.h"


class Vtb_sys5__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtb_sys5_uc_core_v2s__W1 final : public VerilatedModule {
  public:

    // DESIGN SPECIFIC STATE
    // Anonymous structures to workaround compiler member-count bugs
    struct {
        VL_IN8(clk,0,0);
        VL_IN8(rst,0,0);
        VL_IN8(start,0,0);
        VL_IN8(ce,0,0);
        VL_OUT8(halted,0,0);
        VL_OUT8(trap,0,0);
        VL_IN8(ra_data,0,0);
        VL_IN8(rb_data,0,0);
        VL_OUT8(rw_en,0,0);
        VL_OUT8(rw_data,0,0);
        VL_OUT8(d_we,0,0);
        VL_OUT8(d_wdata,0,0);
        VL_IN8(d_rdata,0,0);
        CData/*2:0*/ __PVT__state;
        CData/*4:0*/ __PVT__k;
        CData/*2:0*/ __PVT__j;
        CData/*0:0*/ __PVT__cy;
        CData/*0:0*/ __PVT__nz;
        CData/*0:0*/ __PVT__f_eq;
        CData/*0:0*/ __PVT__f_lt;
        CData/*0:0*/ __PVT__f_ltu;
        CData/*0:0*/ __PVT__sgn;
        CData/*4:0*/ __PVT__shamt_w;
        CData/*0:0*/ __PVT__halted_r;
        CData/*0:0*/ __PVT__trap_r;
        CData/*6:0*/ __PVT__opc;
        CData/*4:0*/ __PVT__rs2;
        CData/*0:0*/ __PVT__is_sys;
        CData/*0:0*/ __PVT__sh_i;
        CData/*0:0*/ __PVT__is_shift;
        CData/*0:0*/ __PVT__is_sll;
        CData/*0:0*/ __PVT__is_cmp;
        CData/*0:0*/ __PVT__is_slt;
        CData/*0:0*/ __PVT__bad;
        CData/*0:0*/ __PVT__shx;
        CData/*0:0*/ __PVT__last_up;
        CData/*0:0*/ __PVT__va;
        CData/*0:0*/ __PVT__vb;
        CData/*0:0*/ __PVT__a_val;
        CData/*0:0*/ __PVT__fill;
        CData/*0:0*/ __PVT__X;
        CData/*0:0*/ __PVT__Yr;
        CData/*0:0*/ __PVT__inv;
        CData/*1:0*/ __PVT__sum_c;
        CData/*0:0*/ __PVT__nz_n;
        CData/*0:0*/ __PVT__wd;
        CData/*0:0*/ __PVT__sll_dir;
        CData/*0:0*/ __PVT__exec_done;
        CData/*0:0*/ __Vlvbound_hb777f176__0;
        CData/*0:0*/ __VdfgTmp_h18c46dac__0;
        VL_OUT16(ra_addr,9,0);
        VL_OUT16(rb_addr,9,0);
        VL_OUT16(rw_addr,9,0);
        SData/*8:0*/ __PVT__ia;
        VL_IN(entry,31,0);
        VL_OUT(imem_addr,29,0);
        VL_IN(imem_data,31,0);
        IData/*31:0*/ __PVT__pc;
        IData/*31:0*/ __PVT__ir;
        IData/*31:0*/ __PVT__addr;
        IData/*31:0*/ __PVT__imm_sr;
        IData/*31:0*/ __PVT__imm;
        IData/*31:0*/ __PVT__pc_rot;
        IData/*31:0*/ __PVT__imm_rot;
    };
    struct {
        IData/*31:0*/ __PVT__pc_ins;
        IData/*31:0*/ __PVT__addr_ins;
        IData/*31:0*/ __VdfgTmp_h586768a0__0;
        IData/*31:0*/ __Vdly__pc;
        VL_OUT64(d_addr,34,0);
    };

    // INTERNAL VARIABLES
    Vtb_sys5__Syms* const vlSymsp;

    // CONSTRUCTORS
    Vtb_sys5_uc_core_v2s__W1(Vtb_sys5__Syms* symsp, const char* v__name);
    ~Vtb_sys5_uc_core_v2s__W1();
    VL_UNCOPYABLE(Vtb_sys5_uc_core_v2s__W1);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
