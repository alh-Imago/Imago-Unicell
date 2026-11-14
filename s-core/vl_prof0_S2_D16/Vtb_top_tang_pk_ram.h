// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtb_top_tang.h for the primary calling header

#ifndef VERILATED_VTB_TOP_TANG_PK_RAM_H_
#define VERILATED_VTB_TOP_TANG_PK_RAM_H_  // guard

#include "verilated.h"
#include "verilated_timing.h"


class Vtb_top_tang__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtb_top_tang_pk_ram final : public VerilatedModule {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(we,0,0);
    VL_IN8(wa,4,0);
    VL_IN8(ra,4,0);
    VL_IN(wdata,31,0);
    VL_IN(wen,31,0);
    VL_OUT(rq,31,0);
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__0__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__1__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__2__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__3__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__4__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__5__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__6__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__7__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__8__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__9__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__10__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__11__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__12__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__13__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__14__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__15__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__16__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__17__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__18__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__19__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__20__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__21__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__22__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__23__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__24__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__25__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__26__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__27__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__28__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__29__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__30__KET____DOT__m;
    VlUnpacked<CData/*0:0*/, 32> __PVT__lane__BRA__31__KET____DOT__m;

    // INTERNAL VARIABLES
    Vtb_top_tang__Syms* const vlSymsp;

    // CONSTRUCTORS
    Vtb_top_tang_pk_ram(Vtb_top_tang__Syms* symsp, const char* v__name);
    ~Vtb_top_tang_pk_ram();
    VL_UNCOPYABLE(Vtb_top_tang_pk_ram);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
