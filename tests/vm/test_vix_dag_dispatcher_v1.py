"""tests/vm/test_vix_dag_dispatcher_v1.py — points.md #779/#780: real
tests for the DAG dispatcher, confirming Alan's own "growing frontier"
architectural correction produces a correct, collision-free compiler
for every real case built and verified this session: plain chains,
genuine fan-out, commutative convergence, and non-commutative
convergence (which the dispatcher routes through SEQUENCER, per its
own honest, named STAGGER limitation).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from vix_dag_dispatcher_v1 import compile_dag, DagInstr, DagOperand  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _run(icm, dynamics, seq_orders, records, ticks=600, inject=None):
    grid = SuperGrid(records)
    for label, r, c in dynamics:
        cell = grid.cells[(r, c)]
        cell.ram_data_reg = (inject or {}).get(label, 1)
        cell.ram_data_valid = True
    for name, order in seq_orders.items():
        for rec in records:
            if rec.cell_id == f"main.pri_{name}":
                grid.cells[(rec.row, rec.col)].pri_seq_order = order
    for _ in range(ticks):
        grid.tick()
    return grid


def test_plain_chain_two_instructions():
    """#756's own shape, dispatched automatically: t1 = x + 5 (x
    dynamic), t2 = t1 + 10."""
    instrs = [
        DagInstr(name="t1", opcode="add", operands=[DagOperand(kind="dynamic"), DagOperand(kind="const", value=5)]),
        DagInstr(name="t2", opcode="add", operands=[DagOperand(kind="ref", ref_name="t1"),
                                                     DagOperand(kind="const", value=10)]),
    ]
    icm, positions, dynamics, seq_orders = compile_dag(instrs)
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = _run(icm, dynamics, seq_orders, records)
    assert grid.cells[positions["t1"]].adder_out_buffer == 6    # 1 + 5
    assert grid.cells[positions["t2"]].adder_out_buffer == 16   # 6 + 10


def test_isolated_commutative_convergence():
    """#751/#777's own PRIORITY shape, dispatched automatically: two
    independent leaves feeding one real add, no fan-out involved."""
    instrs = [
        DagInstr(name="t1", opcode="add", operands=[DagOperand(kind="dynamic"), DagOperand(kind="const", value=5)]),
        DagInstr(name="t2", opcode="add", operands=[DagOperand(kind="dynamic"), DagOperand(kind="const", value=10)]),
        DagInstr(name="t3", opcode="add", operands=[DagOperand(kind="ref", ref_name="t1"),
                                                     DagOperand(kind="ref", ref_name="t2")]),
    ]
    icm, positions, dynamics, seq_orders = compile_dag(instrs)
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = _run(icm, dynamics, seq_orders, records, inject={"t1_x": 1, "t2_x": 2})
    assert grid.cells[positions["t1"]].adder_out_buffer == 6    # 1 + 5
    assert grid.cells[positions["t2"]].adder_out_buffer == 12   # 2 + 10
    assert grid.cells[positions["t3"]].adder_out_buffer == 18   # 6 + 12


def test_fanout_plus_convergence_no_collisions():
    """points.md #779/#780: the real, central proof of Alan's own
    "growing frontier" correction. t1's own result feeds BOTH t2 (a
    plain chain) and t3 (genuine convergence with t2) -- the exact
    shape that repeatedly collided under the first, independently-
    placed-then-routed design. Confirmed here to compile and run
    correctly with zero real position collisions."""
    instrs = [
        DagInstr(name="t1", opcode="add", operands=[DagOperand(kind="dynamic"), DagOperand(kind="const", value=5)]),
        DagInstr(name="t2", opcode="add", operands=[DagOperand(kind="ref", ref_name="t1"),
                                                     DagOperand(kind="const", value=10)]),
        DagInstr(name="t3", opcode="add", operands=[DagOperand(kind="ref", ref_name="t1"),
                                                     DagOperand(kind="ref", ref_name="t2")]),
    ]
    icm, positions, dynamics, seq_orders = compile_dag(instrs)
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = _run(icm, dynamics, seq_orders, records)
    assert grid.cells[positions["t1"]].adder_out_buffer == 6    # 1 + 5
    assert grid.cells[positions["t2"]].adder_out_buffer == 16   # 6 + 10
    assert grid.cells[positions["t3"]].adder_out_buffer == 22   # 6 + 16


def test_non_commutative_convergence_uses_sequencer_correctly():
    """#773/#774/#777's own real chain of findings, dispatched
    automatically: subtract needs its own operand-identity guarantee.
    The dispatcher honestly routes this through SEQUENCER (not
    STAGGER, since natural branch lengths aren't guaranteed equal in
    this architecture) -- confirmed to correctly preserve t1 as the
    real minuend regardless of arrival order."""
    instrs = [
        DagInstr(name="t1", opcode="add", operands=[DagOperand(kind="dynamic"),
                                                     DagOperand(kind="const", value=100)]),
        DagInstr(name="t2", opcode="add", operands=[DagOperand(kind="dynamic"),
                                                     DagOperand(kind="const", value=3)]),
        DagInstr(name="t3", opcode="sub", operands=[DagOperand(kind="ref", ref_name="t1"),
                                                     DagOperand(kind="ref", ref_name="t2")]),
    ]
    icm, positions, dynamics, seq_orders = compile_dag(instrs)
    assert icm.check_connections() == []
    assert "t3" in seq_orders  # confirms SEQUENCER, not STAGGER, was chosen
    records, _ = icm.flatten()
    grid = _run(icm, dynamics, seq_orders, records, inject={"t1_x": 1, "t2_x": 2})
    assert grid.cells[positions["t1"]].adder_out_buffer == 101  # 1 + 100
    assert grid.cells[positions["t2"]].adder_out_buffer == 5    # 2 + 3
    t3_cell = grid.cells[positions["t3"]]
    assert t3_cell.adder_out_buffer == 96   # 101 - 5, t1 correctly the minuend
    assert t3_cell.adder_a_reg == 101       # t1, not t2, became "A"
