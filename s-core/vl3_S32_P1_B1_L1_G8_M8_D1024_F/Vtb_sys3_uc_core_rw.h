// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtb_sys3.h for the primary calling header

#ifndef VERILATED_VTB_SYS3_UC_CORE_RW_H_
#define VERILATED_VTB_SYS3_UC_CORE_RW_H_  // guard

#include "verilated.h"
#include "verilated_timing.h"


class Vtb_sys3__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtb_sys3_uc_core_rw final : public VerilatedModule {
  public:

    // DESIGN SPECIFIC STATE
    // Anonymous structures to workaround compiler member-count bugs
    struct {
        VL_IN8(clk,0,0);
        VL_IN8(rst,0,0);
        VL_IN8(start,0,0);
        VL_IN8(lw_in,2,0);
        VL_OUT8(halted,0,0);
        VL_OUT8(trap,0,0);
        VL_OUT8(lw_cur,2,0);
        VL_OUT8(rw_en,0,0);
        VL_OUT8(d_we,0,0);
        CData/*2:0*/ __PVT__state;
        CData/*4:0*/ __PVT__k;
        CData/*2:0*/ __PVT__j;
        CData/*2:0*/ __PVT__lw_r;
        CData/*0:0*/ __PVT__cy;
        CData/*0:0*/ __PVT__nz;
        CData/*0:0*/ __PVT__f_eq;
        CData/*0:0*/ __PVT__f_lt;
        CData/*0:0*/ __PVT__f_ltu;
        CData/*0:0*/ __PVT__sgn;
        CData/*0:0*/ __PVT__halted_r;
        CData/*0:0*/ __PVT__trap_r;
        CData/*5:0*/ __PVT__nd;
        CData/*5:0*/ __PVT__wm1;
        CData/*6:0*/ __PVT__opc;
        CData/*4:0*/ __PVT__rs2;
        CData/*0:0*/ __PVT__is_sys;
        CData/*0:0*/ __PVT__sh_i;
        CData/*0:0*/ __PVT__is_shift;
        CData/*0:0*/ __PVT__is_sll;
        CData/*0:0*/ __PVT__is_cmp;
        CData/*0:0*/ __PVT__is_slt;
        CData/*0:0*/ __PVT__bad;
        CData/*0:0*/ __PVT__last_up;
        CData/*0:0*/ __PVT__cout;
        CData/*0:0*/ __PVT__nz_n;
        CData/*0:0*/ __PVT__we;
        CData/*0:0*/ __PVT__exec_done;
        CData/*5:0*/ __PVT__mlast;
        CData/*5:0*/ __PVT__jw;
        VL_OUT16(ra_addr,9,0);
        VL_OUT16(rb_addr,9,0);
        VL_OUT16(rw_addr,9,0);
        VL_IN(entry,31,0);
        VL_OUT(imem_addr,29,0);
        VL_IN(imem_data,31,0);
        VL_IN(ra_data,31,0);
        VL_IN(rb_data,31,0);
        VL_OUT(rw_data,31,0);
        VL_OUT(d_wdata,31,0);
        VL_IN(d_rdata,31,0);
        IData/*31:0*/ __PVT__pc;
        IData/*31:0*/ __PVT__ir;
        IData/*31:0*/ __PVT__addr;
        IData/*31:0*/ __PVT__imm_sr;
        IData/*31:0*/ __PVT__shamt_w;
        IData/*31:0*/ __PVT__mask;
        IData/*31:0*/ __PVT__imm;
        IData/*31:0*/ __PVT__a_val;
        IData/*31:0*/ __PVT__pc_rot;
        IData/*31:0*/ __PVT__imm_rot;
        IData/*31:0*/ __PVT__addr_ins;
        IData/*31:0*/ __PVT__xsh;
        IData/*31:0*/ __PVT__ysh;
        IData/*31:0*/ __PVT__wd;
    };
    struct {
        IData/*31:0*/ __VdfgTmp_he4828306__0;
        IData/*31:0*/ __VdfgTmp_h7980eff3__0;
        VL_OUT64(d_addr,34,0);
    };

    // INTERNAL VARIABLES
    Vtb_sys3__Syms* const vlSymsp;

    // CONSTRUCTORS
    Vtb_sys3_uc_core_rw(Vtb_sys3__Syms* symsp, const char* v__name);
    ~Vtb_sys3_uc_core_rw();
    VL_UNCOPYABLE(Vtb_sys3_uc_core_rw);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
