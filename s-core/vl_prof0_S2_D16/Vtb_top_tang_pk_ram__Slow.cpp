// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtb_top_tang.h for the primary calling header

#include "Vtb_top_tang__pch.h"
#include "Vtb_top_tang__Syms.h"
#include "Vtb_top_tang_pk_ram.h"

void Vtb_top_tang_pk_ram___ctor_var_reset(Vtb_top_tang_pk_ram* vlSelf);

Vtb_top_tang_pk_ram::Vtb_top_tang_pk_ram(Vtb_top_tang__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , vlSymsp{symsp}
 {
    // Reset structure values
    Vtb_top_tang_pk_ram___ctor_var_reset(this);
}

void Vtb_top_tang_pk_ram::__Vconfigure(bool first) {
    if (false && first) {}  // Prevent unused
}

Vtb_top_tang_pk_ram::~Vtb_top_tang_pk_ram() {
}
