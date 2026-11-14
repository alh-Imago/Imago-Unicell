// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_sys5.h for the primary calling header

#include "Vtb_sys5__pch.h"
#include "Vtb_sys5__Syms.h"
#include "Vtb_sys5_uc_core_v2s__W1.h"

void Vtb_sys5_uc_core_v2s__W1___ctor_var_reset(Vtb_sys5_uc_core_v2s__W1* vlSelf);

Vtb_sys5_uc_core_v2s__W1::Vtb_sys5_uc_core_v2s__W1(Vtb_sys5__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , vlSymsp{symsp}
 {
    // Reset structure values
    Vtb_sys5_uc_core_v2s__W1___ctor_var_reset(this);
}

void Vtb_sys5_uc_core_v2s__W1::__Vconfigure(bool first) {
    if (false && first) {}  // Prevent unused
}

Vtb_sys5_uc_core_v2s__W1::~Vtb_sys5_uc_core_v2s__W1() {
}
