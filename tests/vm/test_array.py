"""
test_array.py — UniCell and UniCellArray tests.

Updated for two-arrival model and configure_cell() API (2026-05-18).
Run with: python3 test_array.py  OR  pytest test_array.py
"""

import pytest
from unicell import UniCell
from unicell_array import UniCellArray
from gate_states import (
    GS_PASS, GS_NOT, GS_AND, GS_OR, GS_XOR, GS_XNOR,
    GS_LATCH_IN, GS_LOOP_BACK, GS_ONE_SHOT
)

M32 = 0xFFFFFFFF


# ── UniCell unit tests ────────────────────────────────────────────────────────

def test_unicell_not_truth_table():
    """NOT(A) = ~A for full 32-bit words (silicon-confirmed)."""
    for a_in in [0, 1, 0xDEADBEEF, 0xCAFEBABE]:
        c = UniCell(0x1000)
        c.configure(GS_NOT, input_addr=0x1000, output_addr=0x2000)
        c.receive(a_in); c.receive(a_in)
        assert c._output_buf is not None
        assert c._output_buf[1] == (~a_in) & M32, f"NOT({a_in:#x}) failed: got {c._output_buf[1]:#010x}"


def test_unicell_pass():
    """PASS(A) = A."""
    c = UniCell(0x1000)
    c.configure(GS_PASS, input_addr=0x1000, output_addr=0x2000)
    c.receive(0xDEADBEEF); c.receive(0xDEADBEEF)
    assert c._output_buf[1] == 0xDEADBEEF


def test_unicell_and_truth_table():
    """AND(A,B) truth table."""
    for a, b in [(0,0),(0,1),(1,0),(1,1)]:
        c = UniCell(0x1000)
        c.configure(GS_AND, input_addr=0x1000, output_addr=0x2000)
        c.receive(a); c.receive(b)
        assert c._output_buf[1] == (a & b), f"AND({a},{b}) failed"


def test_unicell_xnor_equality():
    """XNOR(A,A) = 0xFFFFFFFF (full 32-bit equality comparator)."""
    A = 0xDEADBEEF
    c = UniCell(0x1000)
    c.configure(GS_XNOR, input_addr=0x1000, output_addr=0x2000)
    c.receive(A); c.receive(A)
    assert c._output_buf[1] == M32, "XNOR(A,A) should be 0xFFFFFFFF"


def test_unicell_xnor_inequality():
    """XNOR(A,B≠A) != 0xFFFFFFFF."""
    c = UniCell(0x1000)
    c.configure(GS_XNOR, input_addr=0x1000, output_addr=0x2000)
    c.receive(0xDEADBEEF); c.receive(0xCAFEBABE)
    assert c._output_buf[1] != M32


def test_unicell_no_fire_on_first_arrival():
    """Two-arrival model: no output on first arrival."""
    c = UniCell(0x1000)
    c.configure(GS_NOT, input_addr=0x1000, output_addr=0x2000)
    c.receive(1)   # first arrival only
    assert c._output_buf is None, "Should not fire on first arrival"


def test_unicell_start_flag_gate():
    """Cell does not fire when disarmed."""
    c = UniCell(0x1000)
    c.configure(GS_NOT, input_addr=0x1000, output_addr=0x2000)
    c.freeze()
    c.receive(0); c.receive(0)
    assert c._output_buf is None, "Frozen cell should not fire"


def test_unicell_latch_in():
    """latch_in: single arrival fires, a_arrived stays set."""
    c = UniCell(0x1000)
    c.configure(GS_PASS | GS_LATCH_IN, input_addr=0x1000, output_addr=0x2000)
    c.receive(0xDEADBEEF); c.receive(0xDEADBEEF)   # prime
    assert c.a_arrived, "a_arrived should stay set with latch_in"
    c.drain_output_buf()
    c.receive(0xCAFEBABE)   # single arrival fires
    assert c._output_buf is not None, "latch_in: single arrival should fire"


def test_unicell_one_shot():
    """one_shot: fires exactly once then disarms."""
    c = UniCell(0x1000)
    c.configure(GS_NOT | GS_ONE_SHOT, input_addr=0x1000, output_addr=0x2000)
    c.receive(0); c.receive(0)
    assert c._output_buf is not None
    assert not c.start_flag, "start_flag should clear after one_shot"
    c.drain_output_buf()
    c.receive(0); c.receive(0)
    assert c._output_buf is None, "one_shot should not fire twice"


def test_unicell_loop_back():
    """loop_back: result feeds back as next a_data."""
    c = UniCell(0x1000)
    c.configure(GS_NOT | GS_LOOP_BACK, input_addr=0x1000, output_addr=0x2000)
    c.receive(0); c.receive(0)   # NOT(0) = 0xFFFFFFFF
    assert c._output_buf[1] == M32
    assert c.a_data == M32, "loop_back should update a_data"


def test_unicell_is_loopback_property():
    """is_loopback: True when output_address == input_address."""
    c = UniCell(0x1000)
    c.configure(GS_PASS, input_addr=0x1000, output_addr=0x1000)
    assert c.is_loopback


def test_unicell_32bit_not():
    """NOT operates on full 32-bit word (silicon-confirmed)."""
    A = 0xDEADBEEF
    c = UniCell(0x1000)
    c.configure(GS_NOT, input_addr=0x1000, output_addr=0x2000)
    c.receive(A); c.receive(A)
    assert c._output_buf[1] == (~A) & M32, "NOT should flip all 32 bits"


# ── Array tests ───────────────────────────────────────────────────────────────

def test_array_not_chain():
    """Two-cell NOT→PASS chain propagates correctly."""
    arr = UniCellArray(cell_count=16)
    cA = arr.allocate_cell()
    cB = arr.allocate_cell()
    arr.configure_cell(cA.address, GS_NOT,  input_addr=0x1000, output_addr=0x2000)
    arr.configure_cell(cB.address, GS_PASS, input_addr=0x2000, output_addr=0x3000)

    arr._injected[0x1000] = (0, 0)   # NOT(0) should give 1
    arr.tick(); arr.tick()            # first arrival fires cA
    arr._injected[0x1000] = (0, 0)
    arr.tick(); arr.tick()            # second arrival fires cA, output drains to cB
    arr.tick(); arr.tick()            # cB fires, drains to bus

    result = arr.bus.get(0x3000)
    assert result is not None, "Chain should produce output"
    assert result[0] == M32, f"NOT(0) chain: expected 0xFFFFFFFF, got {result[0]:#010x}"


def test_array_parallelism():
    """Multiple independent cells all fire in the same tick."""
    arr = UniCellArray(cell_count=200)
    N = 10
    for i in range(N):
        c = arr.allocate_cell()
        arr.configure_cell(c.address, GS_NOT,
                           input_addr=0x1000 + i,
                           output_addr=0x2000 + i)
        arr._injected[0x1000 + i] = (1, 0)   # NOT(1) = 0xFFFFFFFE

    arr.tick()   # first arrivals
    for i in range(N):
        arr._injected[0x1000 + i] = (1, 0)
    arr.tick()   # second arrivals — all cells fire
    arr.tick()   # drain

    for i in range(N):
        result = arr.bus.get(0x2000 + i)
        exp = (~1) & M32  # 0xFFFFFFFE
        assert result is not None and result[0] == exp, \
            f"Cell {i}: NOT(1) should be {exp:#010x}, got {result}"


def test_array_address_isolation():
    """Value at address X only received by cell listening on X."""
    arr = UniCellArray(cell_count=16)
    cX = arr.allocate_cell()
    cY = arr.allocate_cell()
    arr.configure_cell(cX.address, GS_PASS, input_addr=0xAAAA, output_addr=0xBBBB)
    arr.configure_cell(cY.address, GS_PASS, input_addr=0xCCCC, output_addr=0xDDDD)

    arr._injected[0xAAAA] = (1, 0)   # only cX should hear this
    arr.tick(); arr._injected[0xAAAA] = (1, 0); arr.tick(); arr.tick()

    assert arr.bus.get(0xBBBB) is not None, "cX should fire"
    assert arr.bus.get(0xDDDD) is None,     "cY should be silent"


def test_array_configure_cell_missing():
    """configure_cell returns False for missing cell address."""
    arr = UniCellArray(cell_count=4)
    ok = arr.configure_cell(0xDEAD, GS_NOT, 0x100, 0x200)
    assert ok == False


def test_array_defect_map():
    """Defective addresses skipped during allocation."""
    arr = UniCellArray(cell_count=16)
    arr.load_defect_map([0x0001, 0x0002, 0x0003])
    c = arr.allocate_cell()
    assert c.address == 0x0004, f"Expected 0x0004, got {c.address:#x}"


def test_array_status():
    """Status dict contains expected keys."""
    arr = UniCellArray(cell_count=16)
    arr.allocate_cell()
    status = arr.status()
    assert status["allocated_cells"] > 0
    assert status["defective_cells"] == 0


def test_array_32bit_xnor():
    """XNOR cell in array produces 0xFFFFFFFF for equal words."""
    arr = UniCellArray(cell_count=8)
    c = arr.allocate_cell()
    A = 0xDEADBEEF
    arr.configure_cell(c.address, GS_XNOR, input_addr=0x10, output_addr=0x20)

    arr._injected[0x10] = (A, 0)
    arr.tick()
    arr._injected[0x10] = (A, 0)
    arr.tick(); arr.tick()

    result = arr.bus.get(0x20)
    assert result is not None and result[0] == M32, \
        f"XNOR(A,A) in array: expected 0xFFFFFFFF, got {result}"


# ── Script mode ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    r = pytest.main([__file__, "-v"])
    sys.exit(r)
