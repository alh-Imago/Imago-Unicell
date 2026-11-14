# Verilated -*- Makefile -*-
# DESCRIPTION: Verilator output: Make include file with class lists
#
# This file lists generated Verilated files, for including in higher level makefiles.
# See Vtb_sys3.mk for the caller.

### Switches...
# C11 constructs required?  0/1 (always on now)
VM_C11 = 1
# Timing enabled?  0/1
VM_TIMING = 1
# Coverage output mode?  0/1 (from --coverage)
VM_COVERAGE = 0
# Parallel builds?  0/1 (from --output-split)
VM_PARALLEL_BUILDS = 1
# Tracing output mode?  0/1 (from --trace/--trace-fst)
VM_TRACE = 0
# Tracing output mode in VCD format?  0/1 (from --trace)
VM_TRACE_VCD = 0
# Tracing output mode in FST format?  0/1 (from --trace-fst)
VM_TRACE_FST = 0

### Object file lists...
# Generated module classes, fast-path, compile with highest optimization
VM_CLASSES_FAST += \
	Vtb_sys3 \
	Vtb_sys3___024root__DepSet_h7fa57171__0 \
	Vtb_sys3___024root__DepSet_h7fa57171__1 \
	Vtb_sys3___024root__DepSet_h7fa57171__2 \
	Vtb_sys3___024root__DepSet_hca8d9bc0__0 \
	Vtb_sys3_uc_core_rw__DepSet_h0bb727af__0 \
	Vtb_sys3_uc_core_rw__DepSet_h0bb727af__1 \
	Vtb_sys3_uc_core_rw__DepSet_h0bb727af__2 \
	Vtb_sys3__main \

# Generated module classes, non-fast-path, compile with low/medium optimization
VM_CLASSES_SLOW += \
	Vtb_sys3__ConstPool_0 \
	Vtb_sys3___024root__Slow \
	Vtb_sys3___024root__DepSet_h7fa57171__0__Slow \
	Vtb_sys3___024root__DepSet_hca8d9bc0__0__Slow \
	Vtb_sys3_uc_core_rw__Slow \
	Vtb_sys3_uc_core_rw__DepSet_h0bb727af__0__Slow \
	Vtb_sys3_uc_core_rw__DepSet_h0bb727af__1__Slow \
	Vtb_sys3_uc_core_rw__DepSet_h0bb727af__2__Slow \
	Vtb_sys3_uc_core_rw__DepSet_hb67fc57e__0__Slow \

# Generated support classes, fast-path, compile with highest optimization
VM_SUPPORT_FAST += \

# Generated support classes, non-fast-path, compile with low/medium optimization
VM_SUPPORT_SLOW += \
	Vtb_sys3__Syms \

# Global classes, need linked once per executable, fast-path, compile with highest optimization
VM_GLOBAL_FAST += \
	verilated \
	verilated_timing \
	verilated_threads \

# Global classes, need linked once per executable, non-fast-path, compile with low/medium optimization
VM_GLOBAL_SLOW += \


# Verilated -*- Makefile -*-
